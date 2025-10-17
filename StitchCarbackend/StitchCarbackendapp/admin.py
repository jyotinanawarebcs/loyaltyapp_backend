from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'service', 'appointment_date', 'appointment_time', 'status', 'total_price')
    list_filter = ('status', 'appointment_date', 'service')
    search_fields = ('customer__user__username', 'service__title', 'vehicle_make', 'vehicle_model')
