from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from employee_discount_check.permissions import HasEmployeeDiscountCheckAccess
from employee_discount_check.serializers import (
    EmployeeDiscountCheckQuerySerializer,
    EmployeeDiscountCheckResponseSerializer,
    EmployeeLookupQuerySerializer,
    EmployeeLookupResponseSerializer,
    EmployeePhoneChangeRequestSerializer,
    EmployeePhoneChangeResponseSerializer,
)
from employee_discount_check.services.employee_discount_check_service import EmployeeDiscountCheckService
from employee_discount_check.services.employee_phone_change_service import (
    EmployeeNotFoundError,
    EmployeePhoneChangeService,
    PhoneAlreadyInUseError,
)


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


class EmployeeLookupView(APIView):
    """Preview step before changing a phone: find the employee by phone, falling
    back to ИИН, without mutating anything."""

    permission_classes = [IsAuthenticated, HasEmployeeDiscountCheckAccess]

    def get(self, request):
        query_serializer = EmployeeLookupQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        identifier = query_serializer.validated_data['identifier']

        service = EmployeePhoneChangeService()
        employee, matched_by = service.find_employee_with_source(identifier)

        if not employee:
            payload = {'found': False, 'matched_by': 'none'}
        else:
            payload = {
                'found': True,
                'matched_by': matched_by,
                'employee_id': str(employee.get('id') or ''),
                'employee_name': employee.get('full_name') or '',
                'employee_department': employee.get('division_name') or '',
                'employee_position': employee.get('position_name') or '',
                'current_phone': employee.get('phone') or '',
                'iin': employee.get('iin') or '',
            }

        response_serializer = EmployeeLookupResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data)


class EmployeePhoneChangeView(APIView):
    permission_classes = [IsAuthenticated, HasEmployeeDiscountCheckAccess]

    def post(self, request):
        request_serializer = EmployeePhoneChangeRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        service = EmployeePhoneChangeService()
        try:
            payload = service.change_phone(
                identifier=data['identifier'],
                new_phone=data['new_phone'],
            )
        except EmployeeNotFoundError as exc:
            raise ValidationError({'identifier': str(exc)})
        except PhoneAlreadyInUseError as exc:
            raise ValidationError({'new_phone': str(exc)})
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})

        response_serializer = EmployeePhoneChangeResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
