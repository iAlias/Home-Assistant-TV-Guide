
"""Multi‑source TV Guide Sensor.

Combina palinsesti da più endpoint pubblici (TVmaze, TVIT, IPTV‑org JSON).
Verifica coerenza tra fonti e restituisce solo i programmi presenti
in almeno 2/3 fonti (o un'unica fonte se le altre non coprono il canale).
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, date
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

import async_timeout
import aiohttp
import voluptuous as vol
from dateutil import parser as dtparser

from homeassistant.const import CONF_NAME
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_COUNTRY = "country"
DEFAULT_COUNTRY = "IT"
DEFAULT_NAME = "Guida TV"
MIN_AGREEMENT = 2  # quante fonti devono concordare

TM_API = "https://api.tvmaze.com/schedule?country={country}&date={date}"
TVIT_API = "https://raw.githubusercontent.com/leica37/tvit/main/epg/it_full.json"
IPTV_JSON = "https://iptv-org.github.io/api/guide/it.json"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_COUNTRY, default=DEFAULT_COUNTRY): cv.string,
    }
)


async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, _=None):
    name = config[CONF_NAME]
    country = config[CONF_COUNTRY].upper()
    session = async_get_clientsession(hass)
    sensors = [
        TVGMNowSensor(name, country, session),
        TVGMPrimeSensor(name, country, session),
    ]
    async_add_entities(sensors, True)


# ------------------------------------------------------------------------
# Source fetchers
# ------------------------------------------------------------------------

class BaseSource:
    """Abstract base class for a palinsesto source."""

    async def fetch(self, session: aiohttp.ClientSession, country: str, today: date) -> List[Dict]:
        raise NotImplementedError


class TVMazeSource(BaseSource):
    async def fetch(self, session, country, today):
        url = TM_API.format(country=country, date=today.isoformat())
        async with async_timeout.timeout(10):
            resp = await session.get(url)
            if resp.status != 200:
                _LOGGER.debug("TVMaze %s -> %s", url, resp.status)
                return []
            data = await resp.json(content_type=None)
            result = []
            for item in data:
                show = item.get("show", {})
                network = show.get("network") or show.get("webChannel") or {}
                result.append(
                    {
                        "channel": network.get("name"),
                        "title": show.get("name"),
                        "airtime": item.get("airtime"),
                        "runtime": item.get("runtime") or 60,
                    }
                )
            return result


class TVITSource(BaseSource):
    async def fetch(self, session, country, today):
        if country != "IT":
            return []
        async with async_timeout.timeout(15):
            resp = await session.get(TVIT_API)
            if resp.status != 200:
                return []
            j = await resp.json(content_type=None)
        raw = j.get("epg") or j.get("list") or j
        res = []
        for ep in raw:
            try:
                chan = ep["channel"]
                title = ep["title"]
                start_iso = ep["start"]
                stop_iso = ep["stop"]
                start_dt = dtparser.isoparse(start_iso).astimezone()
                runtime = int((dtparser.isoparse(stop_iso) - dtparser.isoparse(start_iso)).total_seconds() / 60)
                res.append(
                    {
                        "channel": chan,
                        "title": title,
                        "airtime": start_dt.strftime("%H:%M"),
                        "runtime": runtime,
                    }
                )
            except Exception:
                continue
        return res


class IPTVOrgSource(BaseSource):
    async def fetch(self, session, country, today):
        if country != "IT":
            return []
        async with async_timeout.timeout(15):
            resp = await session.get(IPTV_JSON)
            if resp.status != 200:
                return []
            data = await resp.json(content_type=None)
        res = []
        for ch in data:
            chan = ch.get("name")
            for pr in ch.get("programs", []):
                try:
                    title = pr["title"]
                    start = dtparser.isoparse(pr["start"]).astimezone()
                    runtime = int((dtparser.isoparse(pr["stop"]) - dtparser.isoparse(pr["start"])).total_seconds() / 60)
                    res.append(
                        {
                            "channel": chan,
                            "title": title,
                            "airtime": start.strftime("%H:%M"),
                            "runtime": runtime,
                        }
                    )
                except Exception:
                    continue
        return res


SOURCES = [TVMazeSource(), TVITSource(), IPTVOrgSource()]

# ------------------------------------------------------------------------
# Consensus builder
# ------------------------------------------------------------------------

def build_consensus(lists: List[List[Dict]]) -> List[Dict]:
    """Return items present in at least MIN_AGREEMENT sources.

    Key for grouping: (channel, airtime)
    """
    buckets: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    info: Dict[Tuple[str, str], Dict] = {}
    for source_idx, lst in enumerate(lists):
        for item in lst:
            key = (item.get("channel"), item.get("airtime"))
            if not key[0] or not key[1]:
                continue
            buckets[key][item.get("title")] += 1
            # store detail once
            info.setdefault(key, item)

    consensus = []
    for key, counter in buckets.items():
        # choose the most common title
        title, votes = counter.most_common(1)[0]
        if votes >= MIN_AGREEMENT or len(counter) == 1:
            itm = info[key].copy()
            itm["title"] = title
            consensus.append(itm)
    return consensus


# ------------------------------------------------------------------------
# Sensors
# ------------------------------------------------------------------------

class TVGuideMultiBase(SensorEntity):
    _attr_should_poll = True

    def __init__(self, name: str, country: str, session: aiohttp.ClientSession):
        self._name_base = name
        self._country = country
        self._session = session
        self._schedule: List[Dict] = []
        self._fetched_date: date | None = None
        self._attr_extra_state_attributes = {}
        self._attr_icon = "mdi:television"
        self._attr_native_value = None

    async def _update_schedule(self):
        today = datetime.now().date()
        if self._fetched_date == today:
            return
        # fetch in parallel
        fetched_lists = await asyncio.gather(
            *[src.fetch(self._session, self._country, today) for src in SOURCES],
            return_exceptions=True,
        )
        cleaned = []
        for idx, lst in enumerate(fetched_lists):
            if isinstance(lst, Exception):
                _LOGGER.debug("Source %s error: %s", SOURCES[idx].__class__.__name__, lst)
                continue
            cleaned.append(lst)
        self._schedule = build_consensus(cleaned)
        self._fetched_date = today

    # helpers
    @staticmethod
    def _parse_time(tstr: str) -> time:
        h, m = map(int, tstr.split(":"))
        return time(h, m)

    def _now_list(self):
        now_dt = datetime.now()
        return [
            it for it in self._schedule
            if self._is_on_air(now_dt, it)
        ]

    def _is_on_air(self, now_dt: datetime, item: Dict) -> bool:
        start_t = self._parse_time(item["airtime"])
        runtime = item["runtime"]
        start_dt = datetime.combine(now_dt.date(), start_t)
        return start_dt <= now_dt < start_dt + timedelta(minutes=runtime)

    def _prime_time_list(self):
        return [
            it for it in self._schedule if self._parse_time(it["airtime"]) >= time(20, 30)
        ]


import asyncio

class TVGMNowSensor(TVGuideMultiBase):
    _attr_icon = "mdi:television-play"

    def __init__(self, name, country, session):
        super().__init__(name, country, session)
        self._attr_name = f"{name} - Ora in onda"
        self._attr_unique_id = f"tvgm_now_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        nowlist = self._now_list()
        if nowlist:
            first = nowlist[0]
            self._attr_native_value = f"{first['title']} ({first['channel']})"
            self._attr_extra_state_attributes = {
                "programmi_correnti": {it["channel"]: it["title"] for it in nowlist},
                "fonte": "multi",
            }
        else:
            self._attr_native_value = "Nessun dato"
            self._attr_extra_state_attributes = {
                "programmi_correnti": {},
                "fonte": "multi",
            }


class TVGMPrimeSensor(TVGuideMultiBase):
    _attr_icon = "mdi:movie-open"

    def __init__(self, name, country, session):
        super().__init__(name, country, session)
        self._attr_name = f"{name} - Prima serata"
        self._attr_unique_id = f"tvgm_prime_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        primelist = self._prime_time_list()
        primelist.sort(key=lambda x: TVGuideMultiBase._parse_time(x["airtime"]))
        if primelist:
            first = primelist[0]
            self._attr_native_value = f"{first['title']} ({first['channel']})"
        else:
            self._attr_native_value = "Nessun dato"

        self._attr_extra_state_attributes = {
            "prima_serata": {
                it["channel"]: f"{it['title']} alle {it['airtime']}" for it in primelist
            },
            "fonte": "multi",
        }
