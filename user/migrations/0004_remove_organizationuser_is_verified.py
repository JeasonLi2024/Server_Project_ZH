# Generated manually on 2025-08-08 16:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0003_update_organization_user_status"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="organizationuser",
            name="is_verified",
        ),
    ]