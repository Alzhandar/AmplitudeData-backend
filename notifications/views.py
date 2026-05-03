import logging

from rest_framework import status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.permissions import HasPushDispatchAccess
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

		service = PushDispatchService()
		try:
			result = service.send_mass_push(**serializer.validated_data)
		except PushDispatchUpstreamError as exc:
			payload = serializer.validated_data
			logger.exception(
				'Push dispatch upstream failure',
				extra={
					'target': payload.get('target'),
					'city_id': payload.get('city_id'),
					'recipients_count': len(payload.get('phone_numbers') or []),
				},
			)
			raise PushGatewayUnavailable(str(exc))

		return Response(
			{
				'target': result.target,
				'city_id': result.city_id,
				'recipients_count': result.recipients_count,
				'notification_id': result.notification_id,
				'status': result.status,
			},
			status=201,
		)
