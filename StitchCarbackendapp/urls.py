from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet,RegisterAPIView,LoginAPIView,LogoutAPIView
from .views import AdminServiceViewSet,CustomUserViewSet,BookingViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   
    TokenRefreshView,     
)

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'admin-services', AdminServiceViewSet, basename='admin-service')
router.register(r'users', CustomUserViewSet, basename='user')
urlpatterns = [
    path('', include(router.urls)),
    path('api/register/', RegisterAPIView.as_view(), name='register'),
    path('api/login/', LoginAPIView.as_view(), name='login'),
    path('api/logout/', LogoutAPIView.as_view(), name='logout'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
 
]