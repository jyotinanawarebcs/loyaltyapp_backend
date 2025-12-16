from django.shortcuts import render
from django.contrib.auth import login, get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta
from rest_framework.generics import GenericAPIView


from rest_framework import (
    viewsets,
    generics,
    permissions,
    status,
    filters,
    serializers,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication

from .permissions import IsCustomerOrReadOnly, IsAdminOrReadOnly

from .models import (
    CustomUser,
    Customer,
    Booking,
    Service,
    PasswordResetCode,
    Coupon,
    AppliedCoupon,
    Vehicle,
    Recall,
    VehicleRecall,
    RecallServiceHistory,
    Review,
    ServiceFeedback,
    Reward,
    LoyaltyPoint,
    RedeemedReward,
    EarningRule,
    Notification,
    Offer,
    ReferralProfile,
    ReferralActivity,
    FeaturedPromotion,
    PromotionBanner,
    ServiceFeedback,
    MembershipPlan,
    CustomerMembership,
)

from .serializers import (
    CustomUserSerializer,
    RegisterSerializer,
    LoginSerializer,
    BookingSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    SendVerificationCodeSerializer,
    VerifyCodeSerializer,
    NotificationSerializer,
    ServiceFeedbackSerializer,
    ServiceSerializer,
    CouponSerializer,
    ApplyCouponSerializer,
    VehicleSerializer,
    RecallSerializer,
    VehicleRecallSerializer,
    ReviewSerializer,
    LoyaltyPointSerializer,
    RewardSerializer,
    RedeemRewardSerializer,
    EarningRuleSerializer,
    OfferSerializer,
    ReferralProfileSerializer,
    InviteFriendSerializer,
    FeaturedPromotionSerializer,
    PromotionBannerSerializer,
    MembershipPlanSerializer,
    CustomerMembershipSerializer,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_list(request):
    # return notifications for logged-in user
    customer = getattr(request.user, 'customer_profile', None)
    if not customer:
        return Response([], status=200)

    if not customer.notifications_enabled:
        return Response([], status=200)  
          
    qs = Notification.objects.filter(customer=customer).order_by('-created_at')
    serializer = NotificationSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_unread_count(request):
    customer = getattr(request.user, 'customer_profile', None)
    if not customer:
        return Response({"count": 0})
    count = Notification.objects.filter(customer=customer, is_read=False).count()
    return Response({"count": count})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    print("➡️ User:", request.user)
    try:
        customer = request.user.customer_profile
        print("✅ Customer:", customer)
    except Exception as e:
        print("⚠️ No customer_profile:", e)
        return Response({"error": "Customer profile not found"}, status=400)

    try:
        notification = Notification.objects.get(pk=pk, customer=customer)
        print("✅ Found notification:", notification)
    except Notification.DoesNotExist:
        print("⚠️ No notification found for this customer")
        return Response({"error": "Notification not found for this user"}, status=404)

    notification.is_read = True
    notification.save()
    print("✅ Notification marked as read")
    return Response({"message": "Marked as read"})


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
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        if self.request.user.is_staff:
            return CustomUser.objects.all()
        return CustomUser.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get', 'put'], url_path='me')
    def me(self, request):
        """Fetch or update the currently logged-in user"""
        user = request.user

        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=200)

        elif request.method == 'PUT':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=200)


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
    
# class IsCustomerOrReadOnly(permissions.BasePermission):
#     """
#     Allow safe methods for anyone (or restrict to staff); unsafe methods allowed
#     only if user is the booking.customer or staff.
#     """
#     def has_permission(self, request, view):
#         if request.method in permissions.SAFE_METHODS:
#             return True
#         return request.user and request.user.is_authenticated

