from rest_framework import serializers
from .models import Service,CustomUser,Booking,Customer,Offer,Reward, LoyaltyPoint, RedeemedReward, EarningRule, Notification, Coupon, AppliedCoupon, Booking, Service,Vehicle, Recall, VehicleRecall, RecallServiceHistory,Review,ServiceFeedback
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, datetime
from django.contrib.auth import get_user_model
from .models import Offer
from rest_framework import serializers
from .models import ReferralProfile, ReferralActivity
from .models import Vehicle, FeaturedPromotion, PromotionBanner
from rest_framework.decorators import action
from django.utils import timezone
User = get_user_model()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__' 

class BookingSerializer(serializers.ModelSerializer):
   
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False)
    services = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), many=True, required=False )
    vehicle_number = serializers.CharField(required=False, allow_blank=True)
    offer = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.all(), allow_null=True, required=False)
    customer_username = serializers.SerializerMethodField(read_only=True)
    customer_contact = serializers.SerializerMethodField(read_only=True)
    service_title = serializers.SerializerMethodField(read_only=True)
    offer_code = serializers.SerializerMethodField(read_only=True)
    total_price = serializers.SerializerMethodField()

    reward_id = serializers.PrimaryKeyRelatedField(
        source='reward',
        queryset=Reward.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'customer_username', 'customer_contact','services', 'service_title', 'offer', 'offer_code',
            'booking_date', 'appointment_date', 'appointment_time',
            'vehicle_make', 'vehicle_model', 'vehicle_year',
            'total_price', "vehicle_number",'vehicle', 'status', 'offer_code','notes','reward_id'
        ]
        read_only_fields = ['id', 'booking_date', 'customer_username', 'service_title']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Safe access to context
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request and not request.user.is_staff:
            # Normal users: hide the customer field in the form
            self.fields.pop('customer', None),
            # self.fields.pop('status', None)  # hide status


    def get_customer_username(self, obj):
        try:
            return obj.customer.user.username
        except Exception:
            return None 

    def get_service_title(self, obj):
        return ", ".join([s.title for s in obj.services.all()])


    def get_offer_code(self, obj):
        return getattr(obj.offer, 'code', None) if obj.offer else None

    def validate_appointment_date(self, value):
        # must be a date in the future (or today) — adjust per business rules
        if value < date.today():
            raise serializers.ValidationError("appointment_date must be today or a future date.")
        return value

    def validate_vehicle_year(self, value):
        if not value.isdigit() or len(value) not in (3,4):
            raise serializers.ValidationError("vehicle_year must be numeric (e.g. '2020').")
        return value
    def get_customer_contact(self, obj):
        try:
            return obj.customer.user.phone_number  # or whatever your field name is in Customer model
        except Exception:
            return None

    def validate(self, data):
        # appointment_date + appointment_time combined in future
        appt_date = data.get('appointment_date', None)
        appt_time = data.get('appointment_time', None)
        if appt_date and appt_time:
            combined = datetime.combine(appt_date, appt_time)
            if combined < datetime.now():
                raise serializers.ValidationError("Appointment date/time must be in the future.")
        return data

    def create(self, validated_data):
        services = validated_data.pop('services', [])
        booking = Booking.objects.create(**validated_data)
        booking.services.set(services)
        booking.save()
        return booking
    
    def get_total_price(self, obj):
        # ✅ Return the actual total_price from DB (which may have reward discount applied)
        # Always return the DB value (including 0 for free rewards)
        # Only calculate from services if not set
        if obj.total_price is not None:
            return float(obj.total_price)
        return sum([s.price for s in obj.services.all()])



    def update(self, instance, validated_data):
        services = validated_data.pop('services', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if services is not None:
            instance.services.set(services)
        return instance
# class BookingSerializer(serializers.ModelSerializer):
#     # show related object titles for readability (read-only)
#     customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False)
#     service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
#     offer = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.all(), allow_null=True, required=False)
#     customer_username = serializers.SerializerMethodField(read_only=True)
#     customer_contact = serializers.SerializerMethodField(read_only=True)
#     service_title = serializers.SerializerMethodField(read_only=True)
#     offer_code = serializers.SerializerMethodField(read_only=True)

#     class Meta:
#         model = Booking
#         fields = [
#             'id', 'customer', 'customer_username', 'customer_contact','service', 'service_title', 'offer', 'offer_code',
#             'booking_date', 'appointment_date', 'appointment_time',
#             'vehicle_make', 'vehicle_model', 'vehicle_year',
#             'total_price', 'status', 'offer_code','notes'
#         ]
#         read_only_fields = ['id', 'booking_date', 'total_price', 'customer_username', 'service_title']

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Safe access to context
#         request = self.context.get('request') if hasattr(self, 'context') else None
#         if request and not request.user.is_staff:
#             # Normal users: hide the customer field in the form
#             self.fields.pop('customer', None),
#             # self.fields.pop('status', None)  # hide status


#     def get_customer_username(self, obj):
#         try:
#             return obj.customer.user.username
#         except Exception:
#             return None

#     def get_service_title(self, obj):
#         return getattr(obj.service, 'title', None)

#     def get_offer_code(self, obj):
#         return getattr(obj.offer, 'code', None) if obj.offer else None

#     def validate_appointment_date(self, value):
#         # must be a date in the future (or today) — adjust per business rules
#         if value < date.today():
#             raise serializers.ValidationError("appointment_date must be today or a future date.")
#         return value

#     def validate_vehicle_year(self, value):
#         if not value.isdigit() or len(value) not in (3,4):
#             raise serializers.ValidationError("vehicle_year must be numeric (e.g. '2020').")
#         return value
#     def get_customer_contact(self, obj):
#         try:
#             return obj.customer.user.phone_number  # or whatever your field name is in Customer model
#         except Exception:
#             return None

#     def validate(self, data):
#         # appointment_date + appointment_time combined in future
#         appt_date = data.get('appointment_date', None)
#         appt_time = data.get('appointment_time', None)
#         if appt_date and appt_time:
#             combined = datetime.combine(appt_date, appt_time)
#             if combined < datetime.now():
#                 raise serializers.ValidationError("Appointment date/time must be in the future.")
#         return data

#     def create(self, validated_data):
#         # customer assignment is handled in the view (preferred), but if customer is present allow it
#         booking = Booking.objects.create(**validated_data)
#         # model's save() will compute total_price already, but we called create -> ensure total_price is set
#         booking.save()
#         return booking

#     def update(self, instance, validated_data):
#         for k, v in validated_data.items():
#             setattr(instance, k, v)
#         instance.save()
#         return instance


class CustomUserSerializer(serializers.ModelSerializer):
    customer_profile = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'password','first_name', 'last_name',
            'phone_number', 'profile_image', 'is_customer', 'is_staff','customer_profile'
        ]
        read_only_fields=['id','is_staff']
    
    def get_customer_profile(self, obj):
        """Return or auto-create customer profile safely."""
        try:
            from .serializers import CustomerSerializer

            # ✅ Create a Customer record if missing
            customer, _ = Customer.objects.get_or_create(user=obj)
            return CustomerSerializer(customer).data

        except Exception as e:
            print(f"⚠️ Error in get_customer_profile for user {obj.id}: {e}")
            return None

    def create(self, validated_data):
        customer_data = validated_data.pop('customer_profile', None)
        password = validated_data.pop('password', None)
        is_customer = validated_data.get("is_customer", True)
        user = CustomUser.objects.create(**validated_data)
        if is_customer:
            validated_data["is_staff"] = False
        else:
            validated_data["is_staff"] = True

        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()

            # ✅ Ensure a Customer profile is always created
        from .models import Customer
        Customer.objects.get_or_create(user=user)
        if customer_data:
            Customer.objects.create(user=user, **customer_data)
        return user

    def update(self, instance, validated_data):
        customer_data = validated_data.pop('customer_profile', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        # ✅ Always ensure a Customer exists (create if missing)
        from .models import Customer
        Customer.objects.get_or_create(user=instance)

        if isinstance(customer_data, dict):
            Customer.objects.update_or_create(user=instance, defaults=customer_data)
        return instance

    @action(detail=False, methods=['post'], url_path='upload-image')
    def upload_image(self, request):
        """Upload or change profile image"""
        user = request.user
        image = request.FILES.get('profile_image')

        if not image:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

        user.profile_image = image
        user.save()
        return Response({'message': 'Profile image updated successfully', 'image_url': user.profile_image.url})

    @action(detail=False, methods=['delete'], url_path='delete-image')
    def delete_image(self, request):
        """Delete user’s profile image"""
        user = request.user
        if not user.profile_image:
            return Response({'error': 'No image to delete'}, status=status.HTTP_400_BAD_REQUEST)

        user.profile_image.delete(save=True)
        return Response({'message': 'Profile image deleted successfully'})

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['address', 'city', 'country', 'joined_at','notifications_enabled']
        read_only_fields = ['joined_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone_number',
                  'password', 'confirm_password', 'referral_code']

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value  

    def validate_username(self, value):
        if not value.isalpha():
            raise serializers.ValidationError("Username must contain only letters")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')

        # create user
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()

        # ---- Referral Handling ----
        if referral_code:
            try:
                referrer_profile = ReferralProfile.objects.get(referral_code=referral_code)
                ReferralActivity.objects.create(
                    referrer=referrer_profile.user,
                    referred_phone=user.phone_number,
                    status="registered"
                )
                # increase invited count
                referrer_profile.invited_count += 1
                referrer_profile.save()

            except ReferralProfile.DoesNotExist:
                raise serializers.ValidationError({"referral_code": "Invalid referral code"})

        return user


# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)
#     confirm_password = serializers.CharField(write_only=True)

#     class Meta:
#         model = CustomUser
#         fields = ['username', 'email','phone_number','password', 'confirm_password']

#     def validate_email(self, value):
#         if User.objects.filter(email=value).exists():
#             raise serializers.ValidationError("Email already exists")
#         return value   

#     def validate_username(self, value):
#         if not value.isalpha():
#             raise serializers.ValidationError("Username must contain only letters")
#         return value    

#     def validate(self, attrs):
#         if attrs['password'] != attrs['confirm_password']:
#             raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
#         return attrs

#     def create(self, validated_data):
#         validated_data.pop('confirm_password')  
#         password = validated_data.pop('password')
#         user = CustomUser(**validated_data)
#         user.set_password(password)
#         user.save()
#         return user
            
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        print("Username:", username)
        print("Password:", password)
        if not username or not password:
            raise serializers.ValidationError("Must include username and password.")
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs['user'] = user
        return attrs

class SendVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6) 



