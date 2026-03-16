from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional

from amplitude.models import DailyDeviceActivity, DeviceVisitTime
from amplitude.services.bigdata_visit_service import BigDataVisitSyncService
from utils.avatariya_client import AvatariyaClient


class LocationPresenceAnalyticsService:
    def __init__(self, avatariya_client: Optional[AvatariyaClient] = None, bigdata_visit_service: Optional[BigDataVisitSyncService] = None) -> None:
        self.avatariya_client = avatariya_client or AvatariyaClient()
        self.bigdata_visit_service = bigdata_visit_service or BigDataVisitSyncService(avatariya_client=self.avatariya_client)

    def calculate(self, start_date: date, end_date: date, window_hours: int = 24, auto_sync: bool = False) -> Dict:
        if window_hours <= 0:
            raise ValueError('window_hours must be greater than 0')
        if start_date > end_date:
            raise ValueError('start_date must be <= end_date')

        daily_rows = DailyDeviceActivity.objects.filter(
            date__range=(start_date, end_date),
        ).only('id', 'user_id', 'device_id', 'phone_number')

        users_without_phone = self._count_users_without_phone(daily_rows)
        phone_to_app_times = self._build_phone_to_app_times(start_date, end_date)

        phones = sorted(phone_to_app_times.keys())
        if not phones:
            return {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'window_hours': window_hours,
                'unique_users_total': users_without_phone,
                'users_with_phone': 0,
                'users_without_phone': users_without_phone,
                'in_location_users': 0,
                'not_in_location_users': 0,
                'visit_records_total': 0,
                'matched_visit_records': 0,
            }

        if auto_sync:
            self.bigdata_visit_service.sync_visits(
                start_date=start_date,
                end_date=end_date,
                phones=phones,
            )
        phone_to_visit_times, visits_total = self.bigdata_visit_service.build_phone_to_visit_times(
            start_date=start_date,
            end_date=end_date,
            phones=phones,
        )

        in_location_users = 0
        not_in_location_users = 0
        matched_visit_records = 0

        for phone, app_times in phone_to_app_times.items():
            visit_times = phone_to_visit_times.get(phone, [])
            matched_app_events = self._count_matches_within_window(app_times, visit_times, window_hours)
            unmatched_app_events = len(app_times) - matched_app_events

            # Majority rule per user: classify as in-location only when matched events prevail.
            if matched_app_events > unmatched_app_events:
                in_location_users += 1
            else:
                not_in_location_users += 1

            matched_visit_records += matched_app_events

        users_with_phone = len(phone_to_app_times)

        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'window_hours': window_hours,
            'unique_users_total': users_with_phone + users_without_phone,
            'users_with_phone': users_with_phone,
            'users_without_phone': users_without_phone,
            'in_location_users': in_location_users,
            'not_in_location_users': not_in_location_users,
            'visit_records_total': visits_total,
            'matched_visit_records': matched_visit_records,
        }

    def _count_users_without_phone(self, daily_rows: Iterable[DailyDeviceActivity]) -> int:
        unique_keys = set()
        for row in daily_rows:
            if self._normalize_phone(row.phone_number):
                continue
            unique_keys.add(self._build_user_key(row.user_id, row.device_id, row.id))
        return len(unique_keys)

    def _build_phone_to_app_times(self, start_date: date, end_date: date) -> Dict[str, List]:
        mapping: Dict[str, List] = defaultdict(list)

        rows = DeviceVisitTime.objects.filter(
            daily_activity__date__range=(start_date, end_date),
        ).values_list('daily_activity__phone_number', 'event_time')

        for phone, event_time in rows:
            normalized_phone = self._normalize_phone(phone)
            if not normalized_phone:
                continue
            mapping[normalized_phone].append(event_time)

        for phone in mapping:
            mapping[phone].sort()

        return mapping

    def _count_matches_within_window(self, app_times: List, visit_times: List, window_hours: int) -> int:
        if not app_times or not visit_times:
            return 0

        window_seconds = window_hours * 3600
        pointer = 0
        matches = 0

        for app_time in app_times:
            while pointer < len(visit_times) and visit_times[pointer] < app_time:
                pointer += 1

            is_matched = False

            if pointer < len(visit_times):
                if abs((app_time - visit_times[pointer]).total_seconds()) <= window_seconds:
                    is_matched = True

            if not is_matched and pointer - 1 >= 0:
                if abs((app_time - visit_times[pointer - 1]).total_seconds()) <= window_seconds:
                    is_matched = True

            if is_matched:
                matches += 1

        return matches

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
