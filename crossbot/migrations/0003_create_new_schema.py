from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crossbot', '0002_fix_old_schema'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelDate',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('date', models.IntegerField()),
                ('difficulty', models.FloatField()),
                ('difficulty_25', models.FloatField()),
                ('difficulty_75', models.FloatField()),
            ],
            options={
                'db_table': 'model_dates',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ModelUser',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('uid', models.TextField(unique=True)),
                ('nth', models.IntegerField()),
                ('skill', models.FloatField()),
                ('skill_25', models.FloatField()),
                ('skill_75', models.FloatField()),
            ],
            options={
                'db_table': 'model_users',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CBUser',
            fields=[
                ('slackid', models.CharField(max_length=10, primary_key=True)),
                ('slackname', models.CharField(blank=True, max_length=100)),
                ('auth_user',
                 models.OneToOneField(
                     null=True,
                     blank=True,
                     on_delete=django.db.models.deletion.SET_NULL,
                     related_name='cb_user',
                     to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'CBUser',
                'verbose_name_plural': 'CBUsers',
            },
        ),
        migrations.CreateModel(
            name='TempQueryShorthand',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True)),
                ('command', models.TextField()),
                ('timestamp', models.DateTimeField(
                    null=True, auto_now_add=True)),
                ('user',
                 models.ForeignKey(
                     null=True,
                     on_delete=django.db.models.deletion.SET_NULL,
                     to='crossbot.CBUser')),
            ],
        ),
        migrations.CreateModel(
            name='TempCrosswordTime',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(
                    auto_now_add=True, null=True)),
                ('user',
                 models.ForeignKey(
                     on_delete=django.db.models.deletion.CASCADE,
                     to='crossbot.CBUser')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TempEasySudokuTime',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(
                    auto_now_add=True, null=True)),
                ('user',
                 models.ForeignKey(
                     on_delete=django.db.models.deletion.CASCADE,
                     to='crossbot.CBUser')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TempMiniCrosswordTime',
            fields=[
                ('id',
                 models.AutoField(
                     auto_created=True,
                     primary_key=True,
                     serialize=False,
                     verbose_name='ID')),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(
                    auto_now_add=True, null=True)),
                ('user',
                 models.ForeignKey(
                     on_delete=django.db.models.deletion.CASCADE,
                     to='crossbot.CBUser')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterModelOptions(
            name='modelparams',
            options={
                'managed': False,
                'verbose_name_plural': 'ModelParams'
            },
        ),
        migrations.AlterUniqueTogether(
            name='tempminicrosswordtime',
            unique_together={('user', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='tempeasysudokutime',
            unique_together={('user', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='tempcrosswordtime',
            unique_together={('user', 'date')},
        ),
    ]
