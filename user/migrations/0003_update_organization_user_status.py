# Generated manually to update OrganizationUser status choices

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0002_remove_organizationuser_joined_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organizationuser",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "待审核"),
                    ("approved", "已通过"),
                    ("rejected", "未通过"),
                ],
                default="pending",
                max_length=20,
                verbose_name="认证状态",
            ),
        ),
    ]