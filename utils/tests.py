from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

from utils.avatracker_client import AvatrackerClient
from utils.phone_utils import normalize_phone_number, phone_search_variants


class NormalizePhoneNumberTests(SimpleTestCase):
    # Kazakhstan
    def test_kz_full_number(self):
        self.assertEqual(normalize_phone_number('77071234567'), '77071234567')

    def test_kz_legacy_8_prefix(self):
        self.assertEqual(normalize_phone_number('87071234567'), '77071234567')

    def test_kz_with_formatting(self):
        self.assertEqual(normalize_phone_number('+7 (707) 123-45-67'), '77071234567')

    def test_kz_bare_mobile_number(self):
        self.assertEqual(normalize_phone_number('7071234567'), '77071234567')

    def test_kz_10_digits_non_mobile_prefix_rejected(self):
        self.assertEqual(normalize_phone_number('1234567890'), '')

    # Uzbekistan (Tashkent park)
    def test_uz_full_number(self):
        self.assertEqual(normalize_phone_number('998901234567'), '998901234567')

    def test_uz_with_plus_and_formatting(self):
        self.assertEqual(normalize_phone_number('+998 90 123-45-67'), '998901234567')

    def test_uz_bare_mobile_number(self):
        self.assertEqual(normalize_phone_number('901234567'), '998901234567')

    # Invalid input
    def test_empty(self):
        self.assertEqual(normalize_phone_number(''), '')

    def test_none(self):
        self.assertEqual(normalize_phone_number(None), '')

    def test_garbage(self):
        self.assertEqual(normalize_phone_number('abc'), '')


class PhoneSearchVariantsTests(SimpleTestCase):
    def test_kz_variants_include_legacy_8_prefix(self):
        variants = phone_search_variants('77071234567')
        self.assertIn('77071234567', variants)
        self.assertIn('87071234567', variants)
        self.assertIn('+77071234567', variants)

    def test_uz_variants_do_not_include_bogus_8_prefix(self):
        variants = phone_search_variants('998901234567')
        self.assertIn('998901234567', variants)
        self.assertIn('+998901234567', variants)
        self.assertNotIn('898901234567', variants)

    def test_invalid_returns_empty(self):
        self.assertEqual(phone_search_variants('abc'), [])


def _make_detail_response(status_code, payload):
    response = MagicMock()
    response.status_code = status_code
    if status_code < 400:
        response.raise_for_status = MagicMock()
    else:
        response.raise_for_status = MagicMock(side_effect=requests.HTTPError(response=response))
    response.text = ''
    response.json.return_value = payload
    return response


class AvatrackerClientFindByIinTests(SimpleTestCase):
    """/employees/<iin>/ is a direct detail lookup (confirmed live: GET
    /employees/050402501662/ returns that one employee — the path segment is
    the ИИН, not a numeric id) — a single request, no pagination involved."""

    def setUp(self):
        cache.clear()

    @patch('utils.avatracker_client.requests.get')
    def test_found_returns_the_employee_in_one_request(self, mock_get):
        target = {'id': 259, 'iin': '900101300123', 'full_name': 'Test User', 'phone': '77071234567'}
        mock_get.return_value = _make_detail_response(200, {'success': True, 'id': 259, 'data': target, 'error': []})

        client = AvatrackerClient(base_url='https://example.test/api/v1', token='x')
        result = client.find_employee_by_iin('900101300123')

        self.assertEqual(result, target)
        self.assertEqual(mock_get.call_count, 1)
        called_url = mock_get.call_args.args[0]
        self.assertTrue(called_url.endswith('/employees/900101300123/'))

    @patch('utils.avatracker_client.requests.get')
    def test_404_returns_none(self, mock_get):
        mock_get.return_value = _make_detail_response(404, {'detail': "Сотрудник с ИИН '000000000000' не найден"})

        client = AvatrackerClient(base_url='https://example.test/api/v1', token='x')
        result = client.find_employee_by_iin('000000000000')

        self.assertIsNone(result)

    @patch('utils.avatracker_client.requests.get')
    def test_not_found_result_is_cached(self, mock_get):
        mock_get.return_value = _make_detail_response(404, {'detail': 'not found'})

        client = AvatrackerClient(base_url='https://example.test/api/v1', token='x')
        first = client.find_employee_by_iin('000000000000')
        calls_after_first_search = mock_get.call_count
        second = client.find_employee_by_iin('000000000000')

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(mock_get.call_count, calls_after_first_search, 'second lookup should be served from cache')

    @patch('utils.avatracker_client.requests.get')
    def test_found_result_is_cached(self, mock_get):
        target = {'id': 259, 'iin': '900101300123', 'full_name': 'Test User', 'phone': '77071234567'}
        mock_get.return_value = _make_detail_response(200, {'success': True, 'id': 259, 'data': target, 'error': []})

        client = AvatrackerClient(base_url='https://example.test/api/v1', token='x')
        client.find_employee_by_iin('900101300123')
        calls_after_first_search = mock_get.call_count
        result = client.find_employee_by_iin('900101300123')

        self.assertEqual(result, target)
        self.assertEqual(mock_get.call_count, calls_after_first_search)

    def test_blank_iin_returns_none_without_request(self):
        client = AvatrackerClient(base_url='https://example.test/api/v1', token='x')
        self.assertIsNone(client.find_employee_by_iin(''))
        self.assertIsNone(client.find_employee_by_iin(None))
