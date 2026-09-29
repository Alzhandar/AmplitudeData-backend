"""Shared phone-number normalization for parks in multiple countries.

Currently supports Kazakhstan (+7) and Uzbekistan (+998, Tashkent park).
This is the single source of truth for phone normalization across the
project — add a new country's format here rather than duplicating a
country-specific check in an individual app.
"""

from typing import List, Optional

_KZ_MOBILE_PREFIXES = ('70', '71', '72', '73', '74', '75', '76', '77')


def normalize_phone_number(raw_phone) -> str:
    """Return a digits-only phone number with country code, or '' if unrecognized.

    Recognized shapes:
      - Kazakhstan: 11 digits starting with 7 (or legacy 8 -> 7), or a bare
        10-digit KZ mobile number (7XX...) without the country code.
      - Uzbekistan: 12 digits starting with 998, or a bare 9-digit UZ mobile
        number (9X...) without the country code.
    """
    digits = ''.join(ch for ch in str(raw_phone or '') if ch.isdigit())
    if not digits:
        return ''

    # Legacy Kazakhstan trunk prefix "8" -> country code "7".
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]

    if len(digits) == 11 and digits.startswith('7'):
        return digits

    if len(digits) == 10 and digits.startswith(_KZ_MOBILE_PREFIXES):
        return '7' + digits

    if len(digits) == 12 and digits.startswith('998'):
        return digits

    if len(digits) == 9 and digits.startswith('9'):
        return '998' + digits

    return ''


def phone_search_variants(normalized_phone: str) -> List[str]:
    """Build alternate representations of a normalized phone to try against upstream search APIs."""
    normalized = normalize_phone_number(normalized_phone)
    if not normalized:
        return []

    variants = [normalized, f'+{normalized}']

    if normalized.startswith('7') and len(normalized) == 11:
        # Legacy Kazakhstan trunk-prefix form.
        variants.append(f'8{normalized[1:]}')
        variants.append(f'+7{normalized[1:]}')

    # Keep order, remove duplicates.
    return list(dict.fromkeys(variants))
