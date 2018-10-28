from django.db import migrations, models


def give_backpay(apps, schema_editor):
    for user in apps.get_model('crossbot', 'CBUser').objects.all():
        user.crossbucks = 10 * (
            user.minicrosswordtime_set.count() + user.crosswordtime_set.count()
            + user.easysudokutime_set.count()
        )
        user.save()


class Migration(migrations.Migration):
    dependencies = [
        ('crossbot', '0005_add_user_columns'),
    ]

    operations = [
        migrations.AddField(
            model_name='cbuser',
            name='crossbucks',
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(give_backpay)
    ]
