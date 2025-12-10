from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.conf import settings
import uuid
from django.contrib.auth.models import User
from decimal import Decimal


# Create your models here.

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_customer = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",  
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups"
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_set_permissions",  
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions"
    )
    def __str__(self):
        return self.username

class Customer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='customer_profile')
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    joined_at = models.DateTimeField(default=timezone.now)
    notifications_enabled = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    # NEW CUSTOMER
    def is_new_customer(self):
        from .models import Booking
  # replace with your actual Booking model path
        return not Booking.objects.filter(customer=self).exists()

    # INACTIVE CUSTOMER (no booking in last 60 days)
    def is_inactive_customer(self, days=60):
        from .models import Booking
        last_booking = (
            Booking.objects.filter(customer=self)
            .order_by('-created_at')
            .first()
        )
        if not last_booking:
            return False  # handled by new customer check
        return (timezone.now() - last_booking.created_at).days >= days

    # LOYAL CUSTOMER (example: 5+ bookings)
    def is_loyal_customer(self):
        from .models import Booking
        count = Booking.objects.filter(customer=self).count()
        return count >= 5
    
class Service(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='services/')
    is_popular = models.BooleanField(default=False)
    interval_days = models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.title

class Offer(models.Model):
    OFFER_TYPE_CHOICES = [
        ('fixed', 'Fixed Services'),
        ('flexible', 'Flexible Services')  # customer can choose any service
    ]

    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES, default='flexible')
    services = models.ManyToManyField('Service', related_name='offers')
    title= models.CharField(max_length=100)
    description=models.TextField(blank=True,null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage discount (e.g., 10.00 = 10%)")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='offers/', blank=True, null=True)
     
    def __str__(self):
        service_titles = ", ".join([s.title for s in self.services.all()])
        return f"{self.title} - {service_titles}"

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to
    


class Booking(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),            # user booked
        ('in_progress', 'In Progress'),  # admin confirmed / service ongoing
        ('completed', 'Completed'),      # service done
        ('ready_for_pickup', 'Ready for Pickup'),  # car ready
        ('cancelled', 'Cancelled'),      # cancelled
    ]

    customer = models.ForeignKey("Customer", on_delete=models.CASCADE, related_name='bookings')
    services = models.ManyToManyField("Service", related_name='bookings')
    vehicle = models.ForeignKey("Vehicle", on_delete=models.CASCADE, null=True, blank=True)
    offer = models.ForeignKey("Offer", on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    reward = models.ForeignKey('Reward', on_delete=models.SET_NULL, null=True, blank=True)
    booking_date = models.DateTimeField(default=timezone.now)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    vehicle_make = models.CharField(max_length=100)
    vehicle_model = models.CharField(max_length=100)
    vehicle_year = models.CharField(max_length=4)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    notes = models.TextField(blank=True, null=True)
    is_recall_service = models.BooleanField(default=False)
    earning_rule = models.ForeignKey("EarningRule", on_delete=models.SET_NULL, null=True, blank=True)
    points_awarded = models.IntegerField(default=0)


    def __str__(self):
        # ✅ Fix: Booking can have *multiple services*, so show all titles
        service_titles = ", ".join([s.title for s in self.services.all()]) if self.id else "No Services"
        return f"{self.customer.user.username} - {service_titles} ({self.appointment_date})"

    def calculate_discounted_price(self):
        """
        Calculates the total price of all selected services,
        applying any offer discount and reward discount if present.
        """
        # Work with Decimal for safe arithmetic
        total_service_price = sum((service.price for service in self.services.all()), Decimal('0'))

        # Apply offer discount first if present
        if self.offer and hasattr(self.offer, 'discount_percentage'):
            discount = (Decimal(str(self.offer.discount_percentage)) / Decimal('100')) * total_service_price
            total_service_price = total_service_price - discount

        # Apply reward discount if present
        if self.reward:
            discount_value = Decimal(str(self.reward.discount_value or 0))
            if self.reward.type == "discount":
                if discount_value > Decimal('1'):
                    # treat as percentage like 10 (meaning 10%)
                    discount_amount = total_service_price * (discount_value / Decimal('100'))
                else:
                    # treat as fractional like 0.10
                    discount_amount = total_service_price * discount_value
                total_service_price = max(total_service_price - discount_amount, Decimal('0'))
            elif self.reward.type == "flat":
                total_service_price = max(total_service_price - discount_value, Decimal('0'))
            elif self.reward.type == "free":
                total_service_price = Decimal('0')

        return total_service_price

    def save(self, *args, **kwargs):
        """Automatically calculate total price.

        Behavior:
        - If caller explicitly updates `total_price` via `update_fields`, do not overwrite it.
        - Only recalculate when services exist (M2M present).
        """
        update_fields = kwargs.get('update_fields', None)

        # First perform the regular save
        super().save(*args, **kwargs)

        # If caller asked to update total_price explicitly, respect it and do not overwrite
        if update_fields and 'total_price' in update_fields:
            return

        # If there are no services yet, skip recalculation (services are M2M and set after create)
        try:
            has_services = self.services.exists()
        except Exception:
            has_services = False

        if not has_services:
            return

        # Recalculate and persist
        total = self.calculate_discounted_price()
        Booking.objects.filter(pk=self.pk).update(total_price=total)

class PasswordResetCode(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.code}"   

class FeaturedPromotion(models.Model):
    offer = models.ForeignKey('Offer', on_delete=models.CASCADE, related_name='featured_promotions')
    title = models.CharField(max_length=150, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    highlight_text = models.CharField(max_length=100, blank=True, null=True)  # E.g., 'Limited Time', 'New Customers'
    button_text = models.CharField(max_length=50, default="View Details")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='featured_promotions/', blank=True, null=True)  # ADD THIS

    PROMO_TYPES = [
    ('all', 'General Users'),
    ('new', 'New Customers'),
    ('inactive', 'Inactive Customers'),
    ('loyal', 'Loyal Customers'),
]

    promo_type = models.CharField(
        max_length=20,
        choices=PROMO_TYPES,
        default='all'
    )

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"Featured: {self.offer.title} ({self.highlight_text})"
    
class PromotionBanner(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, null=True, blank=True, related_name='promotion_banners')
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='promotion_banners/')
    button_text = models.CharField(max_length=50, default="Book Now")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title



