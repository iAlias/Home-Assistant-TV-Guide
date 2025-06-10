"""Sensori Guida TV per Home Assistant basati sull'API pubblica di TVmaze."""
from datetime import datetime, time, timedelta
import logging

import aiohttp
import async_timeout
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME

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


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configura i sensori."""
    name = config.get(CONF_NAME)
    country = config.get(CONF_COUNTRY)
    session = aiohttp.ClientSession()

    async_add_entities(
        [
            TVNowSensor(name, country, session),
            TVPrimeSensor(name, country, session),
        ],
        True,
    )


class TVGuideBaseSensor(SensorEntity):
    """Classe base per i sensori Guida TV."""

    def __init__(self, base_name, country, session):
        self._base_name = base_name
        self._country = country
        self._session = session
        self._state = None
        self._attrs = {"attribution": ATTRIBUTION}
        self._schedule = []
        self._last_fetch_date = None

    @property
    def should_poll(self):
        return True

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
                response = await self._session.get(url)
                response.raise_for_status()
                self._schedule = await response.json()
                self._last_fetch_date = today
        except Exception as err:
            _LOGGER.error("Errore nel recupero del palinsesto: %s", err)

    async def async_update(self):
        """Da implementare nelle sottoclassi."""
        raise NotImplementedError

    # -- Helper methods ---------------------------------------------------
    @staticmethod
    def _parse_time(tstr: str) -> time:
        hours, minutes = map(int, tstr.split(":"))
        return time(hours, minutes)

    def _channel(self, item):
        network = item["show"].get("network") or item["show"].get("webChannel") or {}
        return network.get("name", "Sconosciuto")

    def _is_on_air(self, now_dt: datetime, item) -> bool:
        start_t = self._parse_time(item["airtime"])
        runtime = item.get("runtime") or 60  # fallback un'ora
        start_dt = datetime.combine(now_dt.date(), start_t)
        end_dt = start_dt + timedelta(minutes=runtime)
        return start_dt <= now_dt < end_dt


class TVNowSensor(TVGuideBaseSensor):
    """Mostra cosa c'è in onda adesso."""

    _attr_icon = "mdi:television-classic"

    def __init__(self, base_name, country, session):
        super().__init__(base_name, country, session)
        self._attr_name = f"{base_name} - Ora in onda"
        self._attr_unique_id = f"tv_guide_now_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        now_dt = datetime.now()
        current = [item for item in self._schedule if self._is_on_air(now_dt, item)]

        if current:
            first = current[0]
            self._state = f"{first['show']['name']} ({self._channel(first)})"
            self._attrs["programmi_correnti"] = {
                self._channel(it): it["show"]["name"] for it in current
            }
        else:
            self._state = "Nessun dato"
            self._attrs["programmi_correnti"] = {}


class TVPrimeSensor(TVGuideBaseSensor):
    """Mostra la prima serata (>= 20:30)."""

    _attr_icon = "mdi:movie-open"
    PRIME_TIME = time(20, 30)

    def __init__(self, base_name, country, session):
        super().__init__(base_name, country, session)
        self._attr_name = f"{base_name} - Prima serata"
        self._attr_unique_id = f"tv_guide_prime_{country.lower()}"

    async def async_update(self):
        await self._update_schedule()
        prime_shows = [
            item
            for item in self._schedule
            if self._parse_time(item["airtime"]) >= self.PRIME_TIME
        ]
        prime_shows.sort(key=lambda x: self._parse_time(x["airtime"]))

        if prime_shows:
            first = prime_shows[0]
            self._state = f"{first['show']['name']} ({self._channel(first)})"
        else:
            self._state = "Nessun dato"

        self._attrs["prima_serata"] = {
            self._channel(it): f"{it['show']['name']} alle {it['airtime']}"
            for it in prime_shows
        }
