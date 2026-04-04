from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkLogViewSet, TaskViewSet, UserViewSet, NotificationViewSet, TaskAttachmentViewSet

router = DefaultRouter()
router.register(r'worklog', WorkLogViewSet, basename='worklog')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'users', UserViewSet, basename='user')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'attachments', TaskAttachmentViewSet, basename='attachment')

urlpatterns = [
    path('', include(router.urls)),
]