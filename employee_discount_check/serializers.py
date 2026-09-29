from rest_framework import serializers

from utils.phone_utils import normalize_phone_number


class EmployeeDiscountCheckQuerySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)

    def validate_phone(self, value: str) -> str:
        normalized = normalize_phone_number(value)
        if not normalized:
            raise serializers.ValidationError('invalid_phone_format')
        return normalized


class EmployeeDiscountScopeResultSerializer(serializers.Serializer):
    eligible = serializers.BooleanField(default=False)
    remaining_discounts = serializers.IntegerField(required=False, allow_null=True)
    employee_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    employee_department = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    employee_position = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    used_count = serializers.IntegerField(required=False, allow_null=True)
    max_discounts = serializers.IntegerField(required=False, allow_null=True)
    policy_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    discount_scope = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class EmployeeDiscountCheckResponseSerializer(serializers.Serializer):
    phone = serializers.CharField()
    employee_found = serializers.BooleanField()
    restaurant = EmployeeDiscountScopeResultSerializer()
    park = EmployeeDiscountScopeResultSerializer()


class EmployeeLookupQuerySerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=32,
        help_text='Номер телефона или ИИН сотрудника (если по номеру не находит — ищем по ИИН)',
    )

    def validate_identifier(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError('required')
        return stripped


class EmployeeLookupResponseSerializer(serializers.Serializer):
    found = serializers.BooleanField()
    matched_by = serializers.ChoiceField(choices=('phone', 'iin', 'none'))
    employee_id = serializers.CharField(required=False, allow_blank=True)
    employee_name = serializers.CharField(required=False, allow_blank=True)
    employee_department = serializers.CharField(required=False, allow_blank=True)
    employee_position = serializers.CharField(required=False, allow_blank=True)
    current_phone = serializers.CharField(required=False, allow_blank=True)
    iin = serializers.CharField(required=False, allow_blank=True)


class EmployeePhoneChangeRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=32,
        help_text='Номер телефона или ИИН сотрудника, чей номер меняем',
    )
    new_phone = serializers.CharField(max_length=32)

    def validate_identifier(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError('required')
        return stripped

    def validate_new_phone(self, value: str) -> str:
        normalized = normalize_phone_number(value)
        if not normalized:
            raise serializers.ValidationError('invalid_phone_format')
        return normalized


class EmployeePhoneChangeResponseSerializer(serializers.Serializer):
    employee_id = serializers.CharField()
    employee_name = serializers.CharField(required=False, allow_blank=True)
    old_phone = serializers.CharField()
    new_phone = serializers.CharField()
