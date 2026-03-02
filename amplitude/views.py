from datetime import datetime

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import DailyDeviceActivity
from .services.location_presence_service import LocationPresenceAnalyticsService
from .serializers import DailyDeviceActivitySerializer


class DailyDeviceActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyDeviceActivitySerializer

    def get_queryset(self):
        date_value = self.request.query_params.get('date') or timezone.localdate().isoformat()
        return DailyDeviceActivity.objects.filter(date=date_value).order_by('-last_seen')


class LocationPresenceStatsViewSet(viewsets.ViewSet):
    def list(self, request):
        raw_date = request.query_params.get('date') or timezone.localdate().isoformat()
        raw_window_hours = request.query_params.get('window_hours') or '24'

        try:
            date_value = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValidationError({'date': 'Use YYYY-MM-DD format'}) from exc

        try:
            window_hours = int(raw_window_hours)
        except ValueError as exc:
            raise ValidationError({'window_hours': 'Must be integer'}) from exc

        service = LocationPresenceAnalyticsService()
        try:
            result = service.calculate(date_value=date_value, window_hours=window_hours)
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc

        return Response(result)
