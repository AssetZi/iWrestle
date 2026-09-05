"""Parser tests against a saved copy of the real page, so they run offline."""
from pathlib import Path

import pytest

from iwpipe.collectors import pywrestling
from iwpipe.collectors.pywrestling import _split_street_city, _title_case

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "pywrestling-index.html"


@pytest.fixture(scope="module")
def events():
    return pywrestling.collect(None, fixture=FIXTURE)


def test_finds_the_whole_calendar(events):
    """The page listed 34 events when the fixture was saved."""
    assert len(events) >= 30


def test_every_event_has_the_basics(events):
    for event in events:
        assert event["name"]
        assert event["dateText"]
        assert event["address"]


def test_address_is_comma_separated_for_addressparts(events):
    """AddressParts in the app splits on commas: venue, street, city, ST ZIP."""
    for event in events:
        assert event["address"].count(",") >= 2, event["address"]


def test_a_known_event_parses_exactly(events):
    match = next(e for e in events if "Takedown In The Den" in e["name"])
    assert match["organizer"] == "Elizabethtown Mat Club"
    assert match["address"] == (
        "Elizabethtown Area School District, 600 East High Street, "
        "Elizabethtown, PA 17022"
    )
    assert match["divisionsText"] == "Youth, Jr High, High School"


def test_events_that_link_offsite_are_still_found(events):
    """Battle in the Burg links to the organizer's own site, not a PYW page."""
    assert any("Battle In The Burg" in e["name"] for e in events)


def test_venue_split_across_elements_is_rejoined(events):
    match = next(e for e in events if "Lebanon Girls" in e["name"])
    assert match["address"].startswith("Lebanon High School,")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("275 Swamp Road Newtown, PA 18940", "275 Swamp Road, Newtown, PA 18940"),
        ("256 US-6 E Milford, PA 18337", "256 US-6 E, Milford, PA 18337"),
        ("1 University Avenue Mechanicsburg, PA 17055",
         "1 University Avenue, Mechanicsburg, PA 17055"),
    ],
)
def test_street_city_split(raw, expected):
    assert _split_street_city(raw) == expected


def test_acronyms_survive_title_casing():
    assert _title_case("MAT-TOWN USA FALL CLASSIC") == "Mat-Town USA Fall Classic"
    assert _title_case("HAROLD WINSHEL MEMORIAL") == "Harold Winshel Memorial"


def test_nearly_every_event_has_a_banner(events):
    """The banner is the real flyer. Two listings on the saved page have none."""
    with_banner = [e for e in events if e["bannerUrl"]]
    assert len(with_banner) >= 0.9 * len(events)
    assert all(e["bannerUrl"].startswith("https://www.pywrestling.com/images/") for e in with_banner)


def test_banner_prefers_the_large_rendition():
    from bs4 import BeautifulSoup

    from iwpipe.collectors.pywrestling import _banner_url

    html = """<div>
      <img src="images/j/youth-160.jpg"><img src="images/e/26x-640.jpg">
      <img src="images/e/26x-1280.jpg"><img src="images/s/22signuplogo-288.png">
    </div>"""
    assert _banner_url(BeautifulSoup(html, "html.parser")).endswith("26x-1280.jpg")


def test_obfuscated_emails_decode():
    from iwpipe.collectors.pywrestling import _decode_emn

    encoded = "".join(chr(ord(c) + 1) for c in "coach@example.com")
    html = f'<script>function em1(){{var c="{encoded}";var a="mailto:";}}</script>'
    assert _decode_emn(html) == ["coach@example.com"]


def test_detail_page_jotform_becomes_registration():
    from iwpipe.collectors import pywrestling
    from iwpipe.schema import blank_event

    class Response:
        text = '<html><body><iframe src="https://form.jotform.com/262174666443159"></iframe>'
        text += "<p>See you at the tournament.</p></body></html>"

    class Session:
        def get(self, *a, **k):
            return Response()

    event = blank_event("pywrestling")
    event["pages"] = {"info": "https://www.pywrestling.com/x-9-19.html", "signup": None, "external": None}
    pywrestling._enrich_from_detail(_FakeGetSession(Response()), event)
    assert event["registration"] == "https://form.jotform.com/262174666443159"
    assert "See you" in event["detailText"]


class _FakeGetSession:
    """Stands in for requests.Session inside iwpipe.http.get."""

    def __init__(self, response):
        self._response = response
        self.headers = {}

    def get(self, *args, **kwargs):
        response = self._response
        response.status_code = 200
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.encoding = "utf-8"
        response.raise_for_status = lambda: None
        return response


