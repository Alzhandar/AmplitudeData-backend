from django.urls import include, path
from rest_framework.routers import DefaultRouter

from bonus_transactions.views import BonusTransactionJobViewSet

router = DefaultRouter()
router.register('jobs', BonusTransactionJobViewSet, basename='bonus-transaction-jobs')

urlpatterns = [
    path('bonus-transactions/', include(router.urls)),
]
