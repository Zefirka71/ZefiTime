from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
class GlobalSettings(models.Model):
    company_name = models.CharField(max_length=200, default="Моя Компания", verbose_name="Название организации")
    
    def __str__(self):
        return self.company_name

    class Meta:
        verbose_name = "Настройки системы"
        verbose_name_plural = "Настройки системы"

# --- ПРОФИЛЬ СОТРУДНИКА ---
class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Пользователь")
    personnel_number = models.CharField(max_length=20, verbose_name="Табельный номер (Логин)", unique=True)
    position = models.CharField(max_length=100, verbose_name="Должность")
    department = models.CharField(max_length=100, verbose_name="Отдел", blank=True)
    # Настройки Anti-AFK для конкретного сотрудника
    anti_afk_enabled = models.BooleanField(default=False, verbose_name="Включить Anti-AFK для сотрудника")
    anti_afk_idle_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name="Минут бездействия до предупреждения (Anti-AFK)"
    )
    anti_afk_grace_seconds = models.PositiveIntegerField(
        default=30,
        verbose_name="Секунды обратного отсчета перед авто-паузой (Anti-AFK)"
    )
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name="Последняя активность")

    def __str__(self):
        return f"{self.personnel_number} ({self.user.get_full_name()})"
    
    def is_online(self):
        """Считаем онлайн если активность была менее 5 минут назад"""
        if not self.last_activity:
            return False
        from datetime import timedelta
        return (timezone.now() - self.last_activity) < timedelta(minutes=5)
    
    class Meta:
        verbose_name = "Профиль сотрудника"
        verbose_name_plural = "Профили сотрудников"

# --- ЛОГИ ---
class WorkLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs', verbose_name="Сотрудник")
    event = models.CharField(max_length=20, verbose_name="Событие")
    timestamp = models.FloatField(verbose_name="Метка времени")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    client_version = models.CharField(max_length=10, blank=True, null=True, verbose_name="Версия ПО")

    class Meta:
        verbose_name = "Рабочий лог"
        verbose_name_plural = "Рабочие логи"

    def __str__(self):
        return f"{self.user.username} -> {self.event}"

# --- ЗАДАЧИ ---
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Сотрудник")
    title = models.CharField(max_length=200, verbose_name="Задача")
    description = models.TextField(blank=True, verbose_name="Описание")
    deadline = models.DateTimeField(null=True, blank=True, verbose_name="Срок сдачи")
    is_completed = models.BooleanField(default=False, verbose_name="Выполнено")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tasks', verbose_name="Создано пользователем")

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"

# --- ВЛОЖЕНИЯ К ЗАДАЧАМ ---
class TaskAttachment(models.Model):
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.csv', '.xlsx'}
    BLOCKED_EXTENSIONS = {'.exe', '.bat', '.sh', '.py'}
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments', verbose_name="Задача")
    file = models.FileField(upload_to='task_attachments/%Y/%m/%d/%H%M%S/', verbose_name="Файл")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Загружено")
    original_filename = models.CharField(max_length=255, verbose_name="Оригинальное имя файла")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    file_size = models.PositiveIntegerField(help_text="Размер файла в байтах", verbose_name="Размер")

    class Meta:
        verbose_name = "Вложение к задаче"
        verbose_name_plural = "Вложения к задачам"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} ({self.task.title})"
    
    @staticmethod
    def validate_extension(filename):
        """Проверить расширение файла"""
        import os
        ext = os.path.splitext(filename)[1].lower()
        
        # Сначала проверяем черный список
        if ext in TaskAttachment.BLOCKED_EXTENSIONS:
            return False, f"Расширение {ext} запрещено по соображениям безопасности"
        
        # Потом проверяем белый список
        if ext not in TaskAttachment.ALLOWED_EXTENSIONS:
            return False, f"Расширение {ext} не разрешено. Допустимые: {', '.join(TaskAttachment.ALLOWED_EXTENSIONS)}"
        
        return True, ""
    
    @staticmethod
    def validate_file_size(file_size, max_size_mb=10):
        """Проверить размер файла"""
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"Размер файла превышает {max_size_mb}MB"
        return True, ""

# --- УВЕДОМЛЕНИЯ ---
class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('new_task', 'Новая задача'),
        ('task_overdue', 'Просроченная задача'),
        ('task_completed', 'Задача выполнена'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="Сотрудник")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='notifications', verbose_name="Задача", null=True, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='new_task', verbose_name="Тип уведомления")
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Сообщение")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ['-created_at']

    def __str__(self):
        return f"Уведомление для {self.user.username}: {self.title}"

# Сигналы
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Task)
def create_notification_for_new_task(sender, instance, created, **kwargs):
    """Создаёт уведомление для сотрудника при создании новой задачи"""
    if created:
        Notification.objects.create(
            user=instance.user,
            task=instance,
            notification_type='new_task',
            title=f'Новая задача: {instance.title}',
            message=f'Вам назначена новая задача: {instance.title}' + 
                   (f' с дедлайном {instance.deadline.strftime("%d.%m.%Y %H:%M")}' if instance.deadline else '')
        )