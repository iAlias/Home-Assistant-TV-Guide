
"""Sensori Guida TV per Home Assistant basati sull'API pubblica di TVmaze."""
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
ATTRIBUTION = "Dati forniti da TVmaze.com"

API_URL = "https://api.tvmaze.com/schedule?country={country}&date={date}"

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_COUNTRY, default=DEFAULT_COUNTRY): cv.string,
    }
)


async def async_setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    """Configura i sensori."""
    name = config.get(CONF_NAME)
    country = config.get(CONF_COUNTRY, DEFAULT_COUNTRY).upper()
    session = async_get_clientsession(hass)

    add_entities(
        [
            TVNowSensor(name, country, session),
            TVPrimeSensor(name, country, session),
        ],
        True,
    )


class TVGuideBaseSensor(SensorEntity):
    """Classe base per i sensori Guida TV."""

    _attr_should_poll = True

    def __init__(self, base_name: str, country: str, session):
        self._base_name = base_name
        self._country = country
        self._session = session
        self._attrs: dict[str, str | dict] = {"attribution": ATTRIBUTION}
        self._schedule: list[dict] = []
        self._last_fetch_date: datetime.date | None = None
        self._state: str | None = None

    @property
    def extra_state_attributes(self):
        return self._attrs

    async def _update_schedule(self):
        today = datetime.now().date()
        if self._last_fetch_date == today:
            return

        url = API_URL.format(country=self._country, date=today.isoformat())

        try:
            async with async_timeout.timeout(10):
                resp = await self._session.get(url)
                if resp.status != 200:
                    _LOGGER.warning(
                        "TVmaze ha risposto %s per %s – paese forse non supportato",
                        resp.status,
                        self._country,
                    )
                    self._schedule = []
                    self._last_fetch_date = today
                    return

                data = await resp.json()
                if not isinstance(data, list):
                    _LOGGER.error("Risposta inattesa da TVmaze: %s", str(data)[:120])
                    data = []

                self._schedule = data
                self._last_fetch_date = today

        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Errore nel recupero del palinsesto: %s", err)

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_time(tstr: str | None) -> time:
        if not tstr:
            return time(0, 0)
        hours, minutes = map(int, tstr.split(":"))
        return time(hours, minutes)

    def _channel(self, item):
        network = item["show"].get("network") or item["show"].get("webChannel") or {}
        return network.get("name", "Sconosciuto")

    def _is_on_air(self, now_dt: datetime, item) -> bool:
        start_t = self._parse_time(item.get("airtime"))
        runtime = item.get("runtime") or 60
        start_dt = datetime.combine(now_dt.date(), start_t)
        end_dt = start_dt + timedelta(minutes=runtime)
        return start_dt <= now_dt < end_dt


class TVNowSensor(TVGuideBaseSensor):
    """Programmi in onda adesso."""

    _attr_icon = "mdi:television-classic"

    def __init__(self, base_name: str, country: str, session):
        super().__init__(base_name, country, session)
        self._attr_name = f"{base_name} - Ora in onda"
        self._attr_unique_id = f"tv_guide_now_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        now_dt = datetime.now()
        airing = [ep for ep in self._schedule if self._is_on_air(now_dt, ep)]

        if airing:
            first = airing[0]
            self._state = f"{first['show']['name']} ({self._channel(first)})"
            self._attrs["programmi_correnti"] = {
                self._channel(ep): ep["show"]["name"] for ep in airing
            }
        else:
            self._state = "Nessun dato"
            self._attrs["programmi_correnti"] = {}


class TVPrimeSensor(TVGuideBaseSensor):
    """Programmi di prima serata (≥ 20:30)."""

    _attr_icon = "mdi:movie-open"
    PRIME_TIME = time(20, 30)

    def __init__(self, base_name: str, country: str, session):
        super().__init__(base_name, country, session)
        self._attr_name = f"{base_name} - Prima serata"
        self._attr_unique_id = f"tv_guide_prime_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        prime_shows = [
            ep
            for ep in self._schedule
            if self._parse_time(ep.get("airtime")) >= self.PRIME_TIME
        ]
        prime_shows.sort(key=lambda ep: self._parse_time(ep.get("airtime")))

        if prime_shows:
            first = prime_shows[0]
            self._state = f"{first['show']['name']} ({self._channel(first)})"
        else:
            self._state = "Nessun dato"

        self._attrs["prima_serata"] = {
            self._channel(ep): f"{ep['show']['name']} alle {ep.get('airtime', '??:??')}"
            for ep in prime_shows
        }
