from django.db import migrations


BARANGAY_NAMES = (
    'San Isidro',
    'San Basillo',
    'Dila-Dila',
    'San Agustin',
    'San Jose',
    'San Juan',
    'Santa Monica',
    'San Matias',
    'Becuran',
)


def create_barangays(apps, schema_editor):
    Barangay = apps.get_model('locations', 'Barangay')
    Barangay.objects.using(schema_editor.connection.alias).bulk_create(
        [Barangay(name=name) for name in BARANGAY_NAMES],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0002_barangay_dashboardmessage_importantreminder_incident_and_more'),
    ]

    operations = [
        migrations.RunPython(create_barangays, migrations.RunPython.noop),
    ]
