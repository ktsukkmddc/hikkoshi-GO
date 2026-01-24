from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0004_remove_message_group_message_move_info"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
    ]