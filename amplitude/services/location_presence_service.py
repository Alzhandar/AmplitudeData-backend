from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional

from django.utils.dateparse import parse_datetime

from amplitude.models import DailyDeviceActivity, DeviceVisitTime
from utils.avatariya_client import AvatariyaClient


class LocationPresenceAnalyticsService:
    def __init__(self, avatariya_client: Optional[AvatariyaClient] = None) -> None:
        self.avatariya_client = avatariya_client or AvatariyaClient()

    def calculate(self, date_value: date, window_hours: int = 24) -> Dict:
        if window_hours <= 0:
            raise ValueError('window_hours must be greater than 0')

        daily_rows = DailyDeviceActivity.objects.filter(date=date_value).only('id', 'user_id', 'device_id', 'phone_number')

        users_without_phone = self._count_users_without_phone(daily_rows)
        phone_to_app_times = self._build_phone_to_app_times(date_value)

        phones = sorted(phone_to_app_times.keys())
        if not phones:
            return {
                'date': date_value.isoformat(),
                'window_hours': window_hours,
                'unique_users_total': users_without_phone,
                'users_with_phone': 0,
                'users_without_phone': users_without_phone,
                'in_location_users': 0,
                'not_in_location_users': 0,
                'visit_records_total': 0,
                'matched_visit_records': 0,
            }

        visit_rows = self.avatariya_client.visit_search_all_by_date_phones(
            date=date_value.isoformat(),
            phones=phones,
        )
        phone_to_visit_times = self._build_phone_to_visit_times(visit_rows)

        in_location_users = 0
        matched_visit_records = 0

        for phone, app_times in phone_to_app_times.items():
            visit_times = phone_to_visit_times.get(phone, [])
            if self._has_match_within_window(app_times, visit_times, window_hours):
                in_location_users += 1
                matched_visit_records += len(visit_times)

        users_with_phone = len(phone_to_app_times)
        not_in_location_users = users_with_phone - in_location_users

        return {
            'date': date_value.isoformat(),
            'window_hours': window_hours,
            'unique_users_total': users_with_phone + users_without_phone,
            'users_with_phone': users_with_phone,
            'users_without_phone': users_without_phone,
            'in_location_users': in_location_users,
            'not_in_location_users': not_in_location_users,
            'visit_records_total': len(visit_rows),
            'matched_visit_records': matched_visit_records,
        }

    def _count_users_without_phone(self, daily_rows: Iterable[DailyDeviceActivity]) -> int:
        unique_keys = set()
        for row in daily_rows:
            if self._normalize_phone(row.phone_number):
                continue
            unique_keys.add(self._build_user_key(row.user_id, row.device_id, row.id))
        return len(unique_keys)

    def _build_phone_to_app_times(self, date_value: date) -> Dict[str, List]:
        mapping: Dict[str, List] = defaultdict(list)

        rows = DeviceVisitTime.objects.filter(
            daily_activity__date=date_value,
        ).values_list('daily_activity__phone_number', 'event_time')

        for phone, event_time in rows:
            normalized_phone = self._normalize_phone(phone)
            if not normalized_phone:
                continue
            mapping[normalized_phone].append(event_time)

        for phone in mapping:
            mapping[phone].sort()

        return mapping

    def _build_phone_to_visit_times(self, visit_rows: List[Dict]) -> Dict[str, List]:
        mapping: Dict[str, List] = defaultdict(list)

        for row in visit_rows:
            normalized_phone = self._normalize_phone(row.get('guest_phone'))
            if not normalized_phone:
                continue

            visit_time = parse_datetime(row.get('time_create', ''))
            if visit_time is None:
                continue

            mapping[normalized_phone].append(visit_time)

        for phone in mapping:
            mapping[phone].sort()

        return mapping

    def _has_match_within_window(self, app_times: List, visit_times: List, window_hours: int) -> bool:
        if not app_times or not visit_times:
            return False

        window_seconds = window_hours * 3600
        pointer = 0

        for app_time in app_times:
            while pointer < len(visit_times) and visit_times[pointer] < app_time:
                pointer += 1

            neighbors = []
            if pointer < len(visit_times):
                neighbors.append(visit_times[pointer])
            if pointer - 1 >= 0:
                neighbors.append(visit_times[pointer - 1])

            for visit_time in neighbors:
                if abs((app_time - visit_time).total_seconds()) <= window_seconds:
                    return True

        return False

    def _normalize_phone(self, phone: Optional[str]) -> str:
        digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
        if not digits:
            return ''
        if len(digits) == 11 and digits.startswith('8'):
            return '7' + digits[1:]
        return digits

    def _build_user_key(self, user_id: str, device_id: str, row_id: int) -> str:
        if user_id:
            return f'user:{user_id}'
        if device_id:
            return f'device:{device_id}'
        return f'row:{row_id}'
