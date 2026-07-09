from app.services.file_parser import normalize_text


def test_normalize_text_removes_extra_blank_lines_and_nulls():
    assert normalize_text("A\x00  B\r\n\r\n\r\nC") == "A B\n\nC"
