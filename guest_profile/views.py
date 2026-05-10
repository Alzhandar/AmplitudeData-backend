from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from guest_profile.permissions import HasGuestProfileAccess
from guest_profile.serializers import GuestProfileQuerySerializer
from guest_profile.services.guest_profile_service import GuestNotFoundError, GuestProfileService


class GuestProfileByPhoneView(APIView):
	permission_classes = [IsAuthenticated, HasGuestProfileAccess]

	def get(self, request):
		serializer = GuestProfileQuerySerializer(data=request.query_params)
		serializer.is_valid(raise_exception=True)
		data = serializer.validated_data

		service = GuestProfileService()
		try:
			payload = service.get_profile_by_phone(
				normalized_phone=data['phone'],
				from_date=data['from_date'],
				to_date=data['to_date'],
				orders_limit=data['orders_limit'],
				mobile_events_limit=data['mobile_events_limit'],
				cashback_limit=data['cashback_limit'],
				crystal_limit=data['crystal_limit'],
			)
		except GuestNotFoundError:
			return Response({'detail': 'guest_not_found'}, status=status.HTTP_404_NOT_FOUND)

		return Response(payload)
