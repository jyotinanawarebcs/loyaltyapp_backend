# yourapp/management/commands/generate_notifications.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.conf import settings
from StitchCarbackendapp.models import Booking, Notification

# Avoid creating duplicate notifications within a certain time window (default: 24 hours)
DUPLICATE_WINDOW_HOURS = getattr(settings, 'NOTIFICATION_DUPLICATE_WINDOW_HOURS', 24)


def recently_created(customer, title,message, window_hours=DUPLICATE_WINDOW_HOURS):
    """Check if a similar notification was recently created for the same customer and title."""
    cutoff = timezone.now() - timedelta(hours=window_hours)
    return Notification.objects.filter(
        customer=customer,
        title=title,
        message=message,
        created_at__gte=cutoff
    ).exists()


class Command(BaseCommand):
    help = "Generate upcoming (tomorrow), due (today), and overdue service notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            '--only',
            type=str,
            choices=['upcoming', 'due', 'overdue', 'all'],
            default='all',
            help='Run only specific notifications: upcoming, due, overdue, or all'
        )

    def handle(self, *args, **options):
        only = options.get('only', 'all')

        # ✅ Use local timezone-aware date
        now = timezone.localtime(timezone.now())
        today = now.date()
        tomorrow = today + timedelta(days=1)

        created = 0
        skipped = 0

        self.stdout.write(f"📅 Starting notification generation at {now.isoformat()} (only={only})")

        # Fetch all active bookings
        bookings = Booking.objects.prefetch_related('services', 'customer__user').all()

        for booking in bookings:
            # Skip cancelled or completed bookings
            if booking.status in ['cancelled', 'completed']:
                continue

            for service in booking.services.all():
                appointment_date = booking.appointment_date
                interval = getattr(service, "interval_days", 0)

                # 🧠 Debug info (optional, can remove in production)
                # print(f"Booking {booking.id}: {appointment_date=} {today=} {tomorrow=} {interval=}")

                # ---------------- UPCOMING (Tomorrow) ----------------
                if only in ('upcoming', 'all') and appointment_date == tomorrow:
                    title = "Upcoming Service Reminder"
                    message = (
                        f"You have a service appointment for {service.title} tomorrow "
                        f"at {booking.appointment_time}."
                    )
                    if recently_created(booking.customer, title,message):
                        skipped += 1
                    else:
                        with transaction.atomic():
                            Notification.objects.create(
                                customer=booking.customer,
                                title=title,
                                message=message
                            )
                        created += 1

                # ---------------- DUE TODAY ----------------
                elif only in ('due', 'all') and appointment_date == today:
                    title = "Service Due Today"
                    message = f"Your {service.title} service is due today at {booking.appointment_time}."
                    if recently_created(booking.customer, title,message):
                        skipped += 1
                    else:
                        with transaction.atomic():
                            Notification.objects.create(
                                customer=booking.customer,
                                title=title,
                                message=message
                            )
                        created += 1

                # ---------------- OVERDUE ----------------
                elif only in ('overdue', 'all') and appointment_date < today:
                    title = "Service Overdue"
                    message = f"Your {service.title} service was due on {appointment_date}. Please book soon."
                    if recently_created(booking.customer, title,message):
                        skipped += 1
                    else:
                        with transaction.atomic():
                            Notification.objects.create(
                                customer=booking.customer,
                                title=title,
                                message=message
                            )
                        created += 1

                # ---------------- OPTIONAL: RECURRING SERVICE DUE ----------------
                elif interval and (appointment_date + timedelta(days=interval)) == today:
                    title = "Recurring Service Due"
                    message = f"Your recurring {service.title} service is due today."
                    if recently_created(booking.customer, title,message):
                        skipped += 1
                    else:
                        with transaction.atomic():
                            Notification.objects.create(
                                customer=booking.customer,
                                title=title,
                                message=message
                            )
                        created += 1
        retention_days = getattr(settings, 'NOTIFICATION_RETENTION_DAYS', 30)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        old_count = Notification.objects.filter(created_at__lt=cutoff_date).count()

        if old_count > 0:
            Notification.objects.filter(created_at__lt=cutoff_date).delete()
            self.stdout.write(f"🧹 Cleaned up {old_count} old notifications (older than {retention_days} days).")
        else:
            self.stdout.write(f"🧹 No old notifications to clean up.")        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Finished. Created: {created}, Skipped (duplicates): {skipped}")
        )
