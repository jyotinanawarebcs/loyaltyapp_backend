# loyaltyapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Booking, LoyaltyPoint, Reward, Customer,EarningRule,Review
from django.contrib.auth import get_user_model

def calculate_points(amount):
    from .models import EarningRule
    rule = EarningRule.objects.first()  # get the first or active rule

    # fallback to defaults if admin hasn’t set anything yet
    base = rule.amount_base if rule and rule.amount_base > 0 else 199
    per_points = rule.points if rule and rule.points > 0 else 10

    return int((float(amount or 0) / base) * per_points)



User = get_user_model()

@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created and getattr(instance, 'is_customer', True):
        Customer.objects.get_or_create(user=instance)


@receiver(post_save, sender=Booking)
def handle_loyalty_on_booking(sender, instance, created, **kwargs):
    with transaction.atomic():
        loyalty, _ = LoyaltyPoint.objects.select_for_update().get_or_create(customer=instance.customer)

        # ✅ Deduct points when reward used (creation)
        if created and instance.reward:
            required_points = instance.reward.required_points or 0
            if loyalty.points >= required_points:
                loyalty.deduct_points(required_points)
            else:
                raise ValueError("Insufficient points for reward redemption.")

        # ✅ Award points for normal bookings
       

        # elif created and not instance.reward:
        #     amount = float(instance.total_price or 0)

        #     rule = instance.earning_rule or EarningRule.objects.filter(is_active=True).first()
        #     if rule and amount >= rule.amount_base:
        #         points_to_award = int((amount / rule.amount_base) * rule.points)
        #         if points_to_award > 0:
        #             loyalty.add_points(points_to_award)
        #             print(f"✅ Added {points_to_award} points for {instance.customer.user.username}")        

        # ✅ Cashback after service completion
        elif instance.status == 'completed' and instance.reward and instance.reward.type == 'cashback':
            cashback_value = float(instance.reward.discount_value or 0)
            cashback_points = int(cashback_value * 10)
            if cashback_points > 0:
                loyalty.add_points(cashback_points)

@receiver(post_save, sender=Review)
def award_points_for_review(sender, instance, created, **kwargs):
    """
    📝 3. Award 50 points for every new review submitted by a customer.
    """
    if not created:
        return

    try:
        loyalty, _ = LoyaltyPoint.objects.select_for_update().get_or_create(
            customer=instance.customer
        )
        loyalty.add_points(50)
    except Exception as e:
        print(f"[Review Points Error] {e}")


# # loyaltyapp/signals.py
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.db import transaction
# from .models import Booking, LoyaltyPoint, Reward, Customer
# from django.contrib.auth import get_user_model

# User = get_user_model()

# @receiver(post_save, sender=User)
# def create_customer_profile(sender, instance, created, **kwargs):
#     if created and getattr(instance, 'is_customer', True):
#         Customer.objects.get_or_create(user=instance)


# @receiver(post_save, sender=Booking)
# def handle_loyalty_on_booking(sender, instance, created, **kwargs):
#     """
#     Loyalty rules:
#     - Deduct points if reward used (on booking creation)
#     - Award points for normal bookings (10 points per ₹199 spent)
#     """
#     if not created:
#         return

#     with transaction.atomic():
#         loyalty, _ = LoyaltyPoint.objects.select_for_update().get_or_create(
#             customer=instance.customer
#         )

      
#         if instance.reward:
#             required_points = instance.reward.required_points or 0
#             if loyalty.points >= required_points:
#                 loyalty.deduct_points(required_points)
#                 instance.reward.is_active = False
#                 instance.reward.save(update_fields=["is_active"])
#             else:
#                 raise ValueError(f"Insufficient points for reward redemption.")

     
#         else:
#             try:
#                 amount = float(instance.total_price or 0)
#             except Exception:
#                 amount = 0

#             # Award 10 points per ₹199 spent
#             points_to_award = int((amount / 199) * 10)
#             if points_to_award > 0:
#                 loyalty.add_points(points_to_award)


