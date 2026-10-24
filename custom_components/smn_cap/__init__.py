"""Home Assistant SMN CAP integration."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from xml.etree.ElementTree import ParseError
import re
from pathlib import Path
from homeassistant.components.http import StaticPathConfig
from aiohttp import ClientError, ClientTimeout, ClientResponseError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, FEED_URL, UPDATE_INTERVAL, MAX_BYTES
from .parser import rss_links, parse_cap, combine_alerts, xml, tag

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

class SharedCAPFeed:
    """One HTTP feed reader shared across all configured cities."""
    def __init__(self, hass):
        self.hass = hass
        self.lock = asyncio.Lock()
        self.snapshot = None
        self.refreshed_at = None
        self.retry_after = None
        self.documents = {}

    async def _fetch(self, url):
        session = async_get_clientsession(self.hass)
        async with session.get(url, timeout=ClientTimeout(total=20), allow_redirects=False) as response:
            response.raise_for_status()
            if response.content_length and response.content_length > MAX_BYTES:
                raise ValueError("CAP response exceeds size limit")
            body = await response.content.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("CAP response exceeds size limit")
            return body

    async def get_documents(self):
        async with self.lock:
            now = datetime.now(timezone.utc)
            if self.refreshed_at and now - self.refreshed_at < UPDATE_INTERVAL:
                return self.snapshot
            if self.retry_after and now < self.retry_after:
                raise UpdateFailed("CAP upstream rate limit; retry pending")
            try:
                links = rss_links(await self._fetch(FEED_URL))
                if not links:
                    raise UpdateFailed("CAP index contains no supported links")
                links = [link for link in links if not is_historical_link(link, now)]
                if not links:
                    raise UpdateFailed("CAP index contains only historical documents")
                if len(links) > 200:
                    raise UpdateFailed("CAP index exceeds safe document limit")
                self.documents = {url: val for url, val in self.documents.items() if url in links}
                for url in links:
                    if url in self.documents:
                        continue
                    try:
                        body = await self._fetch(url)
                        root = xml(body)
                        if tag(root) != "alert":
                            raise ValueError("CAP document is not an alert")
                        self.documents[url] = body
                    except ClientResponseError as err:
                        if err.status == 429:
                            self.retry_after = now + timedelta(minutes=10)
                        raise UpdateFailed(f"CAP HTTP {err.status}; cached {len(self.documents)}/{len(links)}") from err
                    await asyncio.sleep(0.15)
                self.snapshot = [self.documents[url] for url in links]
                self.refreshed_at = datetime.now(timezone.utc)
                self.retry_after = None
                return self.snapshot
            except (ClientError, asyncio.TimeoutError, OSError, ValueError, ParseError) as err:
                raise UpdateFailed(f"SMN CAP source error: {type(err).__name__}") from err


class SMNCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.entry = entry

    async def _async_update_data(self):
        store = self.hass.data[f"{DOMAIN}_shared_feed"]
        documents = await store.get_documents()
        now = datetime.now(timezone.utc)
        lat = float(self.entry.data["latitude"])
        lon = float(self.entry.data["longitude"])
        location = self.entry.data.get("location", "")
        try:
            alerts = [alert for document in documents
                      for alert in parse_cap(document, lat, lon, location, now=now)]
        except (ValueError, ParseError) as err:
            raise UpdateFailed(f"CAP processing failed: {type(err).__name__}") from err
        return {"alerts": combine_alerts(alerts), "checked_at": store.refreshed_at.isoformat()}


async def async_setup(hass, config):
    """Register frontend resource even when a CAP entry cannot initialize."""
    if not hass.data.get(f"{DOMAIN}_card_registered"):
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                "/smn_cap/smn-cap-card.js",
                str(Path(__file__).parent / "www" / "smn-cap-card.js"),
                cache_headers=False,
            )
        ])
        hass.data[f"{DOMAIN}_card_registered"] = True
    return True


async def async_setup_entry(hass, entry):
    await async_setup(hass, {})
    hass.data.setdefault(f"{DOMAIN}_shared_feed", SharedCAPFeed(hass))
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
