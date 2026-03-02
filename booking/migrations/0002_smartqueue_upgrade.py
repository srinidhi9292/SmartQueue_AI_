"""
SmartQueue AI - Migration: Add new fields for AI upgrade.
"""

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0001_initial'),
    ]

    operations = [
        # Add role to Profile
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.CharField(
                choices=[('user', 'User'), ('staff', 'Staff'), ('admin', 'Admin')],
                default='user',
                max_length=10,
            ),
        ),
        # Add capacity to TimeSlot
        migrations.AddField(
            model_name='timeslot',
            name='capacity',
            field=models.PositiveIntegerField(default=3),
        ),
        # Add completed and checked_in to Appointment status
        migrations.AlterField(
            model_name='appointment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('rejected', 'Rejected'),
                    ('checked_in', 'Checked In'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        # Add QR fields
        migrations.AddField(
            model_name='appointment',
            name='qr_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AddField(
            model_name='appointment',
            name='qr_code_image',
            field=models.ImageField(blank=True, null=True, upload_to='qrcodes/'),
        ),
    ]
