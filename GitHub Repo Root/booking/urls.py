"""SmartQueue AI - URL Configuration"""

from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.HomeView.as_view(), name='home'),
    path('docs/', views.DocumentationView.as_view(), name='documentation'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('services/', views.ServiceListView.as_view(), name='services'),

    # Booking
    path('book/', views.BookAppointmentView.as_view(), name='book_appointment'),
    path('api/available-slots/', views.GetAvailableSlotsView.as_view(), name='get_available_slots'),
    path('booking/confirmation/<int:pk>/', views.BookingConfirmationView.as_view(), name='booking_confirmation'),
    path('my-appointments/', views.MyAppointmentsView.as_view(), name='my_appointments'),
    path('appointment/<int:pk>/cancel/', views.CancelAppointmentView.as_view(), name='cancel_appointment'),

    # QR Check-In
    path('checkin/<uuid:token>/', views.QRCheckInView.as_view(), name='qr_checkin'),

    # Admin / Staff Panel
    path('admin-panel/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-panel/analytics/', views.AdminAnalyticsView.as_view(), name='admin_analytics'),
    path('admin-panel/appointments/', views.AdminAppointmentListView.as_view(), name='admin_appointments'),
    path('admin-panel/appointment/<int:pk>/<str:action>/', views.AdminAppointmentActionView.as_view(), name='admin_appointment_action'),
    path('admin-panel/services/', views.AdminServiceListView.as_view(), name='admin_services'),
    path('admin-panel/services/add/', views.AdminServiceCreateView.as_view(), name='admin_service_add'),
    path('admin-panel/services/<int:pk>/edit/', views.AdminServiceUpdateView.as_view(), name='admin_service_edit'),
    path('admin-panel/services/<int:pk>/delete/', views.AdminServiceDeleteView.as_view(), name='admin_service_delete'),
    path('admin-panel/timeslots/', views.AdminTimeSlotListView.as_view(), name='admin_timeslots'),
    path('admin-panel/timeslots/add/', views.AdminTimeSlotCreateView.as_view(), name='admin_timeslot_add'),
    path('admin-panel/timeslots/<int:pk>/edit/', views.AdminTimeSlotUpdateView.as_view(), name='admin_timeslot_edit'),
    path('admin-panel/timeslots/<int:pk>/delete/', views.AdminTimeSlotDeleteView.as_view(), name='admin_timeslot_delete'),
    path('admin-panel/blocked-dates/', views.AdminBlockedDateListView.as_view(), name='admin_blocked_dates'),
    path('admin-panel/blocked-dates/add/', views.AdminBlockedDateCreateView.as_view(), name='admin_blocked_date_add'),
    path('admin-panel/blocked-dates/<int:pk>/delete/', views.AdminBlockedDateDeleteView.as_view(), name='admin_blocked_date_delete'),
]
