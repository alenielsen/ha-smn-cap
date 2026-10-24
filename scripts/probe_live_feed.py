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
            except Exception as exc:
                statuses[type(exc).__name__+":"+str(exc)[:70]]+=1
        print("SAMPLE_RESULTS",dict(statuses))
    except Exception as exc:
        print("SOURCE_FAILURE",repr(exc))
