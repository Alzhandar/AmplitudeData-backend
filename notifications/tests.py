from django.test import SimpleTestCase

from notifications.serializers import PushDispatchRequestSerializer
from notifications.services.push_dispatch_service import PushDispatchService


class PushDispatchRequestSerializerTests(SimpleTestCase):
	def test_phones_target_normalizes_and_deduplicates(self):
		serializer = PushDispatchRequestSerializer(
			data={
				'target': 'phones',
				'phone_numbers': ['8 (707) 123-45-67', '77071234567', '77075554433'],
				'title': 'Title',
				'body': 'Body',
			}
		)

		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(serializer.validated_data['phone_numbers'], ['77071234567', '77075554433'])
		self.assertIsNone(serializer.validated_data['city_id'])

	def test_phones_target_accepts_tashkent_park_numbers(self):
		serializer = PushDispatchRequestSerializer(
			data={
				'target': 'phones',
				'phone_numbers': ['77071234567', '+998901234567', '998907654321'],
				'title': 'Title',
				'body': 'Body',
			}
		)

		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(
			serializer.validated_data['phone_numbers'],
			['77071234567', '998901234567', '998907654321'],
		)

	def test_city_target_requires_city_id(self):
		serializer = PushDispatchRequestSerializer(
			data={
				'target': 'city',
				'title': 'Title',
				'body': 'Body',
			}
		)

		self.assertFalse(serializer.is_valid())
		self.assertIn('city_id', serializer.errors)


class _FakeAvatariyaClient:
	def list_cities(self):
		return [
			{'id': 2, 'name_ru': 'Алматы', 'name_kz': 'Алматы'},
			{'id': 7, 'name_ru': 'Караганда', 'name_kz': 'Караганда'},
			{'id': 5000005, 'name_ru': '', 'name_kz': ''},
		]


class _FakeMobileClient:
	def __init__(self):
		self.calls = []

	def send_mass_push(self, **kwargs):
		self.calls.append(kwargs)
		return 123


class PushDispatchServiceTests(SimpleTestCase):
	def test_list_cities_filters_empty_names_and_search(self):
		service = PushDispatchService(
			avatariya_client=_FakeAvatariyaClient(),
			mobile_client=_FakeMobileClient(),
		)

		cities = service.list_cities(search='кар')
		self.assertEqual(len(cities), 1)
		self.assertEqual(cities[0].id, 7)

	def test_send_mass_push_to_phones(self):
		mobile = _FakeMobileClient()
		service = PushDispatchService(
			avatariya_client=_FakeAvatariyaClient(),
			mobile_client=mobile,
		)

		result = service.send_mass_push(
			target='phones',
			phone_numbers=['77071234567', '77075554433'],
			title='Title',
			body='Body',
			title_kz='Title KZ',
			body_kz='Body KZ',
			notification_type='default',
		)

		self.assertEqual(result.target, 'phones')
		self.assertEqual(result.recipients_count, 2)
		self.assertIsNone(result.city_id)
		self.assertEqual(result.notification_id, 123)
		self.assertEqual(len(mobile.calls), 1)
		self.assertEqual(mobile.calls[0]['phone_numbers'], ['77071234567', '77075554433'])
		self.assertEqual(mobile.calls[0]['city'], '')

	def test_send_mass_push_to_city(self):
		mobile = _FakeMobileClient()
		service = PushDispatchService(
			avatariya_client=_FakeAvatariyaClient(),
			mobile_client=mobile,
		)

		result = service.send_mass_push(
			target='city',
			city_id=7,
			title='Title',
			body='Body',
			notification_type='default',
		)

		self.assertEqual(result.target, 'city')
		self.assertEqual(result.city_id, 7)
		self.assertIsNone(result.recipients_count)
		self.assertEqual(result.notification_id, 123)
		self.assertEqual(len(mobile.calls), 1)
		self.assertIsNone(mobile.calls[0]['phone_numbers'])
		self.assertEqual(mobile.calls[0]['city'], '7')
