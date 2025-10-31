from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Customer
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    # Create customer profile for new non-staff users if flagged as customer
    if created and getattr(instance, 'is_customer', True):
        Customer.objects.create(user=instance)