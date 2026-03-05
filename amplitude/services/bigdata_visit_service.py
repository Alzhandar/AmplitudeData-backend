import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from amplitude.models import BigDataPhoneDaySyncState, BigDataVisit
from utils.avatariya_client import AvatariyaClient


class BigDataVisitSyncService:
    def __init__(self, avatariya_client: Optional[AvatariyaClient] = None) -> None:
        self.avatariya_client = avatariya_client or AvatariyaClient()

    def sync_visits(self, start_date: date, end_date: date, phones: List[str], force_refresh: bool = False) -> Dict:
        normalized_phones = self._normalize_unique_phones(phones)
        if not normalized_phones:
            return {
                'phones_total': 0,
                'phones_fetched': 0,
                'rows_fetched': 0,
                'inserted': 0,
                'updated': 0,
            }

        days = self._iter_days(start_date, end_date)
        required_days_count = len(days)
        phones_to_fetch = normalized_phones
        if not force_refresh:
            synced_phones = set(
                BigDataPhoneDaySyncState.objects.filter(
                    phone_normalized__in=normalized_phones,
                    date__range=(start_date, end_date),
                )
                .values('phone_normalized')
                .annotate(days_synced=Count('date', distinct=True))
                .filter(days_synced=required_days_count)
                .values_list('phone_normalized', flat=True)
            )
            phones_to_fetch = [phone for phone in normalized_phones if phone not in synced_phones]

        if not phones_to_fetch:
            return {
                'phones_total': len(normalized_phones),
                'phones_fetched': 0,
                'rows_fetched': 0,
                'inserted': 0,
                'updated': 0,
            }

        rows = self.avatariya_client.visit_search_all_by_date_phones(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            phones=phones_to_fetch,
        )

        inserted = 0
        updated = 0
        day_counts: Dict[Tuple[str, date], int] = defaultdict(int)
        for row in rows:
            state = self._upsert_visit_row(row)
            if state == 'inserted':
                inserted += 1
            elif state == 'updated':
                updated += 1

            normalized_phone = self._normalize_phone(row.get('guest_phone'))
            visit_time = self._parse_visit_time(row)
            if normalized_phone and visit_time is not None:
                visit_day = visit_time.date()
                if start_date <= visit_day <= end_date:
                    day_counts[(normalized_phone, visit_day)] += 1

        now = timezone.localtime(timezone.now())
        sync_rows = []
        for phone in phones_to_fetch:
            for day in days:
                sync_rows.append(
                    BigDataPhoneDaySyncState(
                        phone_normalized=phone,
                        date=day,
                        result_count=day_counts.get((phone, day), 0),
                        synced_at=now,
                    )
                )

        if sync_rows:
            BigDataPhoneDaySyncState.objects.bulk_create(
                sync_rows,
                update_conflicts=True,
                unique_fields=['phone_normalized', 'date'],
                update_fields=['result_count', 'synced_at'],
                batch_size=5000,
            )

        return {
            'phones_total': len(normalized_phones),
            'phones_fetched': len(phones_to_fetch),
            'rows_fetched': len(rows),
            'inserted': inserted,
            'updated': updated,
        }

    def build_phone_to_visit_times(self, start_date: date, end_date: date, phones: List[str]) -> Tuple[Dict[str, List], int]:
        normalized_phones = self._normalize_unique_phones(phones)
        if not normalized_phones:
            return {}, 0

        rows = BigDataVisit.objects.filter(
            time_create__date__range=(start_date, end_date),
            guest_phone_normalized__in=normalized_phones,
        ).values_list('guest_phone_normalized', 'time_create')

        mapping: Dict[str, List] = defaultdict(list)
        total = 0
        for phone, visit_time in rows:
            if not phone:
                continue
            mapping[phone].append(visit_time)
            total += 1

        for phone in mapping:
            mapping[phone].sort()

        return mapping, total

    def _upsert_visit_row(self, row: Dict) -> str:
        visit_time = self._parse_visit_time(row)
        if visit_time is None:
            return 'skipped'

        raw_phone = str(row.get('guest_phone') or '').strip()
        normalized_phone = self._normalize_phone(raw_phone)
        bigdata_visit_id = self._extract_bigdata_visit_id(row)

        with transaction.atomic():
            _, created = BigDataVisit.objects.update_or_create(
                bigdata_visit_id=bigdata_visit_id,
                defaults={
                    'guest_phone_raw': raw_phone,
                    'guest_phone_normalized': normalized_phone,
                    'time_create': visit_time,
                    'payload': row,
                },
            )

        if created:
            return 'inserted'
        return 'updated'

    def _extract_bigdata_visit_id(self, row: Dict) -> str:
        for key in ('id', 'visit_id', 'visitId', 'bigdata_id', 'uuid'):
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text

        payload = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        return f'generated:{hashlib.sha256(payload.encode("utf-8")).hexdigest()}'

    def _parse_visit_time(self, row: Dict):
        parsed = parse_datetime(str(row.get('time_create') or '').strip())
        if parsed is None:
            return None
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return timezone.localtime(parsed)

    def _normalize_unique_phones(self, phones: List[str]) -> List[str]:
        unique: List[str] = []
        seen = set()
        for phone in phones:
            normalized = self._normalize_phone(phone)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(normalized)
        return unique

    def _normalize_phone(self, phone: Optional[str]) -> str:
        digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
        if not digits:
            return ''
        if len(digits) == 11 and digits.startswith('8'):
            return '7' + digits[1:]
        return digits

    def _iter_days(self, start_date: date, end_date: date) -> List[date]:
        days = []
        current = start_date
        while current <= end_date:
            days.append(current)
            current += timedelta(days=1)
        return days
