from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from bonus_transactions.serializers import BonusTransactionJobCreateSerializer
from bonus_transactions.services.bonus_transaction_service import BonusTransactionService


class BonusTransactionJobCreateSerializerTests(SimpleTestCase):
    def test_requires_source(self):
        serializer = BonusTransactionJobCreateSerializer(
            data={
                'description': 'test',
                'amount': 100,
                'start_date': '2025-01-01',
                'expiration_date': '2025-01-31',
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_rejects_invalid_file_extension(self):
        serializer = BonusTransactionJobCreateSerializer(
            data={
                'description': 'test',
                'amount': 100,
                'start_date': '2025-01-01',
                'expiration_date': '2025-01-31',
                'excel_file': SimpleUploadedFile('phones.csv', b'1,2,3', content_type='text/csv'),
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_accepts_manual_phones(self):
        serializer = BonusTransactionJobCreateSerializer(
            data={
                'description': 'test',
                'amount': 100,
                'start_date': '2025-01-01',
                'expiration_date': '2025-01-31',
                'phones_text': '+7 700 111 22 33',
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class BonusTransactionServicePhoneNormalizationTests(SimpleTestCase):
    def test_accepts_kazakhstan_number(self):
        service = BonusTransactionService()
        self.assertEqual(service._normalize_phone('87071234567'), '77071234567')

    def test_accepts_tashkent_park_number(self):
        service = BonusTransactionService()
        self.assertEqual(service._normalize_phone('+998901234567'), '998901234567')
