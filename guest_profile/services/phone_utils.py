from __future__ import annotations

from typing import List


def normalize_phone_number(raw_phone: str) -> str:
    digits = ''.join(ch for ch in str(raw_phone or '') if ch.isdigit())
    if not digits:
        return ''

    if len(digits) == 11 and digits.startswith('8'):
        return f'7{digits[1:]}'
    if len(digits) == 11 and digits.startswith('7'):
        return digits
    if len(digits) == 10 and digits.startswith(('70', '71', '72', '73', '74', '75', '76', '77')):
        return f'7{digits}'

    return ''


def phone_search_variants(normalized_phone: str) -> List[str]:
    normalized = normalize_phone_number(normalized_phone)
    if not normalized:
        return []

    variants = [
        normalized,
        f'8{normalized[1:]}',
        f'+{normalized}',
        f'+7{normalized[1:]}',
    ]

    # Keep order, remove duplicates.
    return list(dict.fromkeys(variants))
