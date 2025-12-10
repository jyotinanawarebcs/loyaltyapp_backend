from django.contrib import admin
from .models import (
    Service, Booking, Coupon, Reward, LoyaltyPoint,
    RedeemedReward, EarningRule,Offer,Vehicle,Customer,ServiceFeedback
)
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from .models import Recall, VehicleRecall, RecallServiceHistory

User = get_user_model()
admin.site.register(User)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'is_popular', 'interval_days')
    list_filter = ('is_popular',)
    search_fields = ('title', 'description')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer',
        'get_services',
        'appointment_date',
        'appointment_time',
        'status',
        'total_price',
    )
    list_filter = ('status', 'appointment_date', 'services')  # ✅ plural field
    search_fields = (
        'customer__user__username',
        'services__title',
        'vehicle_make',
        'vehicle_model',
    )

    def get_services(self, obj):
        """Show all related services in a comma-separated list."""
        return ", ".join([s.title for s in obj.services.all()])
    get_services.short_description = "Services"


# ✅ Reward Admin (Improved for cashback, discount %, flat, free)
@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'type', 'discount_value', 'required_points',
        'service', 'is_active', 'created_at'
    )
    list_filter = ('type', 'is_active', 'service')
    search_fields = ('title', 'description')
    ordering = ('required_points',)
    list_editable = ('is_active',)

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'type', 'discount_value', 'service')
        }),
        ('Points & Availability', {
            'fields': ('required_points', 'is_active')
        }),
    )

    def colored_type(self, obj):
        """Display reward type in colors for clarity"""
        colors = {
            'free': 'green',
            'discount': 'blue',
            'flat': 'orange',
            'cashback': 'purple'
        }
        color = colors.get(obj.type, 'black')
        return format_html('<b style="color:{};">{}</b>', color, obj.type)
    colored_type.short_description = "Reward Type"


@admin.register(LoyaltyPoint)
class LoyaltyPointAdmin(admin.ModelAdmin):
    list_display = ('customer', 'points', 'updated_at')
    search_fields = ('customer__user__username', 'customer__user__email')


@admin.register(RedeemedReward)
class RedeemedRewardAdmin(admin.ModelAdmin):
    list_display = ('customer', 'reward', 'redeemed_at')
    search_fields = ('customer__user__username', 'reward__title')


@admin.register(EarningRule)
class EarningRuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'is_active', 'display_order')
    ordering = ('display_order',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'discount_type', 'discount_value',
                    'expiry_date_colored', 'applicable_service', 'is_active')
    list_filter = ('discount_type', 'is_active', 'expiry_date', 'applicable_service')
    search_fields = ('code', 'title', 'description')
    ordering = ('-expiry_date',)
    list_editable = ('is_active',)
    readonly_fields = ('created_status',)
    date_hierarchy = 'expiry_date'

    def created_status(self, obj):
        """Helper: show created/expired/active label."""
        if not obj.is_valid():
            return "Expired"
        return "Active"
    created_status.short_description = "Status"

    def expiry_date_colored(self, obj):
        """Display expiry date color coded"""
        today = timezone.now().date()
        if obj.expiry_date < today:
            color = "red"
        elif (obj.expiry_date - today).days <= 7:
            color = "orange"
        else:
            color = "green"
        return format_html('<span style="color:{};">{}</span>', color, obj.expiry_date)
    expiry_date_colored.short_description = "Expiry Date"

    fieldsets = (
        (None, {
            'fields': ('code', 'title', 'description', 'discount_type', 'discount_value')
        }),
        ('Validity & Rules', {
            'fields': ('expiry_date', 'applicable_service', 'is_active', 'created_status')
        }),
    )
@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'discount_percentage', 'valid_from', 'valid_to', 'is_active')
    list_filter = ('is_active', 'valid_from', 'valid_to')
    search_fields = ('title', 'description')
    filter_horizontal = ('services',)



@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'country', 'joined_at')
    search_fields = ('user__username', 'user__email', 'city', 'country')
    list_filter = ('city', 'country', 'joined_at')
    ordering = ('-joined_at',)


# ============================
# VEHICLE ADMIN
# ============================

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number', 'make', 'model', 'year', 'customer', 'created_at')
    search_fields = ('vehicle_number', 'vin', 'make', 'model', 'customer__user__username')
    list_filter = ('make', 'model', 'year', 'created_at')
    ordering = ('-created_at',)
    autocomplete_fields = ('customer',)


# ============================
# ============================
# INLINE CLASSES
# ============================

class RecallServiceHistoryInline(admin.TabularInline):
    """Inline view for Recall Service History under VehicleRecall."""
    model = RecallServiceHistory
    extra = 0
    readonly_fields = ('service_date',)
    fields = ('customer', 'booking', 'service_date', 'remarks', 'is_repeat_service')


# ============================
# RECALL ADMIN
# ============================

@admin.register(Recall)
class RecallAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'recall_number',
        'urgency',
        'service',
        'affected_make',
        'affected_model',
        'year_from',
        'year_to',
        'created_at',
    )
    list_filter = ('urgency', 'affected_make', 'affected_model', 'created_at')
    search_fields = ('title', 'recall_number', 'description', 'affected_make', 'affected_model')
    ordering = ('-created_at',)
    autocomplete_fields = ('service',)
    list_per_page = 25


