from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AuthLoginView, AuthLogoutView, AuthMeView, AuthRegisterView, DailyDeviceActivityViewSet, LocationPresenceStatsViewSet

router = DefaultRouter()
router.register('amplitude/today-mobile-activity', DailyDeviceActivityViewSet, basename='today-mobile-activity')
router.register('amplitude/location-presence-stats', LocationPresenceStatsViewSet, basename='location-presence-stats')

urlpatterns = router.urls
urlpatterns += [
	path('auth/register/', AuthRegisterView.as_view(), name='auth-register'),
	path('auth/login/', AuthLoginView.as_view(), name='auth-login'),
	path('auth/me/', AuthMeView.as_view(), name='auth-me'),
	path('auth/logout/', AuthLogoutView.as_view(), name='auth-logout'),
]
