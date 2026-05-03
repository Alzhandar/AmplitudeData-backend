from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from bonus_transactions.serializers import BonusTransactionJobCreateSerializer


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
