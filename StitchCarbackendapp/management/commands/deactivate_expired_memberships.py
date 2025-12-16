from django.core.management.base import BaseCommand
from django.utils import timezone
from memberships.models import CustomerMembership  # <-- change to your actual app name

class Command(BaseCommand):
    help = "Deactivate all expired memberships"

    def handle(self, *args, **options):
        today = timezone.now().date()
        expired_memberships = CustomerMembership.objects.filter(active=True, expiry_date__lt=today)

        count = expired_memberships.count()
        for membership in expired_memberships:
            membership.deactivate()

        self.stdout.write(self.style.SUCCESS(f"✅ {count} expired memberships deactivated."))
