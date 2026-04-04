#!/usr/bin/env python
"""
Скрипт для создания тестовых данных для системы загрузки отчётов
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '/c/Users/Zefir/Desktop/Study/KOD_BKR-copy7/server_app')

django.setup()

from django.contrib.auth.models import User
from api.models import Task, EmployeeProfile

def create_test_data():
    """Создать тестовые данные"""
    
    # 1. Создать тестового пользователя (сотрудника)
    print("1️⃣ Создание тестового пользователя...")
    try:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Тест',
            last_name='Пользователь',
            password='123456'
        )
        print(f"   ✅ Пользователь создан: {user.username}")
        
        # Создать профиль сотрудника
        profile = EmployeeProfile.objects.create(
            user=user,
            personnel_number='TEST001',
            position='Тестовая должность',
            department='QA'
        )
        print(f"   ✅ Профиль сотрудника создан: {profile.personnel_number}")
    except Exception as e:
        print(f"   ⚠️ Пользователь уже существует или ошибка: {e}")
        user = User.objects.filter(username='testuser').first()
    
    # 2. Создать тестовую задачу
    print("\n2️⃣ Создание тестовой задачи...")
    try:
        task = Task.objects.create(
            user=user,
            title='Тестовая задача для загрузки отчётов',
            description='Это задача для тестирования системы загрузки файлов. Нажмите кнопку 📎 Файлы для загрузки отчёта.',
            created_by=user
        )
        print(f"   ✅ Задача создана: {task.title}")
    except Exception as e:
        print(f"   ⚠️ Задача уже существует: {e}")
    
    print("\n✨ Тестовые данные подготовлены!")
    print("\nДанные для входа в приложение:")
    print("   Логин: testuser")
    print("   Пароль: 123456")
    print("\nДанные для админ-панели:")
    print("   Логин: admin")
    print("   Пароль: (оставить пустым)")

if __name__ == '__main__':
    create_test_data()
