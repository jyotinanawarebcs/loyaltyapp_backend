from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets,permissions
from .models import Service,PasswordResetCode
from .serializers import ServiceSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import CustomUser
from rest_framework.permissions import AllowAny
from .serializers import CustomUserSerializer
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import login
from .serializers import  RegisterSerializer,LoginSerializer,BookingSerializer,PasswordResetRequestSerializer,PasswordResetConfirmSerializer,SendVerificationCodeSerializer,VerifyCodeSerializer
from .models import Booking,Customer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.views import APIView
from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework import generics
from .models import PasswordResetCode
from .serializers import SendVerificationCodeSerializer, VerifyCodeSerializer
from django.core.mail import EmailMultiAlternatives
from datetime import date
from .permissions import IsCustomerOrReadOnly
from rest_framework import generics, permissions
from .models import Offer
from .serializers import OfferSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework.views import APIView
from .models import ReferralProfile, ReferralActivity, Booking
from .serializers import ReferralProfileSerializer,InviteFriendSerializer
from .serializers import VehicleSerializer
from .models import Vehicle
from .models import FeaturedPromotion, PromotionBanner
from .serializers import FeaturedPromotionSerializer, PromotionBannerSerializer
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from datetime import timedelta


User = get_user_model()
token_generator = PasswordResetTokenGenerator()


