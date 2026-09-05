from iwpipe.pdftext import contacts_from_text, extract_text


def test_contacts_are_read_as_printed():
    text = "Website: SEPAwrestling.com / email: sepatournaments@gmail.com\nQuestions? (814) 555-0100"
    assert contacts_from_text(text) == ("sepatournaments@gmail.com", "814-555-0100")


def test_site_wide_addresses_are_skipped():
    text = "pywrestlingadam@gmail.com coach@club.org"
    assert contacts_from_text(text, {"pywrestlingadam@gmail.com"}) == ("coach@club.org", "")


def test_text_pdf_round_trip(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "flyer.pdf"
    page = canvas.Canvas(str(path))
    page.drawString(72, 700, "ENTRY FEE: $35 email: coach@club.org")
    page.save()
    text = extract_text(path)
    assert "coach@club.org" in text
    assert contacts_from_text(text)[0] == "coach@club.org"


def test_unreadable_pdf_yields_empty_text(tmp_path):
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"%PDF-1.4 not really")
    assert extract_text(path) == ""
