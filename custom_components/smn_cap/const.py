"""SMN CAP constants."""
from datetime import timedelta
DOMAIN = "smn_cap"
FEED_URL = "https://ssl.smn.gob.ar/feeds/CAP/rss_alertaCAP_nuevo.xml"
UPDATE_INTERVAL = timedelta(minutes=5)
MAX_BYTES = 2_000_000
