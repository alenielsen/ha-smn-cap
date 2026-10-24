import unittest
from datetime import datetime, timezone
from pathlib import Path
import importlib.util

path = Path(__file__).resolve().parents[1] / "custom_components" / "smn_cap" / "parser.py"
spec = importlib.util.spec_from_file_location("smn_parser", path)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

RSS = b'<rss><channel><item><link>https://ssl.smn.gob.ar/feeds/CAP/a.xml</link></item><item><link>https://evil.com/feeds/b.xml</link></item></channel></rss>'
CAP = b'<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>x1</identifier><status>Actual</status><msgType>Alert</msgType><sent>2026-10-23T12:00:00Z</sent><info><event>Tormentas</event><severity>Severe</severity><effective>2026-10-23T12:00:00Z</effective><expires>2026-10-24T12:00:00Z</expires><area><areaDesc>Necochea</areaDesc><polygon>-38.8,-58.9 -38.8,-58.6 -38.4,-58.6 -38.4,-58.9 -38.8,-58.9</polygon></area></info></alert>'

class TestParser(unittest.TestCase):
    def test_feed_links(self):
        self.assertEqual(parser.rss_links(RSS), ["https://ssl.smn.gob.ar/feeds/CAP/a.xml"])

    def test_cap_registered_feed_links(self):
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><link href="https://ssl.smn.gob.ar/feeds/CAP/xml_generados/CAP_20261023170000_Tormenta.xml" /></entry></feed>'
        self.assertEqual(parser.rss_links(atom), ["https://ssl.smn.gob.ar/feeds/CAP/xml_generados/CAP_20261023170000_Tormenta.xml"])

    def test_allow_cap_path_and_block_foreign(self):
        feed = b'<rss><channel><item><link>https://ssl.smn.gob.ar/CAP/alert.xml</link></item><item><link>https://example.com/CAP/alert.xml</link></item></channel></rss>'
        self.assertEqual(parser.rss_links(feed), ["https://ssl.smn.gob.ar/CAP/alert.xml"])

    def test_polygon_in_and_out(self):
        at = datetime(2026, 10, 23, 15, tzinfo=timezone.utc)
        self.assertEqual(len(parser.parse_cap(CAP, -38.6, -58.75, "", at)), 1)
        self.assertEqual(len(parser.parse_cap(CAP, -34.6, -58.4, "", at)), 0)

    def test_expiry(self):
        at = datetime(2026, 10, 25, tzinfo=timezone.utc)
        self.assertEqual(parser.parse_cap(CAP, -38.6, -58.75, "", at), [])

    def test_malicious_dtd(self):
        with self.assertRaises(ValueError):
            parser.rss_links(b"<!DOCTYPE foo><rss/>")

    def test_truncated_feed_raises_parse_error(self):
        from xml.etree.ElementTree import ParseError
        with self.assertRaises(ParseError):
            parser.rss_links(b"<rss><channel><item><link>https://ssl.smn.gob.ar/feeds/CAP/a.xml</link>")

    def test_non_xml_response_raises_parse_error(self):
        from xml.etree.ElementTree import ParseError
        with self.assertRaises(ParseError):
            parser.rss_links(b"<html><body>Just a moment")

    def test_update(self):
        a = dict(id="old", sent="2026-10-23T10:00:00Z", msg_type="Alert", references="", event="Tormentas", headline="Tormentas")
        b = dict(a, id="new", sent="2026-10-23T11:00:00Z", msg_type="Update", references="smn,old,2026-10-23T10:00:00Z")
        self.assertEqual([x["id"] for x in parser.combine_alerts([a, b])], ["new"])