# ============================
# VEHICLE RECALL ADMIN
# ============================

@admin.register(VehicleRecall)
class VehicleRecallAdmin(admin.ModelAdmin):
    list_display = (
        'vehicle',
        'recall',
        'status',
        'last_service_date',
        'next_service_date',
        'service_count',
        'created_at',
    )
    list_filter = ('status', 'recall__urgency', 'created_at')
    search_fields = (
        'vehicle__registration_number',
        'vehicle__customer__username',
        'recall__title',
        'recall__recall_number',
    )
    inlines = [RecallServiceHistoryInline]
    autocomplete_fields = ('vehicle', 'recall')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    actions = ['mark_as_completed'] 

    # ============================
    # ✅ CUSTOM ACTIONS
    # ============================

    @admin.action(description="Mark selected recalls as Completed")
    def mark_as_completed(self, request, queryset):
        count = 0
        for vr in queryset:
            if vr.status != 'completed':
                vr.mark_completed()
                count += 1
        self.message_user(
            request,
            f"{count} recall(s) marked as completed.",
            messages.SUCCESS
        )

    @admin.action(description="Reschedule selected recalls for next week")
    def reschedule_next_week(self, request, queryset):
        next_week = timezone.now() + timezone.timedelta(days=7)
        count = queryset.update(status='rescheduled', next_service_date=next_week)
        self.message_user(
            request,
            f"{count} recall(s) rescheduled to next week.",
            messages.INFO
        )

    actions = ['mark_as_completed', 'reschedule_next_week']


# ============================
# RECALL SERVICE HISTORY ADMIN
# ============================

@admin.register(RecallServiceHistory)
class RecallServiceHistoryAdmin(admin.ModelAdmin):
    list_display = ('vehicle_recall', 'customer', 'booking', 'service_date', 'is_repeat_service')
    list_filter = ('is_repeat_service', 'service_date')
    search_fields = (
        'vehicle_recall__vehicle__registration_number',
        'vehicle_recall__recall__title',
        'customer__username',
    )
    autocomplete_fields = ('vehicle_recall', 'customer', 'booking')
    ordering = ('-service_date',)

from django.contrib import admin
from .models import FeaturedPromotion, PromotionBanner


@admin.register(FeaturedPromotion)
class FeaturedPromotionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'offer',
        'title',
        'highlight_text',
        'promo_type',
        'display_order',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'promo_type', 'created_at')
    search_fields = ('title', 'offer__title', 'highlight_text')
    ordering = ('display_order',)
    list_editable = ('display_order', 'is_active')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Offer Details', {
            'fields': ('offer', 'promo_type', 'is_active', 'display_order')
        }),
        ('Content', {
            'fields': ('title', 'description', 'highlight_text', 'button_text', 'image')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(PromotionBanner)
class PromotionBannerAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'offer',
        'valid_from',
        'valid_to',
        'is_active',
    )
    list_filter = ('is_active', 'valid_from', 'valid_to')
    search_fields = ('title', 'offer__title', 'description')
    readonly_fields = ('valid_from',)
    ordering = ('-valid_from',)
    list_editable = ('is_active',)

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'image', 'button_text')
        }),
        ('Offer Link', {
            'fields': ('offer',)
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'is_active')
        }),
    )
from django.contrib import admin
from .models import ReferralProfile, ReferralActivity


@admin.register(ReferralProfile)
class ReferralProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "referral_code",
        "invited_count",
        "rewards_earned",
    )
    search_fields = ("user__username", "user__email", "referral_code")
    list_filter = ("rewards_earned",)
    ordering = ("-rewards_earned",)
    readonly_fields = ("referral_code",)

    fieldsets = (
        (None, {"fields": ("user", "referral_code")}),
        ("Referral Stats", {"fields": ("invited_count", "rewards_earned")}),
    )


@admin.register(ReferralActivity)
class ReferralActivityAdmin(admin.ModelAdmin):
    list_display = (
        "referrer",
        "referred_phone",
        "status",
        "reward_given",
        "created_at",
    )
    search_fields = ("referrer__username", "referred_phone")
    list_filter = ("status", "reward_given", "created_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("referrer", "referred_phone")}),
        ("Referral Progress", {"fields": ("status", "reward_given")}),
    )

    actions = ["mark_as_registered", "mark_as_completed"]

    @admin.action(description="Mark selected as Registered")
    def mark_as_registered(self, request, queryset):
        updated = queryset.update(status="registered")
        self.message_user(request, f"{updated} referral(s) marked as registered.")

    @admin.action(description="Mark selected as Completed and Reward Given")
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status="completed", reward_given=True)
        self.message_user(request, f"{updated} referral(s) marked as completed and rewarded.")

@admin.register(ServiceFeedback)
class ServiceFeedbackAdmin(admin.ModelAdmin):
    list_display = ('customer', 'get_services', 'overall_rating', 'review', 'submitted_at')

    def get_services(self, obj):
        return ", ".join([s.title for s in obj.booking.services.all()])
    get_services.short_description = 'Services'
    
