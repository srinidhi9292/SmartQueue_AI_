"""
SmartQueue AI - Views
All views for the intelligent appointment and queue management system.
"""

from datetime import date, datetime, timedelta
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.db.models import Count, Q, Avg
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Service, TimeSlot, Appointment, Profile, BlockedDate
from .forms import (
    UserRegisterForm, ProfileForm, ServiceForm,
    TimeSlotForm, BookingForm, BlockedDateForm
)
from .ai_engine import SmartSlotRecommender


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------

class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        try:
            return user.profile.role in ('staff', 'admin')
        except Exception:
            return False


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        try:
            return user.profile.role == 'admin'
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Public Views
# ---------------------------------------------------------------------------

class HomeView(TemplateView):
    template_name = 'booking/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['services'] = Service.objects.filter(is_active=True)
        context['total_bookings'] = Appointment.objects.count()
        context['active_services'] = Service.objects.filter(is_active=True).count()
        return context


class DocumentationView(TemplateView):
    template_name = 'booking/documentation.html'


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'booking/register.html', {'form': UserRegisterForm()})

    def post(self, request):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to SmartQueue AI!')
            return redirect('home')
        return render(request, 'booking/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'booking/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        is_staff = user.is_staff or user.is_superuser
        if not is_staff:
            try:
                is_staff = user.profile.role in ('staff', 'admin')
            except Exception:
                pass
        if is_staff:
            return reverse_lazy('admin_dashboard')
        return reverse_lazy('home')


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, 'You have been logged out.')
        return redirect('home')


class ProfileView(LoginRequiredMixin, View):
    def get(self, request):
        form = ProfileForm(instance=request.user.profile)
        return render(request, 'booking/profile.html', {'form': form})

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            user = request.user
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.email = form.cleaned_data.get('email', '')
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        return render(request, 'booking/profile.html', {'form': form})


class ServiceListView(ListView):
    model = Service
    template_name = 'booking/services.html'
    context_object_name = 'services'
    queryset = Service.objects.filter(is_active=True)


# ---------------------------------------------------------------------------
# Booking Views
# ---------------------------------------------------------------------------

class BookAppointmentView(LoginRequiredMixin, View):
    def get(self, request):
        form = BookingForm()
        recommender = SmartSlotRecommender()
        recommended_slots = recommender.get_recommended_slots()
        return render(request, 'booking/book_appointment.html', {
            'form': form,
            'recommended_slots': recommended_slots,
        })

    def post(self, request):
        form = BookingForm(request.POST)
        service_id = request.POST.get('service')
        date_str = request.POST.get('date')
        timeslot_id = request.POST.get('timeslot')

        if not (service_id and date_str and timeslot_id):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'booking/book_appointment.html', {'form': form})

        if BlockedDate.objects.filter(date=date_str).exists():
            messages.error(request, 'This date is blocked and not available for booking.')
            return render(request, 'booking/book_appointment.html', {'form': form})

        try:
            with transaction.atomic():
                timeslot = TimeSlot.objects.select_for_update().get(pk=timeslot_id)

                # Check capacity
                if timeslot.available_spots() <= 0:
                    messages.error(request, 'This time slot is fully booked. Please choose another.')
                    return render(request, 'booking/book_appointment.html', {'form': form})

                # Prevent duplicate booking by same user
                if Appointment.objects.filter(
                    user=request.user,
                    timeslot=timeslot
                ).exclude(status__in=['cancelled', 'rejected']).exists():
                    messages.error(request, 'You already have a booking for this time slot.')
                    return render(request, 'booking/book_appointment.html', {'form': form})

                service = get_object_or_404(Service, pk=service_id, is_active=True)
                appointment = Appointment.objects.create(
                    user=request.user,
                    service=service,
                    timeslot=timeslot,
                    notes=request.POST.get('notes', ''),
                    status='pending',
                )

                # Update slot availability if capacity reached
                if timeslot.available_spots() <= 0:
                    timeslot.is_available = False
                    timeslot.save()

                # Generate QR code
                appointment.generate_qr_code()
                appointment.save()

        except TimeSlot.DoesNotExist:
            messages.error(request, 'Invalid time slot selected.')
            return render(request, 'booking/book_appointment.html', {'form': form})

        # Send confirmation email
        _send_booking_confirmation_email(appointment)

        return redirect('booking_confirmation', pk=appointment.pk)


