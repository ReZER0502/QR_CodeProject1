# Generated by Django 5.1.2 on 2025-03-26 00:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0024_remove_mealclaim_meal_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendee',
            name='department',
            field=models.CharField(default='Visitor', max_length=100),
        ),
        migrations.AlterField(
            model_name='attendee',
            name='sub_department',
            field=models.CharField(blank=True, default='Visitor', max_length=100, null=True),
        ),
    ]
