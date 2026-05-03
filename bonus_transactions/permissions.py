from rest_framework.permissions import BasePermission

from amplitude.services.employee_access_service import EmployeeAccessService


class HasBonusTransactionsAccess(BasePermission):
    message = 'You do not have access to bonus transactions section.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        try:
            iin = user.employee_binding.iin
        except Exception:
            return False

        allowed_pages = EmployeeAccessService().allowed_pages_for_iin(iin)
        return 'bonus-transactions' in allowed_pages