#     def has_object_permission(self, request, view, obj):
#         if request.method in permissions.SAFE_METHODS:
#             return True
#         if request.user.is_staff:
#             return True
#         try:
#             return obj.customer.user == request.user
#         except Exception:
#             return False
        
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
                "phone_number": user.phone_number,
                "membership": getattr(user, "membership", "Member"),
                "joined": user.date_joined.strftime("%Y-%m-%d")
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
        customer = None

    # ===== CUSTOMER BOOKING VALIDATION =====
        if user.is_authenticated and not user.is_staff:
            try:
                customer = Customer.objects.get(user=user)
            except Customer.DoesNotExist:
                raise serializers.ValidationError("Customer profile not found.")
        else:
            customer_id = self.request.data.get("customer")
            if customer_id:
                try:
                    customer = Customer.objects.get(id=int(customer_id))
                except Customer.DoesNotExist:
                    raise serializers.ValidationError("Invalid customer.")
            else:
                raise serializers.ValidationError("Customer not specified.")

        # ===== 2️⃣ VEHICLE VALIDATION =====
        vehicle_make = self.request.data.get("vehicle_make")
        vehicle_model = self.request.data.get("vehicle_model")
        vehicle_year = self.request.data.get("vehicle_year")

        # Detect if this is a recall service booking
        is_recall_service = str(self.request.data.get("is_recall_service")).lower() in ["true", "1"]
        notes_text = str(self.request.data.get("notes") or "").lower()

        # ⚙ Only block duplicate bookings for normal services
        if not (is_recall_service or "recall" in notes_text):
            if vehicle_make and vehicle_model and vehicle_year:
                active_booking = Booking.objects.filter(
                    customer=customer,
                    vehicle_make=vehicle_make,
                    vehicle_model=vehicle_model,
                    vehicle_year=vehicle_year,
                    status__in=['pending', 'in_progress', 'ready_for_pickup', 'rescheduled']
                ).first()

                if active_booking:
                    raise serializers.ValidationError({
                        "detail": "You cannot book a new service until your current service for this vehicle is completed."
                    })

        # ===== 3️⃣ PRE-VALIDATE REWARD (if provided) BEFORE CREATING BOOKING =====
        # Use serializer.validated_data so we don't create a booking and then raise.
        services_from_payload = serializer.validated_data.get('services', [])
        reward_from_payload = serializer.validated_data.get('reward')

        if reward_from_payload:
            if reward_from_payload.service and reward_from_payload.service not in services_from_payload:
                raise serializers.ValidationError("This reward can only be used for its associated service.")
        # ===== 4️⃣ SAVE BOOKING =====
        booking = serializer.save(customer=customer)

        # ===== 5️⃣ CALCULATE TOTAL PRICE =====
        service_total = float(sum(float(s.price) for s in booking.services.all()))
        booking.total_price = service_total
        

        try:
            membership = booking.customer.membership
            if membership and membership.active:
                benefits = membership.get_benefits()
                discount_percent = benefits.get("booking_discount", 0)
                if discount_percent > 0:
                    discount_amount = (discount_percent / 100) * float(booking.total_price)
                    booking.total_price = max(float(booking.total_price) - discount_amount, 0)
                    booking.save(update_fields=["total_price"])
        except Exception:
            pass
            
        if booking.offer:
            offer = booking.offer

            # 🚨 Check if offer is active and valid
            if not offer.is_valid():
                raise serializers.ValidationError({"offer": "This offer is not currently active or has expired."})

            # 🚨 Check eligibility for membership-only offers
            if not offer.is_eligible_for(customer):
                raise serializers.ValidationError({"offer": "You are not eligible for this membership-exclusive offer."})

            # ✅ Apply discount only if eligible
            discount_type = getattr(offer, "discount_type", "percentage")
            discount_percentage = float(getattr(offer, "discount_percentage", 0))

            if discount_type == "percentage":
                discount = (discount_percentage / 100) * booking.total_price
                booking.total_price = max(booking.total_price - discount, 0.0)

            elif discount_type == "flat":
                booking.total_price = max(booking.total_price - discount_percentage, 0.0)

            elif discount_type == "free":
                booking.total_price = 0.0

        
        # ===== 6️⃣ APPLY REWARD IF ANY =====
        reward_id_from_request = self.request.data.get('reward_id')
        
        reward = reward_from_payload or (
            Reward.objects.filter(
                id=reward_id_from_request,
                is_active=True
            ).first()
            if reward_id_from_request
            else None
        )

        if reward:
            discount_value = float(reward.discount_value or 0)
            reward_type = reward.type  # ✅ define variable explicitly

            if reward_type == "discount":
                # Handles both 0.10 (10%) and 10 (10%) formats
                discount_amount = (
                    service_total * (discount_value / 100)
                    if discount_value > 1
                    else service_total * discount_value
                )
                booking.total_price = max(service_total - discount_amount, 0.0)

            elif reward_type == "flat":
                booking.total_price = max(service_total - discount_value, 0.0)

            elif reward_type == "free":
                booking.total_price = 0.0

            elif reward_type == "cashback":
                # Cashback handled later in signal
                pass

            # ✅ Assign and save the updated total
            booking.reward = reward
            booking.save(update_fields=["reward", "total_price"])
            # reward applied and saved

        else:

            booking.save(update_fields=["total_price"])


        # ===== 6️⃣ EARNING RULE (LOYALTY POINTS) =====
        earning_rule_id = self.request.data.get("earningRuleId")
        if earning_rule_id:
            try:
                earning_rule = EarningRule.objects.get(id=earning_rule_id, is_active=True)
            except EarningRule.DoesNotExist:
                earning_rule = None

            if earning_rule:
                total_spend = float(booking.total_price or 0)
                if total_spend >= earning_rule.amount_base:
                    points_to_award = int((total_spend / earning_rule.amount_base) * earning_rule.points)
                    if points_to_award > 0:
                        loyalty, _ = LoyaltyPoint.objects.get_or_create(customer=booking.customer)
                        loyalty.add_points(points_to_award)

           # ✅ Only attach the rule — don’t re-save serializer again
                booking.earning_rule = earning_rule
                booking.save(update_fields=["earning_rule", "total_price","offer"])
                print("OFFER APPLIED:", booking.offer, booking.offer.discount_type, booking.offer.discount_value)

        # ===== 7️⃣ VEHICLE RECALL AUTO-COMPLETE =====
        try:
            notes = str(self.request.data.get("notes") or "").lower()
            recall_flag = self.request.data.get("is_recall_service")
            is_recall_service = recall_flag in (True, "true", "True", "1", 1)
            vehicle_make = str(self.request.data.get("vehicle_make") or "").strip()
            vehicle_model = str(self.request.data.get("vehicle_model") or "").strip()

            if (is_recall_service or "recall" in notes) and vehicle_make and vehicle_model:
                recall = VehicleRecall.objects.filter(
                    vehicle__customer=customer,
                    vehicle__make__iexact=vehicle_make,
                    vehicle__model__iexact=vehicle_model,
                    status="active"
                ).first()

                if recall:
                    recall.status = "completed"
                    recall.last_service_date = timezone.now()
                    recall.service_count += 1
                    recall.save()

                    RecallServiceHistory.objects.create(
                        vehicle_recall=recall,
                        customer=customer,
                        booking=booking,
                        remarks="Auto-completed via booking",
                        is_repeat_service=(recall.service_count > 1)
                    )
        except Exception:
            # Fail-safe: booking should always succeed even if recall fails
            pass

        # ===== 8️⃣ FINAL SAVE & RETURN =====
        booking.refresh_from_db()
        return booking

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = self.perform_create(serializer)
        booking.refresh_from_db()
        response_serializer = self.get_serializer(booking)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status

        response = super().update(request, *args, **kwargs)
        booking = instance
        booking.refresh_from_db()  # ← IMPORTANT: get latest status

        if old_status != "completed" and booking.status == "completed":
            print(f"Booking {booking.id} marked completed → triggering referral reward")
            give_referral_reward(booking.customer.user)

        return response
    # def update(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     old_status = instance.status  # before update

    #     response = super().update(request, *args, **kwargs)

    #     new_status = response.data.get("status")

    #     # reward only when booking marked completed
    #     if old_status != "completed" and new_status == "completed":
    #         give_referral_reward(instance.customer.user)

    #     return response
    

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if not (request.user.is_staff or booking.customer.user == request.user):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        booking.status = 'cancelled'
        booking.save()
        return Response(self.get_serializer(booking).data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def complete(self, request, pk=None):
        """Mark a booking as completed. Frontend should call this when service is completed/paid.

        Permissions: only staff or the booking owner may complete a booking.
        Triggers the existing referral/reward logic when status changes to 'completed'.
        """
        booking = self.get_object()
        if not (request.user.is_staff or booking.customer.user == request.user):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        if booking.status == 'completed':
            return Response(self.get_serializer(booking).data)

        old_status = booking.status
        booking.status = 'completed'
        booking.save()

        # If update() path exists it will handle give_referral_reward; signals also handle it.
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
                status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def completed_for_feedback(self, request):
        """
        Returns only completed bookings that do NOT have feedback yet.
        Used by 'Leave Review' flow in Loyalty Page.
        """
        user = request.user
        try:
            customer = Customer.objects.get(user=user)
        except Customer.DoesNotExist:
            return Response([], status=200)

        completed = Booking.objects.filter(
            customer=customer,
            status='ready_for_pickup'
        ).exclude(
            id__in=ServiceFeedback.objects.filter(customer=customer).values_list('booking_id', flat=True)
        ).prefetch_related('services')

        serializer = self.get_serializer(completed, many=True)
        return Response(serializer.data)            
            
    
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
               
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def history(self, request):
        user = request.user

        # Only customer's history
        try:
            customer = Customer.objects.get(user=user)
        except Customer.DoesNotExist:
            return Response([], status=200)

        queryset = Booking.objects.filter(
            customer=customer,
            status__in=['completed', 'ready_for_pickup']
        ).select_related('customer__user', 'offer').prefetch_related('services').order_by('-appointment_date')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

 
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def recalculate_price(self, request, pk=None):
        booking = self.get_object()
        booking.refresh_from_db()

        # Recalculate any applicable membership or offers if needed
        try:
            membership = booking.customer.membership
            if membership and membership.active:
                benefits = membership.get_benefits()
                discount_percent = benefits.get("booking_discount", 0)
                if discount_percent > 0:
                    base_price = sum(float(s.price) for s in booking.services.all())
                    membership_discount = (discount_percent / 100) * base_price
                    booking.total_price = max(base_price - membership_discount, 0)
                    booking.save(update_fields=["total_price"])
        except Exception:
            pass

        serializer = self.get_serializer(booking)
        return Response(serializer.data)

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
        now = timezone.now()
        if self.request.user.is_staff:
            return Offer.objects.all().order_by('-valid_from')
        
        return Offer.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        ).order_by('-valid_from')

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
    
    def list(self, request, *args, **kwargs):
    # Disable pagination when ?no_pagination=true
        if request.GET.get("no_pagination") == "true":
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        # default paginated response
        return super().list(request, *args, **kwargs)    


class UserPointsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        customer = request.user.customer_profile
        loyalty, _ = LoyaltyPoint.objects.get_or_create(customer=customer)
        serializer = LoyaltyPointSerializer(loyalty)
        return Response(serializer.data)


class RewardViewSet(viewsets.ModelViewSet):
    queryset = Reward.objects.all().order_by('required_points')
    serializer_class = RewardSerializer

    # ✅ Only admins can create/update/delete, but all authenticated users can view
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
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

    # utils.py or inside your referral app
def give_referral_reward(referred_user):
        from .models import ReferralActivity, ReferralProfile, Booking, LoyaltyPoint

        try:
            # 1. Count how many COMPLETED bookings this user has
            completed_count = Booking.objects.filter(
                customer__user=referred_user,
                status="completed"
            ).count()

            # Only give reward on the VERY FIRST completed booking
            if completed_count != 1:
                print(f"Reward skipped: User has {completed_count} completed bookings")
                return

            # 2. Find the pending referral
            # First check for registered + reward not given
            activity = ReferralActivity.objects.filter(
                referred_phone=referred_user.phone_number,
                status="registered",
                reward_given=False
            ).first()

            # Fallback: check for completed but reward_given=False (previous award failed)
            if not activity:
                activity = ReferralActivity.objects.filter(
                    referred_phone=referred_user.phone_number,
                    status="completed",
                    reward_given=False
                ).first()

            if not activity:
                print("No pending referral to reward")
                return

            reward_amount = 100

            # 3. GIVE REWARD TO REFERRER (ReferralProfile + LoyaltyPoints)
            referrer = activity.referrer
            referrer_profile, _ = ReferralProfile.objects.get_or_create(user=referrer)
            referrer_profile.rewards_earned = referrer_profile.rewards_earned + reward_amount
            # referrer_profile.invited_count = referrer_profile.invited_count + 1
            referrer_profile.save()

            # Also add to referrer's LoyaltyPoints
            try:
                referrer_customer = referrer.customer_profile
                referrer_loyalty, _ = LoyaltyPoint.objects.get_or_create(customer=referrer_customer)
                referrer_loyalty.add_points(reward_amount)
            except Exception as loyalty_err:
                print(f"⚠️  Could not add loyalty points to referrer: {loyalty_err}")

            # 4. GIVE REWARD TO REFERRED USER (ReferralProfile + LoyaltyPoints)
            referred_profile, _ = ReferralProfile.objects.get_or_create(user=referred_user)
            referred_profile.rewards_earned = referred_profile.rewards_earned + reward_amount
            referred_profile.save()

            # Also add to referred user's LoyaltyPoints
            try:
                referred_customer = referred_user.customer_profile
                referred_loyalty, _ = LoyaltyPoint.objects.get_or_create(customer=referred_customer)
                referred_loyalty.add_points(reward_amount)
            except Exception as loyalty_err:
                print(f"⚠️  Could not add loyalty points to referred user: {loyalty_err}")

            # 5. Mark activity as completed
            activity.status = "completed"
            activity.reward_given = True
            activity.save()

            # Refresh to confirm
            referrer_profile.refresh_from_db()
            referred_profile.refresh_from_db()

            print(f"✅ REFERRAL REWARD SUCCESS: +{reward_amount} to both!")
            print(f"   Referrer ({referrer.phone_number}): {referrer_profile.rewards_earned} ReferralProfile points + {reward_amount} LoyaltyPoints")
            print(f"   Referred ({referred_user.phone_number}): {referred_profile.rewards_earned} ReferralProfile points + {reward_amount} LoyaltyPoints")

        except Exception as e:
            print(f"❌ give_referral_reward ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

class RedeemRewardView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RedeemRewardSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        redeemed = serializer.save()
        return Response({"message": f"Reward '{redeemed.reward.title}' redeemed successfully."}, status=status.HTTP_201_CREATED)


class EarningRuleViewSet(viewsets.ModelViewSet):
    queryset = EarningRule.objects.all().order_by('display_order')
    serializer_class = EarningRuleSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]
            


