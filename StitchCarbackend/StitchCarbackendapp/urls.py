from rest_framework import routers
from django.urls import path, include
from .views import BookingViewSet,CustomUserViewSet

# Step 1: Create router
router = routers.DefaultRouter()

# Step 2: Register your ViewSet
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'users', CustomUserViewSet, basename='user')

# Step 3: Connect router to urlpatterns
urlpatterns = [
    path('', include(router.urls)),
]
