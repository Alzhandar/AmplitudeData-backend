import logging

from rest_framework import status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.permissions import HasPushDispatchAccess
from notifications.models import PushDispatchLog, PushDispatchStatus
from notifications.serializers import NotificationCitySerializer, PushDispatchRequestSerializer
from notifications.services.push_dispatch_service import PushDispatchService, PushDispatchUpstreamError


logger = logging.getLogger(__name__)


class PushGatewayUnavailable(APIException):
	status_code = status.HTTP_502_BAD_GATEWAY
	default_detail = 'Сервис push-уведомлений временно недоступен.'
	default_code = 'push_gateway_unavailable'


class NotificationCityViewSet(viewsets.ViewSet):
	permission_classes = [IsAuthenticated, HasPushDispatchAccess]

	def list(self, request):
		search = str(request.query_params.get('search', '')).strip()
		service = PushDispatchService()
		cities = service.list_cities(search=search)
		serializer = NotificationCitySerializer(cities, many=True)
		return Response(serializer.data)


class PushDispatchViewSet(viewsets.ViewSet):
	permission_classes = [IsAuthenticated, HasPushDispatchAccess]

	def create(self, request):
		serializer = PushDispatchRequestSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		payload = serializer.validated_data

		initiator_email = ''
		if getattr(request, 'user', None) is not None:
			initiator_email = str(getattr(request.user, 'email', '') or '').strip().lower()

		dispatch_log = PushDispatchLog.objects.create(
			initiated_by=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
			initiated_by_email=initiator_email,
			target=str(payload.get('target') or '').strip(),
			city_id=payload.get('city_id'),
			recipients_count=len(payload.get('phone_numbers') or []) or None,
			title=str(payload.get('title') or '').strip(),
			body=str(payload.get('body') or '').strip(),
			title_kz=str(payload.get('title_kz') or '').strip(),
			body_kz=str(payload.get('body_kz') or '').strip(),
			notification_type=str(payload.get('notification_type') or 'default').strip() or 'default',
			survey_id=payload.get('survey_id'),
			review_id=payload.get('review_id'),
		)

		service = PushDispatchService()
		try:
			result = service.send_mass_push(**payload)
		except PushDispatchUpstreamError as exc:
			dispatch_log.status = PushDispatchStatus.FAILED
			dispatch_log.error_message = str(exc)
			dispatch_log.save(update_fields=['status', 'error_message', 'updated_at'])

			logger.exception(
				'Push dispatch upstream failure',
				extra={
					'target': payload.get('target'),
					'city_id': payload.get('city_id'),
					'recipients_count': len(payload.get('phone_numbers') or []),
				},
			)
			raise PushGatewayUnavailable(str(exc))

		dispatch_log.status = PushDispatchStatus.ACCEPTED
		dispatch_log.notification_id = result.notification_id
		dispatch_log.recipients_count = result.recipients_count
		dispatch_log.save(update_fields=['status', 'notification_id', 'recipients_count', 'updated_at'])

		return Response(
			{
				'target': result.target,
				'city_id': result.city_id,
				'recipients_count': result.recipients_count,
				'notification_id': result.notification_id,
				'dispatch_log_id': dispatch_log.id,
				'status': result.status,
			},
			status=201,
		)
