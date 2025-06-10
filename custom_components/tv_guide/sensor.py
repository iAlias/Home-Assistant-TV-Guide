"""TV Guide Multi-Source 3.1.0 — scraper “TV Sorrisi e Canzoni”.

Preleva due pagine HTML:
    • https://www.sorrisi.com/guidatv/ora-in-tv/
    • https://www.sorrisi.com/guidatv/stasera-in-tv/

Estrae (canale, titolo) e popola i sensori:
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
from bs4 import BeautifulSoup

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Guida TV"

URL_NOW = "https://www.sorrisi.com/guidatv/ora-in-tv/"
URL_PRIME = "https://www.sorrisi.com/guidatv/stasera-in-tv/"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string}
)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    """Configura i sensori."""
    name = config.get(CONF_NAME)
    session = async_get_clientsession(hass)

    async_add_entities(
        [SorrisiNowSensor(name, session), SorrisiPrimeSensor(name, session)], True
    )


# -----------------------------------------------------------------------------


async def _fetch_page(session: aiohttp.ClientSession, url: str) -> str | None:
    """Download semplice con timeout e log."""
    try:
        async with async_timeout.timeout(15):
            resp = await session.get(url)
            if resp.status != 200:
                _LOGGER.warning("Sorrisi: %s status %s", url, resp.status)
                return None
            return await resp.text()
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Errore fetching %s: %s", url, err)
        return None


def _parse_sorrisi(html: str) -> Dict[str, str]:
    """Ritorna {canale: titolo} dal markup di Sorrisi e Canzoni."""
    soup = BeautifulSoup(html, "html.parser")
    mapping: Dict[str, str] = {}

    # Ogni canale è in <h3> col titolo del programma subito dopo
    # il markup attuale è: <h3>Rai 1</h3><p class="title">Il Paradiso...</p>
    for h in soup.find_all("h3"):
        channel = h.get_text(strip=True)
        # Cerca l'elemento successivo che contenga il titolo
        nxt = h.find_next(lambda tag: tag.name in ("h4", "p") and tag.get_text(strip=True))
        if channel and nxt:
            title = nxt.get_text(strip=True)
            mapping[channel] = title

    _LOGGER.debug("Estratti %s programmi", len(mapping))
    return mapping


async def get_now_and_prime(session) -> tuple[Dict[str, str], Dict[str, str]]:
    """Scarica ed estrae le due sezioni; ritorna (ora, stasera)."""
    html_now, html_prime = await asyncio.gather(
        _fetch_page(session, URL_NOW), _fetch_page(session, URL_PRIME)
    )
    now_map = _parse_sorrisi(html_now) if html_now else {}
    prime_map = _parse_sorrisi(html_prime) if html_prime else {}
    return now_map, prime_map


# -----------------------------------------------------------------------------


class _SorrisiBase(SensorEntity):
    """Base comune; scarica una sola volta al giorno."""

    _attr_should_poll = True
    _cache_date: str | None = None
    _cache_now: Dict[str, str] = {}
    _cache_prime: Dict[str, str] = {}
    _session: aiohttp.ClientSession

    async def _ensure_cache(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self._cache_date == today:
            return
        self._cache_now, self._cache_prime = await get_now_and_prime(self._session)
        self._cache_date = today


class SorrisiNowSensor(_SorrisiBase):
    """Programmi in onda adesso."""

    _attr_icon = "mdi:television-play"

    def __init__(self, base_name: str, session):
        self._attr_name = f"{base_name} - Ora in onda"
        self._attr_unique_id = "tvguide_sorrisi_now"
        self._session = session

    async def async_update(self):
        await self._ensure_cache()
        self._attr_native_value = (
            next(iter(self._cache_now.values())) if self._cache_now else "Nessun dato"
        )
        self._attr_extra_state_attributes = {
            "programmi_correnti": self._cache_now,
            "fonte": "sorrisi.com",
        }


class SorrisiPrimeSensor(_SorrisiBase):
    """Programmi di prima serata (Stasera)."""

    _attr_icon = "mdi:movie-open"

    def __init__(self, base_name: str, session):
        self._attr_name = f"{base_name} - Prima serata"
        self._attr_unique_id = "tvguide_sorrisi_prime"
        self._session = session

    async def async_update(self):
        await self._ensure_cache()
        self._attr_native_value = (
            next(iter(self._cache_prime.values())) if self._cache_prime else "Nessun dato"
        )
        self._attr_extra_state_attributes = {
            "prima_serata": self._cache_prime,
            "fonte": "sorrisi.com",
        }
