# Generated manually to add missing updated_at field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0018_remove_tag2_tag_2_post_a2db1b_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationuser',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
    ]