from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from django.db.models import Q

from amplitude.models import MobileSession
from guest_profile.services.phone_utils import phone_search_variants


class MobileActivityService:
    def __init__(self, model=MobileSession) -> None:
        self.model = model

    def get_activity_history(
        self,
        *,
        normalized_phone: str,
        from_date: date,
        to_date: date,
        limit: int,
    ) -> Dict[str, Any]:
        variants = phone_search_variants(normalized_phone)
        if not variants:
            return {'count': 0, 'results': []}

        phone_filter = Q()
        for variant in variants:
            phone_filter |= Q(phone_number__icontains=variant)

        base_qs = self.model.objects.filter(date__gte=from_date, date__lte=to_date).filter(phone_filter)
        total_count = base_qs.count()
        rows = base_qs.order_by('-event_time')[:limit]

        results: List[Dict[str, Optional[str]]] = []
        for row in rows:
            results.append(
                {
                    'event_time': row.event_time.isoformat() if row.event_time else None,
                    'event_type': str(row.event_type or '').strip(),
                    'platform': str(row.platform or '').strip(),
                    'device_id': str(row.device_id or '').strip(),
                    'device_model': str(row.device_model or '').strip(),
                    'device_brand': str(row.device_brand or '').strip(),
                    'phone_number': str(row.phone_number or '').strip(),
                }
            )

        return {
            'count': total_count,
            'results': results,
        }
