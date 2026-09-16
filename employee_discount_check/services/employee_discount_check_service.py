from __future__ import annotations

import logging
from typing import Dict, Optional

from utils.avatariya_client import AvatariyaClient

logger = logging.getLogger(__name__)


class EmployeeDiscountCheckService:
    RESTAURANT_SCOPE = 'restaurant'
    PARK_SCOPE = 'park'

    def __init__(self, avatariya_client: Optional[AvatariyaClient] = None) -> None:
        self.avatariya_client = avatariya_client or AvatariyaClient()

    def check(self, phone_number: str) -> Dict:
        restaurant = self._check_scope(phone_number, self.RESTAURANT_SCOPE)
        park = self._check_scope(phone_number, self.PARK_SCOPE)

        employee_found = bool(
            restaurant.get('employee_name') or park.get('employee_name')
        )

        return {
            'phone': phone_number,
            'employee_found': employee_found,
            'restaurant': restaurant,
            'park': park,
        }

    def _check_scope(self, phone_number: str, scope: str) -> Dict:
        try:
            result = self.avatariya_client.check_employee_discount(
                phone_number=phone_number,
                discount_scope=scope,
            )
        except Exception:
            logger.exception(
                'employee_discount_check_upstream_error',
                extra={'phone': phone_number, 'scope': scope},
            )
            return {'eligible': False, 'discount_scope': scope}

        if not isinstance(result, dict):
            return {'eligible': False, 'discount_scope': scope}

        result.setdefault('discount_scope', scope)
        return result
