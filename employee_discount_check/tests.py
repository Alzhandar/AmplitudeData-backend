from django.test import SimpleTestCase

from employee_discount_check.serializers import EmployeeDiscountCheckQuerySerializer
from employee_discount_check.services.employee_discount_check_service import EmployeeDiscountCheckService


class EmployeeDiscountCheckQuerySerializerTests(SimpleTestCase):
	def test_normalizes_phone(self):
		serializer = EmployeeDiscountCheckQuerySerializer(data={'phone': '+7 (707) 123-45-67'})
		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(serializer.validated_data['phone'], '77071234567')

	def test_rejects_invalid_phone(self):
		serializer = EmployeeDiscountCheckQuerySerializer(data={'phone': '123'})
		self.assertFalse(serializer.is_valid())
		self.assertIn('phone', serializer.errors)


class _FakeAvatariyaClient:
	def __init__(self, *, restaurant=None, park=None, raise_for_scope=None):
		self.restaurant = restaurant
		self.park = park
		self.raise_for_scope = raise_for_scope

	def check_employee_discount(self, phone_number, discount_scope):
		if self.raise_for_scope == discount_scope:
			raise ValueError('upstream failed')
		if discount_scope == 'restaurant':
			return self.restaurant
		return self.park


class EmployeeDiscountCheckServiceTests(SimpleTestCase):
	def test_combines_both_scopes(self):
		service = EmployeeDiscountCheckService(
			avatariya_client=_FakeAvatariyaClient(
				restaurant={'eligible': True, 'employee_name': 'Иван Иванов', 'remaining_discounts': 5},
				park={'eligible': False, 'employee_name': 'Иван Иванов', 'remaining_discounts': 0},
			)
		)

		payload = service.check(phone_number='77071234567')

		self.assertTrue(payload['employee_found'])
		self.assertTrue(payload['restaurant']['eligible'])
		self.assertFalse(payload['park']['eligible'])
		self.assertEqual(payload['restaurant']['discount_scope'], 'restaurant')
		self.assertEqual(payload['park']['discount_scope'], 'park')

	def test_employee_not_found_in_either_scope(self):
		service = EmployeeDiscountCheckService(
			avatariya_client=_FakeAvatariyaClient(
				restaurant={'eligible': False},
				park={'eligible': False},
			)
		)

		payload = service.check(phone_number='77071234567')

		self.assertFalse(payload['employee_found'])
		self.assertFalse(payload['restaurant']['eligible'])
		self.assertFalse(payload['park']['eligible'])

	def test_one_scope_upstream_failure_does_not_break_the_other(self):
		service = EmployeeDiscountCheckService(
			avatariya_client=_FakeAvatariyaClient(
				park={'eligible': True, 'employee_name': 'Иван Иванов'},
				raise_for_scope='restaurant',
			)
		)

		payload = service.check(phone_number='77071234567')

		self.assertFalse(payload['restaurant']['eligible'])
		self.assertTrue(payload['park']['eligible'])
		self.assertTrue(payload['employee_found'])
