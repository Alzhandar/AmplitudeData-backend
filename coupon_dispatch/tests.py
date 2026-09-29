from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.utils import timezone

from coupon_dispatch.serializers import CouponDispatchJobCreateSerializer
from coupon_dispatch.services.coupon_dispatch_service import CouponDispatchService


class CouponDispatchJobCreateSerializerTests(SimpleTestCase):
	def test_requires_valid_until(self):
		serializer = CouponDispatchJobCreateSerializer(
			data={
				'dispatch_mode': 'marketing_sale',
				'title': 'Купон 15%',
				'marketing_sale_id': 42,
				'phones_text': '77071112233',
			}
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('valid_until', serializer.errors)

	def test_rejects_past_valid_until(self):
		yesterday = timezone.localdate() - timedelta(days=1)
		serializer = CouponDispatchJobCreateSerializer(
			data={
				'dispatch_mode': 'marketing_sale',
				'title': 'Купон 15%',
				'marketing_sale_id': 42,
				'valid_until': yesterday.isoformat(),
				'phones_text': '77071112233',
			}
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('valid_until', serializer.errors)

	def test_requires_source(self):
		serializer = CouponDispatchJobCreateSerializer(
			data={
				'dispatch_mode': 'marketing_sale',
				'title': 'Купон 15%',
				'marketing_sale_id': 42,
				'valid_until': timezone.localdate().isoformat(),
			}
		)
		self.assertFalse(serializer.is_valid())

	def test_rejects_invalid_file_extension(self):
		serializer = CouponDispatchJobCreateSerializer(
			data={
				'dispatch_mode': 'marketing_sale',
				'title': 'Купон 15%',
				'marketing_sale_id': 42,
				'valid_until': timezone.localdate().isoformat(),
				'excel_file': SimpleUploadedFile('phones.csv', b'1,2,3', content_type='text/csv'),
			}
		)
		self.assertFalse(serializer.is_valid())

	def test_accepts_manual_phones(self):
		serializer = CouponDispatchJobCreateSerializer(
			data={
				'dispatch_mode': 'marketing_sale',
				'title': 'Купон 15%',
				'marketing_sale_id': 42,
				'valid_until': timezone.localdate().isoformat(),
				'phones_text': '77071112233',
			}
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)

	def test_predefined_coupon_mode_requires_excel(self):
		serializer = CouponDispatchJobCreateSerializer(
			data={
				'dispatch_mode': 'predefined_coupon',
				'title': '50% скидка',
				'valid_until': timezone.localdate().isoformat(),
			}
		)
		self.assertFalse(serializer.is_valid())
		self.assertIn('excel_file', serializer.errors)

	def test_predefined_coupon_mode_accepts_excel(self):
		excel = SimpleUploadedFile(
			'phones.xlsx',
			b'xlsx-bytes',
			content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
		)
		serializer = CouponDispatchJobCreateSerializer(
			data={
				'dispatch_mode': 'predefined_coupon',
				'title': '50% скидка',
				'valid_until': timezone.localdate().isoformat(),
				'excel_file': excel,
			}
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)


class CouponDispatchServicePhoneNormalizationTests(SimpleTestCase):
	def test_accepts_kazakhstan_number(self):
		service = CouponDispatchService()
		row = service._parse_phone('8 707 123 45 67')
		self.assertTrue(row.valid)
		self.assertEqual(row.phone_normalized, '77071234567')

	def test_accepts_tashkent_park_number(self):
		service = CouponDispatchService()
		row = service._parse_phone('+998 90 123 45 67')
		self.assertTrue(row.valid)
		self.assertEqual(row.phone_normalized, '998901234567')

	def test_rejects_garbage(self):
		service = CouponDispatchService()
		row = service._parse_phone('abc')
		self.assertFalse(row.valid)
		self.assertEqual(row.error_message, 'invalid_phone_format')
