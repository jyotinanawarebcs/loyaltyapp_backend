from django.contrib import admin
from .models import (
    Service, Booking, Coupon, Reward, LoyaltyPoint,
    RedeemedReward, EarningRule
)
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils import timezone

User = get_user_model()
admin.site.register(User)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'is_popular', 'interval_days')
    list_filter = ('is_popular',)
    search_fields = ('title', 'description')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'get_services', 'appointment_date',
                    'appointment_time', 'status', 'total_price')
    list_filter = ('status', 'appointment_date', 'services')
    search_fields = ('customer__user__username', 'services__title',
                     'vehicle_make', 'vehicle_model')

    def get_services(self, obj):
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
