from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from guest_profile.services.phone_utils import normalize_phone_number


class GuestProfileQuerySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)
    orders_limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
    mobile_events_limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)
    cashback_limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)
    crystal_limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)

    default_history_days = 90
    max_range_days = 365

    def validate_phone(self, value: str) -> str:
        normalized = normalize_phone_number(value)
        if not normalized:
            raise serializers.ValidationError('invalid_phone_format')
        return normalized

    def validate(self, attrs):
        today = timezone.localdate()

        from_date = attrs.get('from_date')
        to_date = attrs.get('to_date')

        if from_date is None and to_date is None:
            to_date = today
            from_date = today - timedelta(days=self.default_history_days)
        elif from_date is None:
            from_date = to_date
        elif to_date is None:
            to_date = from_date

        if to_date < from_date:
            raise serializers.ValidationError({'to_date': 'to_date must be greater than or equal to from_date'})

        if (to_date - from_date).days > self.max_range_days:
            raise serializers.ValidationError({'to_date': f'maximum date range is {self.max_range_days} days'})

        attrs['from_date'] = from_date
        attrs['to_date'] = to_date
        return attrs