class OfferSerializer(serializers.ModelSerializer):
    services_with_details = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            'id',
            'services',
            'services_with_details',
            'title',
            'description',
            'discount_percentage',
            'valid_from',
            'valid_to',
            'is_active',
            'image_url',
        ]

    def get_services_with_details(self, obj):
        return [
            {
                "id": s.id,
                "title": s.title,
                "price": s.price,
            }
            for s in obj.services.all()
        ]
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url)
        return None



class ReferralProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralProfile
        fields = ["referral_code", "invited_count", "rewards_earned"]


class ReferralActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralActivity
        fields = ["id", "referred_phone", "status", "reward_given", "created_at"]   

class InviteFriendSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits.")
        return value
    code = serializers.CharField(max_length=6)    

class LoyaltyPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyPoint
        fields = ['points']


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ['id', 'title', 'description', 'required_points', 'image', 'is_active','service','discount_value']


class RedeemedRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = RedeemedReward
        fields = ['id', 'reward', 'redeemed_at']


class RedeemRewardSerializer(serializers.Serializer):
    reward_id = serializers.IntegerField()

    def validate(self, data):
        reward_id = data.get('reward_id')
        reward = Reward.objects.filter(id=reward_id, is_active=True).first()
        if not reward:
            raise serializers.ValidationError("Reward not found or inactive.")
        data['reward'] = reward
        return data

    def save(self, **kwargs):
        request = self.context['request']
        # ensure customer exists
        try:
            customer = request.user.customer_profile
        except Exception:
            raise serializers.ValidationError("Customer profile not found for user.")
        reward = self.validated_data['reward']
        loyalty, _ = LoyaltyPoint.objects.get_or_create(customer=customer)

        if loyalty.points < reward.required_points:
            raise serializers.ValidationError("Insufficient points to redeem this reward.")

        # Deduct and create record
        success = loyalty.deduct_points(reward.required_points)
        if not success:
            raise serializers.ValidationError("Failed to deduct points.")

        redeemed = RedeemedReward.objects.create(customer=customer, reward=reward)
        return redeemed


class EarningRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EarningRule
        fields = ['id', 'title', 'description', 'points', 'icon', 'display_order','amount_base','min_spend']        

class NotificationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']     

class CouponSerializer(serializers.ModelSerializer):
    applicable_service_title = serializers.CharField(source='applicable_service.title', read_only=True, allow_null=True)
    usage_restriction = serializers.SerializerMethodField()


    class Meta:
        model = Coupon
        fields = ['id', 'code', 'title', 'description', 'discount_type', 'discount_value', 'expiry_date', 'applicable_service','applicable_service_title', 'usage_restriction']
    def get_usage_restriction(self, obj):
        if obj.applicable_service:
            return f"Only for {obj.applicable_service.title}"
        return "Can be used on any service"

class ApplyCouponSerializer(serializers.Serializer):
    coupon_code = serializers.CharField()
    booking_id = serializers.IntegerField()
    
    def validate(self, data):
        user = self.context['request'].user
        coupon_code = data['coupon_code']
        booking_id = data['booking_id']

        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired coupon code.")

        if coupon.expiry_date and coupon.expiry_date < timezone.now().date():
            raise serializers.ValidationError("Coupon has expired.")

        try:
            booking = Booking.objects.get(id=booking_id, customer__user=user)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found or access denied.")

        # KEY FIX: Check if coupon is restricted to a specific service
        if coupon.applicable_service:
            # Check if ANY of the booking's services match the allowed one
            if not booking.services.filter(id=coupon.applicable_service.id).exists():
                raise serializers.ValidationError(
                    f"This coupon is only valid for '{coupon.applicable_service.title}' service."
                )

        # Optional: Prevent reuse (if you want one-time use per customer)
        if AppliedCoupon.objects.filter(customer=booking.customer, coupon=coupon).exists():
            raise serializers.ValidationError("You have already used this coupon.")

        data['coupon'] = coupon
        data['booking'] = booking
        return data
    # def validate(self, data):
    #     user = self.context['request'].user
    #     coupon_code = data['coupon_code']
    #     booking_id = data['booking_id']

    #     try:
    #         coupon = Coupon.objects.get(code=coupon_code, is_active=True)
    #     except Coupon.DoesNotExist:
    #         raise serializers.ValidationError("Invalid coupon code.")

    #     if coupon.expiry_date < timezone.now().date():
    #         raise serializers.ValidationError("Coupon has expired.")

    
    #     try:
    #         booking = Booking.objects.get(id=booking_id, customer__user=user)
    #     except Booking.DoesNotExist:
    #         raise serializers.ValidationError("Booking not found for this user.")

    #     data['coupon'] = coupon
    #     data['booking'] = booking
    #     return data

    def create(self, validated_data):
        customer = validated_data['booking'].customer
        coupon = validated_data['coupon']
        booking = validated_data['booking']

        # 🔹 Store original price BEFORE changing it
        original_price = booking.total_price

        # 🔹 Calculate discount
        if coupon.discount_type == 'percentage':
            discount = (coupon.discount_value / 100) * original_price
        elif coupon.discount_type == 'fixed':
            discount = coupon.discount_value
        elif coupon.discount_type == 'free':
            discount = original_price
        else:
            discount = 0

        final_price = max(original_price - discount, 0)

        # 🔹 Save applied coupon record
        applied_coupon, created = AppliedCoupon.objects.get_or_create(
            customer=customer,
            booking=booking,
            coupon=coupon,
            defaults={'discounted_price': final_price}
        )
        booking.total_price = final_price
        booking.save()

        # ✅ Return both prices (we’ll use original in the view)
        applied_coupon.original_price = original_price  # temporary attach for response
        return applied_coupon


