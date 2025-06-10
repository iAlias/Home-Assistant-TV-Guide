
"""TV Guide Sensor (v2.0.1) – robust fallback for Italian EPG."""
from __future__ import annotations

from datetime import datetime, time, timedelta
import logging

import async_timeout
import voluptuous as vol
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_COUNTRY = "country"
DEFAULT_COUNTRY = "IT"
DEFAULT_NAME = "Guida TV"
ATTRIBUTION = "Dati forniti da TVmaze.com / TVIT / GitHub"

API_URL = "https://api.tvmaze.com/schedule?country={country}&date={date}"
# lista di fonti free EPG per l'Italia (prima valida vince)
TVIT_SOURCES = [
    "https://raw.githubusercontent.com/leica37/tvit/main/epg/it_full.json",
    "https://raw.githubusercontent.com/leica37/tvit/main/epg/it.json",
    "https://tvit.leicaflorianrobert.dev/epg/list.json",
]

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_COUNTRY, default=DEFAULT_COUNTRY): cv.string,
    }
)


async def async_setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    """Set up sensors."""
    name = config.get(CONF_NAME)
    country = config.get(CONF_COUNTRY, DEFAULT_COUNTRY).upper()
    session = async_get_clientsession(hass)

    add_entities(
        [TVNowSensor(name, country, session), TVPrimeSensor(name, country, session)],
        True,
    )


class TVGuideBaseSensor(SensorEntity):
    _attr_should_poll = True

    def __init__(self, base_name: str, country: str, session):
        self._base_name = base_name
        self._country = country
        self._session = session
        self._attrs: dict[str, str | dict] = {"attribution": ATTRIBUTION}
        self._schedule: list[dict] = []
        self._last_fetch_date = None

    @property
    def extra_state_attributes(self):
        return self._attrs

    # ------------- fetching helpers ---------------------------------
    async def _get_json(self, url: str, timeout: int = 15):
        async with async_timeout.timeout(timeout):
            resp = await self._session.get(url)
            if resp.status != 200:
                _LOGGER.debug("Url %s status %s", url, resp.status)
                return None
            try:
                return await resp.json()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("Invalid JSON from %s: %s", url, exc)
                return None

    async def _fetch_tvmaze(self, today):
        url = API_URL.format(country=self._country, date=today.isoformat())
        data = await self._get_json(url, 10)
        return data if isinstance(data, list) else []

    async def _fetch_tvit(self, today):
        """Loop through candidate endpoints until one works."""
        for url in TVIT_SOURCES:
            data = await self._get_json(url, 15)
            if not data:
                continue

            # If root is dict, try to get common keys
            if isinstance(data, dict):
                raw = (
                    data.get("epg")
                    or data.get("programmi")
                    or data.get("programs")
                    or data.get("list")
                    or []
                )
            elif isinstance(data, list):
                raw = data
            else:
                raw = []

            if not raw:
                continue

            # convert each item
            converted: list[dict] = []
            for item in raw:
                chan = item.get("channel") or item.get("name") or item.get("network")
                title = item.get("title") or item.get("programme") or item.get("show")
                start_iso = item.get("start") or item.get("start_iso") or item.get("start_time")
                stop_iso = item.get("stop") or item.get("end") or item.get("stop_time")
                if not (chan and title and start_iso and stop_iso):
                    continue
                try:
                    start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                    stop_dt = datetime.fromisoformat(stop_iso.replace("Z", "+00:00"))
                except ValueError:
                    continue
                start_dt_local = start_dt.astimezone()
                runtime = int((stop_dt - start_dt).total_seconds() / 60)
                converted.append(
                    {
                        "airtime": start_dt_local.strftime("%H:%M"),
                        "runtime": runtime,
                        "show": {"name": title, "network": {"name": chan}},
                    }
                )
            if converted:
                _LOGGER.info("EPG loaded from %s (%s voci)", url, len(converted))
                return converted

        _LOGGER.error("Nessuna sorgente EPG italiana valida trovata")
        return []

    async def _update_schedule(self):
        today = datetime.now().date()
        if self._last_fetch_date == today:
            return

        schedule = []
        try:
            schedule = await self._fetch_tvmaze(today)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("TVmaze fetch error: %s", exc)

        if not schedule and self._country == "IT":
            schedule = await self._fetch_tvit(today)

        self._schedule = schedule
        self._last_fetch_date = today

    # ------------- common helpers -----------------------------------
    @staticmethod
    def _parse_time(tstr):
        try:
            h, m = map(int, tstr.split(":"))
            return time(h, m)
        except Exception:
            return time(0, 0)

    def _channel(self, item):
        network = item["show"].get("network") or item["show"].get("webChannel") or {}
        return network.get("name", "Sconosciuto")

    def _is_on_air(self, now_dt, item):
        start_t = self._parse_time(item.get("airtime"))
        runtime = item.get("runtime") or 60
        start_dt = datetime.combine(now_dt.date(), start_t)
        return start_dt <= now_dt < start_dt + timedelta(minutes=runtime)


class TVNowSensor(TVGuideBaseSensor):
    _attr_icon = "mdi:television-classic"

    def __init__(self, base_name, country, session):
        super().__init__(base_name, country, session)
        self._attr_name = f"{base_name} - Ora in onda"
        self._attr_unique_id = f"tv_guide_now_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        now_dt = datetime.now()
        airing = [i for i in self._schedule if self._is_on_air(now_dt, i)]

        if airing:
            first = airing[0]
            self._attr_native_value = f"{first['show']['name']} ({self._channel(first)})"
            self._attrs["programmi_correnti"] = {
                self._channel(ep): ep["show"]["name"] for ep in airing
            }
        else:
            self._attr_native_value = "Nessun dato"
            self._attrs["programmi_correnti"] = {}


class TVPrimeSensor(TVGuideBaseSensor):
    _attr_icon = "mdi:movie-open"
    PRIME_TIME = time(20, 30)

    def __init__(self, base_name, country, session):
        super().__init__(base_name, country, session)
        self._attr_name = f"{base_name} - Prima serata"
        self._attr_unique_id = f"tv_guide_prime_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        prime = [
            i
            for i in self._schedule
            if self._parse_time(i.get("airtime")) >= self.PRIME_TIME
        ]
        prime.sort(key=lambda x: self._parse_time(x.get("airtime")))

        if prime:
            first = prime[0]
            self._attr_native_value = f"{first['show']['name']} ({self._channel(first)})"
        else:
            self._attr_native_value = "Nessun dato"

        self._attrs["prima_serata"] = {
            self._channel(ep): f"{ep['show']['name']} alle {ep.get('airtime', '--:--')}"
            for ep in prime
        }
