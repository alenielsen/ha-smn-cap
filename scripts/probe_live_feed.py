"""Read-only, reproducible live CAP source probe. No credentials required."""
import datetime as dt
import importlib.util
import pathlib
import urllib.request
from collections import Counter
from xml.etree import ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("smnparser", ROOT / "custom_components/smn_cap/parser.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
sources = ["https://ssl.smn.gob.ar/CAP/AR.php", "https://ssl.smn.gob.ar/feeds/CAP/rss_alertaCAP_nuevo.xml"]
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"ha-smn-cap-healthcheck/0.2"})
    with urllib.request.urlopen(req, timeout=18) as r:
        body = r.read(2000001)
        if len(body)>2000000:
            raise ValueError("over size limit")
        return body

for source in sources:
    print("SOURCE",source, flush=True)
    try:
        payload=fetch(source)
        print("SOURCE_LENGTH",len(payload))
        links=p.rss_links(payload)
        print("LINKS_TOTAL",len(links))
        print("LINKS_EXAMPLES",links[:3])
        print("SOURCE_XML_TYPE",p.tag(p.xml(payload)))
        statuses=Counter()
        for url in links[:5]:
            try:
                cap=fetch(url)
                root=p.xml(cap)
                statuses[p.tag(root)]+=1
                if p.tag(root)=="alert":
                    print("CAP_SAMPLE",p.value(root,"identifier"),p.value(root,"sent"),
                        p.value(root,"status"),p.value(root,"msgType"))
                    for info in p.children(root,"info")[:1]:
                        print("CAP_INFO", {k:p.value(info,k)[:150] for k in ("event","severity","effective","expires")})
                        for area in p.children(info,"area")[:2]:
                            print("CAP_AREA",{k:p.value(area,k)[:150] for k in ("areaDesc","polygon","circle")}, "geocodes",[(p.value(g,"valueName"),p.value(g,"value")) for g in p.children(area,"geocode")][:3])
            except Exception as exc:
                statuses[type(exc).__name__+":"+str(exc)[:70]]+=1
        print("SAMPLE_RESULTS",dict(statuses))
    except Exception as exc:
        print("SOURCE_FAILURE",repr(exc))

print("FULL_FEED_VALIDATION_START",flush=True)
try:
    source=sources[0]
    links=p.rss_links(fetch(source))
    counters=Counter()
    found=[]
    now=dt.datetime.now(dt.timezone.utc)
    for ix,url in enumerate(links):
        try:
            data=fetch(url)
            items=p.parse_cap(data,-38.5545,-58.7396,"Necochea",now=now)
            counters["ok"]+=1
            for a in items:
                found.append(a)
        except Exception as exc:
            counters["error"]+=1
            if counters["error"]<=5:
                print("FULL_ERROR",ix,repr(exc),url)
    print("FULL_TOTAL",len(links),"COUNTS",dict(counters),
          "NECOCHEA_ALERTS",len(p.combine_alerts(found)),flush=True)
except Exception as exc:
    print("FULL_FATAL",repr(exc),flush=True)

print("THREE_LOCATIONS_VALIDATION", flush=True)
LOCATIONS = {
    "Anelo_Neuquen": (-38.354, -68.790, "Añelo"),
    "General_Obligado_Dept_Center": (-28.75, -59.75, "General Obligado"),
    "General_Obligado_Reconquista": (-29.14515, -59.65107, "Reconquista"),
    "Obera_Misiones": (-27.487, -55.120, "Oberá"),
}
try:
    feed_data=fetch(sources[0])
    urls=p.rss_links(feed_data)
    all_docs=[]
    for url in urls:
        try:
            all_docs.append(fetch(url))
        except Exception as exc:
            print("LOCATION_DOCUMENT_ERROR",repr(exc),url)
    print("LOCATION_DOCUMENTS",len(all_docs),len(urls))
    for name,(lat,lon,location) in LOCATIONS.items():
        raw=[a for doc in all_docs for a in p.parse_cap(doc,lat,lon,location)]
        combined=p.combine_alerts(raw)
        print("LOCATION_RESULT",name,"RAW",len(raw),"AFTER_UPDATES",len(combined))
        for a in combined[:8]:
            print("LOCATION_ALERT",name,a["id"],a["event"],a["severity"],a["effective"],a["expires"],a["areas"][:1])
except Exception as exc:
    print("LOCATION_FATAL",repr(exc))
