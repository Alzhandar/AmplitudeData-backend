from django.urls import path

from employee_discount_check.views import EmployeeDiscountCheckView

urlpatterns = [
    path('employee-discount-check/', EmployeeDiscountCheckView.as_view(), name='employee-discount-check'),
]
