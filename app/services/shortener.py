"""Base62 URL shortening service.

Encoding is a pure math function — no external API calls.
The alphabet is 0-9, a-z, A-Z (62 characters).

Usage:
    encode(12345)  -> "3d7"
    decode("3d7")  -> 12345
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def encode(num: int) -> str:
    """Convert a positive integer to a base62 short code.

    Args:
        num: A positive integer (typically the link's sequence_id).

    Returns:
        A base62-encoded string.

    Raises:
        ValueError: If *num* is negative.
    """
    if num < 0:
        raise ValueError("encode() only accepts non-negative integers")
    if num == 0:
        return ALPHABET[0]

    chars: list[str] = []
    while num > 0:
        num, remainder = divmod(num, BASE)
        chars.append(ALPHABET[remainder])
    return "".join(reversed(chars))


def decode(code: str) -> int:
    """Convert a base62 short code back to its integer.

    Args:
        code: A base62 string previously produced by :func:`encode`.

    Returns:
        The original integer.

    Raises:
        ValueError: If *code* contains characters outside the base62 alphabet.
    """
    num = 0
    for char in code:
        idx = ALPHABET.find(char)
        if idx == -1:
            raise ValueError(f"Invalid base62 character: {char!r}")
        num = num * BASE + idx
    return num
