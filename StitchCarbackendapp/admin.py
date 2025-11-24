from django.contrib import admin
from .models import Service,Booking
from django.contrib.auth import get_user_model

User = get_user_model()
admin.site.register(User)


# Register your models here.
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'is_popular')
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


# @admin.register(Booking)
# class BookingAdmin(admin.ModelAdmin):
#     list_display = ('id', 'customer', 'service', 'appointment_date', 'appointment_time', 'status', 'total_price')
#     list_filter = ('status', 'appointment_date', 'service')
#     search_fields = ('customer__user__username', 'service__title', 'vehicle_make', 'vehicle_model')
