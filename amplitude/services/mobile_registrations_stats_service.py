from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from utils.mobile_client import MobileClient


class MobileRegistrationsUpstreamError(Exception):
    pass


class MobileRegistrationsStatsService:
    def __init__(self, mobile_client: Optional[MobileClient] = None) -> None:
        self.mobile_client = mobile_client or MobileClient()

    def get_stats(self, *, year: int, start_date: date, end_date: date) -> Dict[str, Any]:
        if start_date > end_date:
            raise ValueError('start_date must be <= end_date')

        if year < 2000 or year > 2100:
            raise ValueError('year must be in range 2000..2100')

        if start_date.year != year or end_date.year != year:
            raise ValueError('year must match both start_date and end_date')

        try:
            payload = self.mobile_client.get_new_user_registration_stats(
                year=year,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        except Exception as exc:
            raise MobileRegistrationsUpstreamError(str(exc)) from exc

        try:
            registrations = _to_non_negative_int(payload.get('registrations'))
            total_users = _to_non_negative_int(payload.get('total_users'))
            date_from = _parse_iso_date(payload.get('date_from'))
            date_to = _parse_iso_date(payload.get('date_to'))
        except ValueError as exc:
            raise MobileRegistrationsUpstreamError(str(exc)) from exc

        if date_from > date_to:
            raise MobileRegistrationsUpstreamError('invalid_upstream_payload: date_from must be <= date_to')

        return {
            'registrations': registrations,
            'total_users': total_users,
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'source': 'mobile_api',
            'cached': False,
        }


def _to_non_negative_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('invalid_upstream_payload: numeric field is invalid') from exc

    if parsed < 0:
        raise ValueError('invalid_upstream_payload: numeric field must be >= 0')

    return parsed


def _parse_iso_date(value: Any) -> date:
    raw = str(value or '').strip()
    if not raw:
        raise ValueError('invalid_upstream_payload: date field is required')

    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('invalid_upstream_payload: date field must use YYYY-MM-DD') from exc
