from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="anti_afk_enabled",
            field=models.BooleanField(
                default=False,
                verbose_name="Включить Anti-AFK для сотрудника",
            ),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="anti_afk_idle_minutes",
            field=models.PositiveIntegerField(
                default=15,
                verbose_name="Минут бездействия до предупреждения (Anti-AFK)",
            ),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="anti_afk_grace_seconds",
            field=models.PositiveIntegerField(
                default=30,
                verbose_name="Секунды обратного отсчета перед авто-паузой (Anti-AFK)",
            ),
        ),
    ]

