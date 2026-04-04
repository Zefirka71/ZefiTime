from rest_framework import serializers
from django.contrib.auth.models import User
from .models import WorkLog, Task, EmployeeProfile, Notification, TaskAttachment

class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для личного кабинета"""
    full_name = serializers.SerializerMethodField()
    personnel_number = serializers.CharField(source='profile.personnel_number', read_only=True)
    position = serializers.CharField(source='profile.position', read_only=True)
    department = serializers.CharField(source='profile.department', read_only=True)
    # Настройки Anti-AFK с профиля сотрудника
    anti_afk_enabled = serializers.BooleanField(source='profile.anti_afk_enabled', read_only=True)
    anti_afk_idle_minutes = serializers.IntegerField(source='profile.anti_afk_idle_minutes', read_only=True)
    anti_afk_grace_seconds = serializers.IntegerField(source='profile.anti_afk_grace_seconds', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'full_name',
            'personnel_number',
            'position',
            'department',
            'anti_afk_enabled',
            'anti_afk_idle_minutes',
            'anti_afk_grace_seconds',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

class WorkLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLog
        fields = ['id', 'event', 'timestamp', 'created_at']
        read_only_fields = ['id', 'created_at']

class TaskSerializer(serializers.ModelSerializer):
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'deadline', 'is_completed', 'is_overdue', 'created_at', 'created_by']
        read_only_fields = ['id', 'created_at', 'created_by', 'is_overdue']
    
    def get_is_overdue(self, obj):
        """Проверяет, просрочена ли задача"""
        if obj.deadline and not obj.is_completed:
            from django.utils import timezone
            return timezone.now() > obj.deadline
        return False

class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TaskAttachment
        fields = ['id', 'task', 'file', 'original_filename', 'uploaded_by', 'uploaded_by_username', 'created_at', 'file_size', 'file_size_mb', 'download_url']
        read_only_fields = ['id', 'created_at', 'uploaded_by', 'file_size']
    
    def get_file_size_mb(self, obj):
        """Получить размер файла в МБ"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_download_url(self, obj):
        """Получить URL для скачивания файла"""
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(f'/api/attachments/{obj.id}/download/')
        return None

class NotificationSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True, allow_null=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'task', 'task_title', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']

    
    def get_file_size_mb(self, obj):
        """Получить размер файла в МБ"""
        return obj.get_file_size_mb()
    
    def get_file_url(self, obj):
        """Получить URL для скачивания файла"""
        if obj.file:
            from rest_framework.reverse import reverse
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/attachments/{obj.id}/download/')
        return None