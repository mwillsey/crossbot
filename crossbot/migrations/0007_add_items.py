from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crossbot', '0006_cbuser_crossbucks'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemOwnershipRecord',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('item_key', models.CharField(max_length=20)),
                ('quantity', models.IntegerField(default=0)),
                ('owner',
                 models.ForeignKey(
                     on_delete=django.db.models.deletion.CASCADE,
                     to='crossbot.CBUser')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='itemownershiprecord',
            unique_together={('owner', 'item_key')},
        ),
    ]