class CouponListView(generics.ListAPIView):
    queryset = Coupon.objects.filter(is_active=True)
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class ApplyCouponView(generics.CreateAPIView):
    serializer_class = ApplyCouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        applied_coupon = serializer.save()

        return Response({
            "message": f"Coupon '{applied_coupon.coupon.code}' applied successfully!",
            "booking_id": applied_coupon.booking.id,
            "original_price": float(applied_coupon.original_price),
            "discounted_price": float(applied_coupon.discounted_price),
            "coupon_details": {
                "code": applied_coupon.coupon.code,
                "type": applied_coupon.coupon.discount_type,
                "value": float(applied_coupon.coupon.discount_value or 0)
            }
        }, status=status.HTTP_200_OK)

class AdminCouponListView(generics.ListAPIView):
    queryset = Coupon.objects.all().order_by('-expiry_date')
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]



class AdminCouponCreateView(generics.CreateAPIView):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(is_active=True)


class AdminCouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAdminUser]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def urgent_recalls_home(request):
    """
    Returns urgent and important recalls for the user's vehicles.
    Used for home screen alerts.
    """
    user = request.user
    if not hasattr(user, 'customer_profile'):
        return Response([], status=200)

    customer = user.customer_profile

    recalls = VehicleRecall.objects.filter(
        vehicle__customer=customer,
        recall__urgency__in=['urgent', 'important','moderate']
    ).select_related('vehicle', 'recall').order_by(
        '-recall__urgency', 'status', '-recall__created_at'  # active first, then completed
    )

    # Format a lightweight response for home UI
    data = [
        {
            "id": r.id, 
            "vehicle": f"{r.vehicle.make} {r.vehicle.model} ({r.vehicle.year})",
            "recall_title": r.recall.title,
            "urgency": r.recall.urgency,
            "description": r.recall.description,
            "recall_number": r.recall.recall_number,
            "status": r.status,
            "already_serviced": r.status == 'completed',
            "created_at": r.recall.created_at.strftime("%Y-%m-%d"),
        }
        for r in recalls
    ]
    return Response(data)

