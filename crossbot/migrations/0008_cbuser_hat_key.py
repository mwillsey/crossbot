# Generated by Django 2.1.2 on 2018-10-27 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crossbot', '0007_add_items'),
    ]

    operations = [
        migrations.AddField(
            model_name='cbuser',
            name='hat_key',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
