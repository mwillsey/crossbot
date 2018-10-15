from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('crossbot', '0001_setup_old_schema'),
    ]

    operations = [
        migrations.AddField(
            model_name=model_name,
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'))
        for model_name in [
            'CrosswordTime',
            'EasySudokuTime',
            'MiniCrosswordModel',
            'MiniCrosswordTime',
            'ModelDates',
            'ModelParams',
            'ModelUsers',
            'QueryShorthands',
        ]
    ]
