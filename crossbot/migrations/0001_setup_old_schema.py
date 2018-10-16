from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CrosswordTime',
            fields=[
                ('userid', models.TextField()),
                ('date', models.IntegerField()),
                ('seconds', models.IntegerField()),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'crossword_time',
            },
        ),
        migrations.CreateModel(
            name='EasySudokuTime',
            fields=[
                ('userid', models.TextField()),
                ('date', models.IntegerField()),
                ('seconds', models.IntegerField()),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'easy_sudoku_time',
            },
        ),
        migrations.CreateModel(
            name='MiniCrosswordModel',
            fields=[
                ('userid', models.TextField()),
                ('date', models.IntegerField()),
                ('prediction', models.IntegerField()),
                ('residual', models.FloatField()),
            ],
            options={
                'db_table': 'mini_crossword_model',
            },
        ),
        migrations.CreateModel(
            name='MiniCrosswordTime',
            fields=[
                ('userid', models.TextField()),
                ('date', models.IntegerField()),
                ('seconds', models.IntegerField()),
                ('timestamp', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'mini_crossword_time',
            },
        ),
        migrations.CreateModel(
            name='ModelDates',
            fields=[
                ('date', models.IntegerField()),
                ('difficulty', models.FloatField()),
                ('difficulty_25', models.FloatField()),
                ('difficulty_75', models.FloatField()),
            ],
            options={
                'db_table': 'model_dates',
            },
        ),
        migrations.CreateModel(
            name='ModelParams',
            fields=[
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
                ('when_run', models.FloatField()),
            ],
            options={
                'db_table': 'model_params',
            },
        ),
        migrations.CreateModel(
            name='ModelUsers',
            fields=[
                ('uid', models.TextField(unique=True)),
                ('nth', models.IntegerField()),
                ('skill', models.FloatField()),
                ('skill_25', models.FloatField()),
                ('skill_75', models.FloatField()),
            ],
            options={
                'db_table': 'model_users',
            },
        ),
        migrations.CreateModel(
            name='QueryShorthands',
            fields=[
                ('name', models.TextField(unique=True)),
                ('command', models.TextField()),
                ('userid', models.TextField()),
                ('timestamp', models.TextField()),
            ],
            options={
                'db_table': 'query_shorthands',
            },
        ),
    ]