class PasswordResetRequestAPIView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not leak whether user exists
            return Response({"message": "If this email exists, a reset link has been sent."},
                            status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        reset_url = f"http://localhost:8000/api/password-reset/confirm?uid={uid}&token={token}"

        subject = "Password Reset Request"
        message = (
            f"Hi {user.username},\n\n"
            f"You requested a password reset.\n\n"
            f"Click this link to set a new password:\n{reset_url}\n\n"
            f"If you did not request this, please ignore this email."
        )
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

        return Response({"message": "If this email exists, a reset link has been sent."},
                        status=status.HTTP_200_OK)


class PasswordResetConfirmAPIView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid user ID."}, status=status.HTTP_400_BAD_REQUEST)

        if not token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({"message": "Password has been reset successfully."},
                        status=status.HTTP_200_OK)

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by('id')
    serializer_class = ServiceSerializer

    def get_permissions(self):
        """Allow anyone to view, but only authenticated users can modify."""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

class AdminServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAdminUser]

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]  

    
    def perform_create(self, serializer):
        user = serializer.save()
        password = self.request.data.get('password')
        if password:
            user.set_password(password)
            user.save()

    def get_permissions(self):
        if self.action in ['list', 'create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]  
        return [IsAuthenticated()]         
    
class IsCustomerOrReadOnly(permissions.BasePermission):
    """
    Allow safe methods for anyone (or restrict to staff); unsafe methods allowed
    only if user is the booking.customer or staff.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        try:
            return obj.customer.user == request.user
        except Exception:
            return False
        
class RegisterAPIView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()  
            phone = user.phone_number

            # --------------------------
            # REFERRAL REGISTRATION LOGIC
            # --------------------------
            referral_code = request.data.get("referral_code")

            if referral_code:
                try:
                    ref_profile = ReferralProfile.objects.get(referral_code=referral_code)
                    referrer = ref_profile.user
                except ReferralProfile.DoesNotExist:
                    referrer = None

                if referrer:
                    # Create or update referral activity
                    activity, created = ReferralActivity.objects.get_or_create(
                        referrer=referrer,
                        referred_phone=phone,
                        defaults={"status": "registered"}
                    )

                    if not created:
                        activity.status = "registered"
                        activity.save()

            # --------------------------

            return Response({
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "phone_number": user.phone_number,
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

      
# class RegisterAPIView(GenericAPIView):
#     serializer_class = RegisterSerializer
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()  

#             return Response({
#                 "message": "User registered successfully",
#                 "user": {
#                     "id": user.id,
#                     "username": user.username,
#                     "email": user.email,
#                     "phone_number": user.phone_number,
#                 }
#             }, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        from_device = request.data.get("device", "mobile")
        if from_device == "web" and not user.is_staff:
            return Response({"error": "Access denied. Only admin can login here."}, status=403)

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
               
            }
        }, status=status.HTTP_200_OK)

class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()  

            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookingViewSet(viewsets.ModelViewSet):
    # queryset = Booking.objects.all().select_related('customer__user',  'offer')
    queryset = Booking.objects.all().select_related('customer__user', 'offer').prefetch_related('services')
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCustomerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['service__title', 'customer__user__username', 'status', 'vehicle_make', 'vehicle_model']
    ordering_fields = ['booking_date', 'appointment_date', 'total_price']

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    # def get_queryset(self):
    #     qs = super().get_queryset()
    #     user = getattr(self.request, 'user', None)
    #     if user and user.is_authenticated and not user.is_staff:
    #         try:
    #             customer = Customer.objects.get(user=user)
    #             return qs.filter(customer=customer)
    #         except Customer.DoesNotExist:
    #             return Booking.objects.none()
    #     return qs


    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)

        # filter by authenticated customer
        if user and user.is_authenticated and not user.is_staff:
            try:
                customer = Customer.objects.get(user=user)
                qs = qs.filter(customer=customer)
            except Customer.DoesNotExist:
                return Booking.objects.none()

        # ✅ Filter by vehicle_number if provided
        vehicle_number = self.request.query_params.get("vehicle_number")
        if vehicle_number:
            qs = qs.filter(vehicle_number=vehicle_number)

        return qs

      
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


    def perform_create(self, serializer):
        user = self.request.user
        customer_data = self.request.data.get("customer", None)

    # ===== CUSTOMER BOOKING VALIDATION =====
        if user.is_authenticated and not user.is_staff:
            try:
                    customer = Customer.objects.get(user=user)
            except Customer.DoesNotExist:
                    raise PermissionError("No Customer profile found for this user.")

        # Extract vehicle fields from request
        vehicle_make = self.request.data.get("vehicle_make")
        vehicle_model = self.request.data.get("vehicle_model")
        vehicle_year = self.request.data.get("vehicle_year")

        # 🚫 Block booking ONLY if the SAME car has active booking
        active_booking = Booking.objects.filter(
            customer=customer,
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            vehicle_year=vehicle_year,
            status__in=['in_progress', 'completed', 'ready_for_pickup']
        ).first()

        if active_booking:
            raise serializers.ValidationError({
                "detail": "You cannot book a new service until your current service is completed."
            })

        serializer.save(customer=customer)
        return

        if customer_data:
            try:
                customer = Customer.objects.get(id=int(customer_data))
            except (ValueError, Customer.DoesNotExist):
                raise serializers.ValidationError("Customer not found.")

        serializer.save(customer=customer)
        return

    # ===== DEFAULT SAVE =====
        serializer.save()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status  # before update

        response = super().update(request, *args, **kwargs)

        new_status = response.data.get("status")

        # reward only when booking marked completed
        if old_status != "completed" and new_status == "completed":
            give_referral_reward(instance.customer.user)

        return response
    

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if not (request.user.is_staff or booking.customer.user == request.user):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        booking.status = 'cancelled'
        booking.save()
        return Response(self.get_serializer(booking).data)
    
    @action(detail=False, methods=['get'], url_path='check-status/(?P<user_id>[^/.]+)')
    def check_user_booking_status(self, request, user_id=None):
        try:
            booking = Booking.objects.filter(customer__user_id=user_id).order_by('-id').first()

            if not booking:
                return Response(
                    {'status': 'no_booking'},
                    status=status.HTTP_200_OK
                )

            return Response(
                {'status': booking.status},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    # ✅ Add this method only
    def list(self, request, *args, **kwargs):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = 'react-native' in user_agent or 'okhttp' in user_agent
        no_pagination = request.query_params.get('no_pagination', '').lower() == 'true'

        if is_mobile or no_pagination:
            # 👇 return all bookings as a flat array for mobile
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        # default (web) keeps pagination
        return super().list(request, *args, **kwargs)
              

class AdminRegisterAPIView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_staff = True  
            user.save()

            return Response({
                "message": "Admin registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_staff": user.is_staff,
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SendVerificationCodeAPIView(GenericAPIView):
    serializer_class = SendVerificationCodeSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "No user found with this email."}, status=status.HTTP_404_NOT_FOUND)

        # Generate verification code
        import random
        code = str(random.randint(100000, 999999))

        # Save in DB
        PasswordResetCode.objects.create(user=user, code=code)

        # Send OTP email
        send_mail(
            "Your Password Reset Verification Code",
            f"Your verification code is: {code}",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        return Response({"message": "Verification code sent to your email."}, status=status.HTTP_200_OK)




class VerifyCodeAPIView(GenericAPIView):
    serializer_class = VerifyCodeSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        code = serializer.validated_data["code"].strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid email or code"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latest_code = PasswordResetCode.objects.filter(user=user).latest("created_at")
        except PasswordResetCode.DoesNotExist:
            return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

        if latest_code.code != code:
            return Response({"error": "Incorrect verification code"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Code Verified → Now generate uid & token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        # ✅ Instead of sending reset link, we return uid & token to app
        return Response({
            "message": "Verification successful.",
            "uid": uid,
            "token": token
        }, status=status.HTTP_200_OK)
    


from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from .models import Offer
from .serializers import OfferSerializer
#
from drf_spectacular.utils import extend_schema


class OfferViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Offer model:
    - Anyone can GET (list/retrieve) active offers.
    - Only admin users can POST, PUT, PATCH, DELETE.
    - Supports bulk creation for admin users.
    """
    serializer_class = OfferSerializer
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Offer.objects.all().order_by('-valid_from')
        return Offer.objects.filter(is_active=True, valid_to__gte=timezone.now()).order_by('-valid_from')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    @extend_schema(
        request=OfferSerializer(many=True),
        responses={201: OfferSerializer(many=True)},
        summary="Create multiple offers",
        description="Create multiple offers for services at once"
    )
    def create(self, request, *args, **kwargs):
        """
        Override create to support both single and bulk creation.
        """
        many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ReferralDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, created = ReferralProfile.objects.get_or_create(user=request.user)
        data = ReferralProfileSerializer(profile).data
        return Response(data)


class InviteFriendAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=InviteFriendSerializer,   # IMPORTANT
        responses={200: dict},
        tags=["Referral"],
        description="Send an invite to a friend's phone number"
    )
    def post(self, request):
        serializer = InviteFriendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        profile, created = ReferralProfile.objects.get_or_create(user=request.user)

        # save activity
        activity = ReferralActivity.objects.create(
            referrer=request.user,
            referred_phone=phone,
            status="invited",
            reward_given=False
        )

        profile.invited_count += 1
        profile.save()

        return Response(
            {"message": "Invitation sent successfully", "phone": phone},
            status=status.HTTP_200_OK
        )


