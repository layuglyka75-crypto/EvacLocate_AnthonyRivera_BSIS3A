from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from .forms import (
    AdminProfileForm,
    AdminAccountCreateForm,
    PublicAdminRegistrationForm,
    AdminUserCreateForm,
    AdminUserUpdateForm,
    AdminAuthenticationForm,
    EmergencySupplyForm,
    EvacuationLocationForm,
    FloodReportAdminForm,
    FloodReportForm,
    RegistrationForm,
    RescueRequestAdminForm,
    RescueRequestForm,
    UserAuthenticationForm,
)
from .models import (
    Barangay,
    DashboardMessage,
    EmergencySupply,
    EvacuationLocation,
    FloodReport,
    ImportantReminder,
    Incident,
    RescueRequest,
    UnitDeployment,
)


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Your account has been created.')
            return redirect('dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


def register_admin(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = PublicAdminRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Administrator account created. You can now sign in using the administrator login.',
            )
            return redirect('admin-login')
    else:
        form = PublicAdminRegistrationForm()

    return render(
        request,
        'registration/admin_register.html',
        {'form': form},
    )


class UserLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = UserAuthenticationForm
    redirect_authenticated_user = True


class AdminLoginView(LoginView):
    template_name = 'registration/admin_login.html'
    authentication_form = AdminAuthenticationForm
    redirect_authenticated_user = True


class OwnedLocationsMixin(LoginRequiredMixin):
    model = EvacuationLocation

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class LocationListView(LoginRequiredMixin, ListView):
    model = EvacuationLocation
    template_name = 'locations/location_list.html'
    context_object_name = 'locations'

    def get_queryset(self):
        return EvacuationLocation.objects.filter(owner=self.request.user)


class LocationDetailView(OwnedLocationsMixin, DetailView):
    template_name = 'locations/location_detail.html'
    context_object_name = 'location'


class LocationCreateView(LoginRequiredMixin, CreateView):
    model = EvacuationLocation
    form_class = EvacuationLocationForm
    template_name = 'locations/location_form.html'
    success_url = reverse_lazy('location-list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Evacuation location added.')
        return super().form_valid(form)


class LocationUpdateView(OwnedLocationsMixin, UpdateView):
    form_class = EvacuationLocationForm
    template_name = 'locations/location_form.html'
    success_url = reverse_lazy('location-list')

    def form_valid(self, form):
        messages.success(self.request, 'Evacuation location updated.')
        return super().form_valid(form)


class LocationDeleteView(OwnedLocationsMixin, DeleteView):
    template_name = 'locations/location_confirm_delete.html'
    success_url = reverse_lazy('location-list')

    def form_valid(self, form):
        messages.success(self.request, 'Evacuation location deleted.')
        return super().form_valid(form)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class DashboardView(LoginRequiredMixin, ListView):
    model = Incident
    template_name = 'locations/dashboard.html'
    context_object_name = 'incidents'

    def get_queryset(self):
        return Incident.objects.exclude(status=Incident.Status.RESOLVED).select_related('barangay')[:8]

    def get_template_names(self):
        if not self.request.user.is_staff:
            return ['locations/user_dashboard.html']
        return ['locations/dashboard.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_staff:
            return self.get_user_dashboard_context(context)

        context.update(dashboard_snapshot())
        context.update(dashboard_overview())
        barangays = list(Barangay.objects.all())
        context['barangays'] = barangays
        context['map_features'] = [
            {
                'name': barangay.name,
                'latitude': float(barangay.latitude),
                'longitude': float(barangay.longitude),
                'condition': barangay.condition,
                'condition_label': barangay.get_condition_display(),
                'rescue_percentage': barangay.rescue_percentage,
            }
            for barangay in barangays
            if barangay.latitude is not None and barangay.longitude is not None
        ]
        context['map_barangays'] = context['map_features']
        context['dashboard_messages'] = DashboardMessage.objects.filter(is_active=True)[:5]
        reports = FloodReport.objects.exclude(status=FloodReport.Status.RESOLVED)
        if not self.request.user.is_staff:
            reports = reports.filter(reporter=self.request.user)
        context['recent_flood_reports'] = reports.select_related('barangay', 'reporter')[:5]
        context['pending_rescue_requests'] = RescueRequest.objects.filter(
            status=RescueRequest.Status.PENDING
        ).select_related('barangay', 'requester')[:5]
        context['reminders'] = ImportantReminder.objects.filter(is_active=True).filter(
            Q(due_at__isnull=True) | Q(due_at__gte=timezone.now())
        )[:5]
        context['is_admin'] = self.request.user.is_staff
        return context

    def get_user_dashboard_context(self, context):
        user = self.request.user
        open_flood_reports = FloodReport.objects.filter(reporter=user).exclude(
            status=FloodReport.Status.RESOLVED
        )
        open_rescue_requests = RescueRequest.objects.filter(requester=user).filter(
            Q(status=RescueRequest.Status.PENDING) | Q(status=RescueRequest.Status.ASSIGNED)
        )
        context.update({
            'is_admin': False,
            'open_flood_reports_count': open_flood_reports.count(),
            'open_rescue_requests_count': open_rescue_requests.count(),
            'available_centers_count': EvacuationLocation.objects.filter(
                status=EvacuationLocation.Status.AVAILABLE
            ).count(),
            'available_supplies_count': EmergencySupply.objects.filter(
                status=EmergencySupply.Status.AVAILABLE,
                quantity__gt=0,
            ).count(),
            'my_flood_reports': FloodReport.objects.filter(
                reporter=user
            ).select_related('barangay')[:5],
            'my_rescue_requests': RescueRequest.objects.filter(
                requester=user
            ).select_related('barangay')[:5],
            'public_alerts': Incident.objects.exclude(
                status=Incident.Status.RESOLVED
            ).select_related('barangay')[:5],
            'barangays': Barangay.objects.all(),
            'dashboard_messages': DashboardMessage.objects.filter(is_active=True)[:3],
            'reminders': ImportantReminder.objects.filter(is_active=True).filter(
                Q(due_at__isnull=True) | Q(due_at__gte=timezone.now())
            )[:3],
        })
        return context


def dashboard_snapshot():
    active_incidents = Incident.objects.exclude(status=Incident.Status.RESOLVED).count()
    deployed = UnitDeployment.objects.filter(status=UnitDeployment.Status.DEPLOYED).aggregate(
        units=Sum('units_count'),
        personnel=Sum('personnel_count'),
    )
    response_durations = [
        (incident.responded_at - incident.reported_at).total_seconds() / 60
        for incident in Incident.objects.filter(responded_at__isnull=False)
    ]
    average_response = (
        round(sum(response_durations) / len(response_durations), 1)
        if response_durations
        else None
    )
    latest_updates = [
        Incident.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        Barangay.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        UnitDeployment.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        DashboardMessage.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        ImportantReminder.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        FloodReport.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        RescueRequest.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        EmergencySupply.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        EvacuationLocation.objects.order_by('-updated_at').values_list('updated_at', flat=True).first(),
        User.objects.order_by('-date_joined').values_list('date_joined', flat=True).first(),
    ]
    last_updated = max((value for value in latest_updates if value), default=None)
    return {
        'active_incidents_count': active_incidents,
        'units_deployed': deployed['units'] or 0,
        'personnel_online': deployed['personnel'] or 0,
        'average_response': average_response,
        'data_version': last_updated.isoformat() if last_updated else '',
    }


def dashboard_overview():
    reported_flood_incidents = FloodReport.objects.exclude(
        status=FloodReport.Status.RESOLVED
    ).count()
    active_flood_alerts = Incident.objects.filter(kind=Incident.Kind.FLOOD).exclude(
        status=Incident.Status.RESOLVED
    ).count()
    return {
        'registered_users_count': User.objects.count(),
        'evacuation_centers_count': EvacuationLocation.objects.count(),
        'pending_rescue_requests_count': RescueRequest.objects.filter(
            status=RescueRequest.Status.PENDING
        ).count(),
        'reported_flood_incidents_count': reported_flood_incidents + active_flood_alerts,
    }


def dashboard_updates(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication required.'}, status=401)
    if not request.user.is_staff:
        user = request.user
        return JsonResponse({
            'open_flood_reports_count': FloodReport.objects.filter(
                reporter=user
            ).exclude(status=FloodReport.Status.RESOLVED).count(),
            'open_rescue_requests_count': RescueRequest.objects.filter(
                requester=user
            ).filter(
                Q(status=RescueRequest.Status.PENDING)
                | Q(status=RescueRequest.Status.ASSIGNED)
            ).count(),
            'available_centers_count': EvacuationLocation.objects.filter(
                status=EvacuationLocation.Status.AVAILABLE
            ).count(),
            'available_supplies_count': EmergencySupply.objects.filter(
                status=EmergencySupply.Status.AVAILABLE,
                quantity__gt=0,
            ).count(),
        })
    return JsonResponse({**dashboard_snapshot(), **dashboard_overview()})


class AdminProfileView(StaffRequiredMixin, FormView):
    template_name = 'locations/admin_profile.html'
    form_class = AdminProfileForm
    success_url = reverse_lazy('admin-profile')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Your profile has been updated.')
        return super().form_valid(form)


class UserManagementView(StaffRequiredMixin, ListView):
    model = User
    template_name = 'locations/user_list.html'
    context_object_name = 'managed_users'
    ordering = ('username',)

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(is_superuser=True)
        return queryset


class UserCreateView(StaffRequiredMixin, CreateView):
    model = User
    form_class = AdminUserCreateForm
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('user-management')
    extra_context = {
        'page_title': 'Create user',
        'cancel_url': reverse_lazy('user-management'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'User account created.')
        return super().form_valid(form)


class AdminAccountCreateView(SuperuserRequiredMixin, CreateView):
    model = User
    form_class = AdminAccountCreateForm
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('user-management')
    extra_context = {
        'page_title': 'Register administrator',
        'cancel_url': reverse_lazy('user-management'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Staff administrator account created.')
        return super().form_valid(form)


class UserUpdateView(StaffRequiredMixin, UpdateView):
    model = User
    form_class = AdminUserUpdateForm
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('user-management')
    extra_context = {
        'page_title': 'Edit user',
        'cancel_url': reverse_lazy('user-management'),
    }

    def get_queryset(self):
        queryset = User.objects.exclude(pk=self.request.user.pk)
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(is_superuser=True)
        return queryset

    def form_valid(self, form):
        messages.success(self.request, 'User account updated.')
        return super().form_valid(form)


class UserDeleteView(StaffRequiredMixin, DeleteView):
    model = User
    template_name = 'locations/record_confirm_delete.html'
    success_url = reverse_lazy('user-management')
    extra_context = {
        'page_title': 'Delete user',
        'cancel_url': reverse_lazy('user-management'),
    }

    def get_queryset(self):
        queryset = User.objects.exclude(pk=self.request.user.pk)
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(is_superuser=True)
        return queryset

    def form_valid(self, form):
        messages.success(self.request, 'User account deleted.')
        return super().form_valid(form)


class EvacuationCenterListView(LoginRequiredMixin, ListView):
    model = EvacuationLocation
    template_name = 'locations/center_list.html'
    context_object_name = 'centers'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.is_staff
        context['map_centers'] = [
            {
                'id': center.pk,
                'name': center.name,
                'address': center.address,
                'status': center.status,
                'status_label': center.get_status_display(),
                'capacity': center.capacity,
                'detail_url': reverse('center-detail', kwargs={'pk': center.pk}),
                'latitude': float(center.latitude),
                'longitude': float(center.longitude),
            }
            for center in context['centers']
            if center.latitude is not None and center.longitude is not None
        ]
        return context


class StaffCenterMixin(StaffRequiredMixin):
    model = EvacuationLocation
    form_class = EvacuationLocationForm
    template_name = 'locations/record_form.html'


class CenterCreateView(StaffCenterMixin, CreateView):
    extra_context = {
        'page_title': 'Add evacuation center',
        'cancel_url': reverse_lazy('center-list'),
    }

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Evacuation center added.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('center-detail', kwargs={'pk': self.object.pk})


class CenterDetailView(LoginRequiredMixin, DetailView):
    model = EvacuationLocation
    template_name = 'locations/center_detail.html'
    context_object_name = 'center'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        center = context['center']
        context['center_map_feature'] = {
            'name': center.name,
            'latitude': float(center.latitude),
            'longitude': float(center.longitude),
            'status': center.status,
            'status_label': center.get_status_display(),
            'capacity': center.capacity,
        } if center.latitude is not None and center.longitude is not None else None
        return context


class CenterUpdateView(StaffCenterMixin, UpdateView):
    extra_context = {
        'page_title': 'Edit evacuation center',
        'cancel_url': reverse_lazy('center-list'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Evacuation center updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('center-detail', kwargs={'pk': self.object.pk})


class CenterDeleteView(StaffRequiredMixin, DeleteView):
    model = EvacuationLocation
    template_name = 'locations/record_confirm_delete.html'
    success_url = reverse_lazy('center-list')
    extra_context = {
        'page_title': 'Delete evacuation center',
        'cancel_url': reverse_lazy('center-list'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Evacuation center deleted.')
        return super().form_valid(form)


class FloodReportListView(LoginRequiredMixin, ListView):
    model = FloodReport
    template_name = 'locations/flood_report_list.html'
    context_object_name = 'reports'

    def get_queryset(self):
        queryset = FloodReport.objects.select_related('barangay', 'reporter')
        if not self.request.user.is_staff:
            queryset = queryset.filter(reporter=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.is_staff
        return context


class FloodReportCreateView(LoginRequiredMixin, CreateView):
    model = FloodReport
    form_class = FloodReportForm
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('flood-reports')
    extra_context = {
        'page_title': 'Report flooding',
        'cancel_url': reverse_lazy('flood-reports'),
    }

    def form_valid(self, form):
        form.instance.reporter = self.request.user
        messages.success(self.request, 'Flood report submitted for review.')
        return super().form_valid(form)


class OwnedFloodReportMixin(LoginRequiredMixin):
    model = FloodReport

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(reporter=self.request.user)
        return queryset

    def get_form_class(self):
        if self.request.user.is_staff:
            return FloodReportAdminForm
        return FloodReportForm


class FloodReportUpdateView(OwnedFloodReportMixin, UpdateView):
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('flood-reports')
    extra_context = {
        'page_title': 'Update flood report',
        'cancel_url': reverse_lazy('flood-reports'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Flood report updated.')
        return super().form_valid(form)


class FloodReportDeleteView(OwnedFloodReportMixin, DeleteView):
    template_name = 'locations/record_confirm_delete.html'
    success_url = reverse_lazy('flood-reports')
    extra_context = {
        'page_title': 'Delete flood report',
        'cancel_url': reverse_lazy('flood-reports'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Flood report deleted.')
        return super().form_valid(form)


class RescueRequestListView(LoginRequiredMixin, ListView):
    model = RescueRequest
    template_name = 'locations/rescue_request_list.html'
    context_object_name = 'requests'

    def get_queryset(self):
        queryset = RescueRequest.objects.select_related('barangay', 'requester')
        if not self.request.user.is_staff:
            queryset = queryset.filter(requester=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.is_staff
        return context


class RescueRequestCreateView(LoginRequiredMixin, CreateView):
    model = RescueRequest
    form_class = RescueRequestForm
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('rescue-requests')
    extra_context = {
        'page_title': 'Request emergency assistance',
        'cancel_url': reverse_lazy('rescue-requests'),
    }

    def form_valid(self, form):
        form.instance.requester = self.request.user
        messages.success(self.request, 'Rescue request submitted to the response team.')
        return super().form_valid(form)


class OwnedRescueRequestMixin(LoginRequiredMixin):
    model = RescueRequest

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(requester=self.request.user)
        return queryset

    def get_form_class(self):
        if self.request.user.is_staff:
            return RescueRequestAdminForm
        return RescueRequestForm


class RescueRequestUpdateView(OwnedRescueRequestMixin, UpdateView):
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('rescue-requests')
    extra_context = {
        'page_title': 'Update rescue request',
        'cancel_url': reverse_lazy('rescue-requests'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Rescue request updated.')
        return super().form_valid(form)


class RescueRequestDeleteView(OwnedRescueRequestMixin, DeleteView):
    template_name = 'locations/record_confirm_delete.html'
    success_url = reverse_lazy('rescue-requests')
    extra_context = {
        'page_title': 'Delete rescue request',
        'cancel_url': reverse_lazy('rescue-requests'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Rescue request deleted.')
        return super().form_valid(form)


class EmergencySupplyListView(LoginRequiredMixin, ListView):
    model = EmergencySupply
    template_name = 'locations/supply_list.html'
    context_object_name = 'supplies'

    def get_queryset(self):
        return EmergencySupply.objects.select_related('center', 'updated_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.request.user.is_staff
        return context


class EmergencySupplyCreateView(StaffRequiredMixin, CreateView):
    model = EmergencySupply
    form_class = EmergencySupplyForm
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('emergency-supplies')
    extra_context = {
        'page_title': 'Add emergency supply',
        'cancel_url': reverse_lazy('emergency-supplies'),
    }

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Emergency supply added.')
        return super().form_valid(form)


class EmergencySupplyUpdateView(StaffRequiredMixin, UpdateView):
    model = EmergencySupply
    form_class = EmergencySupplyForm
    template_name = 'locations/record_form.html'
    success_url = reverse_lazy('emergency-supplies')
    extra_context = {
        'page_title': 'Update emergency supply',
        'cancel_url': reverse_lazy('emergency-supplies'),
    }

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Emergency supply updated.')
        return super().form_valid(form)


class EmergencySupplyDeleteView(StaffRequiredMixin, DeleteView):
    model = EmergencySupply
    template_name = 'locations/record_confirm_delete.html'
    success_url = reverse_lazy('emergency-supplies')
    extra_context = {
        'page_title': 'Delete emergency supply',
        'cancel_url': reverse_lazy('emergency-supplies'),
    }

    def form_valid(self, form):
        messages.success(self.request, 'Emergency supply deleted.')
        return super().form_valid(form)
