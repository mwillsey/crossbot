# Generated by Django 2.1.2 on 2018-11-04 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crossbot', '0010_fix_time_model'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='MiniCrosswordModel',
            options={'managed': True},
        ),
        migrations.AlterModelOptions(
            name='ModelUser',
            options={'managed': True},
        ),
        migrations.AlterModelOptions(
            name='ModelDate',
            options={'managed': True},
        ),
        migrations.AlterModelOptions(
            name='ModelParams',
            options={'managed': True},
        ),
        migrations.DeleteModel('MiniCrosswordModel'),
        migrations.DeleteModel('ModelUser'),
        migrations.DeleteModel('ModelDate'),
        migrations.DeleteModel('ModelParams'),
        migrations.CreateModel(
            name='Prediction',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, to='crossbot.CBUser')),
                ('date', models.DateField()),
                ('prediction', models.FloatField()),
                ('residual', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='PredictionDate',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                ('date', models.DateField()),
                ('difficulty', models.FloatField()),
                ('difficulty_25', models.FloatField()),
                ('difficulty_75', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='PredictionParameter',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                ('time', models.FloatField()),
                ('time_25', models.FloatField()),
                ('time_75', models.FloatField()),
                ('satmult', models.FloatField()),
                ('satmult_25', models.FloatField()),
                ('satmult_75', models.FloatField()),
                ('bgain', models.FloatField()),
                ('bgain_25', models.FloatField()),
                ('bgain_75', models.FloatField()),
                ('bdecay', models.FloatField()),
                ('bdecay_25', models.FloatField()),
                ('bdecay_75', models.FloatField()),
                ('skill_dev', models.FloatField()),
                ('date_dev', models.FloatField()),
                ('sigma', models.FloatField()),
                ('lp', models.FloatField()),
                ('when_run', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='PredictionUser',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, to='crossbot.CBUser')),
                ('skill', models.FloatField()),
                ('skill_25', models.FloatField()),
                ('skill_75', models.FloatField()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='prediction',
            unique_together={('user', 'date')},
        ),
    ]
