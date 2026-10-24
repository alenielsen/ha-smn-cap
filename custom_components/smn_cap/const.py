"""SMN CAP constants."""
from datetime import timedelta
DOMAIN = "smn_cap"
FEED_URL = "https://ssl.smn.gob.ar/CAP/AR.php"
UPDATE_INTERVAL = timedelta(minutes=5)
MAX_BYTES = 2_000_000
