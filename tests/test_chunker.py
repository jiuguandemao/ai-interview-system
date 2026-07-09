import pytest

from app.services.text_chunker import split_text


def test_split_text_keeps_content_and_limits_chunk_size():
    text = "第一段" * 100 + "\n\n" + "第二段" * 100
    chunks = split_text(text, chunk_size=120, overlap=20)
    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 140 for chunk in chunks)


def test_split_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        split_text("hello", chunk_size=100, overlap=100)
