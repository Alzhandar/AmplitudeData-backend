from django.test import SimpleTestCase

from employee_discount_check.serializers import (
	EmployeeDiscountCheckQuerySerializer,
	EmployeeLookupQuerySerializer,
	EmployeeLookupResponseSerializer,
	EmployeePhoneChangeRequestSerializer,
)
from employee_discount_check.services.employee_discount_check_service import EmployeeDiscountCheckService
from employee_discount_check.services.employee_phone_change_service import (
	EmployeeNotFoundError,
	EmployeePhoneChangeService,
	PhoneAlreadyInUseError,
)


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


class EmployeePhoneChangeRequestSerializerTests(SimpleTestCase):
	def test_accepts_phone_identifier(self):
		serializer = EmployeePhoneChangeRequestSerializer(
			data={'identifier': '8 707 123 45 67', 'new_phone': '+998 90 123 45 67'}
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(serializer.validated_data['identifier'], '8 707 123 45 67')
		self.assertEqual(serializer.validated_data['new_phone'], '998901234567')

	def test_accepts_iin_identifier(self):
		# ИИН isn't a valid phone shape — identifier is passed through as-is,
		# the service decides how to interpret it.
		serializer = EmployeePhoneChangeRequestSerializer(
			data={'identifier': '900101300123', 'new_phone': '77071234567'}
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(serializer.validated_data['identifier'], '900101300123')

	def test_rejects_invalid_new_phone(self):
		serializer = EmployeePhoneChangeRequestSerializer(
			data={'identifier': '77071234567', 'new_phone': 'abc'}
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('new_phone', serializer.errors)

	def test_rejects_blank_identifier(self):
		serializer = EmployeePhoneChangeRequestSerializer(
			data={'identifier': '   ', 'new_phone': '77071234567'}
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('identifier', serializer.errors)


class _FakeAvatrackerClient:
	def __init__(self, by_phone=None, by_iin=None):
		# by_phone: dict phone -> employee dict; by_iin: dict iin -> employee dict
		self.by_phone = dict(by_phone or {})
		self.by_iin = dict(by_iin or {})
		self.updated = []

	def find_employee_by_phone(self, phone_number):
		return self.by_phone.get(phone_number)

	def find_employee_by_iin(self, iin):
		return self.by_iin.get(iin)

	def update_employee_phone(self, employee_id, new_phone):
		self.updated.append((employee_id, new_phone))
		for store in (self.by_phone, self.by_iin):
			for key, employee in list(store.items()):
				if str(employee.get('id')) == str(employee_id):
					employee['phone'] = new_phone
		# also make the employee findable under their new phone going forward
		for store in (self.by_phone,):
			for employee in list(store.values()):
				if str(employee.get('id')) == str(employee_id):
					store[new_phone] = employee
					break
		return {}


class EmployeePhoneChangeServiceTests(SimpleTestCase):
	def test_changes_phone_when_found_by_phone(self):
		client = _FakeAvatrackerClient(by_phone={
			'77071234567': {'id': 1, 'full_name': 'Иван Иванов', 'phone': '77071234567'},
		})
		service = EmployeePhoneChangeService(avatracker_client=client)

		result = service.change_phone(identifier='77071234567', new_phone='998901234567')

		self.assertEqual(result['employee_id'], '1')
		self.assertEqual(result['old_phone'], '77071234567')
		self.assertEqual(result['new_phone'], '998901234567')
		self.assertEqual(client.updated, [(1, '998901234567')])

	def test_falls_back_to_iin_when_phone_not_found(self):
		# The exact recurring case that prompted this feature: the employee's
		# avatracker phone doesn't match what they want to search/change to.
		employee = {'id': 5, 'full_name': 'Петр Петров', 'phone': '77009998877', 'iin': '900101300123'}
		client = _FakeAvatrackerClient(
			by_phone={'77009998877': employee},
			by_iin={'900101300123': employee},
		)
		service = EmployeePhoneChangeService(avatracker_client=client)

		# Staff types the ИИН because searching by the desired new phone (or any
		# phone the employee gives) doesn't find anyone.
		result = service.change_phone(identifier='900101300123', new_phone='77077778899')

		self.assertEqual(result['employee_id'], '5')
		self.assertEqual(result['old_phone'], '77009998877')
		self.assertEqual(result['new_phone'], '77077778899')
		self.assertEqual(client.updated, [(5, '77077778899')])

	def test_find_employee_with_source_reports_iin_match(self):
		employee = {'id': 5, 'full_name': 'Петр Петров', 'phone': '77009998877', 'iin': '900101300123'}
		client = _FakeAvatrackerClient(by_iin={'900101300123': employee})
		service = EmployeePhoneChangeService(avatracker_client=client)

		found, matched_by = service.find_employee_with_source('900101300123')

		self.assertEqual(found, employee)
		self.assertEqual(matched_by, 'iin')

	def test_raises_when_not_found_by_phone_or_iin(self):
		client = _FakeAvatrackerClient()
		service = EmployeePhoneChangeService(avatracker_client=client)

		with self.assertRaises(EmployeeNotFoundError):
			service.change_phone(identifier='900101300123', new_phone='998901234567')

	def test_raises_when_new_phone_belongs_to_another_employee(self):
		client = _FakeAvatrackerClient(by_phone={
			'77071234567': {'id': 1, 'full_name': 'Иван Иванов', 'phone': '77071234567'},
			'998901234567': {'id': 2, 'full_name': 'Петр Петров', 'phone': '998901234567'},
		})
		service = EmployeePhoneChangeService(avatracker_client=client)

		with self.assertRaises(PhoneAlreadyInUseError):
			service.change_phone(identifier='77071234567', new_phone='998901234567')

		self.assertEqual(client.updated, [])

	def test_no_op_when_new_phone_matches_current_phone(self):
		client = _FakeAvatrackerClient(by_phone={
			'77071234567': {'id': 1, 'full_name': 'Иван Иванов', 'phone': '77071234567'},
		})
		service = EmployeePhoneChangeService(avatracker_client=client)

		result = service.change_phone(identifier='77071234567', new_phone='77071234567')

		self.assertEqual(client.updated, [])
		self.assertEqual(result['new_phone'], '77071234567')


class EmployeeLookupSerializerTests(SimpleTestCase):
	def test_query_rejects_blank_identifier(self):
		serializer = EmployeeLookupQuerySerializer(data={'identifier': '  '})
		self.assertFalse(serializer.is_valid())
		self.assertIn('identifier', serializer.errors)

	def test_response_found_by_iin(self):
		serializer = EmployeeLookupResponseSerializer(data={
			'found': True,
			'matched_by': 'iin',
			'employee_id': '5',
			'employee_name': 'Петр Петров',
			'employee_department': 'Ресторан Астана',
			'employee_position': 'Официант',
			'current_phone': '77009998877',
			'iin': '900101300123',
		})
		self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_response_not_found(self):
		serializer = EmployeeLookupResponseSerializer(data={'found': False, 'matched_by': 'none'})
		self.assertTrue(serializer.is_valid(), serializer.errors)
