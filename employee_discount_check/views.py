from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from employee_discount_check.permissions import HasEmployeeDiscountCheckAccess
from employee_discount_check.serializers import (
    EmployeeDiscountCheckQuerySerializer,
    EmployeeDiscountCheckResponseSerializer,
)
from employee_discount_check.services.employee_discount_check_service import EmployeeDiscountCheckService


class EmployeeDiscountCheckView(APIView):
    permission_classes = [IsAuthenticated, HasEmployeeDiscountCheckAccess]

    def get(self, request):
        query_serializer = EmployeeDiscountCheckQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        phone = query_serializer.validated_data['phone']

        service = EmployeeDiscountCheckService()
        payload = service.check(phone_number=phone)

        response_serializer = EmployeeDiscountCheckResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data)
