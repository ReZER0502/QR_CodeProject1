# Generated by Django 5.1.2 on 2024-11-21 05:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0006_delete_adminrequest'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='adminwhitelist',
            name='is_approved',
        ),
    ]
