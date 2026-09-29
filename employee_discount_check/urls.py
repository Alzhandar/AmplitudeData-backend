from django.urls import path

from employee_discount_check.views import EmployeeDiscountCheckView, EmployeeLookupView, EmployeePhoneChangeView

urlpatterns = [
    path('employee-discount-check/', EmployeeDiscountCheckView.as_view(), name='employee-discount-check'),
    path('employee-discount-check/lookup/', EmployeeLookupView.as_view(), name='employee-discount-check-lookup'),
    path('employee-discount-check/change-phone/', EmployeePhoneChangeView.as_view(), name='employee-discount-check-change-phone'),
]