from django.db import models
from django.conf import settings
import uuid

def generate_referral_code():
    return f"CARSVC-{uuid.uuid4().hex[:5].upper()}"
    

class ReferralProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="referral_profile"
    )
    referral_code = models.CharField(max_length=20, unique=True, default=generate_referral_code)
    invited_count = models.IntegerField(default=0)
    rewards_earned = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user} - {self.referral_code}"


class ReferralActivity(models.Model):
    STATUS_CHOICES = (
        ("invited", "Invited"),
        ("registered", "Registered"),
        ("completed", "Completed First Booking"),
    )

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_made"
    )
    referred_phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="invited")
    reward_given = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer} invited {self.referred_phone}"

        return f"{self.user.email} - {self.code}"    

class Reward(models.Model):
    REWARD_TYPES = [
        ('free', 'Free Service'),
        ('discount', 'Discount (%) or ₹'),
        ('flat', 'Flat ₹ Off'),
        ('cashback', 'Cashback (₹)'),
    ]
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(
        max_length=20,
        choices=REWARD_TYPES,
        default='free',
        help_text="Type of reward: Free, Discount, Flat, or Cashback"
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="For 'discount' use 0.10 for 10%. For flat/cashback use ₹ value."
    )
    required_points = models.PositiveIntegerField()
    image = models.ImageField(upload_to='rewards/', blank=True, null=True)
    service = models.ForeignKey('Service', on_delete=models.CASCADE, related_name='rewards', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.title} ({self.required_points} pts)"
    class Meta:
        ordering = ['required_points']

class LoyaltyPoint(models.Model):
    customer = models.OneToOneField('Customer', on_delete=models.CASCADE, related_name='loyalty')
    points = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def add_points(self, amount):
        self.points += int(amount)
        self.save()

    def deduct_points(self, amount):
        if self.points >= int(amount):
            self.points -= int(amount)
            self.save()
            return True
        return False

    def __str__(self):
        return f"{self.customer.user.username} - {self.points} pts"


class RedeemedReward(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='redeemed_rewards')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.username} redeemed {self.reward.title}"


class EarningRule(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    min_spend = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True, help_text="Minimum spend to qualify for points (optional).")
    points = models.PositiveIntegerField(default=0, help_text="Points for this action (may be used as a fixed bonus).")
    amount_base = models.IntegerField(default=0)      
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="frontend icon name (optional)")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} (+{self.points} pts)"        

