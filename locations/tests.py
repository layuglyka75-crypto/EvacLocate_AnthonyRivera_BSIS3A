from datetime import timedelta
from hashlib import sha256
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    AdminRegistrationInvite,
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


class AccountAndLocationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='responder', password='Strong-pass-245')
        self.other_user = User.objects.create_user(username='other', password='Strong-pass-245')

    def test_registration_creates_account_and_logs_user_in(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'new-responder',
                'email': 'responder@example.com',
                'password1': 'Safe-password-384!',
                'password2': 'Safe-password-384!',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='new-responder').exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_location_crud_is_scoped_to_owner(self):
        self.client.force_login(self.user)
        create_response = self.client.post(
            reverse('location-create'),
            {
                'name': 'North Shelter',
                'address': '12 River Road',
                'description': 'Community hall',
                'capacity': 75,
                'status': EvacuationLocation.Status.AVAILABLE,
            },
        )
        location = EvacuationLocation.objects.get(name='North Shelter')

        self.assertRedirects(create_response, reverse('location-list'))
        self.assertEqual(location.owner, self.user)
        self.assertContains(self.client.get(reverse('location-list')), 'North Shelter')

        self.client.force_login(self.other_user)
        self.assertEqual(
            self.client.get(reverse('location-detail', args=[location.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse('location-update', args=[location.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse('location-delete', args=[location.pk])).status_code,
            404,
        )

    def test_owner_can_edit_and_delete_location(self):
        location = EvacuationLocation.objects.create(
            owner=self.user,
            name='East School',
            address='5 Hill Street',
            capacity=100,
        )
        self.client.force_login(self.user)

        edit_response = self.client.post(
            reverse('location-update', args=[location.pk]),
            {
                'name': 'East Community School',
                'address': '5 Hill Street',
                'description': '',
                'capacity': 120,
                'status': EvacuationLocation.Status.FULL,
            },
        )
        location.refresh_from_db()
        self.assertRedirects(edit_response, reverse('location-list'))
        self.assertEqual(location.name, 'East Community School')
        self.assertEqual(location.capacity, 120)

        delete_response = self.client.post(reverse('location-delete', args=[location.pk]))
        self.assertRedirects(delete_response, reverse('location-list'))
        self.assertFalse(EvacuationLocation.objects.filter(pk=location.pk).exists())

    def test_location_pages_require_login(self):
        response = self.client.get(reverse('location-list'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('location-list')}")

    def test_user_can_log_in_and_log_out(self):
        login_response = self.client.post(
            reverse('login'),
            {'username': 'responder', 'password': 'Strong-pass-245'},
        )

        self.assertRedirects(login_response, reverse('dashboard'))
        self.assertTrue(login_response.wsgi_request.user.is_authenticated)

        logout_response = self.client.post(reverse('logout'))
        self.assertRedirects(logout_response, reverse('login'))
        self.assertFalse(logout_response.wsgi_request.user.is_authenticated)

    def test_user_and_admin_login_pages_are_separate_and_enforce_account_roles(self):
        User.objects.create_user(
            username='operator',
            password='Strong-pass-245',
            is_staff=True,
        )
        user_login_page = self.client.get(reverse('login'))
        admin_login_page = self.client.get(reverse('admin-login'))
        self.assertTemplateUsed(user_login_page, 'registration/login.html')
        self.assertTemplateUsed(admin_login_page, 'registration/admin_login.html')

        rejected_staff_login = self.client.post(
            reverse('login'),
            {'username': 'operator', 'password': 'Strong-pass-245'},
        )
        self.assertEqual(rejected_staff_login.status_code, 200)
        self.assertFalse(rejected_staff_login.wsgi_request.user.is_authenticated)
        self.assertContains(rejected_staff_login, 'Staff accounts must use the administrator login.')

        rejected_user_login = self.client.post(
            reverse('admin-login'),
            {'username': 'responder', 'password': 'Strong-pass-245'},
        )
        self.assertEqual(rejected_user_login.status_code, 200)
        self.assertFalse(rejected_user_login.wsgi_request.user.is_authenticated)
        self.assertContains(rejected_user_login, 'This login is only for administrator accounts.')

        accepted_admin_login = self.client.post(
            reverse('admin-login'),
            {'username': 'operator', 'password': 'Strong-pass-245'},
        )
        self.assertRedirects(accepted_admin_login, reverse('dashboard'))
        self.assertTrue(accepted_admin_login.wsgi_request.user.is_staff)

    def test_public_registration_never_grants_staff_access(self):
        response = self.client.post(
            reverse('register'),
            {
                'username': 'public-user',
                'email': 'public@example.com',
                'password1': 'Safe-password-384!',
                'password2': 'Safe-password-384!',
                'is_staff': 'on',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        account = User.objects.get(username='public-user')
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)

    def test_admin_registration_form_is_available_but_rejects_missing_invitation(self):
        response = self.client.get(reverse('admin-register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Register as administrator')
        self.assertIsNotNone(response.context['form'])

        rejected_response = self.client.post(
            reverse('admin-register'),
            {
                'username': 'blocked-admin',
                'email': 'blocked@example.com',
                'password1': 'Safe-password-384!',
                'password2': 'Safe-password-384!',
                'invitation_code': 'guess',
            },
        )
        self.assertEqual(rejected_response.status_code, 200)
        self.assertFalse(User.objects.filter(username='blocked-admin').exists())

    def test_admin_registration_requires_valid_code_and_creates_staff_not_superuser(self):
        invitation_code = 'private-test-invitation'
        AdminRegistrationInvite.objects.create(
            token_hash=sha256(invitation_code.encode('utf-8')).hexdigest(),
            expires_at=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            reverse('admin-register'),
            {
                'username': 'invalid-admin',
                'email': 'invalid@example.com',
                'password1': 'Safe-password-384!',
                'password2': 'Safe-password-384!',
                'invitation_code': 'wrong-code',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='invalid-admin').exists())

        response = self.client.post(
            reverse('admin-register'),
            {
                'username': 'invited-admin',
                'email': 'invited@example.com',
                'first_name': 'Invited',
                'last_name': 'Admin',
                'password1': 'Safe-password-384!',
                'password2': 'Safe-password-384!',
                'invitation_code': invitation_code,
            },
        )

        self.assertRedirects(response, reverse('admin-login'))
        account = User.objects.get(username='invited-admin')
        self.assertTrue(account.is_staff)
        self.assertFalse(account.is_superuser)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        login_response = self.client.post(
            reverse('admin-login'),
            {'username': 'invited-admin', 'password': 'Safe-password-384!'},
        )
        self.assertRedirects(login_response, reverse('dashboard'))
        self.assertTrue(login_response.wsgi_request.user.is_staff)
        invite = AdminRegistrationInvite.objects.get()
        self.assertIsNotNone(invite.used_at)

    def test_admin_invite_command_generates_a_usable_one_time_code(self):
        output = StringIO()
        call_command('create_admin_invite', stdout=output)
        code = output.getvalue().splitlines()[1]
        self.assertTrue(
            AdminRegistrationInvite.objects.filter(
                token_hash=sha256(code.encode('utf-8')).hexdigest(),
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exists()
        )


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='resident', password='Strong-pass-245')
        self.admin = User.objects.create_user(
            username='operator',
            password='Strong-pass-245',
            is_staff=True,
        )
        self.barangay = Barangay.objects.get(name='Becuran')
        self.barangay.condition = Barangay.Condition.CRITICAL
        self.barangay.affected_people = 20
        self.barangay.rescued_people = 5
        self.barangay.latitude = '15.000000'
        self.barangay.longitude = '120.000000'
        self.barangay.save()

    def test_dashboard_shows_barangay_progress_and_response_metrics(self):
        Incident.objects.create(
            title='Flood warning',
            kind=Incident.Kind.FLOOD,
            severity=Incident.Severity.CRITICAL,
            barangay=self.barangay,
            description='Rising water reported.',
        )
        UnitDeployment.objects.create(
            unit_name='Rescue team A',
            barangay=self.barangay,
            units_count=2,
            personnel_count=7,
        )
        DashboardMessage.objects.create(title='Radio check', body='Check in at 18:00.')
        ImportantReminder.objects.create(title='Bring life jackets')
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Becuran')
        self.assertContains(response, '25%')
        self.assertContains(response, 'Flood warning')
        self.assertContains(response, 'Radio check')
        self.assertContains(response, 'Bring life jackets')
        self.assertEqual(response.context['active_incidents_count'], 1)
        self.assertEqual(response.context['units_deployed'], 2)
        self.assertEqual(response.context['personnel_online'], 7)
        self.assertEqual(len(response.context['map_features']), 1)
        self.assertContains(response, 'Quick operations')

    def test_dashboard_update_endpoint_requires_login_and_returns_current_counts(self):
        url = reverse('dashboard-updates')
        self.assertEqual(self.client.get(url).status_code, 401)

        UnitDeployment.objects.create(unit_name='Rescue team B', personnel_count=4)
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['open_flood_reports_count'], 0)
        self.assertNotIn('personnel_online', response.json())

        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.json()['personnel_online'], 4)

    def test_staff_profile_and_admin_quick_operations_are_staff_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('admin-profile')).status_code, 403)

        self.client.force_login(self.admin)
        dashboard_response = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard_response, 'Quick operations')
        self.assertEqual(self.client.get(reverse('admin-profile')).status_code, 200)
        profile_response = self.client.post(
            reverse('admin-profile'),
            {'first_name': 'Response', 'last_name': 'Lead', 'email': 'lead@example.com'},
        )
        self.assertRedirects(profile_response, reverse('admin-profile'))
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, 'Response')
        self.assertEqual(self.admin.email, 'lead@example.com')

    def test_barangay_rescue_percentage_is_zero_without_affected_people(self):
        empty_barangay = Barangay.objects.create(name='Test Barangay')
        self.assertEqual(empty_barangay.rescue_percentage, 0)

    def test_dashboard_overview_totals_and_api_include_new_records(self):
        EvacuationLocation.objects.create(
            owner=self.user,
            name='Becuran Elementary',
            address='Main road',
            capacity=80,
        )
        RescueRequest.objects.create(
            requester=self.user,
            barangay=self.barangay,
            location_details='Near the bridge',
            contact_number='09170000000',
            details='Water entering the home.',
        )
        FloodReport.objects.create(
            reporter=self.user,
            barangay=self.barangay,
            location_details='Riverside',
            description='Water is rising.',
        )
        Incident.objects.create(
            title='Flood alert at riverside',
            kind=Incident.Kind.FLOOD,
            barangay=self.barangay,
            description='Response team monitoring river level.',
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['registered_users_count'], 2)
        self.assertEqual(response.context['evacuation_centers_count'], 1)
        self.assertEqual(response.context['pending_rescue_requests_count'], 1)
        self.assertEqual(response.context['reported_flood_incidents_count'], 2)
        updates = self.client.get(reverse('dashboard-updates')).json()
        self.assertEqual(updates['pending_rescue_requests_count'], 1)
        self.assertEqual(updates['reported_flood_incidents_count'], 2)

    def test_regular_user_gets_personal_dashboard_without_admin_metrics_or_controls(self):
        FloodReport.objects.create(
            reporter=self.user,
            barangay=self.barangay,
            location_details='My street',
            description='Water rising outside.',
        )
        FloodReport.objects.create(
            reporter=self.admin,
            barangay=self.barangay,
            location_details='Staff test location',
            description='Private report from another account.',
        )
        RescueRequest.objects.create(
            requester=self.user,
            barangay=self.barangay,
            location_details='My home',
            contact_number='09170000000',
            details='Need evacuation.',
        )
        RescueRequest.objects.create(
            requester=self.admin,
            barangay=self.barangay,
            location_details='Other home',
            contact_number='09170000001',
            details='Another private request.',
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('dashboard'))

        self.assertTemplateUsed(response, 'locations/user_dashboard.html')
        self.assertContains(response, 'My active flood reports')
        self.assertContains(response, 'My open rescue requests')
        self.assertContains(response, 'My street')
        self.assertContains(response, 'My home')
        self.assertNotContains(response, 'Staff test location')
        self.assertNotContains(response, 'Other home')
        self.assertNotContains(response, 'User Management')
        self.assertNotContains(response, 'Quick operations')
        self.assertNotContains(response, 'Total Registered Users')
        self.assertEqual(response.context['open_flood_reports_count'], 1)
        self.assertEqual(response.context['open_rescue_requests_count'], 1)


class PortalManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reporter', password='Strong-pass-245')
        self.other_user = User.objects.create_user(username='neighbor', password='Strong-pass-245')
        self.admin = User.objects.create_user(
            username='staffer',
            password='Strong-pass-245',
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username='rootadmin',
            email='root@example.com',
            password='Strong-pass-245',
        )
        self.barangay = Barangay.objects.get(name='San Isidro')

    def test_users_can_browse_shared_centers_and_supplies(self):
        center = EvacuationLocation.objects.create(
            owner=self.admin,
            name='Town Hall Shelter',
            address='Central road',
            capacity=60,
            latitude='15.000000',
            longitude='120.000000',
        )
        EmergencySupply.objects.create(
            name='Drinking water',
            quantity=120,
            unit='bottles',
            center=center,
            updated_by=self.admin,
        )
        self.client.force_login(self.user)

        list_response = self.client.get(reverse('center-list'))
        self.assertContains(list_response, 'Town Hall Shelter')
        self.assertContains(list_response, 'center-map')
        self.assertEqual(len(list_response.context['map_centers']), 1)
        detail_response = self.client.get(reverse('center-detail', args=[center.pk]))
        self.assertContains(detail_response, 'center-detail-map')
        self.assertContains(self.client.get(reverse('emergency-supplies')), 'Drinking water')
        self.assertEqual(
            self.client.post(reverse('supply-create'), {}).status_code,
            403,
        )

    def test_staff_can_create_edit_and_delete_evacuation_centers(self):
        self.client.force_login(self.admin)
        create_response = self.client.post(
            reverse('center-create'),
            {
                'name': 'San Isidro School',
                'address': 'Barangay road',
                'description': 'Temporary shelter.',
                'capacity': 150,
                'status': EvacuationLocation.Status.AVAILABLE,
                'latitude': '15.100000',
                'longitude': '120.200000',
            },
        )
        center = EvacuationLocation.objects.get(name='San Isidro School')
        self.assertRedirects(create_response, reverse('center-detail', args=[center.pk]))
        self.assertEqual(center.owner, self.admin)
        self.assertEqual(str(center.latitude), '15.100000')

        edit_response = self.client.post(
            reverse('center-update', args=[center.pk]),
            {
                'name': 'San Isidro Evacuation Center',
                'address': 'Barangay road',
                'description': 'Updated shelter details.',
                'capacity': 180,
                'status': EvacuationLocation.Status.FULL,
                'latitude': '15.100000',
                'longitude': '120.200000',
            },
        )
        center.refresh_from_db()
        self.assertRedirects(edit_response, reverse('center-detail', args=[center.pk]))
        self.assertEqual(center.name, 'San Isidro Evacuation Center')
        self.assertEqual(center.status, EvacuationLocation.Status.FULL)

        delete_response = self.client.post(reverse('center-delete', args=[center.pk]))
        self.assertRedirects(delete_response, reverse('center-list'))
        self.assertFalse(EvacuationLocation.objects.filter(pk=center.pk).exists())

    def test_regular_users_cannot_manage_centers_and_coordinates_must_be_a_pair(self):
        center = EvacuationLocation.objects.create(
            owner=self.admin,
            name='North Hall',
            address='Main road',
            capacity=80,
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('center-create')).status_code, 403)
        self.assertEqual(self.client.get(reverse('center-update', args=[center.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('center-delete', args=[center.pk])).status_code, 403)

        self.client.force_login(self.admin)
        invalid_response = self.client.post(
            reverse('center-create'),
            {
                'name': 'Coordinates without pair',
                'address': 'Some road',
                'description': '',
                'capacity': 20,
                'status': EvacuationLocation.Status.AVAILABLE,
                'latitude': '15.100000',
                'longitude': '',
            },
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertFalse(EvacuationLocation.objects.filter(name='Coordinates without pair').exists())

    def test_flood_reports_are_owned_and_only_staff_can_change_status(self):
        self.client.force_login(self.user)
        create_response = self.client.post(
            reverse('flood-report-create'),
            {
                'barangay': self.barangay.pk,
                'location_details': 'Near the creek',
                'description': 'Water is entering homes.',
                'severity': FloodReport.Severity.HIGH,
                'water_depth_cm': 35,
                'affected_people': 8,
            },
        )
        report = FloodReport.objects.get(reporter=self.user)
        self.assertRedirects(create_response, reverse('flood-reports'))
        self.assertEqual(report.status, FloodReport.Status.PENDING)

        self.client.force_login(self.other_user)
        self.assertNotContains(self.client.get(reverse('flood-reports')), 'Near the creek')
        self.assertEqual(
            self.client.get(reverse('flood-report-update', args=[report.pk])).status_code,
            404,
        )

        self.client.force_login(self.admin)
        update_response = self.client.post(
            reverse('flood-report-update', args=[report.pk]),
            {
                'barangay': self.barangay.pk,
                'location_details': 'Near the creek',
                'description': 'Verified rising water.',
                'severity': FloodReport.Severity.HIGH,
                'water_depth_cm': 35,
                'affected_people': 8,
                'status': FloodReport.Status.VERIFIED,
            },
        )
        report.refresh_from_db()
        self.assertRedirects(update_response, reverse('flood-reports'))
        self.assertEqual(report.status, FloodReport.Status.VERIFIED)

    def test_rescue_requests_are_private_to_requester_and_admin_manages_status(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('rescue-request-create'),
            {
                'barangay': self.barangay.pk,
                'request_type': RescueRequest.RequestType.RESCUE,
                'severity': RescueRequest.Severity.CRITICAL,
                'location_details': 'Block 4, Riverside',
                'contact_number': '09170000000',
                'people_count': 3,
                'details': 'Three people need evacuation.',
            },
        )
        rescue = RescueRequest.objects.get(requester=self.user)
        self.assertRedirects(response, reverse('rescue-requests'))

        self.client.force_login(self.other_user)
        self.assertNotContains(self.client.get(reverse('rescue-requests')), 'Block 4, Riverside')

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('rescue-request-update', args=[rescue.pk]),
            {
                'barangay': self.barangay.pk,
                'request_type': RescueRequest.RequestType.RESCUE,
                'severity': RescueRequest.Severity.CRITICAL,
                'location_details': 'Block 4, Riverside',
                'contact_number': '09170000000',
                'people_count': 3,
                'details': 'Team dispatched.',
                'status': RescueRequest.Status.ASSIGNED,
            },
        )
        rescue.refresh_from_db()
        self.assertRedirects(response, reverse('rescue-requests'))
        self.assertEqual(rescue.status, RescueRequest.Status.ASSIGNED)

    def test_user_management_is_staff_only_and_does_not_expose_staff_role(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('user-management')).status_code, 403)

        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('user-management')), 'reporter')
        response = self.client.post(
            reverse('user-create'),
            {
                'username': 'newperson',
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'Person',
                'password1': 'Safe-password-384!',
                'password2': 'Safe-password-384!',
            },
        )
        account = User.objects.get(username='newperson')
        self.assertRedirects(response, reverse('user-management'))
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)

    def test_only_superusers_can_register_staff_admin_accounts(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('admin-account-create')).status_code, 403)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('admin-account-create')).status_code, 403)

        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse('admin-account-create'),
            {
                'username': 'new-staff',
                'email': 'new-staff@example.com',
                'first_name': 'New',
                'last_name': 'Staff',
                'password1': 'Safe-password-384!',
                'password2': 'Safe-password-384!',
            },
        )
        self.assertRedirects(response, reverse('user-management'))
        new_admin = User.objects.get(username='new-staff')
        self.assertTrue(new_admin.is_staff)
        self.assertFalse(new_admin.is_superuser)
        self.assertTrue(new_admin.check_password('Safe-password-384!'))

        login_response = self.client.post(
            reverse('admin-login'),
            {'username': 'new-staff', 'password': 'Safe-password-384!'},
        )
        self.assertRedirects(login_response, reverse('dashboard'))

    def test_staff_can_manage_supply_inventory(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('supply-create'),
            {
                'name': 'First aid kits',
                'quantity': 25,
                'unit': 'kits',
                'status': EmergencySupply.Status.AVAILABLE,
                'center': '',
                'notes': 'Stored in the municipal warehouse.',
            },
        )
        supply = EmergencySupply.objects.get(name='First aid kits')
        self.assertRedirects(response, reverse('emergency-supplies'))
        self.assertEqual(supply.updated_by, self.admin)

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('supply-update', args=[supply.pk])).status_code, 403)
