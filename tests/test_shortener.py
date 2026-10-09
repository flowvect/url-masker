"""Unit tests for the base62 shortener service."""

import pytest

from app.services.shortener import decode, encode


class TestBase62Encode:
    """Verify encode() produces correct base62 strings."""

    def test_zero(self):
        assert encode(0) == "0"

    def test_single_digit(self):
        assert encode(9) == "9"

    def test_lowercase(self):
        # 10 -> 'a', 35 -> 'z'
        assert encode(10) == "a"
        assert encode(35) == "z"

    def test_uppercase(self):
        # 36 -> 'A', 61 -> 'Z'
        assert encode(36) == "A"
        assert encode(61) == "Z"

    def test_two_digit(self):
        # 62 -> '10'
        assert encode(62) == "10"

    def test_large_number(self):
        result = encode(123_456_789)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            encode(-1)


class TestBase62Decode:
    """Verify decode() reverses encode() correctly."""

    def test_zero(self):
        assert decode("0") == 0

    def test_single_char(self):
        assert decode("a") == 10
        assert decode("Z") == 61

    def test_two_char(self):
        assert decode("10") == 62

    def test_invalid_char_raises(self):
        with pytest.raises(ValueError, match="Invalid base62 character"):
            decode("hello!")


class TestRoundTrip:
    """Ensure encode → decode is an identity function."""

    @pytest.mark.parametrize("n", [0, 1, 42, 999, 12345, 999_999, 123_456_789])
    def test_roundtrip(self, n: int):
        assert decode(encode(n)) == n

    @pytest.mark.parametrize("n", range(0, 200))
    def test_sequential_roundtrip(self, n: int):
        assert decode(encode(n)) == n
