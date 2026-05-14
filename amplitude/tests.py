from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from amplitude.serializers import MobileRegistrationsStatsQuerySerializer
from amplitude.services.mobile_registrations_stats_service import (
    MobileRegistrationsStatsService,
    MobileRegistrationsUpstreamError,
)
from amplitude.views import MobileRegistrationsStatsViewSet


class _FakeMobileClient:
    def __init__(self, payload=None, should_raise=False):
        self.payload = payload or {}
        self.should_raise = should_raise

    def get_new_user_registration_stats(self, year, start_date, end_date):
        if self.should_raise:
            raise ValueError('upstream failure')
        return self.payload


class _FakeEmployeeBinding:
    def __init__(self, iin: str):
        self.iin = iin


class _FakeUser:
    is_authenticated = True

    def __init__(self, user_id: int = 1, iin: str = '123456789012'):
        self.id = user_id
        self.employee_binding = _FakeEmployeeBinding(iin)


class MobileRegistrationsStatsQuerySerializerTests(SimpleTestCase):
    def test_valid_query(self):
        serializer = MobileRegistrationsStatsQuerySerializer(
            data={'year': 2026, 'start_date': '2026-02-01', 'end_date': '2026-02-03'}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_year_mismatch(self):
        serializer = MobileRegistrationsStatsQuerySerializer(
            data={'year': 2025, 'start_date': '2026-02-01', 'end_date': '2026-02-03'}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('year', serializer.errors)

    def test_rejects_date_order(self):
        serializer = MobileRegistrationsStatsQuerySerializer(
            data={'year': 2026, 'start_date': '2026-02-04', 'end_date': '2026-02-03'}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('detail', serializer.errors)


class MobileRegistrationsStatsServiceTests(SimpleTestCase):
    def test_returns_normalized_payload(self):
        service = MobileRegistrationsStatsService(
            mobile_client=_FakeMobileClient(
                payload={
                    'registrations': '1608',
                    'total_users': 229796,
                    'date_from': '2026-02-01',
                    'date_to': '2026-02-03',
                }
            )
        )

        payload = service.get_stats(
            year=2026,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 3),
        )

        self.assertEqual(payload['registrations'], 1608)
        self.assertEqual(payload['total_users'], 229796)
        self.assertEqual(payload['date_from'], '2026-02-01')
        self.assertEqual(payload['date_to'], '2026-02-03')
        self.assertEqual(payload['source'], 'mobile_api')
        self.assertFalse(payload['cached'])

    def test_rejects_invalid_year_or_dates(self):
        service = MobileRegistrationsStatsService(mobile_client=_FakeMobileClient(payload={}))

        with self.assertRaises(ValueError):
            service.get_stats(year=2026, start_date=date(2026, 2, 4), end_date=date(2026, 2, 3))

        with self.assertRaises(ValueError):
            service.get_stats(year=2025, start_date=date(2026, 2, 1), end_date=date(2026, 2, 3))

    def test_maps_upstream_failure(self):
        service = MobileRegistrationsStatsService(mobile_client=_FakeMobileClient(should_raise=True))

        with self.assertRaises(MobileRegistrationsUpstreamError):
            service.get_stats(year=2026, start_date=date(2026, 2, 1), end_date=date(2026, 2, 3))

    def test_invalid_upstream_payload_raises_upstream_error(self):
        service = MobileRegistrationsStatsService(
            mobile_client=_FakeMobileClient(
                payload={
                    'registrations': 'abc',
                    'total_users': 229796,
                    'date_from': '2026-02-01',
                    'date_to': '2026-02-03',
                }
            )
        )

        with self.assertRaises(MobileRegistrationsUpstreamError):
            service.get_stats(year=2026, start_date=date(2026, 2, 1), end_date=date(2026, 2, 3))


class MobileRegistrationsStatsViewSetTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = MobileRegistrationsStatsViewSet.as_view({'get': 'list'})

    def test_returns_200_for_valid_query(self):
        request = self.factory.get(
            '/api/amplitude/mobile-registrations-stats/',
            {'year': '2026', 'start_date': '2026-02-01', 'end_date': '2026-02-03'},
        )
        force_authenticate(request, user=_FakeUser())

        with patch('amplitude.views.EmployeeAccessService.allowed_pages_for_iin', return_value=['analytics']):
            with patch('amplitude.views.MobileRegistrationsStatsService') as service_cls:
                service_cls.return_value.get_stats.return_value = {
                    'registrations': 1608,
                    'total_users': 229796,
                    'date_from': '2026-02-01',
                    'date_to': '2026-02-03',
                    'source': 'mobile_api',
                    'cached': False,
                }
                response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['registrations'], 1608)

    def test_returns_403_without_analytics_access(self):
        request = self.factory.get(
            '/api/amplitude/mobile-registrations-stats/',
            {'year': '2026', 'start_date': '2026-02-01', 'end_date': '2026-02-03'},
        )
        force_authenticate(request, user=_FakeUser())

        with patch('amplitude.views.EmployeeAccessService.allowed_pages_for_iin', return_value=['guest-profile']):
            response = self.view(request)

        self.assertEqual(response.status_code, 403)

    def test_returns_502_when_upstream_fails(self):
        request = self.factory.get(
            '/api/amplitude/mobile-registrations-stats/',
            {'year': '2026', 'start_date': '2026-02-01', 'end_date': '2026-02-03'},
        )
        force_authenticate(request, user=_FakeUser())

        with patch('amplitude.views.EmployeeAccessService.allowed_pages_for_iin', return_value=['analytics']):
            with patch('amplitude.views.MobileRegistrationsStatsService') as service_cls:
                service_cls.return_value.get_stats.side_effect = MobileRegistrationsUpstreamError('upstream failure')
                response = self.view(request)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(str(response.data['detail']), 'upstream failure')
