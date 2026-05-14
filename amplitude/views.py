import logging
from datetime import datetime
from typing import Any, Dict

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from .models import DailyDeviceActivity, LocationPresenceStatsCache, UserEmployeeBinding
from .permissions import HasAnalyticsAccess
from .serializers import (
    DailyDeviceActivitySerializer,
    MobileRegistrationsStatsQuerySerializer,
    MobileRegistrationsStatsResponseSerializer,
)
from .services.employee_access_service import EmployeeAccessService
from .services.location_presence_service import LocationPresenceAnalyticsService
from .services.mobile_registrations_stats_service import MobileRegistrationsStatsService, MobileRegistrationsUpstreamError

logger = logging.getLogger(__name__)


class MobileRegistrationsGatewayUnavailable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'Mobile registrations service is temporarily unavailable.'
    default_code = 'mobile_registrations_gateway_unavailable'


class DailyDeviceActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyDeviceActivitySerializer
    permission_classes = [IsAuthenticated, HasAnalyticsAccess]

    def get_queryset(self):
        date_value = self.request.query_params.get('date') or timezone.localdate().isoformat()
        return DailyDeviceActivity.objects.filter(date=date_value).order_by('-last_seen')


class LocationPresenceStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasAnalyticsAccess]
    max_sync_range_days = 3

    def list(self, request):
        today = timezone.localdate().isoformat()
        raw_start = request.query_params.get('start_date') or request.query_params.get('date') or today
        raw_end = request.query_params.get('end_date') or raw_start
        raw_window_hours = request.query_params.get('window_hours') or '24'
        raw_sync = (request.query_params.get('sync') or '0').strip().lower()
        raw_refresh = (request.query_params.get('refresh') or '0').strip().lower()

        try:
            start_date = datetime.strptime(raw_start, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValidationError({'start_date': 'Use YYYY-MM-DD format'}) from exc

        try:
            end_date = datetime.strptime(raw_end, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValidationError({'end_date': 'Use YYYY-MM-DD format'}) from exc

        try:
            window_hours = int(raw_window_hours)
        except ValueError as exc:
            raise ValidationError({'window_hours': 'Must be integer'}) from exc

        auto_sync = raw_sync in {'1', 'true', 'yes'}
        force_refresh = raw_refresh in {'1', 'true', 'yes'}
        range_days = (end_date - start_date).days + 1

        cache_row = LocationPresenceStatsCache.objects.filter(
            start_date=start_date,
            end_date=end_date,
            window_hours=window_hours,
        ).first()

        if cache_row and not force_refresh:
            payload = dict(cache_row.payload or {})
            payload['cached'] = True
            payload['cached_at'] = cache_row.updated_at.isoformat()
            return Response(payload)

        if auto_sync and range_days > self.max_sync_range_days:
            raise ValidationError(
                {
                    'detail': (
                        f'sync=1 is allowed only up to {self.max_sync_range_days} days '
                        f'(requested: {range_days})'
                    )
                }
            )

        service = LocationPresenceAnalyticsService()
        try:
            result = service.calculate(
                start_date=start_date,
                end_date=end_date,
                window_hours=window_hours,
                auto_sync=auto_sync,
            )
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc

        LocationPresenceStatsCache.objects.update_or_create(
            start_date=start_date,
            end_date=end_date,
            window_hours=window_hours,
            defaults={'payload': result},
        )

        result = dict(result)
        result['cached'] = False

        return Response(result)


class MobileRegistrationsStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasAnalyticsAccess]

    def list(self, request):
        query_serializer = MobileRegistrationsStatsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data

        service = MobileRegistrationsStatsService()
        try:
            payload = service.get_stats(
                year=validated['year'],
                start_date=validated['start_date'],
                end_date=validated['end_date'],
            )
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        except MobileRegistrationsUpstreamError as exc:
            logger.exception(
                'Mobile registrations stats upstream failure',
                extra={
                    'year': validated['year'],
                    'start_date': validated['start_date'].isoformat(),
                    'end_date': validated['end_date'].isoformat(),
                    'user_id': getattr(request.user, 'id', None),
                },
            )
            raise MobileRegistrationsGatewayUnavailable(str(exc))

        response_serializer = MobileRegistrationsStatsResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data)


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        password = str(request.data.get('password', ''))

        if not email or not password:
            raise ValidationError({'detail': 'email and password are required'})

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise ValidationError({'detail': 'Invalid credentials'})

        user = authenticate(request=request, username=user.username, password=password)
        if user is None:
            raise ValidationError({'detail': 'Invalid credentials'})

        try:
            binding = user.employee_binding
        except UserEmployeeBinding.DoesNotExist as exc:
            raise ValidationError({'detail': 'Employee binding is missing. Please register first.'}) from exc

        access_service = EmployeeAccessService()
        profile = access_service.get_employee_profile(binding.iin)
        if profile is None:
            raise ValidationError({'detail': 'Employee was not found or has no access to this site'})

        allowed_pages = access_service.allowed_pages_for_position(profile.position_guid)

        token, _ = Token.objects.get_or_create(user=user)
        payload = _build_auth_response(
            user=user,
            iin=binding.iin,
            profile=profile,
            allowed_pages=allowed_pages,
        )
        payload['token'] = token.key
        return Response(payload)


class AuthRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        password = str(request.data.get('password', ''))
        iin = str(request.data.get('iin', '')).strip()

        if not email or not password or not iin:
            raise ValidationError({'detail': 'email, password and iin are required'})

        access_service = EmployeeAccessService()
        profile = access_service.get_employee_profile(iin)
        if profile is None:
            raise ValidationError({'detail': 'Employee was not found or has no access to this site'})

        User = get_user_model()
        if UserEmployeeBinding.objects.filter(iin=iin).exists():
            raise ValidationError({'detail': 'IIN is already registered'})
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({'detail': 'Email is already registered'})

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                )
                UserEmployeeBinding.objects.create(user=user, iin=iin)
        except IntegrityError as exc:
            raise ValidationError({'detail': 'Email or IIN is already registered'}) from exc

        allowed_pages = access_service.allowed_pages_for_position(profile.position_guid)

        token, _ = Token.objects.get_or_create(user=user)
        payload = _build_auth_response(
            user=user,
            iin=iin,
            profile=profile,
            allowed_pages=allowed_pages,
        )
        payload['token'] = token.key
        return Response(payload)


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        iin = ''
        try:
            iin = user.employee_binding.iin
        except UserEmployeeBinding.DoesNotExist:
            pass

        access_service = EmployeeAccessService()
        profile = access_service.get_employee_profile(iin) if iin else None
        allowed_pages = access_service.allowed_pages_for_position(profile.position_guid) if profile else []
        return Response(
            _build_auth_response(
                user=user,
                iin=iin,
                profile=profile,
                allowed_pages=allowed_pages,
            )
        )


class AuthLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({'status': 'ok'})


def _build_auth_response(
    *,
    user,
    iin: str,
    profile,
    allowed_pages,
) -> Dict[str, Any]:
    return {
        'user': {
            'id': user.id,
            'email': user.email,
            'full_name': profile.full_name if profile else '',
            'position': {
                'guid': profile.position_guid if profile else '',
                'name': profile.position_name if profile else '',
            },
        },
        'iin': iin,
        'allowed_pages': allowed_pages,
    }
