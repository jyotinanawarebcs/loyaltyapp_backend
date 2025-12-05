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
    """
    Handles loyalty points:
    - Deduct points when a reward is used (already discounted in perform_create)
    - Add cashback points when service completed with cashback reward
    - Trigger referral rewards when booking is marked as completed
    - Do NOT modify total_price here (handled in perform_create)
    """
    with transaction.atomic():
        loyalty, _ = LoyaltyPoint.objects.select_for_update().get_or_create(
            customer=instance.customer
        )

        # ✅ Deduct reward points on new booking
        if created and instance.reward:
    # Skip deduction if already redeemed manually
            from .models import RedeemedReward
            already_redeemed = RedeemedReward.objects.filter(
                customer=instance.customer, reward=instance.reward
            ).exists()

            if not already_redeemed:
                required = instance.reward.required_points or 0
                if loyalty.points >= required:
                    loyalty.deduct_points(required)
                else:
                    raise ValueError("Insufficient points for reward redemption.")

        # ✅ Cashback on completion
        if (
            instance.status == "completed"
            and instance.reward
            and instance.reward.type == "cashback"
        ):
            cashback_value = float(instance.reward.discount_value or 0)
            cashback_points = int(cashback_value * 10)
            if cashback_points > 0:
                loyalty.add_points(cashback_points)
    
    # ✅ Trigger referral rewards on completion (outside transaction to avoid rollback)
    if instance.status == "completed":
        try:
            from .views import give_referral_reward
            print(f"[Signal] Triggering referral reward for booking {instance.id}, user {instance.customer.user.username}")
            give_referral_reward(instance.customer.user)
        except Exception as e:
            print(f"❌ [Signal] Referral reward trigger FAILED: {e}")
            import traceback
            traceback.print_exc()

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


