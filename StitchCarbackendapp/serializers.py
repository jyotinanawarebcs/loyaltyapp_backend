from rest_framework import serializers
from .models import Service,CustomUser,Booking,Customer,Offer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, datetime
from django.contrib.auth import get_user_model
from .models import Offer
from rest_framework import serializers
from .models import ReferralProfile, ReferralActivity
from .models import Vehicle, FeaturedPromotion, PromotionBanner






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
    services = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), many=True, required=False )
    vehicle_number = serializers.CharField(required=False, allow_blank=True)
    offer = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.all(), allow_null=True, required=False)
    customer_username = serializers.SerializerMethodField(read_only=True)
    customer_contact = serializers.SerializerMethodField(read_only=True)
    service_title = serializers.SerializerMethodField(read_only=True)
    offer_code = serializers.SerializerMethodField(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'customer_username', 'customer_contact','services', 'service_title', 'offer', 'offer_code',
            'booking_date', 'appointment_date', 'appointment_time',
            'vehicle_make', 'vehicle_model', 'vehicle_year',
            'total_price', "vehicle_number",'vehicle', 'status', 'offer_code','notes'
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
    
    def get_total_price(self, obj):
        return sum([s.price for s in obj.services.all()])


    def update(self, instance, validated_data):
        services = validated_data.pop('services', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if services is not None:
            instance.services.set(services)
        return instance


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'password','first_name', 'last_name',
            'phone_number', 'profile_image', 'is_customer', 'is_staff'
        ]
        read_only_fields=['id']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        is_customer = validated_data.get("is_customer", True)
        if is_customer:
            validated_data["is_staff"] = False
        else:
            validated_data["is_staff"] = True

        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

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
    services = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Service.objects.all()
    )
    service_names = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            'id',
            'services',
            'service_names',
            'title',
            'description',
            'discount_percentage',
            'valid_from',
            'valid_to',
            'is_active',
            'image_url',
        ]

    def get_service_names(self, obj):
        return [s.title for s in obj.services.all()]

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
    

class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = '__all__'


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
