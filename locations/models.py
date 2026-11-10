from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator


class EvacuationLocation(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        FULL = 'full', 'Full'
        CLOSED = 'closed', 'Closed'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='evacuation_locations',
    )
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=0)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'evacuation location'
        verbose_name_plural = 'evacuation locations'

    def clean(self):
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError('Enter both latitude and longitude to place this center on the map.')

    def __str__(self):
        return self.name


class Barangay(models.Model):
    class Condition(models.TextChoices):
        NORMAL = 'normal', 'Normal'
        WATCH = 'watch', 'Watch'
        CRITICAL = 'critical', 'Critical'

    name = models.CharField(max_length=100, unique=True)
    condition = models.CharField(
        max_length=10,
        choices=Condition.choices,
        default=Condition.NORMAL,
    )
    affected_people = models.PositiveIntegerField(default=0)
    rescued_people = models.PositiveIntegerField(default=0)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rescued_people__lte=models.F('affected_people')),
                name='rescued_not_over_affected',
            ),
        ]

    def clean(self):
        if self.rescued_people > self.affected_people:
            raise ValidationError({'rescued_people': 'Rescued people cannot exceed affected people.'})

    @property
    def rescue_percentage(self):
        if not self.affected_people:
            return 0
        return round(self.rescued_people / self.affected_people * 100)

    def __str__(self):
        return self.name


class Incident(models.Model):
    class Kind(models.TextChoices):
        EARTHQUAKE = 'earthquake', 'Earthquake'
        FLOOD = 'flood', 'Flood'
        FIRE = 'fire', 'Fire'
        MEDICAL = 'medical', 'Medical emergency'
        OTHER = 'other', 'Other'

    class Severity(models.TextChoices):
        INFO = 'info', 'Information'
        WARNING = 'warning', 'Warning'
        CRITICAL = 'critical', 'Critical'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        RESPONDING = 'responding', 'Responding'
        RESOLVED = 'resolved', 'Resolved'

    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.WARNING)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidents',
    )
    description = models.TextField()
    reported_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-reported_at']

    def __str__(self):
        return self.title


class UnitDeployment(models.Model):
    class Status(models.TextChoices):
        DEPLOYED = 'deployed', 'Deployed'
        STANDBY = 'standby', 'On standby'
        RETURNED = 'returned', 'Returned'

    unit_name = models.CharField(max_length=120)
    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deployments',
    )
    units_count = models.PositiveIntegerField(default=1)
    personnel_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DEPLOYED)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['unit_name']

    def __str__(self):
        return self.unit_name


class DashboardMessage(models.Model):
    title = models.CharField(max_length=160)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dashboard_messages',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'dashboard message'

    def __str__(self):
        return self.title


class ImportantReminder(models.Model):
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='important_reminders',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_at', '-updated_at']

    def __str__(self):
        return self.title


class AdminRegistrationInvite(models.Model):
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'administrator registration invitation'
        verbose_name_plural = 'administrator registration invitations'

    def __str__(self):
        return f'Admin invitation created {self.created_at:%Y-%m-%d %H:%M}'


class FloodReport(models.Model):
    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MODERATE = 'moderate', 'Moderate'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        VERIFIED = 'verified', 'Verified'
        RESPONDING = 'responding', 'Response underway'
        RESOLVED = 'resolved', 'Resolved'

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flood_reports',
    )
    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.SET_NULL,
        null=True,
        related_name='flood_reports',
    )
    location_details = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MODERATE)
    water_depth_cm = models.PositiveIntegerField(null=True, blank=True)
    affected_people = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Flood report - {self.barangay or self.location_details}'


class RescueRequest(models.Model):
    class RequestType(models.TextChoices):
        RESCUE = 'rescue', 'Rescue'
        MEDICAL = 'medical', 'Medical assistance'
        EVACUATION = 'evacuation', 'Evacuation'
        OTHER = 'other', 'Other emergency'

    class Severity(models.TextChoices):
        STANDARD = 'standard', 'Standard'
        URGENT = 'urgent', 'Urgent'
        CRITICAL = 'critical', 'Critical'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ASSIGNED = 'assigned', 'Team assigned'
        RESOLVED = 'resolved', 'Resolved'
        CANCELLED = 'cancelled', 'Cancelled'

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rescue_requests',
    )
    barangay = models.ForeignKey(
        Barangay,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rescue_requests',
    )
    request_type = models.CharField(max_length=12, choices=RequestType.choices, default=RequestType.RESCUE)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.URGENT)
    location_details = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=32)
    people_count = models.PositiveIntegerField(default=1)
    details = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_request_type_display()} request - {self.requester}'


class EmergencySupply(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        LOW = 'low', 'Low stock'
        OUT = 'out', 'Out of stock'

    name = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=32, default='items')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)
    center = models.ForeignKey(
        EvacuationLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_supplies',
    )
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_emergency_supplies',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.quantity} {self.unit})'
