from rest_framework import serializers

from .models import DailyDeviceActivity


class DailyDeviceActivitySerializer(serializers.ModelSerializer):
    visit_times = serializers.SerializerMethodField()

    class Meta:
        model = DailyDeviceActivity
        fields = (
            'date',
            'user_id',
            'device_id',
            'phone_number',
            'platform',
            'device_brand',
            'device_manufacturer',
            'device_model',
            'visits_count',
            'visit_times',
            'first_seen',
            'last_seen',
        )

    def get_visit_times(self, obj):
        return [
            visit_time.isoformat()
            for visit_time in obj.visit_records.order_by('event_time').values_list('event_time', flat=True)
        ]


class MobileRegistrationsStatsQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(required=True, min_value=2000, max_value=2100)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    def validate(self, attrs):
        start_date = attrs['start_date']
        end_date = attrs['end_date']
        year = attrs['year']

        if start_date > end_date:
            raise serializers.ValidationError({'detail': 'start_date must be <= end_date'})

        range_days = (end_date - start_date).days + 1
        if range_days > 366:
            raise serializers.ValidationError({'detail': 'date range must be <= 366 days'})

        if start_date.year != year or end_date.year != year:
            raise serializers.ValidationError({'year': 'year must match both start_date and end_date'})

        return attrs


class MobileRegistrationsStatsResponseSerializer(serializers.Serializer):
    registrations = serializers.IntegerField(min_value=0)
    total_users = serializers.IntegerField(min_value=0)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    source = serializers.CharField()
    cached = serializers.BooleanField()