class GetAvailableSlotsView(View):
    """AJAX endpoint — returns slot data with availability status."""
    def get(self, request):
        selected_date = request.GET.get('date')
        if not selected_date:
            return JsonResponse({'slots': []})

        if BlockedDate.objects.filter(date=selected_date).exists():
            return JsonResponse({'slots': [], 'blocked': True})

        slots = TimeSlot.objects.filter(date=selected_date)
        recommender = SmartSlotRecommender()
        recommended_ids = recommender.get_recommended_slot_ids_for_date(selected_date)

        slot_data = []
        for slot in slots:
            status = slot.slot_status()
            if status == 'full':
                continue  # Don't show full slots
            slot_data.append({
                'id': slot.id,
                'label': f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}",
                'status': status,
                'available_spots': slot.available_spots(),
                'is_recommended': slot.id in recommended_ids,
            })

        return JsonResponse({'slots': slot_data})


class BookingConfirmationView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = 'booking/booking_confirmation.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['waiting_time'] = self.object.estimated_waiting_time()
        return ctx


class MyAppointmentsView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = 'booking/my_appointments.html'
    context_object_name = 'appointments'

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user).select_related('service', 'timeslot')


class CancelAppointmentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk, user=request.user)
        if appointment.status in ('pending', 'approved'):
            appointment.status = 'cancelled'
            appointment.save()
            # Restore slot availability
            ts = appointment.timeslot
            if ts.available_spots() > 0:
                ts.is_available = True
                ts.save()
            _send_cancellation_email(appointment)
            messages.success(request, 'Appointment cancelled successfully.')
        else:
            messages.error(request, 'This appointment cannot be cancelled.')
        return redirect('my_appointments')


class QRCheckInView(View):
    """Handle QR code scan — marks appointment as Checked In."""
    def get(self, request, token):
        appointment = get_object_or_404(Appointment, qr_token=token)
        if appointment.status == 'approved':
            appointment.status = 'checked_in'
            appointment.save()
            return render(request, 'booking/checkin_success.html', {'appointment': appointment})
        return render(request, 'booking/checkin_error.html', {'appointment': appointment})


# ---------------------------------------------------------------------------
# Admin / Staff Views
# ---------------------------------------------------------------------------

