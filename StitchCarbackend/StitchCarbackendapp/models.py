from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
# Create your models here.

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_customer = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",  # <--- change related_name
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups"
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_set_permissions",  # <--- change related_name
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
    
class Service(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='services/')
    is_popular = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Offer(models.Model):
    service=models.ForeignKey('Service',on_delete=models.CASCADE,related_name='offers')
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
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    booking_date = models.DateTimeField(default=timezone.now)
    appointment_date = models.DateField()  
    appointment_time = models.TimeField()
    vehicle_make = models.CharField(max_length=100)   
    vehicle_model = models.CharField(max_length=100)  
    vehicle_year = models.CharField(max_length=4)     
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer.user.username} - {self.service.title} ({self.appointment_date})"

    def calculate_discounted_price(self):
        """If offer is valid, apply discount."""
        if self.offer and self.offer.is_valid():
            discount_amount = (self.service.price * self.offer.discount_percentage) / 100
            return self.service.price - discount_amount
        return self.service.price

    def save(self, *args, **kwargs):
        """Automatically calculate total price"""
        self.total_price = self.calculate_discounted_price()
        super().save(*args, **kwargs)