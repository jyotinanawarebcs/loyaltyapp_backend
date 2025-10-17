from rest_framework import serializers
from .models import Booking, Service, Offer, Customer
from django.utils import timezone
from datetime import date, datetime

class BookingSerializer(serializers.ModelSerializer):
    # show related object titles for readability (read-only)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False)
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    offer = serializers.PrimaryKeyRelatedField(queryset=Offer.objects.all(), allow_null=True, required=False)
    customer_username = serializers.SerializerMethodField(read_only=True)
    customer_contact = serializers.SerializerMethodField(read_only=True)
    service_title = serializers.SerializerMethodField(read_only=True)
    offer_code = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'customer_username', 'customer_contact','service', 'service_title', 'offer', 'offer_code',
            'booking_date', 'appointment_date', 'appointment_time',
            'vehicle_make', 'vehicle_model', 'vehicle_year',
            'total_price', 'status', 'offer_code','notes'
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
        return getattr(obj.service, 'title', None)

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
        # customer assignment is handled in the view (preferred), but if customer is present allow it
        booking = Booking.objects.create(**validated_data)
        # model's save() will compute total_price already, but we called create -> ensure total_price is set
        booking.save()
        return booking

    def update(self, instance, validated_data):
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance


#================================================================================================

from rest_framework import serializers
from .models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'password','first_name', 'last_name',
            'phone_number', 'profile_image', 'is_customer',
        ]
        read_only_fields = ['id']

#=================================================================================================
from rest_framework import serializers
from .models import Offer

class OfferSerializer(serializers.ModelSerializer):
    service_title = serializers.ReadOnlyField(source='service.title')
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            'id', 'service', 'service_title', 'title', 'description',
            'discount_percentage', 'valid_from', 'valid_to', 
            'is_active', 'image', 'is_valid'
        ]
        read_only_fields = ['id', 'is_valid']

    def get_is_valid(self, obj):
        """Return True if offer is currently valid"""
        return obj.is_valid()

