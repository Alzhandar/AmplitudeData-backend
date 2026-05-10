from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from guest_profile.services.external_guest_data_service import ExternalGuestDataService
from guest_profile.services.mobile_activity_service import MobileActivityService

logger = logging.getLogger(__name__)


class GuestNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class GuestStatus:
    code: str
    label: str
    black_list: int
    is_blocked: bool


class GuestProfileService:
    def __init__(
        self,
        external_service: Optional[ExternalGuestDataService] = None,
        mobile_activity_service: Optional[MobileActivityService] = None,
    ) -> None:
        self.external_service = external_service or ExternalGuestDataService()
        self.mobile_activity_service = mobile_activity_service or MobileActivityService()

    def get_profile_by_phone(
        self,
        *,
        normalized_phone: str,
        from_date: date,
        to_date: date,
        orders_limit: int,
        mobile_events_limit: int,
        cashback_limit: int,
        crystal_limit: int,
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        guest = self.external_service.find_guest_by_phone(normalized_phone)
        if not guest:
            raise GuestNotFoundError('guest_not_found')

        guest_id = self._extract_guest_id(guest)
        if guest_id <= 0:
            raise GuestNotFoundError('guest_not_found')

        logger.info('guest_profile_request_started', extra={'guest_id': guest_id})

        guest_payload = self._safe_call(
            warnings,
            'guest_details_unavailable',
            lambda: self.external_service.get_guest(guest_id),
            default_value={},
        )
        status = self._map_guest_status(guest_payload)

        purchase_history = self._safe_call(
            warnings,
            'purchase_history_unavailable',
            lambda: self.external_service.get_purchase_history(
                guest_id=guest_id,
                from_date=from_date,
                to_date=to_date,
                limit=orders_limit,
            ),
            default_value={'count': 0, 'results': []},
        )

        cashback_summary = self._safe_call(
            warnings,
            'cashback_summary_unavailable',
            lambda: self.external_service.get_cashback_summary(guest_id=guest_id),
            default_value={},
        )
        crystal_summary = self._safe_call(
            warnings,
            'crystal_summary_unavailable',
            lambda: self.external_service.get_crystal_summary(guest_id=guest_id),
            default_value={},
        )

        cashback_history = self._safe_call(
            warnings,
            'cashback_history_unavailable',
            lambda: self.external_service.get_cashback_history(
                guest_id=guest_id,
                from_date=from_date,
                to_date=to_date,
                limit=cashback_limit,
            ),
            default_value={'count': 0, 'results': []},
        )
        crystal_history = self._safe_call(
            warnings,
            'crystal_history_unavailable',
            lambda: self.external_service.get_crystal_history(
                guest_id=guest_id,
                limit=crystal_limit,
            ),
            default_value={'count': 0, 'results': []},
        )

        mobile_activity = self._safe_call(
            warnings,
            'mobile_activity_unavailable',
            lambda: self.mobile_activity_service.get_activity_history(
                normalized_phone=normalized_phone,
                from_date=from_date,
                to_date=to_date,
                limit=mobile_events_limit,
            ),
            default_value={'count': 0, 'results': []},
        )

        response = {
            'phone': normalized_phone,
            'guest': {
                'id': guest_id,
                'name': str(guest_payload.get('name') or guest.get('name') or '').strip(),
                'status': {
                    'code': status.code,
                    'label': status.label,
                    'black_list': status.black_list,
                    'is_blocked': status.is_blocked,
                },
            },
            'balances': {
                'cashback': {
                    'sum': cashback_summary.get('sum', 0),
                    'burn_date': cashback_summary.get('burn_date'),
                    'burn_sum': cashback_summary.get('burn_sum', 0),
                },
                'crystals': {
                    'total_crystals': crystal_summary.get('total_crystals', 0),
                },
            },
            'purchase_history': purchase_history,
            'cashback_history': cashback_history,
            'crystal_history': crystal_history,
            'mobile_activity': mobile_activity,
            'warnings': warnings,
        }

        logger.info(
            'guest_profile_request_finished',
            extra={
                'guest_id': guest_id,
                'warnings_count': len(warnings),
                'orders_count': response['purchase_history'].get('count', 0),
            },
        )

        return response

    def _safe_call(
        self,
        warnings: List[str],
        warning_code: str,
        loader: Callable[[], Any],
        default_value: Any,
    ) -> Any:
        try:
            return loader()
        except Exception:
            warnings.append(warning_code)
            logger.exception('guest_profile_block_failed', extra={'warning_code': warning_code})
            return default_value

    def _extract_guest_id(self, guest: Dict[str, Any]) -> int:
        raw = guest.get('id') or guest.get('guest_id')
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def _map_guest_status(self, guest_payload: Dict[str, Any]) -> GuestStatus:
        raw_black_list = guest_payload.get('black_list', 0)
        try:
            black_list = int(raw_black_list)
        except (TypeError, ValueError):
            black_list = 0

        if black_list == 1:
            return GuestStatus(code='blocked', label='Заблокированный', black_list=1, is_blocked=True)

        return GuestStatus(code='active', label='Активный', black_list=black_list, is_blocked=False)
