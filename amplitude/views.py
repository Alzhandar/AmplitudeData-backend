from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import DailyDeviceActivity, UserEmployeeBinding
from .services.employee_access_service import EmployeeAccessService
from .services.location_presence_service import LocationPresenceAnalyticsService
from .serializers import DailyDeviceActivitySerializer


class DailyDeviceActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyDeviceActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        date_value = self.request.query_params.get('date') or timezone.localdate().isoformat()
        return DailyDeviceActivity.objects.filter(date=date_value).order_by('-last_seen')


class LocationPresenceStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        today = timezone.localdate().isoformat()
        raw_start = request.query_params.get('start_date') or request.query_params.get('date') or today
        raw_end = request.query_params.get('end_date') or raw_start
        raw_window_hours = request.query_params.get('window_hours') or '24'

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

        service = LocationPresenceAnalyticsService()
        try:
            result = service.calculate(start_date=start_date, end_date=end_date, window_hours=window_hours)
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc

        return Response(result)


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = str(request.data.get('username', '')).strip()
        password = str(request.data.get('password', ''))

        if not username or not password:
            raise ValidationError({'detail': 'username and password are required'})

        user = authenticate(request=request, username=username, password=password)
        if user is None:
            raise ValidationError({'detail': 'Invalid credentials'})

        try:
            binding = user.employee_binding
        except UserEmployeeBinding.DoesNotExist as exc:
            raise ValidationError({'detail': 'Employee binding is missing. Please register first.'}) from exc

        access_service = EmployeeAccessService()
        if not access_service.can_access_site(binding.iin):
            raise ValidationError({'detail': 'Employee position is not allowed for this site'})

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                },
                'iin': binding.iin,
            }
        )


class AuthRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = str(request.data.get('username', '')).strip()
        password = str(request.data.get('password', ''))
        iin = str(request.data.get('iin', '')).strip()

        if not username or not password or not iin:
            raise ValidationError({'detail': 'username, password and iin are required'})

        access_service = EmployeeAccessService()
        if not access_service.can_access_site(iin):
            raise ValidationError({'detail': 'Employee position is not allowed for this site'})

        User = get_user_model()
        try:
            with transaction.atomic():
                user = User.objects.create_user(username=username, password=password)
                UserEmployeeBinding.objects.create(user=user, iin=iin)
        except IntegrityError as exc:
            raise ValidationError({'detail': 'Username or IIN is already registered'}) from exc

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                },
                'iin': iin,
            }
        )


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                'id': user.id,
                'username': user.username,
            }
        )


class AuthLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({'status': 'ok'})
