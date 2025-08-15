# Generated manually to fix field name mismatch
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_alter_user_avatar_field'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE organization_user CHANGE joined_at created_at datetime(6) NOT NULL;",
            reverse_sql="ALTER TABLE organization_user CHANGE created_at joined_at datetime(6) NOT NULL;"
        ),
    ]