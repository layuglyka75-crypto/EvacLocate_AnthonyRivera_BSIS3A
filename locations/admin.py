from django.contrib import admin
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


@admin.register(EvacuationLocation)
class EvacuationLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'capacity', 'status', 'latitude', 'longitude', 'owner')
    list_filter = ('status',)
    search_fields = ('name', 'address', 'owner__username')


@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    list_display = ('name', 'condition', 'affected_people', 'rescued_people', 'updated_at')
    list_filter = ('condition',)
    search_fields = ('name',)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'severity', 'status', 'barangay', 'reported_at')
    list_filter = ('kind', 'severity', 'status', 'barangay')
    search_fields = ('title', 'description', 'barangay__name')
    readonly_fields = ('reported_at', 'updated_at')


@admin.register(UnitDeployment)
class UnitDeploymentAdmin(admin.ModelAdmin):
    list_display = ('unit_name', 'barangay', 'units_count', 'personnel_count', 'status', 'updated_at')
    list_filter = ('status', 'barangay')
    search_fields = ('unit_name', 'barangay__name')


@admin.register(DashboardMessage)
class DashboardMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_by', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'body')
    readonly_fields = ('updated_at',)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ImportantReminder)
class ImportantReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'due_at', 'is_active', 'created_by', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'body')
    readonly_fields = ('updated_at',)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(FloodReport)
class FloodReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'barangay', 'reporter', 'severity', 'status', 'created_at')
    list_filter = ('severity', 'status', 'barangay')
    search_fields = ('location_details', 'description', 'reporter__username', 'barangay__name')
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.reporter_id:
            obj.reporter = request.user
        super().save_model(request, obj, form, change)


@admin.register(RescueRequest)
class RescueRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'request_type', 'barangay', 'requester', 'severity', 'status', 'created_at')
    list_filter = ('request_type', 'severity', 'status', 'barangay')
    search_fields = ('location_details', 'details', 'requester__username', 'contact_number')
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.requester_id:
            obj.requester = request.user
        super().save_model(request, obj, form, change)


@admin.register(EmergencySupply)
class EmergencySupplyAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'unit', 'status', 'center', 'updated_at')
    list_filter = ('status', 'center')
    search_fields = ('name', 'notes')
    readonly_fields = ('updated_by', 'updated_at')

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
