"""TV Guide Multi-Source.

Versione che utilizza l'API gratuita di TVmaze per ottenere il palinsesto
odierno, evitando qualsiasi scraping di siti web.

Per ogni canale vengono popolati due sensori:
    sensor.guida_tv_ora_in_onda
    sensor.guida_tv_prima_serata
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Dict, List

import aiohttp
import async_timeout
import voluptuous as vol
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
CONF_COUNTRY = "country"
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Guida TV"

API_URL = "https://api.tvmaze.com/schedule?country={country}&date={date}"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_COUNTRY, default="IT"): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    """Configura i sensori."""
    name = config.get(CONF_NAME)
    country = config.get(CONF_COUNTRY)
    session = async_get_clientsession(hass)

    async_add_entities(
        [TvMazeNowSensor(name, country, session), TvMazePrimeSensor(name, country, session)], True
    )


# -----------------------------------------------------------------------------


async def _fetch_schedule(session: aiohttp.ClientSession, country: str) -> list | None:
    """Scarica il palinsesto giornaliero da TVmaze."""
    today = datetime.now().strftime("%Y-%m-%d")
    url = API_URL.format(country=country, date=today)
    try:
        async with async_timeout.timeout(15):
            async with session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("TVmaze: %s status %s", url, resp.status)
                    return None
                return await resp.json()
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Errore fetching %s: %s", url, err)
        return None


def _parse_tvmaze(data: list) -> tuple[Dict[str, str], Dict[str, str]]:
    """Ritorna due mapping {canale: titolo} per ora e prima serata."""
    now = datetime.now(tz=ZoneInfo("Europe/Rome"))
    prime_start = now.replace(hour=21, minute=0, second=0, microsecond=0)
    now_map: Dict[str, str] = {}
    prime_map: Dict[str, str] = {}

    for item in data:
        show = item.get("show") or {}
        network = show.get("network")
        if not network:
            continue
        channel = network.get("name")
        country = network.get("country", {})
        tz_name = country.get("timezone", "UTC")
        start = datetime.fromisoformat(item["airstamp"]).astimezone(ZoneInfo(tz_name))
        runtime = item.get("runtime") or 0
        end = start + timedelta(minutes=runtime)

        if start <= now < end:
            now_map[channel] = item.get("name", "")

        if start >= prime_start and channel not in prime_map:
            prime_map[channel] = item.get("name", "")

    return now_map, prime_map


async def get_now_and_prime(session, country: str) -> tuple[Dict[str, str], Dict[str, str]]:
    """Ritorna i mapping per ora e prima serata da TVmaze."""
    data = await _fetch_schedule(session, country)
    if not data:
        return {}, {}
    return _parse_tvmaze(data)


# -----------------------------------------------------------------------------


class _TvMazeBase(SensorEntity):
    """Base comune; scarica una sola volta al giorno."""

    _attr_should_poll = True
    _cache_date: str | None = None
    _cache_now: Dict[str, str] = {}
    _cache_prime: Dict[str, str] = {}
    _session: aiohttp.ClientSession

    _country: str

    async def _ensure_cache(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self._cache_date == today:
            return
        self._cache_now, self._cache_prime = await get_now_and_prime(
            self._session, self._country
        )
        self._cache_date = today


class TvMazeNowSensor(_TvMazeBase):
    """Programmi in onda adesso."""

    _attr_icon = "mdi:television-play"

    def __init__(self, base_name: str, country: str, session):
        self._attr_name = f"{base_name} - Ora in onda"
        self._attr_unique_id = "tvguide_tvmaze_now"
        self._session = session
        self._country = country

    async def async_update(self):
        await self._ensure_cache()
        self._attr_native_value = (
            next(iter(self._cache_now.values())) if self._cache_now else "Nessun dato"
        )
        self._attr_extra_state_attributes = {
            "programmi_correnti": self._cache_now,
            "fonte": "tvmaze.com",
        }


class TvMazePrimeSensor(_TvMazeBase):
    """Programmi di prima serata (Stasera)."""

    _attr_icon = "mdi:movie-open"

    def __init__(self, base_name: str, country: str, session):
        self._attr_name = f"{base_name} - Prima serata"
        self._attr_unique_id = "tvguide_tvmaze_prime"
        self._session = session
        self._country = country

    async def async_update(self):
        await self._ensure_cache()
        self._attr_native_value = (
            next(iter(self._cache_prime.values())) if self._cache_prime else "Nessun dato"
        )
        self._attr_extra_state_attributes = {
            "prima_serata": self._cache_prime,
            "fonte": "tvmaze.com",
        }
