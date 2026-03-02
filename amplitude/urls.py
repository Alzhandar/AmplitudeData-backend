from rest_framework.routers import DefaultRouter

from .views import DailyDeviceActivityViewSet, LocationPresenceStatsViewSet

router = DefaultRouter()
router.register('amplitude/today-mobile-activity', DailyDeviceActivityViewSet, basename='today-mobile-activity')
router.register('amplitude/location-presence-stats', LocationPresenceStatsViewSet, basename='location-presence-stats')

urlpatterns = router.urls
