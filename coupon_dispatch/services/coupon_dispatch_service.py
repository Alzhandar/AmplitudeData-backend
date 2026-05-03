from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.utils import timezone

from coupon_dispatch.models import (
    CouponDispatchInputSource,
    CouponDispatchJob,
    CouponDispatchJobResult,
    CouponDispatchJobStatus,
)
from utils.avatariya_client import AvatariyaClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketingSaleOption:
    id: int
    name: str
    available_coupons: int


@dataclass(frozen=True)
class ParsedPhoneRow:
    phone_raw: str
    phone_normalized: str
    valid: bool
    error_message: str


class CouponDispatchService:
    def __init__(
        self,
        avatariya_client: Optional[AvatariyaClient] = None,
    ) -> None:
        self.avatariya_client = avatariya_client or AvatariyaClient()

    def list_marketing_sales_with_available_coupons(self, search: str = '') -> List[MarketingSaleOption]:
        raw_items = self.avatariya_client.list_coupon_assign_marketing_sales()
        normalized_search = str(search or '').strip().lower()
        options: List[MarketingSaleOption] = []

        for item in raw_items:
            sale_id = self._to_int(item.get('id'))
            if sale_id is None:
                continue

            status = item.get('status')
            if status is False:
                continue

            sale_name = str(item.get('name') or '').strip()
            if normalized_search and normalized_search not in sale_name.lower():
                continue

            free_coupons_count = self._to_int(item.get('free_coupons_count')) or 0
            options.append(
                MarketingSaleOption(
                    id=sale_id,
                    name=sale_name,
                    available_coupons=max(free_coupons_count, 0),
                )
            )

        options.sort(key=lambda value: (-value.available_coupons, value.name.lower()))
        return options

    def create_job(
        self,
        *,
        user,
        title: str,
        marketing_sale_id: int,
        marketing_sale_name: str,
        phones_text: str,
        source_file,
    ) -> CouponDispatchJob:
        normalized_title = (title or '').strip()
        if not normalized_title:
            raise ValueError('Coupon title is required')

        has_text = bool((phones_text or '').strip())
        has_file = bool(source_file)
        if not has_text and not has_file:
            raise ValueError('Provide manual phone numbers or an Excel file')

        if has_text and has_file:
            input_source = CouponDispatchInputSource.MIXED
        elif has_file:
            input_source = CouponDispatchInputSource.EXCEL
        else:
            input_source = CouponDispatchInputSource.MANUAL

        job = CouponDispatchJob.objects.create(
            title=normalized_title,
            marketing_sale_id=marketing_sale_id,
            marketing_sale_name=(marketing_sale_name or '').strip(),
            initiated_by=user,
            input_source=input_source,
            source_text=phones_text or '',
            source_file=source_file,
            status=CouponDispatchJobStatus.PENDING,
        )
        return job

    def process_job(self, job_id: int) -> Dict[str, Any]:
        job = CouponDispatchJob.objects.filter(id=job_id).first()
        if not job:
            raise ValueError(f'Coupon dispatch job {job_id} does not exist')

        now = timezone.now()
        claimed = CouponDispatchJob.objects.filter(
            id=job_id,
            status=CouponDispatchJobStatus.PENDING,
            coupons_assigned=0,
        ).update(
            status=CouponDispatchJobStatus.PROCESSING,
            started_at=now,
            finished_at=None,
            error_log='',
            updated_at=now,
        )
        if claimed == 0:
            job = CouponDispatchJob.objects.filter(id=job_id).first()
            logger.info(
                'Coupon dispatch job %s skipped: status=%s assigned=%s',
                job_id,
                job.status if job else 'missing',
                job.coupons_assigned if job else 'n/a',
            )
            return {
                'status': 'skipped',
                'reason': 'non_pending_or_already_assigned',
                'job_status': job.status if job else 'missing',
            }

        job = CouponDispatchJob.objects.filter(id=job_id).first()
        logger.info('Coupon dispatch job %s started', job_id)

        try:
            raw_phones = self._collect_raw_phones(job)
            parsed_rows = [self._parse_phone(phone) for phone in raw_phones]

            valid_rows: List[ParsedPhoneRow] = []
            seen = set()
            result_rows: List[CouponDispatchJobResult] = []

            for parsed in parsed_rows:
                if not parsed.valid:
                    result_rows.append(
                        CouponDispatchJobResult(
                            job=job,
                            phone_raw=parsed.phone_raw,
                            phone_normalized='',
                            success=False,
                            error_message=parsed.error_message,
                        )
                    )
                    continue

                if parsed.phone_normalized in seen:
                    result_rows.append(
                        CouponDispatchJobResult(
                            job=job,
                            phone_raw=parsed.phone_raw,
                            phone_normalized=parsed.phone_normalized,
                            success=False,
                            error_message='Duplicate phone in input',
                        )
                    )
                    continue

                seen.add(parsed.phone_normalized)
                valid_rows.append(parsed)

            pre_validation_errors = sum(1 for row in result_rows if not row.success)
            job.total_phones = len(raw_phones)
            job.unique_phones = len(valid_rows)
            job.errors_count = pre_validation_errors
            job.save(update_fields=['total_phones', 'unique_phones', 'errors_count', 'updated_at'])

            guests_found = 0
            coupons_assigned = 0
            mobile_sent_count = 0
            assign_responses: List[Dict[str, Any]] = []

            for row in valid_rows:
                try:
                    assign_result = self.avatariya_client.assign_coupon_via_admin(
                        marketing_sale_id=job.marketing_sale_id,
                        phone_number=row.phone_normalized,
                        amount=job.title,
                    )
                except Exception as exc:
                    result_rows.append(
                        CouponDispatchJobResult(
                            job=job,
                            phone_raw=row.phone_raw,
                            phone_normalized=row.phone_normalized,
                            success=False,
                            error_message=f'Assign API failed: {exc}',
                        )
                    )
                    continue

                assigned = bool(assign_result.get('assigned'))
                guest_id = self._to_int(assign_result.get('guest_id'))
                coupon_id = self._to_int(assign_result.get('coupon_id'))
                coupon_code = str(assign_result.get('coupon_code') or '').strip()
                mobile_sent = bool(assign_result.get('mobile_sent'))

                if guest_id is not None:
                    guests_found += 1
                if mobile_sent:
                    mobile_sent_count += 1

                if assigned:
                    coupons_assigned += 1
                    result_rows.append(
                        CouponDispatchJobResult(
                            job=job,
                            phone_raw=row.phone_raw,
                            phone_normalized=row.phone_normalized,
                            guest_id=guest_id,
                            coupon_id=coupon_id,
                            coupon_code=coupon_code,
                            success=True,
                            error_message='',
                        )
                    )
                else:
                    message = str(assign_result.get('message') or assign_result.get('mobile_message') or 'Coupon was not assigned').strip()
                    result_rows.append(
                        CouponDispatchJobResult(
                            job=job,
                            phone_raw=row.phone_raw,
                            phone_normalized=row.phone_normalized,
                            guest_id=guest_id,
                            coupon_id=coupon_id,
                            coupon_code=coupon_code,
                            success=False,
                            error_message=message,
                        )
                    )

                assign_responses.append(
                    {
                        'phone': row.phone_normalized,
                        'assigned': assigned,
                        'message': str(assign_result.get('message') or ''),
                        'mobile_message': str(assign_result.get('mobile_message') or ''),
                        'mobile_sent': mobile_sent,
                        'coupon_id': coupon_id,
                        'coupon_code': coupon_code,
                    }
                )

            CouponDispatchJobResult.objects.filter(job=job).delete()
            if result_rows:
                CouponDispatchJobResult.objects.bulk_create(result_rows, batch_size=500)

            errors_count = sum(1 for row in result_rows if not row.success)
            error_log_items = [row.error_message for row in result_rows if row.error_message]

            free_count_after = self._get_free_coupons_count_for_sale(job.marketing_sale_id)
            mobile_api_sent = mobile_sent_count > 0
            mobile_api_response: Dict[str, Any] = {
                'assign_api_path': '/api/v1/admin/coupon-assign/assign/',
                'attempted': len(valid_rows),
                'mobile_sent_count': mobile_sent_count,
                'responses_sample': assign_responses[:100],
            }

            job.status = CouponDispatchJobStatus.COMPLETED
            job.total_phones = len(raw_phones)
            job.unique_phones = len(valid_rows)
            job.guests_found = guests_found
            job.available_coupons = free_count_after
            job.coupons_assigned = coupons_assigned
            job.errors_count = errors_count
            job.mobile_api_sent = mobile_api_sent
            job.mobile_api_response = mobile_api_response
            job.mobile_api_sent_at = timezone.now() if mobile_api_sent else None
            job.error_log = '\n'.join(error_log_items)[:8000]
            job.finished_at = timezone.now()
            job.save(
                update_fields=[
                    'status',
                    'total_phones',
                    'unique_phones',
                    'guests_found',
                    'available_coupons',
                    'coupons_assigned',
                    'errors_count',
                    'mobile_api_sent',
                    'mobile_api_response',
                    'mobile_api_sent_at',
                    'error_log',
                    'finished_at',
                    'updated_at',
                ]
            )

            logger.info(
                'Coupon dispatch job %s finished: status=%s assigned=%s errors=%s',
                job.id,
                job.status,
                job.coupons_assigned,
                job.errors_count,
            )
            return {
                'job_id': job.id,
                'status': job.status,
                'coupons_assigned': job.coupons_assigned,
                'errors_count': job.errors_count,
            }
        except Exception as exc:
            logger.exception('Coupon dispatch job %s failed with exception', job.id)
            job.status = CouponDispatchJobStatus.FAILED
            job.finished_at = timezone.now()
            job.error_log = f'{job.error_log}\nUnhandled exception: {exc}'.strip()
            job.save(update_fields=['status', 'finished_at', 'error_log', 'updated_at'])
            raise

    def _get_free_coupons_count_for_sale(self, marketing_sale_id: int) -> int:
        try:
            sales = self.avatariya_client.list_coupon_assign_marketing_sales()
        except Exception:
            logger.exception('Failed to fetch marketing sales for free_coupons_count')
            return 0

        for item in sales:
            sale_id = self._to_int(item.get('id'))
            if sale_id == marketing_sale_id:
                return self._to_int(item.get('free_coupons_count')) or 0
        return 0

    def _collect_raw_phones(self, job: CouponDispatchJob) -> List[str]:
        values: List[str] = []

        if job.source_text.strip():
            values.extend(self._split_text_phones(job.source_text))

        if job.source_file:
            values.extend(self._read_excel_phones(job.source_file.read()))

        return [value for value in values if value]

    def _split_text_phones(self, source_text: str) -> List[str]:
        text = source_text.replace('\r', '\n').replace(';', '\n').replace(',', '\n')
        values: List[str] = []
        for raw_line in text.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            if self._is_phone_header_label(line):
                continue
            values.append(line)
        return values

    def _read_excel_phones(self, binary: bytes) -> List[str]:
        from openpyxl import load_workbook

        workbook = load_workbook(filename=io.BytesIO(binary), data_only=True)
        sheet = workbook.active
        phones: List[str] = []
        for row in sheet.iter_rows(min_row=1, min_col=1, max_col=1):
            value = row[0].value
            if value is None:
                continue
            normalized = str(value).strip()
            if normalized:
                if self._is_phone_header_label(normalized):
                    continue
                phones.append(normalized)
        return phones

    def _is_phone_header_label(self, value: str) -> bool:
        cleaned = ''.join(ch.lower() for ch in str(value) if ch.isalnum() or ch in {' ', '_', '-'})
        cleaned = cleaned.strip().replace('-', ' ').replace('_', ' ')
        collapsed = ' '.join(cleaned.split())
        compact = collapsed.replace(' ', '')

        candidates = {
            'phone',
            'phones',
            'phone number',
            'phone numbers',
            'phonenumber',
            'phonenumbers',
            'телефон',
            'телефоны',
            'номер телефона',
            'номертелефона',
        }
        return collapsed in candidates or compact in candidates

    def _parse_phone(self, phone_raw: str) -> ParsedPhoneRow:
        normalized = ''.join(ch for ch in str(phone_raw or '') if ch.isdigit())
        if not normalized:
            return ParsedPhoneRow(phone_raw=phone_raw, phone_normalized='', valid=False, error_message='Phone is empty')

        if len(normalized) == 11 and normalized.startswith('8'):
            normalized = f'7{normalized[1:]}'

        if len(normalized) != 11 or not normalized.startswith('7'):
            return ParsedPhoneRow(
                phone_raw=phone_raw,
                phone_normalized='',
                valid=False,
                error_message='Phone must be in 11-digit format and start with 7',
            )

        return ParsedPhoneRow(phone_raw=phone_raw, phone_normalized=normalized, valid=True, error_message='')

    def _to_int(self, value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
