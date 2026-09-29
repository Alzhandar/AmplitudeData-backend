from datetime import date
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from amplitude.serializers import MobileRegistrationsStatsQuerySerializer
from amplitude.services.employee_access_service import EmployeeAccessService
from amplitude.services.mobile_registrations_stats_service import (
    MobileRegistrationsStatsService,
    MobileRegistrationsUpstreamError,
)
from amplitude.services.position_directory_service import PositionDirectoryService
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


class _FakeAvatrackerClient:
    def __init__(self, employees=None):
        self.employees = dict(employees or {})

    def find_employee_by_iin(self, iin):
        return self.employees.get(iin)


class EmployeeAccessServiceTests(SimpleTestCase):
    def test_builds_profile_directly_from_avatracker_employee_payload(self):
        # avatracker's employee-by-ИИН response already carries position/
        # position_name inline — no separate position lookup needed.
        client = _FakeAvatrackerClient({
            '900101300123': {
                'iin': '900101300123',
                'full_name': 'Иван Иванов',
                'email': 'Ivan@Example.com',
                'active': True,
                'position': '938780d0-3e44-11ee-83ed-bcf4d42cd2ca',
                'position_name': 'Технический персонал',
            },
        })
        service = EmployeeAccessService(avatracker_client=client)

        profile = service.get_employee_profile('900101300123')

        self.assertIsNotNone(profile)
        self.assertEqual(profile.full_name, 'Иван Иванов')
        self.assertEqual(profile.email, 'ivan@example.com')
        self.assertEqual(profile.position_guid, '938780d0-3e44-11ee-83ed-bcf4d42cd2ca')
        self.assertEqual(profile.position_name, 'Технический персонал')

    def test_returns_none_for_unknown_iin(self):
        service = EmployeeAccessService(avatracker_client=_FakeAvatrackerClient())
        self.assertIsNone(service.get_employee_profile('000000000000'))

    def test_returns_none_for_inactive_employee(self):
        client = _FakeAvatrackerClient({
            '900101300123': {'iin': '900101300123', 'active': False, 'position': 'x', 'position_name': 'y'},
        })
        service = EmployeeAccessService(avatracker_client=client)
        self.assertIsNone(service.get_employee_profile('900101300123'))

    def test_returns_none_for_blank_iin(self):
        service = EmployeeAccessService(avatracker_client=_FakeAvatrackerClient())
        self.assertIsNone(service.get_employee_profile(''))

    def test_upstream_error_returns_none_instead_of_raising(self):
        class _RaisingClient:
            def find_employee_by_iin(self, iin):
                raise ValueError('avatracker unreachable')

        service = EmployeeAccessService(avatracker_client=_RaisingClient())
        self.assertIsNone(service.get_employee_profile('900101300123'))


class _FakePositionDirectoryClient:
    def __init__(self, positions, employees=None):
        self.positions = positions
        self.employees = employees or []

    def list_positions(self):
        return self.positions

    def list_all_employees(self):
        return self.employees


class PositionDirectoryServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_unique_name_uses_the_name_as_is(self):
        client = _FakePositionDirectoryClient(
            positions=[{'name': 'HR manager', 'guid_1c': 'guid-hr'}],
        )
        service = PositionDirectoryService(avatracker_client=client)

        choices = service.list_choices()

        self.assertEqual(choices, [('guid-hr', 'HR manager')])

    def test_duplicate_name_disambiguated_by_most_common_division(self):
        # avatracker's guid_1c values share a long common tail across many
        # unrelated records — only the leading segment is actually unique per
        # record — so fixtures here mimic real UUID shape, not bare strings.
        guid_1 = '93878107-3e44-11ee-83ed-bcf4d42cd2ca'
        guid_2 = '9387811e-3e44-11ee-83ed-bcf4d42cd2ca'
        client = _FakePositionDirectoryClient(
            positions=[
                {'name': 'IT специалист', 'guid_1c': guid_1},
                {'name': 'IT специалист', 'guid_1c': guid_2},
            ],
            employees=[
                {'position': guid_1, 'division_name': 'Головной офис'},
                {'position': guid_1, 'division_name': 'Головной офис'},
                {'position': guid_2, 'division_name': 'Парк Астана'},
            ],
        )
        service = PositionDirectoryService(avatracker_client=client)

        choices = dict(service.list_choices())

        self.assertEqual(choices[guid_1], 'IT специалист — Головной офис (2 чел., 93878107)')
        self.assertEqual(choices[guid_2], 'IT специалист — Парк Астана (1 чел., 9387811e)')

    def test_duplicate_name_with_no_employees_says_so(self):
        guid_1 = '93878107-3e44-11ee-83ed-bcf4d42cd2ca'
        guid_2 = '9387811e-3e44-11ee-83ed-bcf4d42cd2ca'
        client = _FakePositionDirectoryClient(
            positions=[
                {'name': 'Официант', 'guid_1c': guid_1},
                {'name': 'Официант', 'guid_1c': guid_2},
            ],
            employees=[
                {'position': guid_1, 'division_name': 'Ресторан Алматы'},
            ],
        )
        service = PositionDirectoryService(avatracker_client=client)

        choices = dict(service.list_choices())

        self.assertIn('нет сотрудников', choices[guid_2])

    def test_result_is_cached(self):
        calls = {'positions': 0}

        class _CountingClient(_FakePositionDirectoryClient):
            def list_positions(self):
                calls['positions'] += 1
                return super().list_positions()

        client = _CountingClient(positions=[{'name': 'HR manager', 'guid_1c': 'guid-hr'}])
        service = PositionDirectoryService(avatracker_client=client)

        service.list_choices()
        service.list_choices()

        self.assertEqual(calls['positions'], 1)

    def test_force_refresh_bypasses_cache(self):
        calls = {'positions': 0}

        class _CountingClient(_FakePositionDirectoryClient):
            def list_positions(self):
                calls['positions'] += 1
                return super().list_positions()

        client = _CountingClient(positions=[{'name': 'HR manager', 'guid_1c': 'guid-hr'}])
        service = PositionDirectoryService(avatracker_client=client)

        service.list_choices()
        service.list_choices(force_refresh=True)

        self.assertEqual(calls['positions'], 2)

    def test_upstream_failure_returns_empty_list(self):
        class _RaisingClient:
            def list_positions(self):
                raise ValueError('avatracker unreachable')

        service = PositionDirectoryService(avatracker_client=_RaisingClient())
        self.assertEqual(service.list_choices(), [])
