from django.test import SimpleTestCase

from guest_profile.serializers import GuestProfileQuerySerializer
from guest_profile.services.guest_profile_service import GuestProfileService


class GuestProfileQuerySerializerTests(SimpleTestCase):
	def test_normalizes_phone(self):
		serializer = GuestProfileQuerySerializer(data={'phone': '+7 (707) 123-45-67'})
		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(serializer.validated_data['phone'], '77071234567')

	def test_rejects_invalid_phone(self):
		serializer = GuestProfileQuerySerializer(data={'phone': '123'})
		self.assertFalse(serializer.is_valid())
		self.assertIn('phone', serializer.errors)

	def test_rejects_too_wide_date_range(self):
		serializer = GuestProfileQuerySerializer(
			data={
				'phone': '77071234567',
				'from_date': '2024-01-01',
				'to_date': '2026-01-01',
			}
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('to_date', serializer.errors)


class _FakeExternalGuestDataService:
	def __init__(self, *, black_list=2, fail_purchase=False):
		self.black_list = black_list
		self.fail_purchase = fail_purchase

	def find_guest_by_phone(self, normalized_phone):
		return {'id': 123, 'name': 'Test Guest'}

	def get_guest(self, guest_id):
		return {'id': guest_id, 'name': 'Test Guest', 'black_list': self.black_list}

	def get_purchase_history(self, **kwargs):
		if self.fail_purchase:
			raise ValueError('upstream failed')
		return {'count': 1, 'results': [{'id': 1}]}

	def get_cashback_summary(self, **kwargs):
		return {'sum': 10, 'burn_date': None, 'burn_sum': 0}

	def get_cashback_history(self, **kwargs):
		return {'count': 0, 'results': []}

	def get_crystal_summary(self, **kwargs):
		return {'total_crystals': 5}

	def get_crystal_history(self, **kwargs):
		return {'count': 0, 'results': []}


class _FakeMobileActivityService:
	def get_activity_history(self, **kwargs):
		return {'count': 2, 'results': [{'event_type': 'open_home'}, {'event_type': 'open_profile'}]}


class GuestProfileServiceTests(SimpleTestCase):
	def test_maps_blocked_status(self):
		service = GuestProfileService(
			external_service=_FakeExternalGuestDataService(black_list=1),
			mobile_activity_service=_FakeMobileActivityService(),
		)

		payload = service.get_profile_by_phone(
			normalized_phone='77071234567',
			from_date=self._date('2026-01-01'),
			to_date=self._date('2026-01-02'),
			orders_limit=20,
			mobile_events_limit=50,
			cashback_limit=50,
			crystal_limit=50,
		)

		self.assertEqual(payload['guest']['status']['code'], 'blocked')
		self.assertTrue(payload['guest']['status']['is_blocked'])

	def test_collects_warning_on_partial_failure(self):
		service = GuestProfileService(
			external_service=_FakeExternalGuestDataService(fail_purchase=True),
			mobile_activity_service=_FakeMobileActivityService(),
		)

		payload = service.get_profile_by_phone(
			normalized_phone='77071234567',
			from_date=self._date('2026-01-01'),
			to_date=self._date('2026-01-02'),
			orders_limit=20,
			mobile_events_limit=50,
			cashback_limit=50,
			crystal_limit=50,
		)

		self.assertIn('purchase_history_unavailable', payload['warnings'])
		self.assertEqual(payload['purchase_history']['count'], 0)

	def _date(self, value: str):
		from datetime import datetime

		return datetime.strptime(value, '%Y-%m-%d').date()
