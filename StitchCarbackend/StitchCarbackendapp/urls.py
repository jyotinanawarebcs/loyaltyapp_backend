from rest_framework import routers
from django.urls import path, include
from .views import BookingViewSet,CustomUserViewSet,OfferViewSet

# Step 1: Create router
router = routers.DefaultRouter()

# Step 2: Register your ViewSet
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'offers', OfferViewSet, basename='offer')

# Step 3: Connect router to urlpatterns
urlpatterns = [
    path('', include(router.urls)),
]