def give_referral_reward(referred_user):
    referred_phone = referred_user.phone_number

    # find referral activity based on phone
    activity = ReferralActivity.objects.filter(
        referred_phone=referred_phone,
        reward_given=False,
        status="registered"
    ).first()

    if not activity:
        return  # nothing to reward

    reward_amount = 100  # change anytime

    # update referrer’s reward profile
    profile, created = ReferralProfile.objects.get_or_create(user=activity.referrer)
    profile.rewards_earned += reward_amount
    profile.save()

    # mark activity as completed
    activity.reward_given = True
    activity.status = "completed"
    activity.save()


class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Vehicle.objects.all()
        return Vehicle.objects.filter(customer__user=user)

    def perform_create(self, serializer):
        customer = Customer.objects.get(user=self.request.user)
        serializer.save(customer=customer)

    def destroy(self, request, *args, **kwargs):
        vehicle = self.get_object()
        if vehicle.customer.user != request.user:
            return Response({"detail": "Not allowed"}, status=403)
        return super().destroy(request, *args, **kwargs)


from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from django.utils import timezone
from .models import FeaturedPromotion, Booking
from .serializers import FeaturedPromotionSerializer

class FeaturedPromotionViewSet(viewsets.ModelViewSet):
    serializer_class = FeaturedPromotionSerializer

    # Permissions: GET for all, others only for admins
    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [AllowAny()]
        return [IsAdminUser()]

    # Queryset: returns promotions based on customer status
    def get_queryset(self):
        qs = FeaturedPromotion.objects.filter(is_active=True)
        user = self.request.user

        # Not logged in → only general promotions
        if not user.is_authenticated:
            return qs.filter(promo_type='all')

        # Get customer profile
        customer = getattr(user, 'customer_profile', None)
        if not customer:
            return qs.filter(promo_type='all')  # default to general promotions

        # Count total bookings
        booking_count = Booking.objects.filter(customer=customer).count()

        # NEW CUSTOMER → 0 bookings
        if booking_count == 0:
            return qs.filter(promo_type='new')

        # LOYAL CUSTOMER → 5+ bookings
        if booking_count >= 5:
            return qs.filter(promo_type__in=['all', 'loyal'])

       # INACTIVE CUSTOMER → last booking ≥ 60 days
        last_booking = Booking.objects.filter(customer=customer).order_by('-created_at').first()
        if last_booking:
            days_since_last = (timezone.now() - last_booking.created_at).days
            if days_since_last >= 60:
                # Show general + inactive + packages
                return qs.filter(promo_type__in=['all', 'inactive', 'package'])
            
        # Default → general promotions
        return qs.filter(promo_type='all')




class PromotionBannerViewSet(viewsets.ModelViewSet):
    queryset = PromotionBanner.objects.filter(is_active=True)
    serializer_class = PromotionBannerSerializer
    permission_classes = [AllowAny]
