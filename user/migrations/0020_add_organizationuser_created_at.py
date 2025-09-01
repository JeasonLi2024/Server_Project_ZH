# Generated manually to add missing created_at field

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0019_add_organizationuser_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationuser',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name='创建时间'
            ),
            preserve_default=False,
        ),
    ]