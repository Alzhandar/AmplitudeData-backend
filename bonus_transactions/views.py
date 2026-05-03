from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from bonus_transactions.models import BonusTransactionJob
from bonus_transactions.permissions import HasBonusTransactionsAccess
from bonus_transactions.serializers import (
    BonusTransactionJobCreateSerializer,
    BonusTransactionJobDetailSerializer,
    BonusTransactionJobListSerializer,
)
from bonus_transactions.services.bonus_transaction_service import BonusTransactionService
from bonus_transactions.tasks import process_bonus_transaction_job


class BonusTransactionJobViewSet(viewsets.ViewSet):
    permission_classes = [HasBonusTransactionsAccess]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    service_class = BonusTransactionService

    def list(self, request):
        queryset = BonusTransactionJob.objects.select_related('initiated_by').order_by('-created_at')
        limit = request.query_params.get('limit')
        if limit:
            try:
                parsed_limit = max(1, min(500, int(limit)))
                queryset = queryset[:parsed_limit]
            except (TypeError, ValueError):
                pass

        serializer = BonusTransactionJobListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = BonusTransactionJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        job = self.service_class().create_job(
            initiated_by=request.user,
            description=data['description'],
            amount=data['amount'],
            start_date=data['start_date'],
            expiration_date=data['expiration_date'],
            phones_text=data.get('phones_text') or '',
            excel_file=data.get('excel_file'),
        )

        process_bonus_transaction_job.delay(job.id)
        detail = BonusTransactionJobDetailSerializer(job)
        return Response(detail.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        job = get_object_or_404(BonusTransactionJob.objects.prefetch_related('results').select_related('initiated_by'), pk=pk)
        serializer = BonusTransactionJobDetailSerializer(job)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        raise ValidationError({'detail': 'Retry is disabled to prevent duplicate bonus accruals.'})
