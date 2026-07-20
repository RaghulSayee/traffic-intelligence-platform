import pytest

from app.api.media import parse_byte_range


def test_parses_explicit_byte_range() -> None:
    result = parse_byte_range(
        "bytes=100-199",
        file_size=1000,
    )

    assert result.start == 100
    assert result.end == 199
    assert result.length == 100


def test_parses_open_ended_range() -> None:
    result = parse_byte_range(
        "bytes=900-",
        file_size=1000,
    )

    assert result.start == 900
    assert result.end == 999


def test_parses_suffix_range() -> None:
    result = parse_byte_range(
        "bytes=-100",
        file_size=1000,
    )

    assert result.start == 900
    assert result.end == 999


def test_rejects_unsatisfiable_range() -> None:
    with pytest.raises(ValueError):
        parse_byte_range(
            "bytes=2000-3000",
            file_size=1000,
        )
