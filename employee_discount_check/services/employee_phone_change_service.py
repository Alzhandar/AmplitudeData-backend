from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

from utils.avatracker_client import AvatrackerClient
from utils.phone_utils import normalize_phone_number

logger = logging.getLogger(__name__)


class EmployeePhoneChangeError(Exception):
    pass


class EmployeeNotFoundError(EmployeePhoneChangeError):
    pass


class PhoneAlreadyInUseError(EmployeePhoneChangeError):
    pass


class EmployeePhoneChangeService:
    """Lets an employee switch which phone number they use for the discount by
    updating their record directly in avatracker (the actual employee database
    both the discount check and the till read from) — no separate mapping needed.

    The employee is often findable only by ИИН: their avatracker phone doesn't
    match the number they actually want to use for the discount (the recurring
    complaint this whole feature exists for), so a plain phone lookup fails.
    find_employee() therefore tries phone first, then falls back to ИИН.
    """

    IIN_LENGTH = 12

    def __init__(self, avatracker_client: Optional[AvatrackerClient] = None) -> None:
        self.avatracker_client = avatracker_client or AvatrackerClient()

    def find_employee(self, identifier: str) -> Optional[Dict]:
        employee, _ = self.find_employee_with_source(identifier)
        return employee

    def find_employee_with_source(self, identifier: str) -> Tuple[Optional[Dict], str]:
        """Returns (employee, matched_by) where matched_by is 'phone', 'iin' or 'none'."""
        normalized_phone = normalize_phone_number(identifier)
        if normalized_phone:
            employee = self.avatracker_client.find_employee_by_phone(normalized_phone)
            if employee:
                return employee, 'phone'

        digits = ''.join(ch for ch in str(identifier or '') if ch.isdigit())
        if len(digits) == self.IIN_LENGTH:
            employee = self.avatracker_client.find_employee_by_iin(digits)
            if employee:
                return employee, 'iin'

        return None, 'none'

    def change_phone(self, identifier: str, new_phone: str) -> Dict:
        employee = self.find_employee(identifier)
        if not employee:
            raise EmployeeNotFoundError(
                f'Сотрудник не найден по «{identifier}» — проверьте номер телефона или ИИН'
            )

        employee_id = employee.get('id')
        old_phone = str(employee.get('phone') or '')

        if old_phone == new_phone:
            logger.info('employee_phone_already_set', extra={'employee_id': employee_id, 'phone': new_phone})
            return {
                'employee_id': str(employee_id),
                'employee_name': employee.get('full_name') or '',
                'old_phone': old_phone,
                'new_phone': new_phone,
            }

        holder = self.avatracker_client.find_employee_by_phone(new_phone)
        if holder and str(holder.get('id')) != str(employee_id):
            raise PhoneAlreadyInUseError(
                f'Номер {new_phone} уже используется другим сотрудником ({holder.get("full_name")})'
            )

        self.avatracker_client.update_employee_phone(employee_id, new_phone)
        logger.info(
            'employee_phone_changed',
            extra={'employee_id': employee_id, 'old_phone': old_phone, 'new_phone': new_phone},
        )

        return {
            'employee_id': str(employee_id),
            'employee_name': employee.get('full_name') or '',
            'old_phone': old_phone,
            'new_phone': new_phone,
        }