class Notification(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.customer.user.username} - {self.title}"    

class Coupon(models.Model):
    COUPON_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free', 'Free Service'),
    ]

    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=COUPON_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    expiry_date = models.DateField()
    applicable_service = models.ForeignKey('Service', on_delete=models.CASCADE, related_name='coupons', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({self.discount_type})"

    def is_valid(self):
        
        if not self.is_active:
            return False
        if not self.expiry_date:
            return False  
        return timezone.now().date() <= self.expiry_date

class AppliedCoupon(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='applied_coupons')
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='applied_coupons')
    coupon = models.ForeignKey('Coupon', on_delete=models.CASCADE)
    applied_at = models.DateTimeField(auto_now_add=True)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('customer', 'booking', 'coupon')

    def __str__(self):
        return f"{self.customer.user.username} - {self.coupon.code} ({self.booking.id})"

class Vehicle(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='vehicles')
    vin = models.CharField(max_length=17, unique=True)
    vehicle_number = models.CharField(max_length=20, unique=True,blank=True, null=True)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    image = models.ImageField(upload_to='vehicle_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vin']),
            models.Index(fields=['vehicle_number']),
            models.Index(fields=['make', 'model', 'year']),
        ]
    def __str__(self):
        return f"{self.make} {self.model} ({self.year})"


class Recall(models.Model):
    URGENCY_CHOICES = [
        ('urgent', 'Urgent'),
        ('important', 'Important'),
        ('moderate', 'Moderate'),
    ]
    service = models.ForeignKey(
        'Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recalls',
        help_text="Select the existing service this recall is related to."
    )
    title = models.CharField(max_length=150)
    recall_number = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='moderate')
    affected_make = models.CharField(max_length=100, blank=True, null=True)
    affected_model = models.CharField(max_length=100, blank=True, null=True)
    year_from = models.PositiveIntegerField(blank=True, null=True)
    year_to = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} ({self.recall_number})"


class VehicleRecall(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('rescheduled', 'Rescheduled'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='vehicle_recalls')
    recall = models.ForeignKey(Recall, on_delete=models.CASCADE, related_name='vehicle_recalls')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_service_date = models.DateTimeField(blank=True, null=True)
    next_service_date = models.DateTimeField(blank=True, null=True)
    service_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def check_if_already_serviced(self):
        """
        ✅ Checks if this recall-related service has already been done by the user
        through the Booking table.
        """
        completed_bookings = Booking.objects.filter(
            customer=self.vehicle.customer,
            services__title__icontains=self.recall.title,
            status='completed',
            is_recall_service=True
        ).distinct()

        if completed_bookings.exists():
            last_booking = completed_bookings.last()
            self.status = 'completed'
            self.last_service_date = last_booking.appointment_date
            self.service_count = completed_bookings.count()
            self.save()
            return True
        return False

    def mark_completed(self):
        self.status = 'completed'
        self.last_service_date = timezone.now()
        self.service_count += 1
        self.save()

    def schedule_again(self, date=None):
        self.status = 'rescheduled'
        self.next_service_date = date or timezone.now()
        self.save()

    def __str__(self):
        return f"{self.vehicle} - {self.recall.title} ({self.status})"


class RecallServiceHistory(models.Model):
    vehicle_recall = models.ForeignKey(VehicleRecall, on_delete=models.CASCADE, related_name='service_history')
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='recall_services')
    booking = models.ForeignKey('Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='recall_services')
    service_date = models.DateTimeField(default=timezone.now)
    remarks = models.TextField(blank=True, null=True)
    is_repeat_service = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.vehicle_recall.vehicle} - {self.vehicle_recall.recall.title} ({'Repeat' if self.is_repeat_service else 'Initial'})"


class Review(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='reviews')
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    rating = models.PositiveIntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.username} - {self.rating}⭐"



class ServiceFeedback(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='service_feedbacks')
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='feedback')
    overall_rating = models.PositiveSmallIntegerField(default=0)
    punctuality_rating = models.PositiveSmallIntegerField(default=0)
    service_quality_rating = models.PositiveSmallIntegerField(default=0)
    communication_rating = models.PositiveSmallIntegerField(default=0)
    review = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('customer', 'booking')  
    
    def __str__(self):
        return f"{self.customer.user.username} - {self.booking.id} ({self.overall_rating} stars)"