class AdminDashboardView(LoginRequiredMixin, StaffRequiredMixin, TemplateView):
    template_name = 'booking/admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = Appointment.objects.all()
        context['total_bookings'] = appointments.count()
        context['pending_bookings'] = appointments.filter(status='pending').count()
        context['approved_bookings'] = appointments.filter(status='approved').count()
        context['completed_bookings'] = appointments.filter(status='completed').count()
        context['cancelled_bookings'] = appointments.filter(status='cancelled').count()
        context['checked_in_bookings'] = appointments.filter(status='checked_in').count()
        context['recent_appointments'] = appointments.select_related('user', 'service', 'timeslot')[:10]

        # Chart data — last 30 days daily bookings
        today = date.today()
        daily_labels = []
        daily_counts = []
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            count = appointments.filter(created_at__date=d).count()
            daily_labels.append(d.strftime('%b %d'))
            daily_counts.append(count)
        context['daily_labels'] = daily_labels
        context['daily_counts'] = daily_counts

        # Peak hour analysis
        hour_counts = defaultdict(int)
        for appt in appointments:
            hour = appt.timeslot.start_time.hour
            hour_counts[hour] += 1
        peak_labels = [f"{h}:00" for h in range(7, 20)]
        peak_data = [hour_counts.get(h, 0) for h in range(7, 20)]
        context['peak_labels'] = peak_labels
        context['peak_data'] = peak_data

        # Most booked service
        service_stats = (
            appointments.values('service__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        context['service_labels'] = [s['service__name'] for s in service_stats]
        context['service_counts'] = [s['count'] for s in service_stats]

        # Status distribution
        context['status_labels'] = ['Pending', 'Approved', 'Completed', 'Cancelled', 'Checked In']
        context['status_data'] = [
            context['pending_bookings'],
            context['approved_bookings'],
            context['completed_bookings'],
            context['cancelled_bookings'],
            context['checked_in_bookings'],
        ]

        return context


class AdminAppointmentListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Appointment
    template_name = 'booking/admin/appointments.html'
    context_object_name = 'appointments'

    def get_queryset(self):
        qs = Appointment.objects.select_related('user', 'service', 'timeslot')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs


class AdminAppointmentActionView(LoginRequiredMixin, StaffRequiredMixin, View):
    """Approve / Reject / Complete appointments."""
    def post(self, request, pk, action):
        appointment = get_object_or_404(Appointment, pk=pk)
        valid_transitions = {
            'approve': (['pending'], 'approved'),
            'reject': (['pending', 'approved'], 'rejected'),
            'complete': (['approved', 'checked_in'], 'completed'),
        }
        if action not in valid_transitions:
            messages.error(request, 'Invalid action.')
            return redirect('admin_appointments')

        allowed_statuses, new_status = valid_transitions[action]
        if appointment.status not in allowed_statuses:
            messages.error(request, f'Cannot perform "{action}" on a {appointment.status} appointment.')
            return redirect('admin_appointments')

        appointment.status = new_status
        appointment.save()

        if action == 'reject':
            ts = appointment.timeslot
            if ts.available_spots() > 0:
                ts.is_available = True
                ts.save()

        if action == 'approve':
            _send_approval_email(appointment)

        messages.success(request, f'Appointment #{pk} marked as {new_status}.')
        return redirect('admin_appointments')


class AdminAnalyticsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Detailed analytics — admin only."""
    template_name = 'booking/admin/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = Appointment.objects.all()

        # Monthly trend (last 12 months)
        today = date.today()
        monthly_labels = []
        monthly_counts = []
        for i in range(11, -1, -1):
            d = today.replace(day=1) - timedelta(days=i * 28)
            label = d.strftime('%b %Y')
            count = appointments.filter(
                created_at__year=d.year,
                created_at__month=d.month
            ).count()
            monthly_labels.append(label)
            monthly_counts.append(count)

        context['monthly_labels'] = monthly_labels
        context['monthly_counts'] = monthly_counts

        # Top services
        service_stats = (
            appointments.values('service__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        context['service_stats'] = service_stats
        context['total_bookings'] = appointments.count()
        context['total_services'] = Service.objects.filter(is_active=True).count()
        return context


class AdminServiceListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Service
    template_name = 'booking/admin/services.html'
    context_object_name = 'services'


class AdminServiceCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Service
    form_class = ServiceForm
    template_name = 'booking/admin/service_form.html'
    success_url = reverse_lazy('admin_services')

    def form_valid(self, form):
        messages.success(self.request, 'Service created successfully.')
        return super().form_valid(form)


class AdminServiceUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = Service
    form_class = ServiceForm
    template_name = 'booking/admin/service_form.html'
    success_url = reverse_lazy('admin_services')

    def form_valid(self, form):
        messages.success(self.request, 'Service updated successfully.')
        return super().form_valid(form)


class AdminServiceDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Service
    template_name = 'booking/admin/service_confirm_delete.html'
    success_url = reverse_lazy('admin_services')

    def form_valid(self, form):
        messages.success(self.request, 'Service deleted.')
        return super().form_valid(form)


class AdminTimeSlotListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = TimeSlot
    template_name = 'booking/admin/timeslots.html'
    context_object_name = 'timeslots'

    def get_queryset(self):
        return TimeSlot.objects.filter(date__gte=date.today())


class AdminTimeSlotCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = TimeSlot
    form_class = TimeSlotForm
    template_name = 'booking/admin/timeslot_form.html'
    success_url = reverse_lazy('admin_timeslots')

    def form_valid(self, form):
        messages.success(self.request, 'Time slot created successfully.')
        return super().form_valid(form)


class AdminTimeSlotUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = TimeSlot
    form_class = TimeSlotForm
    template_name = 'booking/admin/timeslot_form.html'
    success_url = reverse_lazy('admin_timeslots')

    def form_valid(self, form):
        messages.success(self.request, 'Time slot updated successfully.')
        return super().form_valid(form)


class AdminTimeSlotDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = TimeSlot
    template_name = 'booking/admin/timeslot_confirm_delete.html'
    success_url = reverse_lazy('admin_timeslots')


class AdminBlockedDateListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = BlockedDate
    template_name = 'booking/admin/blocked_dates.html'
    context_object_name = 'blocked_dates'


class AdminBlockedDateCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = BlockedDate
    form_class = BlockedDateForm
    template_name = 'booking/admin/blocked_date_form.html'
    success_url = reverse_lazy('admin_blocked_dates')

    def form_valid(self, form):
        messages.success(self.request, 'Date blocked successfully.')
        return super().form_valid(form)


class AdminBlockedDateDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = BlockedDate
    template_name = 'booking/admin/blocked_date_confirm_delete.html'
    success_url = reverse_lazy('admin_blocked_dates')


# ---------------------------------------------------------------------------
# Email Helpers
# ---------------------------------------------------------------------------

def _send_booking_confirmation_email(appointment):
    try:
        subject = f'[SmartQueue AI] Booking Confirmed – #{appointment.pk}'
        body = (
            f"Dear {appointment.user.first_name or appointment.user.username},\n\n"
            f"Your appointment has been successfully booked!\n\n"
            f"Service: {appointment.service.name}\n"
            f"Date: {appointment.timeslot.date}\n"
            f"Time: {appointment.timeslot.start_time.strftime('%I:%M %p')} – "
            f"{appointment.timeslot.end_time.strftime('%I:%M %p')}\n"
            f"Status: Pending\n"
            f"Estimated Waiting Time: {appointment.estimated_waiting_time()} minutes\n\n"
            f"Your QR check-in token: {appointment.qr_token}\n\n"
            f"You will receive another email once your appointment is approved.\n\n"
            f"— SmartQueue AI Team"
        )
        send_mail(subject, body, 'noreply@smartqueue.ai', [appointment.user.email], fail_silently=True)
    except Exception:
        pass


def _send_approval_email(appointment):
    try:
        subject = f'[SmartQueue AI] Appointment Approved – #{appointment.pk}'
        body = (
            f"Dear {appointment.user.first_name or appointment.user.username},\n\n"
            f"Great news! Your appointment has been approved.\n\n"
            f"Service: {appointment.service.name}\n"
            f"Date: {appointment.timeslot.date}\n"
            f"Time: {appointment.timeslot.start_time.strftime('%I:%M %p')}\n\n"
            f"Please arrive on time. You can check in using your QR code.\n\n"
            f"— SmartQueue AI Team"
        )
        send_mail(subject, body, 'noreply@smartqueue.ai', [appointment.user.email], fail_silently=True)
    except Exception:
        pass


def _send_cancellation_email(appointment):
    try:
        subject = f'[SmartQueue AI] Appointment Cancelled – #{appointment.pk}'
        body = (
            f"Dear {appointment.user.first_name or appointment.user.username},\n\n"
            f"Your appointment (#{appointment.pk}) has been cancelled.\n\n"
            f"If this was a mistake, please book a new appointment.\n\n"
            f"— SmartQueue AI Team"
        )
        send_mail(subject, body, 'noreply@smartqueue.ai', [appointment.user.email], fail_silently=True)
    except Exception:
        pass
