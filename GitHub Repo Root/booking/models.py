"""
SmartQueue AI - Models
Defines all database models for the intelligent appointment and queue system.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------
ROLE_CHOICES = [
    ('user', 'User'),
    ('staff', 'Staff'),
    ('admin', 'Admin'),
]


class Profile(models.Model):
    """Extended user profile with role and contact details."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.role})"

    def is_admin_role(self):
        return self.role == 'admin' or self.user.is_superuser

    def is_staff_role(self):
        return self.role in ('staff', 'admin') or self.user.is_staff


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()


class Service(models.Model):
    """A bookable service offered by the organization."""
    name = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class BlockedDate(models.Model):
    """Dates that are unavailable for booking."""
    date = models.DateField(unique=True)
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.date} - {self.reason}"


SLOT_CAPACITY = 3  # Max appointments per time slot


class TimeSlot(models.Model):
    """A bookable time window on a specific date."""
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(default=SLOT_CAPACITY)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['date', 'start_time', 'end_time']

    def __str__(self):
        return f"{self.date} | {self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"

    def booking_count(self):
        return self.appointments.exclude(status__in=['cancelled', 'rejected']).count()

    def available_spots(self):
        return max(0, self.capacity - self.booking_count())

    def slot_status(self):
        count = self.booking_count()
        if count == 0:
            return 'available'
        elif count < self.capacity:
            return 'almost_full'
        return 'full'


STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('rejected', 'Rejected'),
    ('checked_in', 'Checked In'),
]


class Appointment(models.Model):
    """A booking made by a user for a service at a specific time slot."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='appointments')
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE, related_name='appointments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)

    # QR Code check-in
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_code_image = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.service.name} on {self.timeslot}"

    def estimated_waiting_time(self):
        """
        Waiting time = number of approved/pending bookings before this slot × avg service duration.
        """
        bookings_before = Appointment.objects.filter(
            timeslot__date=self.timeslot.date,
            timeslot__start_time__lt=self.timeslot.start_time,
            status__in=['pending', 'approved', 'checked_in'],
        ).count()
        avg_duration = self.service.duration or 30
        return bookings_before * avg_duration

    def generate_qr_code(self):
        """Generate and save a QR code PNG for this appointment."""
        try:
            import qrcode
            from io import BytesIO
            from django.core.files import File
            qr_data = f"SMARTQUEUE-CHECKIN:{self.qr_token}"
            qr_img = qrcode.make(qr_data)
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            filename = f"qr_{self.qr_token}.png"
            self.qr_code_image.save(filename, File(buffer), save=False)
        except ImportError:
            pass