class RecallSerializer(serializers.ModelSerializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())

    class Meta:
        model = Recall
        fields = [
            'id',
            'service',          
            'recall_number',
            'urgency',
            'affected_make',
            'affected_model',
            'year_from',
            'year_to',
        ]



class VehicleSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id',
            'vin',
            'vehicle_number',
            'make',
            'model',
            'year',
            'image',
            'image_url',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_image_url(self, obj):
        """Return full image URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        elif obj.image:
            return obj.image.url
        return None
    

# class OfferSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Offer
#         fields = '__all__'


class FeaturedPromotionSerializer(serializers.ModelSerializer):
    # Use SerializerMethodField to pass context
    offer = serializers.SerializerMethodField()
    offer_id = serializers.PrimaryKeyRelatedField(
        queryset=Offer.objects.all(), source='offer', write_only=True
    )

    display_title = serializers.SerializerMethodField()
    display_description = serializers.SerializerMethodField()

    class Meta:
        model = FeaturedPromotion
        fields = '__all__'

    def get_offer(self, obj):
        # Pass context so OfferSerializer can build image_url and service_names
        serializer = OfferSerializer(obj.offer, context=self.context)
        return serializer.data

    def get_display_title(self, obj):
        return obj.title if obj.title else obj.offer.title

    def get_display_description(self, obj):
        return obj.description if obj.description else obj.offer.description



class PromotionBannerSerializer(serializers.ModelSerializer):
    offer = OfferSerializer(read_only=True)
    offer_id = serializers.PrimaryKeyRelatedField(
        queryset=Offer.objects.all(), source='offer', write_only=True, required=False
    )

    class Meta:
        model = PromotionBanner
        fields = [
            'id',
            'title',
            'description',
            'image',
            'button_text',
            'offer',
            'offer_id',
            'valid_from',
            'valid_to',
            'is_active'
        ]



class VehicleRecallSerializer(serializers.ModelSerializer):
    recall = RecallSerializer()
    vehicle = VehicleSerializer()
    already_serviced = serializers.SerializerMethodField()

    class Meta:
        model = VehicleRecall
        fields = [
            'id', 'vehicle', 'recall', 'status',
            'last_service_date', 'next_service_date',
            'service_count', 'already_serviced'
        ]

    def get_already_serviced(self, obj):
        return obj.status == 'completed'

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'customer', 'booking', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at', 'customer']

    def create(self, validated_data):
        request = self.context['request']
        customer = request.user.customer_profile
        review = Review.objects.create(customer=customer, **validated_data)
        return review


class ServiceFeedbackSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.user.username', read_only=True)
    service_titles = serializers.SerializerMethodField()
    appointment_date = serializers.DateField(source='booking.appointment_date', read_only=True)

    class Meta:
        model = ServiceFeedback
        fields = [
            'id',
            'customer',
            'booking',
            'overall_rating',
            'punctuality_rating',
            'service_quality_rating',
            'communication_rating',
            'review',
            'submitted_at',
            'customer_name',
            'service_titles',
            'appointment_date'
        ]
        read_only_fields = [
            'submitted_at',
            'customer_name',
            'service_titles',
            'appointment_date',
            'customer',
        ]

    def get_service_titles(self, obj):
        return [service.title for service in obj.booking.services.all()]

    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request else None
        try:
            # ✅ convert user to Customer object
            customer = Customer.objects.get(user=user)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer profile not found.")

        booking = data.get('booking')
        if ServiceFeedback.objects.filter(customer=customer, booking=booking).exists():
            raise serializers.ValidationError("Feedback already submitted for this booking.")
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        try:
            # ✅ convert user to Customer object again here
            customer = Customer.objects.get(user=user)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer profile not found.")

        validated_data['customer'] = customer
        return super().create(validated_data)
