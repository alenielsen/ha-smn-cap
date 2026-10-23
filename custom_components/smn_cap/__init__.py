"""Home Assistant SMN CAP integration."""
import asyncio
import logging
from datetime import datetime, timezone
from aiohttp import ClientError, ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, FEED_URL, UPDATE_INTERVAL, MAX_BYTES
from .parser import rss_links, parse_cap, combine_alerts

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor"]

class SMNCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.entry = entry

    async def _fetch(self, url):
        session = async_get_clientsession(self.hass)
        async with session.get(url, timeout=ClientTimeout(total=15), allow_redirects=False) as response:
            response.raise_for_status()
            if response.content_length and response.content_length > MAX_BYTES:
                raise ValueError("Response too large")
            body = await response.content.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Response too large")
            return body

    async def _async_update_data(self):
        try:
            links = rss_links(await self._fetch(FEED_URL))
            if not links:
                raise UpdateFailed("No compatible CAP links; refusing to assume no alerts")
            lat = float(self.entry.data["latitude"])
            lon = float(self.entry.data["longitude"])
            location = self.entry.data.get("location", "")
            sem = asyncio.Semaphore(4)

            async def download(link):
                async with sem:
                    try:
                        return parse_cap(await self._fetch(link), lat, lon, location)
                    except (ClientError, asyncio.TimeoutError, ValueError, OSError) as exc:
                        _LOGGER.warning("CAP fetch failed %s: %s", link, exc)
                        return None

            results = await asyncio.gather(*(download(link) for link in links[:60]))
            if any(result is None for result in results):
                raise UpdateFailed("CAP document unavailable; preserving prior state")
            return {
                "alerts": combine_alerts([a for result in results for a in result]),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        except (ClientError, asyncio.TimeoutError, ValueError, OSError) as exc:
            raise UpdateFailed(str(exc)) from exc

async def async_setup_entry(hass, entry):
    coordinator = SMNCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