def test_site_wide_webmaster_email_is_not_an_organizer_contact():
    """The site prints its own address on every page; it must not be assigned."""
    from iwpipe.collectors import pywrestling
    from iwpipe.schema import blank_event

    class Response:
        text = "<html><body>Questions? PYWRESTLINGADAM@GMAIL.COM " \
               "<iframe src='https://form.jotform.com/1'></iframe></body></html>"

    event = blank_event("pywrestling")
    event["pages"] = {"info": "https://www.pywrestling.com/x-9-19.html", "signup": None, "external": None}
    site = pywrestling._site_emails("<a>pywrestlingadam@gmail.com</a>")
    pywrestling._enrich_from_detail(_FakeGetSession(Response()), event, site)
    assert event["contact"]["email"] == ""
    assert event["registration"] == "https://form.jotform.com/1"


def test_flyer_pdf_is_found_in_jotform_widget_settings():
    """The PDF Embedder widget keeps its file path as URL-encoded JSON."""
    from urllib.parse import quote

    from iwpipe.collectors.pywrestling import pdf_from_jotform

    settings = quote(
        '[{"name":"link","value":{"name":"26sepa.pdf","type":"application/pdf",'
        '"path":"/uploads/pywrestlingadam/form_files/26sepa-abc.pdf","url":"www.jotform.com"}},'
        '{"name":"attach","value":true}]'
    )
    html = f'<input class="form-hidden form-widget-settings" type="hidden" value="{settings}">'
    assert pdf_from_jotform(html) == (
        "https://www.jotform.com/uploads/pywrestlingadam/form_files/26sepa-abc.pdf?serveInlineWithCache=1"
    )
    assert pdf_from_jotform("<form></form>") == ""


def test_sign_up_pages_are_followed_and_never_the_root(events):
    """`slug-M-D-or.html` is the sign-up page; an event with only that page
    still gets a real link, and no event ever links to the site root."""
    falcon = next(e for e in events if "Falcon Frenzy" in e["name"])
    assert falcon["sourceUrl"].endswith("-9-26-or.html")
    assert falcon["pages"]["signup"] and not falcon["pages"]["info"]
    assert all(e["sourceUrl"].rstrip("/") != "https://www.pywrestling.com" for e in events)


def test_offsite_events_link_to_the_organizer(events):
    burg = next(e for e in events if "Battle In The Burg" in e["name"])
    assert "breakthechainswrestling.com" in burg["sourceUrl"]
    assert burg["organizerWebsite"] == burg["sourceUrl"]


def test_pages_precedence():
    from bs4 import BeautifulSoup

    from iwpipe.collectors.pywrestling import _pages

    html = """<div>
      <a href="x-9-26-or.html">sign up</a>
      <a href="https://club.org/event">CLUB EVENT</a>
      <a href="x-9-26.html">info</a>
      <a href="https://www.trackwrestling.com/reg">Register</a>
    </div>"""
    pages = _pages(BeautifulSoup(html, "html.parser"))
    assert pages["info"].endswith("x-9-26.html")
    assert pages["signup"].endswith("x-9-26-or.html")
    assert pages["external"] == "https://club.org/event"


def test_form_owner_emails_are_ignored():
    """A JotForm page prints its owner's address; that is not the organizer."""
    from urllib.parse import quote

    from iwpipe.collectors import pywrestling
    from iwpipe.schema import blank_event

    settings = quote('[{"name":"link","value":{"path":"/uploads/o/form_files/f.pdf"}}]')
    pages = {
        "https://www.pywrestling.com/x-9-26-or.html":
            '<iframe src="https://pci.jotform.com/form/1"></iframe>',
        "https://pci.jotform.com/form/1":
            f'<input class="form-widget-settings" value="{settings}"> owner@yahoo.com',
    }

    class Response:
        def __init__(self, text):
            self.text = text
            self.status_code = 200
            self.headers = {"Content-Type": "text/html; charset=utf-8"}
            self.encoding = "utf-8"
        def raise_for_status(self):
            pass

    class Session:
        headers = {}
        def get(self, url, **kw):
            return Response(pages[url])

    event = blank_event("pywrestling")
    event["pages"] = {"info": None, "signup": "https://www.pywrestling.com/x-9-26-or.html", "external": None}
    pywrestling._enrich_from_detail(Session(), event)
    assert event["registration"] == "https://pci.jotform.com/form/1"
    assert event["flyer"]["url"].endswith("/uploads/o/form_files/f.pdf?serveInlineWithCache=1")
    assert "owner@yahoo.com" in event["ignoreEmails"]
    assert event["contact"]["email"] == ""
