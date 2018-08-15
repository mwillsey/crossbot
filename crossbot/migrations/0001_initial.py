# Generated by Django 2.1 on 2018-08-15 17:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CrosswordTime',
            fields=[
                ('rowid', models.AutoField(primary_key=True, serialize=False)),
                ('userid', models.CharField(max_length=10)),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(null=True)),
            ],
            options={
                'db_table': 'crossword_time',
            },
        ),
        migrations.CreateModel(
            name='EasySudokuTime',
            fields=[
                ('rowid', models.AutoField(primary_key=True, serialize=False)),
                ('userid', models.CharField(max_length=10)),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(null=True)),
            ],
            options={
                'db_table': 'easy_sudoku_time',
            },
        ),
        migrations.CreateModel(
            name='MiniCrosswordTime',
            fields=[
                ('rowid', models.AutoField(primary_key=True, serialize=False)),
                ('userid', models.CharField(max_length=10)),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(null=True)),
            ],
            options={
                'db_table': 'mini_crossword_time',
            },
        ),
        migrations.CreateModel(
            name='QueryShorthands',
            fields=[
                ('rowid', models.AutoField(primary_key=True, serialize=False)),
                ('userid', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=100)),
                ('command', models.TextField()),
                ('timestamp', models.DateTimeField(null=True)),
            ],
            options={
                'db_table': 'query_shorthands',
            },
        ),
    ]
