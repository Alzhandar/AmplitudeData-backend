import logging

from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from coupon_dispatch.models import CouponDispatchJob
from coupon_dispatch.permissions import HasCouponDispatchAccess
from coupon_dispatch.serializers import (
	CouponDispatchJobCreateSerializer,
	CouponDispatchJobDetailSerializer,
	CouponDispatchJobListSerializer,
	MarketingSaleOptionSerializer,
)
from coupon_dispatch.services.coupon_dispatch_service import CouponDispatchService
from coupon_dispatch.tasks import process_coupon_dispatch_job_task

logger = logging.getLogger(__name__)


class CouponDispatchMarketingSaleViewSet(viewsets.ViewSet):
	permission_classes = [IsAuthenticated, HasCouponDispatchAccess]

	def list(self, request):
		search = str(request.query_params.get('search', '')).strip()
		service = CouponDispatchService()
		options = service.list_marketing_sales_with_available_coupons(search=search)
		serializer = MarketingSaleOptionSerializer(options, many=True)
		return Response(serializer.data)


class CouponDispatchJobViewSet(viewsets.ViewSet):
	permission_classes = [IsAuthenticated, HasCouponDispatchAccess]

	def list(self, request):
		raw_limit = str(request.query_params.get('limit', '20')).strip()
		try:
			limit = int(raw_limit)
		except ValueError as exc:
			raise ValidationError({'limit': 'limit must be integer'}) from exc

		if limit <= 0:
			raise ValidationError({'limit': 'limit must be greater than 0'})

		limit = min(limit, 100)
		queryset = CouponDispatchJob.objects.order_by('-created_at')[:limit]
		serializer = CouponDispatchJobListSerializer(queryset, many=True)
		return Response(serializer.data)

	def retrieve(self, request, pk=None):
		job = CouponDispatchJob.objects.filter(id=pk).prefetch_related('results').first()
		if not job:
			raise ValidationError({'detail': 'Coupon dispatch job not found'})

		serializer = CouponDispatchJobDetailSerializer(job)
		return Response(serializer.data)

	def create(self, request):
		serializer = CouponDispatchJobCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		validated = serializer.validated_data

		service = CouponDispatchService()
		job = service.create_job(
			user=request.user,
			title=validated['title'],
			dispatch_mode=validated['dispatch_mode'],
			marketing_sale_id=validated.get('marketing_sale_id'),
			marketing_sale_name=validated.get('marketing_sale_name', ''),
			valid_until=validated['valid_until'],
			phones_text=validated.get('phones_text', ''),
			source_file=validated.get('excel_file'),
		)

		try:
			process_coupon_dispatch_job_task.delay(job.id)
		except Exception:
			logger.exception('Failed to enqueue coupon dispatch job %s, fallback to sync run', job.id)
			service.process_job(job.id)

		job = CouponDispatchJob.objects.filter(id=job.id).prefetch_related('results').first()
		serializer_out = CouponDispatchJobDetailSerializer(job)
		return Response(serializer_out.data, status=201)
