from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    try:
        site = Site.objects.get(pk=1)
        site.domain = 'healthjustice.co'
        site.name = 'HealthJustice'
        site.save()
    except Site.DoesNotExist:
        Site.objects.create(id=1, domain='healthjustice.co', name='HealthJustice')


def reverse_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    try:
        site = Site.objects.get(pk=1)
        site.domain = 'example.com'
        site.name = 'example.com'
        site.save()
    except Site.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(set_site_domain, reverse_site_domain),
    ]
