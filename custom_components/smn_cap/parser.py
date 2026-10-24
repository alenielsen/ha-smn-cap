"""RSS and CAP parsing without third-party dependencies."""
from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

def tag(element):
    return element.tag.split("}")[-1]

def children(element, name):
    return [x for x in element if tag(x) == name]

def value(element, name, default=""):
    return next(((x.text or "").strip() for x in element if tag(x) == name), default)

def xml(payload):
    if isinstance(payload, str):
        payload = payload.encode()
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("Unsafe XML")
    return ET.fromstring(payload)

def date(value_):
    try:
        return datetime.fromisoformat(value_.replace("Z", "+00:00")).astimezone(timezone.utc) if value_ else None
    except (ValueError, TypeError):
        return None

def rss_links(payload):
    root = xml(payload)
    if tag(root) not in ("rss", "feed", "RDF"):
        raise ValueError("Unexpected RSS format")
    result = []
    for item in root.iter():
        if tag(item) not in ("item", "entry"):
            continue
        link = value(item, "link")
        if not link:
            link = next((c.get("href", "") for c in item if tag(c) == "link"), "")
        u = urlparse(link)
        if (u.scheme == "https" and u.hostname == "ssl.smn.gob.ar" and not u.username
            and not u.password and u.port in (None, 443) and (u.path.startswith("/feeds/CAP/") or u.path.startswith("/CAP/"))
            and u.path.lower().endswith(".xml") and link not in result):
            result.append(link)
        if len(result) >= 100:
            break
    return result

def in_polygon(lat, lon, polygon):
    try:
        points = [tuple(map(float, pair.split(","))) for pair in polygon.split()]
    except ValueError:
        return False
    if len(points) < 3:
        return False
    inside = False
    j = len(points) - 1
    for i, (y, x) in enumerate(points):
        yj, xj = points[j]
        if (x > lon) != (xj > lon) and lat < (yj - y) * (lon - x) / (xj - x) + y:
            inside = not inside
        j = i
    return inside

def within_area(area, lat, lon, location):
    polygons = [(p.text or "") for p in children(area, "polygon")]
    if polygons:
        return any(in_polygon(lat, lon, p) for p in polygons)
    names = [s.strip().casefold() for s in value(area, "areaDesc").replace(";", ",").split(",")]
    return bool(location and location.strip().casefold() in names)

def parse_cap(payload, lat, lon, location, now=None):
    root = xml(payload)
    if tag(root) != "alert" or value(root, "status", "Actual") != "Actual":
        return []
    now = now or datetime.now(timezone.utc)
    sent = date(value(root, "sent"))
    output = []
    for info in children(root, "info"):
        matching = [a for a in children(info, "area") if within_area(a, lat, lon, location)]
        if not matching:
            continue
        expires = date(value(info, "expires"))
        effective = date(value(info, "effective")) or date(value(info, "onset")) or sent
        if expires and expires <= now:
            continue
        output.append({
            "id": value(root, "identifier"),
            "sent": sent.isoformat() if sent else None,
            "msg_type": value(root, "msgType", "Alert"),
            "references": value(root, "references"),
            "event": value(info, "event"),
            "severity": value(info, "severity", "Unknown"),
            "headline": value(info, "headline") or value(info, "event"),
            "description": value(info, "description"),
            "instruction": value(info, "instruction"),
            "effective": effective.isoformat() if effective else None,
            "expires": expires.isoformat() if expires else None,
            "active_now": not effective or effective <= now,
            "areas": [value(a, "areaDesc") for a in matching],
        })
    return output

def combine_alerts(alerts):
    versions = sorted(alerts, key=lambda a: a.get("sent") or "")
    removed = set()
    for alert in versions:
        if alert["msg_type"] in ("Update", "Cancel"):
            for ref in alert.get("references", "").split():
                fields = ref.split(",", 2)
                if len(fields) == 3:
                    removed.add(fields[1])
    valid = [a for a in versions if a["id"] not in removed and a["msg_type"] != "Cancel"]
    return list({(a["id"], a["event"], a["headline"]): a for a in valid}.values())
