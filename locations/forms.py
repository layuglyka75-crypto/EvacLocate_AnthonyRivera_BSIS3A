from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from hashlib import sha256

from .models import (
    AdminRegistrationInvite,
    EmergencySupply,
    EvacuationLocation,
    FloodReport,
    RescueRequest,
)


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')


class UserAuthenticationForm(AuthenticationForm):
    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        if user and user.is_staff:
            raise ValidationError('Staff accounts must use the administrator login.')
        return cleaned_data


class AdminAuthenticationForm(AuthenticationForm):
    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        if user and not user.is_staff:
            raise ValidationError('This login is only for administrator accounts.')
        return cleaned_data


class EvacuationLocationForm(forms.ModelForm):
    class Meta:
        model = EvacuationLocation
        fields = (
            'name',
            'address',
            'description',
            'capacity',
            'status',
            'latitude',
            'longitude',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'latitude': forms.NumberInput(attrs={
                'step': '0.000001',
                'placeholder': 'e.g. 15.000000',
            }),
            'longitude': forms.NumberInput(attrs={
                'step': '0.000001',
                'placeholder': 'e.g. 120.000000',
            }),
        }


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class FloodReportForm(forms.ModelForm):
    class Meta:
        model = FloodReport
        fields = (
            'barangay',
            'location_details',
            'description',
            'severity',
            'water_depth_cm',
            'affected_people',
        )


class FloodReportAdminForm(FloodReportForm):
    class Meta(FloodReportForm.Meta):
        fields = FloodReportForm.Meta.fields + ('status',)


class RescueRequestForm(forms.ModelForm):
    class Meta:
        model = RescueRequest
        fields = (
            'barangay',
            'request_type',
            'severity',
            'location_details',
            'contact_number',
            'people_count',
            'details',
        )


class RescueRequestAdminForm(RescueRequestForm):
    class Meta(RescueRequestForm.Meta):
        fields = RescueRequestForm.Meta.fields + ('status',)


class EmergencySupplyForm(forms.ModelForm):
    class Meta:
        model = EmergencySupply
        fields = ('name', 'quantity', 'unit', 'status', 'center', 'notes')


class AdminUserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

class AdminAccountCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.is_superuser = False
        if commit:
            user.save()
            self.save_m2m()
        return user


class PublicAdminRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    invitation_code = forms.CharField(
        label='Administrator invitation code',
        widget=forms.PasswordInput(render_value=False),
        help_text='Ask the EvacLocate system operator for the current invitation code.',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_invitation_code(self):
        submitted_code = self.cleaned_data['invitation_code'].strip()
        token_hash = sha256(submitted_code.encode('utf-8')).hexdigest()
        invite = AdminRegistrationInvite.objects.filter(
            token_hash=token_hash,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).first()
        if invite is None:
            raise ValidationError('The invitation code is invalid, expired, or already used.')
        self.valid_invite_id = invite.pk
        return submitted_code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.is_superuser = False
        if not commit:
            return user

        with transaction.atomic():
            invite = AdminRegistrationInvite.objects.select_for_update().filter(
                pk=getattr(self, 'valid_invite_id', None),
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if invite is None:
                raise ValidationError('The invitation code is invalid, expired, or already used.')
            user.save()
            invite.used_at = timezone.now()
            invite.save(update_fields=['used_at'])
            self.save_m2m()
        return user


class AdminUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'is_active')
