from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, Optional

from utils.avatariya_client import AvatariyaClient


class ExternalGuestDataService:
    def __init__(self, avatariya_client: Optional[AvatariyaClient] = None) -> None:
        self.avatariya_client = avatariya_client or AvatariyaClient()

    def find_guest_by_phone(self, normalized_phone: str) -> Optional[Dict[str, Any]]:
        return self.avatariya_client.find_guest_by_phone(normalized_phone)

    def get_guest(self, guest_id: int) -> Dict[str, Any]:
        payload = self.avatariya_client.get_guest(guest_id)
        return payload if isinstance(payload, dict) else {}

    def get_purchase_history(self, *, guest_id: int, from_date: date, to_date: date, limit: int) -> Dict[str, Any]:
        payload = self.avatariya_client.list_orders_read(
            guest_id=guest_id,
            c_created_from=self._to_datetime_start(from_date),
            c_created_to=self._to_datetime_end(to_date),
            page=1,
            page_size=limit,
            ordering='-c_created',
        )
        return self._normalize_list_payload(payload)

    def get_cashback_summary(self, *, guest_id: int) -> Dict[str, Any]:
        payload = self.avatariya_client.get_cashback_summary_current(guest_id)
        return payload if isinstance(payload, dict) else {}

    def get_cashback_history(self, *, guest_id: int, from_date: date, to_date: date, limit: int) -> Dict[str, Any]:
        payload = self.avatariya_client.list_cashback_transactions(
            guest_id=guest_id,
            transaction_date_gte=self._to_datetime_start(from_date),
            transaction_date_lte=self._to_datetime_end(to_date),
            page=1,
            page_size=limit,
            ordering='-transaction_date',
        )
        return self._normalize_list_payload(payload)

    def get_crystal_summary(self, *, guest_id: int) -> Dict[str, Any]:
        payload = self.avatariya_client.get_crystal_summary(guest_id)
        return payload if isinstance(payload, dict) else {}

    def get_crystal_history(self, *, guest_id: int, limit: int) -> Dict[str, Any]:
        payload = self.avatariya_client.list_crystal_transactions(
            guest_id=guest_id,
            page=1,
            page_size=limit,
            ordering='-date',
        )
        return self._normalize_list_payload(payload)

    def _normalize_list_payload(self, payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            results = payload.get('results')
            raw_count = payload.get('count')
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                count = len(results) if isinstance(results, list) else 0
            return {
                'count': count,
                'results': results if isinstance(results, list) else [],
            }
        if isinstance(payload, list):
            return {'count': len(payload), 'results': payload}
        return {'count': 0, 'results': []}

    def _to_datetime_start(self, value: date) -> str:
        return datetime.combine(value, time.min).isoformat()

    def _to_datetime_end(self, value: date) -> str:
        return datetime.combine(value, time.max).isoformat()
