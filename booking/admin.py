"""SmartQueue AI - Django Admin Configuration"""

from django.contrib import admin
from .models import Profile, Service, TimeSlot, Appointment, BlockedDate


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration', 'price', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['date', 'start_time', 'end_time', 'is_available', 'capacity']
    list_filter = ['date', 'is_available']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'service', 'timeslot', 'status', 'created_at']
    list_filter = ['status', 'service']
    search_fields = ['user__username', 'service__name']
    readonly_fields = ['qr_token', 'qr_code_image', 'created_at', 'updated_at']


@admin.register(BlockedDate)
class BlockedDateAdmin(admin.ModelAdmin):
    list_display = ['date', 'reason']
