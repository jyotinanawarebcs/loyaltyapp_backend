from django.urls import path, include
from . import views as app_views
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet,RegisterAPIView,LoginAPIView,LogoutAPIView,PasswordResetRequestAPIView,PasswordResetConfirmAPIView,AdminRegisterAPIView,SendVerificationCodeAPIView,VerifyCodeAPIView,UserPointsView, RewardViewSet, RedeemRewardView, EarningRuleViewSet,ReviewViewSet,ServiceFeedbackViewSet
from .views import AdminServiceViewSet,CustomUserViewSet,BookingViewSet,CouponListView, ApplyCouponView,AdminCouponListView, AdminCouponCreateView, AdminCouponDetailView,VehicleViewSet, RecallViewSet, VehicleRecallViewSet, urgent_recalls_home 
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   
    TokenRefreshView,     
)
from .views import OfferViewSet, VehicleViewSet
from .views import ReferralDashboardAPIView, InviteFriendAPIView, FeaturedPromotionViewSet, PromotionBannerViewSet



router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'admin-services', AdminServiceViewSet, basename='admin-service')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'offers', OfferViewSet, basename='offer')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'featured-promotions', FeaturedPromotionViewSet, basename='featured-promotions')
router.register(r'promotion-banners', PromotionBannerViewSet, basename='promotionbanner')
router.register(r'rewards', RewardViewSet, basename='reward')
router.register(r'earn-rules', EarningRuleViewSet)
router.register(r'recalls', RecallViewSet, basename='recall')
router.register(r'vehicle-recalls', VehicleRecallViewSet, basename='vehicle-recall')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'feedbacks', ServiceFeedbackViewSet, basename='feedback')
urlpatterns = [
    path('api/', include(router.urls)),
     path('bookings/check-status/<int:user_id>/',
        BookingViewSet.as_view({'get': 'check_user_booking_status'}),
        name='booking-check-status'
    ),
    path('api/register/', RegisterAPIView.as_view(), name='register'),
    path('api/admin/register/', AdminRegisterAPIView.as_view(), name='admin-register'),
    path('api/login/', LoginAPIView.as_view(), name='login'),
    path('api/logout/', LogoutAPIView.as_view(), name='logout'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("api/password-reset/", PasswordResetRequestAPIView.as_view(), name="password_reset"),
    path("api/password-reset/confirm/", PasswordResetConfirmAPIView.as_view(), name="password_reset_confirm"),
    path('send-verification-code/', SendVerificationCodeAPIView.as_view(), name='send_verification_code'),
    path('verify-code/', VerifyCodeAPIView.as_view(), name='verify_code'),
    path("referral/dashboard/", ReferralDashboardAPIView.as_view()),
    path("referral/invite/", InviteFriendAPIView.as_view()),
    path('api/points/', UserPointsView.as_view(), name='user-points'),
    path('api/rewards/redeem/', RedeemRewardView.as_view(), name='redeem-reward'),
    path('api/notifications/', app_views.notifications_list, name='notifications-list'),
    path('api/notifications/unread-count/', app_views.notifications_unread_count, name='notifications-unread-count'),
    path('api/notifications/mark-read/<int:pk>/', app_views.notification_mark_read, name='notification-mark-read'),
    path('api/coupons/', CouponListView.as_view(), name='coupon-list'),
    path('api/coupons/apply/', ApplyCouponView.as_view(), name='apply-coupon'),
    path('api/admin/coupons/', AdminCouponListView.as_view(), name='admin-coupon-list'),
    path('api/admin/coupons/create/', AdminCouponCreateView.as_view(), name='admin-coupon-create'),
    path('api/admin/coupons/<int:pk>/', AdminCouponDetailView.as_view(), name='admin-coupon-detail'),
    path('api/home/recalls/', urgent_recalls_home, name='home-recalls'),
    
]   
