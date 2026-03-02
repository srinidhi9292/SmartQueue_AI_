# 🤖 SmartQueue AI
### Intelligent Appointment & Waiting Time Optimization Platform

> **Built for Technical Expo Presentation — First Prize Level**

---

## 🚀 Overview

SmartQueue AI is a production-ready, AI-enhanced appointment booking and queue management platform built with Django. It transforms traditional manual scheduling systems into an intelligent, data-driven platform that reduces waiting times and optimizes resource allocation.

**The Problem:** Manual appointment systems cause overcrowding and unpredictable waiting times. Clients waste hours in queues with zero visibility.

**The Solution:** SmartQueue AI analyzes booking patterns to recommend optimal slots, predicts waiting times, and streamlines check-in with QR codes.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **Smart Slot Recommendation** | AI analyzes historical data to suggest low-traffic slots with "Recommended" badge |
| ⏱️ **Waiting Time Prediction** | Real-time estimate: `bookings_before × avg_service_duration` |
| 🟢 **Real-Time Slot Availability** | AJAX-powered status: Available / Almost Full / Fully Booked |
| 📊 **Analytics Dashboard** | Daily/monthly trends, peak hours, service popularity — powered by Chart.js |
| 📱 **QR Code Check-In** | Unique QR per booking; scan to instantly mark Checked In |
| 📧 **Email Notifications** | Confirmation, approval, and cancellation emails via SMTP |
| 🔐 **Role-Based Access** | User / Staff / Admin with appropriate permission gates |
| 🔄 **Status Workflow** | Pending → Approved → Checked In → Completed (or Rejected/Cancelled) |
| 🛡️ **Security** | CSRF protection, atomic transactions, environment-variable secrets |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Django 4.2
- **Database:** SQLite (dev) / PostgreSQL (prod-ready)
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, Chart.js 4.x
- **AI Engine:** Custom heuristic recommender (`ai_engine.py`)
- **QR Codes:** `qrcode[pil]` library
- **Email:** Django SMTP backend (Gmail / SendGrid compatible)

---

## ⚡ Quick Start

```bash
# 1. Clone / unzip the project
cd smartqueue_ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your SECRET_KEY

# 5. Run migrations
python manage.py migrate

# 6. Create superuser (Admin)
python manage.py createsuperuser

# 7. Start server
python manage.py runserver
```

Visit: http://127.0.0.1:8000

---

## 👥 User Roles

| Role | Access |
|------|--------|
| **User** | Book, view, cancel own appointments |
| **Staff** | + Approve/Reject/Complete appointments, manage services & slots |
| **Admin** | + Full analytics dashboard (admin-only) |

To assign a role: Django Admin → Profile → set Role field.

---

## 🤖 AI Engine Explained

Located in `booking/ai_engine.py`, the `SmartSlotRecommender`:

1. Queries booking data for the last 30 days
2. Builds an hour-by-hour traffic map `{hour: count}`
3. Calculates the median traffic value
4. Flags hours at or below median as "low traffic"
5. Recommends future slots in low-traffic hours with available capacity

This is a **lightweight heuristic** approach — no external ML libraries required. The algorithm can be upgraded to a trained regression model for production.

---

## 📧 Email Configuration

Edit `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

For development, emails are printed to console by default.

---

## 📂 Project Structure

```
smartqueue_ai/
├── appointment_project/
│   ├── settings.py          # Env-aware settings
│   └── urls.py
├── booking/
│   ├── models.py            # 6 core models
│   ├── views.py             # 25+ view classes
│   ├── urls.py              # 25+ URL routes
│   ├── forms.py             # 6 form classes
│   ├── admin.py             # Django admin
│   ├── ai_engine.py         # SmartSlotRecommender
│   ├── middleware.py
│   └── templates/           # Bootstrap 5 templates
├── media/qrcodes/           # QR code storage
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔒 Security & Production

- `SECRET_KEY` from environment variable (never hardcoded)
- `DEBUG=False` in production
- CSRF protection on all POST forms
- Atomic database transactions prevent double-booking
- `select_for_update()` on time slot selection

---

## 📜 License

Built for SmartQueue AI — Technical Expo 2026. All rights reserved.
