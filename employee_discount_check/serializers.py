from rest_framework import serializers


def normalize_phone_number(raw_phone: str) -> str:
    digits = ''.join(ch for ch in str(raw_phone or '') if ch.isdigit())
    if not digits:
        return ''
    if len(digits) == 11 and digits.startswith('8'):
        return f'7{digits[1:]}'
    if len(digits) == 11 and digits.startswith('7'):
        return digits
    if len(digits) == 10:
        return f'7{digits}'
    return ''


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
