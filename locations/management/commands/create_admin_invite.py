from datetime import timedelta
from hashlib import sha256
import secrets

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from locations.models import AdminRegistrationInvite


class Command(BaseCommand):
    help = 'Create a one-time invitation code for administrator registration.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--expires-hours',
            type=int,
            default=24,
            help='How long the invitation remains valid (default: 24 hours).',
        )

    def handle(self, *args, **options):
        expires_hours = options['expires_hours']
        if expires_hours < 1:
            raise CommandError('--expires-hours must be at least 1.')

        code = secrets.token_urlsafe(32)
        AdminRegistrationInvite.objects.create(
            token_hash=sha256(code.encode('utf-8')).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=expires_hours),
        )
        self.stdout.write(self.style.SUCCESS('Admin invitation code (shown once):'))
        self.stdout.write(code)
        self.stdout.write(f'Expires in {expires_hours} hour(s).')
