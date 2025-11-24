from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.conf import settings
import uuid
from django.contrib.auth.models import User


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

    def __str__(self):
        return self.title

class Offer(models.Model):
    # service=models.ForeignKey('Service',on_delete=models.CASCADE,related_name='offers')
    services = models.ManyToManyField('Service', related_name='offers')
    title= models.CharField(max_length=100)
    description=models.TextField(blank=True,null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage discount (e.g., 10.00 = 10%)")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='offers/', blank=True, null=True)
     
    def __str__(self):
        return f"{self.title} - {self.service.title}"

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

    def __str__(self):
        # ✅ Fix: Booking can have *multiple services*, so show all titles
        service_titles = ", ".join([s.title for s in self.services.all()]) if self.id else "No Services"
        return f"{self.customer.user.username} - {service_titles} ({self.appointment_date})"

    def calculate_discounted_price(self):
        """
        Calculates the total price of all selected services,
        applying any offer discount if present.
        """
        total_service_price = sum(service.price for service in self.services.all())

        # ✅ Fix: use correct offer discount field
        if self.offer and hasattr(self.offer, 'discount_percentage'):
            discount = (self.offer.discount_percentage / 100) * total_service_price
            return total_service_price - discount

        return total_service_price

    def save(self, *args, **kwargs):
        """Automatically calculate total price"""
        # First save to get an ID (needed before accessing many-to-many)
        super().save(*args, **kwargs)

        # ✅ Now calculate total after saving (because M2M relations come later)
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