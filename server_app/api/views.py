from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import WorkLog, Task, EmployeeProfile, GlobalSettings, Notification, TaskAttachment
from .serializers import WorkLogSerializer, TaskSerializer, UserProfileSerializer, NotificationSerializer, TaskAttachmentSerializer
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum

class UserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        # Обновляем last_activity
        if hasattr(request.user, 'profile'):
            request.user.profile.last_activity = timezone.now()
            request.user.profile.save(update_fields=['last_activity'])
        
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def company_info(self, request):
        """Получить информацию о компании из GlobalSettings"""
        settings = GlobalSettings.objects.first()
        if settings:
            return Response({"company_name": settings.company_name})
        return Response({"company_name": "ООО Моя Компания"})

    # --- НОВЫЙ МЕТОД ДЛЯ ДАШБОРДА ---
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        user = request.user
        now = timezone.now()
        
        # 1. Статистика задач
        total_tasks = Task.objects.filter(user=user).count()
        completed_tasks = Task.objects.filter(user=user, is_completed=True).count()
        
        # 2. Часы за последние 7 дней (для столбчатой диаграммы)
        last_7_days = {}
        for i in range(6, -1, -1):
            day = now.date() - timedelta(days=i)
            last_7_days[day.strftime('%d.%m')] = 0 
            
        # Реальный подсчет часов требует сложной агрегации, 
        # сделаем пока возврат задач, а часы посчитаем на клиенте из логов или упростим
        
        return Response({
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "active": total_tasks - completed_tasks
            },
            "chart_days": list(last_7_days.keys()) 
            # Значения часов для простоты пока будем брать из WorkLogs на клиенте
        })

class WorkLogViewSet(viewsets.ModelViewSet):
    serializer_class = WorkLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkLog.objects.filter(user=self.request.user).order_by('-timestamp')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user).order_by('-id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)
    
    def perform_destroy(self, instance):
        # Пользователь может удалить только задачу, которую он сам создал
        if instance.created_by != self.request.user:
            raise permissions.PermissionDenied("Вы можете удалить только задачи, которые создали сами")
        instance.delete()

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Получить количество непрочитанных уведомлений"""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Отметить все уведомления как прочитанные"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'success'})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Отметить уведомление как прочитанное"""
        notification = self.get_object()
        if notification.user != request.user:
            raise permissions.PermissionDenied()
        notification.is_read = True
        notification.save()
        return Response({'status': 'success'})

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise permissions.PermissionDenied()
        instance.delete()


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Получить вложения для задач текущего пользователя или созданных им"""
        user = self.request.user
        task_id = self.request.query_params.get('task_id')
        
        if task_id:
            # Получить вложения конкретной задачи
            attachments = TaskAttachment.objects.filter(task_id=task_id)
            # Проверяем доступ: пользователь должен быть либо ответственным за задачу, либо её создателем
            task = Task.objects.get(id=task_id)
            if task.user != user and task.created_by != user:
                attachments = TaskAttachment.objects.none()
            return attachments
        
        # Если task_id не указан, получить все вложения задач пользователя
        return TaskAttachment.objects.filter(task__user=user) | TaskAttachment.objects.filter(task__created_by=user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Загрузить файл к задаче"""
        task_id = request.POST.get('task_id') or request.data.get('task_id')
        file = request.FILES.get('file')
        
        if not task_id or not file:
            return Response({'error': 'task_id и file обязательны'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return Response({'error': 'Задача не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем доступ
        if task.user != request.user and task.created_by != request.user:
            return Response({'error': 'Нет доступа к этой задаче'}, status=status.HTTP_403_FORBIDDEN)
        
        # Валидация расширения
        is_valid, error_msg = TaskAttachment.validate_extension(file.name)
        if not is_valid:
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Валидация размера
        is_valid, error_msg = TaskAttachment.validate_file_size(file.size, max_size_mb=10)
        if not is_valid:
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Создаём вложение
        try:
            attachment = TaskAttachment.objects.create(
                task=task,
                file=file,
                uploaded_by=request.user,
                original_filename=file.name,
                file_size=file.size
            )
            
            serializer = self.get_serializer(attachment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            print(f"Error creating attachment: {e}")
            traceback.print_exc()
            return Response({'error': f'Ошибка при сохранении файла: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Скачать файл"""
        try:
            attachment = self.get_object()
        except TaskAttachment.DoesNotExist:
            return Response({'error': 'Файл не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем доступ
        task = attachment.task
        if task.user != request.user and task.created_by != request.user:
            return Response({'error': 'Нет доступа к этому файлу'}, status=status.HTTP_403_FORBIDDEN)
        
        # Скачиваем файл
        if not attachment.file:
            return Response({'error': 'Файл не существует'}, status=status.HTTP_404_NOT_FOUND)
        
        from django.http import FileResponse

        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_filename,
        )
    
    @action(detail=False, methods=['get'])
    def by_task(self, request):
        """Получить все вложения для конкретной задачи"""
        task_id = request.query_params.get('task_id')
        
        if not task_id:
            return Response({'error': 'task_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return Response({'error': 'Задача не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем доступ
        if task.user != request.user and task.created_by != request.user:
            return Response({'error': 'Нет доступа к этой задаче'}, status=status.HTTP_403_FORBIDDEN)
        
        # Получаем вложения
        attachments = TaskAttachment.objects.filter(task=task).order_by('-created_at')
        serializer = self.get_serializer(attachments, many=True)
        return Response(serializer.data)
    
    def perform_destroy(self, instance):
        """Удалить вложение"""
        task = instance.task
        # Проверяем доступ - может удалить тот кто создал или тот кому назначена задача
        if task.user != self.request.user and task.created_by != self.request.user:
            raise permissions.PermissionDenied()
        
        # Удаляем физический файл если существует
        if instance.file:
            instance.file.delete()
        
        instance.delete()