class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Vehicle.objects.all()
        return Vehicle.objects.filter(customer__user=user)

    def perform_create(self, serializer):
        # FIX: fetch the customer for this logged-in user
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




# class PromotionBannerViewSet(viewsets.ModelViewSet):
#     queryset = PromotionBanner.objects.filter(is_active=True)
#     serializer_class = PromotionBannerSerializer
#     permission_classes = [AllowAny]
#     customer = self.request.user.customer_profile
#     serializer.save(customer=customer)

class PromotionBannerViewSet(viewsets.ModelViewSet):
    serializer_class = PromotionBannerSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only logged-in users can access

    def get_queryset(self):
        # Return all active banners
        now = timezone.now()
        return PromotionBanner.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now
        )

    def perform_create(self, serializer):
        serializer.save()


class RecallViewSet(viewsets.ModelViewSet):
    queryset = Recall.objects.all()
    serializer_class = RecallSerializer
    permission_classes = [permissions.IsAdminUser]
    

    def perform_create(self, serializer):
        recall = serializer.save()

        # ✅ Auto-fill title & description if not provided
        if recall.service:
            if not recall.title:
                recall.title = recall.service.title
            if not recall.description:
                recall.description = recall.service.description
            recall.save()

        # 🔍 Auto-link matching vehicles
        vehicles = Vehicle.objects.all()

        if recall.affected_make:
            vehicles = vehicles.filter(make__icontains=recall.affected_make)
        if recall.affected_model:
            vehicles = vehicles.filter(model__icontains=recall.affected_model)
        if recall.year_from:
            vehicles = vehicles.filter(year__gte=recall.year_from)
        if recall.year_to:
            vehicles = vehicles.filter(year__lte=recall.year_to)

        total = 0
        for vehicle in vehicles:
            _, created = VehicleRecall.objects.get_or_create(
                vehicle=vehicle,
                recall=recall,
                defaults={'status': 'active'}
            )
            if created:
                total += 1

        print(f"✅ Linked recall '{recall.title}' to {total} vehicles (auto-linked).")

 


class VehicleRecallViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleRecallSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return VehicleRecall.objects.all()
        return VehicleRecall.objects.filter(vehicle__customer__user=user)

    @action(detail=True, methods=['post'])
    def schedule_service(self, request, pk=None):
        """User schedules service for a recall"""
        recall_instance = self.get_object()
        customer = request.user.customer_profile

        # check if already completed
        if recall_instance.status == 'completed':
            return Response({
            "message": "This recall was already serviced. You can still schedule again.",
            "prefill_data": {
                "vehicle_make": recall_instance.vehicle.make,
                "vehicle_model": recall_instance.vehicle.model,
                "vehicle_year": recall_instance.vehicle.year,
                "service_name": recall_instance.recall.title
            }
        }, status=status.HTTP_200_OK)
            

        recall_instance.schedule_again()
        RecallServiceHistory.objects.create(
            vehicle_recall=recall_instance,
            customer=customer,
            is_repeat_service=False
        )
        return Response({"message": "Service scheduled successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def service_again(self, request, pk=None):
        recall_instance = self.get_object()
        customer = request.user.customer_profile

        recall_instance.schedule_again()
        RecallServiceHistory.objects.create(
            vehicle_recall=recall_instance,
            customer=customer,
            is_repeat_service=True
        )

        # 🎯 Return recall + vehicle info so frontend can prefill Book Service page
        return Response({
            "message": "Repeat recall service scheduled.",
            "prefill_data": {
                "vehicle_make": recall_instance.vehicle.make,
                "vehicle_model": recall_instance.vehicle.model,
                "vehicle_year": recall_instance.vehicle.year,
                "service_name": recall_instance.recall.title
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        recall_instance = self.get_object()
        customer = recall_instance.vehicle.customer

        # Mark as completed
        recall_instance.status = 'completed'
        recall_instance.last_service_date = timezone.now()
        recall_instance.service_count += 1
        recall_instance.save()

        # Create history
        RecallServiceHistory.objects.create(
            vehicle_recall=recall_instance,
            customer=customer,
            service_date=timezone.now(),
            remarks="Service marked completed by admin",
            is_repeat_service=(recall_instance.service_count > 1)
        )

        # Optional: mark related bookings as completed
        Booking.objects.filter(
            customer=customer,
            vehicle_make=recall_instance.vehicle.make,
            vehicle_model=recall_instance.vehicle.model,
            is_recall_service=True
        ).update(status='completed')

        # DON'T CALL check_if_already_serviced() — it's irrelevant now!
        # Just use the serializer's logic → status == 'completed'

        return Response({
                "message": "Recall marked as completed successfully.",
                "status": recall_instance.status,
                "already_serviced": recall_instance.status == 'completed',
                "service_count": recall_instance.service_count,
                "last_service_date": recall_instance.last_service_date
})

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().select_related('customer__user')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Review.objects.all()
        try:
            customer = user.customer_profile
            return Review.objects.filter(customer=customer)
        except:
            return Review.objects.none()


class ServiceFeedbackViewSet(viewsets.ModelViewSet):
    queryset = ServiceFeedback.objects.all().order_by('-submitted_at')
    serializer_class = ServiceFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        try:
            customer = Customer.objects.get(user=user)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer profile not found.")

        booking = serializer.validated_data['booking']

        # ✅ Ensure feedback belongs to this user only
        if booking.customer != customer:
            raise serializers.ValidationError("You cannot submit feedback for another user's booking.")

        # ✅ Allow only if booking completed
        if booking.status != 'ready_for_pickup':
            raise serializers.ValidationError("You can only give feedback for completed bookings.")

        # ✅ Prevent duplicates (extra safety)
        if ServiceFeedback.objects.filter(customer=customer, booking=booking).exists():
            raise serializers.ValidationError("Feedback already submitted for this booking.")

        # Save feedback
        feedback = serializer.save(customer=customer)

        # ✅ Award Loyalty Points for review
        try:
            loyalty, _ = LoyaltyPoint.objects.get_or_create(customer=customer)
            loyalty.add_points(50)
            print(f"✅ Awarded 50 loyalty points for feedback on booking {booking.id}")
        except Exception as e:
            print(f"❌ Loyalty point award failed: {e}")

        return feedback

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ServiceFeedback.objects.all().select_related('customer__user', 'booking').order_by('-submitted_at')
        return ServiceFeedback.objects.filter(customer__user=user).order_by('-submitted_at')
         
    # @action(detail=True, methods=['post'])
    # def mark_completed(self, request, pk=None):
    #     """
    #     ✅ Admin marks recall service as completed.
    #     Automatically updates recall, booking, and already_serviced status.
    #     """
    #     recall_instance = self.get_object()
    #     customer = recall_instance.vehicle.customer

    #     # 1️⃣ Mark recall as completed
    #     recall_instance.status = 'completed'
    #     recall_instance.last_service_date = timezone.now()
    #     recall_instance.service_count += 1
    #     recall_instance.save()

    #     # 2️⃣ Create RecallServiceHistory record
    #     RecallServiceHistory.objects.create(
    #         vehicle_recall=recall_instance,
    #         customer=customer,
    #         service_date=timezone.now(),
    #         remarks="Service marked completed by admin",
    #         is_repeat_service=(recall_instance.service_count > 1)
    #     )

    #     # 3️⃣ Ensure related booking is marked as completed
    #     from .models import Booking
    #     Booking.objects.filter(
    #         customer=customer,
    #         vehicle_make=recall_instance.vehicle.make,
    #         vehicle_model=recall_instance.vehicle.model,
    #         is_recall_service=True
    #     ).update(status='completed')

    #     # 4️⃣ Recheck for already serviced recall
    #     already_serviced = recall_instance.check_if_already_serviced()

    #     # 5️⃣ Return updated info
    #     return Response({
    #         "message": "Recall marked as completed successfully.",
    #         "already_serviced": already_serviced,
    #         "status": recall_instance.status,
    #         "service_count": recall_instance.service_count,
    #         "last_service_date": recall_instance.last_service_date
    #     }, status=status.HTTP_200_OK)

# ──────────────────────────────────────────────────────────────
# DEBUG: Check referral data for current user (temporary)
# Remove this later when everything works
# ──────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_referral(request):
    profile, _ = ReferralProfile.objects.get_or_create(user=request.user)
    activities = ReferralActivity.objects.filter(referrer=request.user).values(
        'id', 'referred_phone', 'status', 'reward_given', 'created_at'
    )
    return Response({
        "debug_user": request.user.phone_number,
        "referral_code": profile.referral_code,
        "invited_count": profile.invited_count,
        "rewards_earned": profile.rewards_earned,
        "referral_activities": list(activities),
        "total_referral_activities": ReferralActivity.objects.filter(referrer=request.user).count(),
    })


class MembershipPlanViewSet(viewsets.ModelViewSet):
    """
    Admin can manage plans; users can view available ones.
    """
    serializer_class = MembershipPlanSerializer
    permission_classes = [IsAdminOrReadOnly]
    queryset = MembershipPlan.objects.all().order_by('price_per_month')

    def get_queryset(self):
        if self.request.user.is_staff:
            return MembershipPlan.objects.all()
        return MembershipPlan.objects.filter(is_active=True)


class CustomerMembershipViewSet(viewsets.ModelViewSet):
    """
    Manage user membership
    - User: View/Select
    - Admin: Manage all
    """
    serializer_class = CustomerMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CustomerMembership.objects.select_related('customer', 'plan')

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return CustomerMembership.objects.all()
        return CustomerMembership.objects.filter(customer__user=user)

    @action(detail=False, methods=['get'])
    def my_membership(self, request):
        """Get current user's membership"""
        customer = request.user.customer_profile
        membership = CustomerMembership.objects.filter(customer=customer, active=True).first()
        if not membership:
            return Response({"message": "No active membership"}, status=404)
        serializer = self.get_serializer(membership)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def activate(self, request):
        """
        User selects a plan from frontend (no payment for now).
        Frontend will send: { "plan_id": <id> }
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        # if membership.active and membership.plan == selected_plan:
        #   return Response({"message": "Already active"}, status=400)

        return Response({
            "message": f"{membership.plan.tier.title()} membership activated!",
            "membership": CustomerMembershipSerializer(membership, context={'request': request}).data
        }, status=201)
