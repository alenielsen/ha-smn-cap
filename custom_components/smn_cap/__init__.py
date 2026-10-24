"""Home Assistant SMN CAP integration."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from xml.etree.ElementTree import ParseError
import re
from pathlib import Path
from homeassistant.components.http import StaticPathConfig
from aiohttp import ClientError, ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, FEED_URL, UPDATE_INTERVAL, MAX_BYTES
from .parser import rss_links, parse_cap, combine_alerts

_STALE_CAP_RE = re.compile(r'/CAP_(\d{14})_')

def is_historical_link(url, now):
    """Ignore CAP archives older than 48 hours; never treat these as current data."""
    match = _STALE_CAP_RE.search(url)
    if not match:
        return False
    try:
        published = datetime.strptime(match.group(1), '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return published < now - timedelta(hours=48)


_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "binary_sensor"]

class SMNCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.entry = entry
        self._document_cache = {}  # url -> (timestamp, XML bytes), bounded below

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
            now = datetime.now(timezone.utc)
            historical = sum(is_historical_link(url, now) for url in links)
            links = [url for url in links if not is_historical_link(url, now)]
            if not links:
                raise UpdateFailed(f'Feed contains only {historical} historical CAP links; source freshness not verified')
            if len(links) > 200:
                raise UpdateFailed(f'Feed contains {len(links)} recent CAP links, exceeding the 200-document safety limit')
            # Prune URLs that the feed no longer advertises, preserving bounded memory.
            active_links = set(links)
            self._document_cache = {k: v for k, v in self._document_cache.items() if k in active_links}
            lat = float(self.entry.data["latitude"])
            lon = float(self.entry.data["longitude"])
            location = self.entry.data.get("location", "")
            sem = asyncio.Semaphore(4)

            async def download(link):
                async with sem:
                    try:
                        cached = self._document_cache.get(link)
                        if cached and now - cached[0] < timedelta(minutes=30):
                            payload = cached[1]
                        else:
                            payload = await self._fetch(link)
                        parsed = parse_cap(payload, lat, lon, location, now=now)
                        if not cached or now - cached[0] >= timedelta(minutes=30):
                            self._document_cache[link] = (now, payload)
                        return parsed
                    except (ClientError, asyncio.TimeoutError, ValueError, OSError, ParseError) as exc:
                        return (link, str(exc))

            results = await asyncio.gather(*(download(link) for link in links))
            failures = [r for r in results if isinstance(r, tuple)]
            if failures:
                _LOGGER.warning("SMN CAP: %d of %d recent documents failed; example %s: %s", len(failures), len(links), failures[0][0], failures[0][1])
                raise UpdateFailed(f"{len(failures)} current CAP documents could not be verified")
            return {
                "alerts": combine_alerts([a for result in results for a in result]),
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        except (ClientError, asyncio.TimeoutError, ValueError, OSError, ParseError) as exc:
            raise UpdateFailed(str(exc)) from exc

async def async_setup_entry(hass, entry):
    await hass.http.async_register_static_paths([StaticPathConfig("/smn_cap/smn-cap-card.js", str(Path(__file__).parent / "www" / "smn-cap-card.js"), cache_headers=False)])
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
