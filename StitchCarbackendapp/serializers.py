from rest_framework import serializers
from .models import Service,CustomUser,Booking,Customer,Offer,Reward, LoyaltyPoint, RedeemedReward, EarningRule, Notification, Coupon, AppliedCoupon, Booking, Service,Vehicle, Recall, VehicleRecall, RecallServiceHistory
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, datetime
from django.contrib.auth import get_user_model
from rest_framework.decorators import action

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
    # show related object titles for readability (read-only)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False)
    services = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), many=True)
    offer = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.all(), allow_null=True, required=False)
    customer_username = serializers.SerializerMethodField(read_only=True)
    customer_contact = serializers.SerializerMethodField(read_only=True)
    service_title = serializers.SerializerMethodField(read_only=True)
    offer_code = serializers.SerializerMethodField(read_only=True)
    reward_id = serializers.PrimaryKeyRelatedField(
        source='reward',
        queryset=Reward.objects.all(),
        required=False,
        allow_null=True
    )
    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'customer_username', 'customer_contact','services', 'service_title', 'offer', 'offer_code',
            'booking_date', 'appointment_date', 'appointment_time',
            'vehicle_make', 'vehicle_model', 'vehicle_year',
            'total_price', 'status', 'offer_code','notes','reward_id'
        ]
        read_only_fields = ['id', 'booking_date', 'total_price', 'customer_username', 'service_title']

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
        """Safely return customer data if exists"""
        try:
            from .serializers_customer import CustomerSerializer  # ✅ local import to avoid circular import
            if hasattr(obj, 'customer_profile'):
                return CustomerSerializer(obj.customer_profile).data
            return None
        except Exception:
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
        fields = ['address', 'city', 'country', 'joined_at']
        read_only_fields = ['joined_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email','phone_number','password', 'confirm_password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
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
        validated_data.pop('confirm_password')  
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user
            
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
        fields = ['id', 'title', 'description', 'points', 'icon', 'display_order']        

class NotificationSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']     

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'title', 'description', 'discount_type', 'discount_value', 'expiry_date', 'applicable_service']


class ApplyCouponSerializer(serializers.Serializer):
    coupon_code = serializers.CharField()
    booking_id = serializers.IntegerField()

    def validate(self, data):
        from django.utils import timezone
        user = self.context['request'].user
        coupon_code = data['coupon_code']
        booking_id = data['booking_id']

        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code.")

        if coupon.expiry_date < timezone.now().date():
            raise serializers.ValidationError("Coupon has expired.")

    
        try:
            booking = Booking.objects.get(id=booking_id, customer__user=user)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found for this user.")

        data['coupon'] = coupon
        data['booking'] = booking
        return data

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