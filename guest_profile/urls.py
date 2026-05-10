from django.urls import path

from guest_profile.views import GuestProfileByPhoneView

urlpatterns = [
    path('guest-profile/by-phone/', GuestProfileByPhoneView.as_view(), name='guest-profile-by-phone'),
]
