"""
SmartQueue AI - AI/Recommendation Engine
Heuristic-based slot recommendation using booking pattern analysis.
"""

from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Count


class SmartSlotRecommender:
    """
    Analyzes historical booking data to recommend optimal time slots.

    Algorithm:
    1. Count bookings per hour across the last 30 days.
    2. Slots with fewer bookings than the median are considered "low traffic".
    3. Low-traffic slots on future dates are marked as recommended.
    """

    ANALYSIS_DAYS = 30

    def _get_hour_traffic(self):
        """Returns dict {hour: booking_count} for the past ANALYSIS_DAYS days."""
        from .models import Appointment
        traffic = defaultdict(int)
        lookback = date.today() - timedelta(days=self.ANALYSIS_DAYS)
        appointments = Appointment.objects.filter(
            timeslot__date__gte=lookback
        ).select_related('timeslot')
        for appt in appointments:
            hour = appt.timeslot.start_time.hour
            traffic[hour] += 1
        return traffic

    def _median_traffic(self, traffic: dict) -> float:
        values = list(traffic.values())
        if not values:
            return 0
        values.sort()
        mid = len(values) // 2
        if len(values) % 2 == 0:
            return (values[mid - 1] + values[mid]) / 2
        return values[mid]

    def get_recommended_slots(self, limit=3):
        """Return a queryset of recommended future TimeSlots."""
        from .models import TimeSlot
        traffic = self._get_hour_traffic()
        median = self._median_traffic(traffic)

        # Gather low-traffic hours
        low_traffic_hours = {h for h, c in traffic.items() if c <= median}

        # Also consider hours with no historical data as low traffic
        all_hours = set(range(7, 20))
        low_traffic_hours |= (all_hours - set(traffic.keys()))

        future_slots = TimeSlot.objects.filter(
            date__gte=date.today(),
            is_available=True,
        )

        recommended = [
            slot for slot in future_slots
            if slot.start_time.hour in low_traffic_hours and slot.available_spots() > 0
        ]
        return recommended[:limit]

    def get_recommended_slot_ids_for_date(self, date_str) -> set:
        """Return set of recommended slot IDs for a given date string."""
        from .models import TimeSlot
        traffic = self._get_hour_traffic()
        median = self._median_traffic(traffic)
        low_traffic_hours = {h for h, c in traffic.items() if c <= median}
        all_hours = set(range(7, 20))
        low_traffic_hours |= (all_hours - set(traffic.keys()))

        slots = TimeSlot.objects.filter(date=date_str)
        return {slot.id for slot in slots if slot.start_time.hour in low_traffic_hours}
