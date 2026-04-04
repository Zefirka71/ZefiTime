#!/usr/bin/env python
"""
Скрипт для восстановления базы данных с исходными данными
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from django.contrib.auth.models import User
from api.models import Task, EmployeeProfile, GlobalSettings

def restore_database():
    """Восстановить БД с исходными данными"""
    
    print("🔄 Восстановление базы данных...\n")
    
    # 1. Создать настройки компании
    print("1️⃣ Создание настроек компании...")
    settings, created = GlobalSettings.objects.get_or_create(
        id=1,
        defaults={'company_name': 'ООО Моя Компания'}
    )
    print(f"   ✅ Компания: {settings.company_name}\n")
    
    # 2. Создать админа
    print("2️⃣ Создание администратора...")
    try:
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@company.local',
            password='admin123',
            first_name='Администратор',
            last_name='Системы'
        )
        print(f"   ✅ Администратор создан (пароль: admin123)\n")
    except Exception as e:
        print(f"   ⚠️ Админ уже существует\n")
        admin_user = User.objects.get(username='admin')
    
    # 3. Создать тестовых сотрудников
    print("3️⃣ Создание сотрудников...")
    employees_data = [
        {'personnel': '001', 'first': 'Иван', 'last': 'Петров', 'pos': 'Разработчик', 'dept': 'IT'},
        {'personnel': '002', 'first': 'Мария', 'last': 'Сидорова', 'pos': 'Дизайнер', 'dept': 'Дизайн'},
        {'personnel': '003', 'first': 'Петр', 'last': 'Иванов', 'pos': 'Менеджер', 'dept': 'Управление'},
        {'personnel': '004', 'first': 'Анна', 'last': 'Смирнова', 'pos': 'QA', 'dept': 'QA'},
        {'personnel': '005', 'first': 'Тесто', 'last': 'Вый', 'pos': 'Тестировщик', 'dept': 'QA'},
    ]
    
    users = {}
    for emp in employees_data:
        try:
            user = User.objects.create_user(
                username=emp['personnel'],
                email=f"{emp['personnel']}@company.local",
                password='12345678',
                first_name=emp['first'],
                last_name=emp['last']
            )
            
            # Создать профиль сотрудника
            EmployeeProfile.objects.create(
                user=user,
                personnel_number=emp['personnel'],
                position=emp['pos'],
                department=emp['dept']
            )
            
            users[emp['personnel']] = user
            print(f"   ✅ {emp['first']} {emp['last']} ({emp['personnel']})")
        except Exception as e:
            print(f"   ⚠️ {emp['first']} {emp['last']} уже существует")
            users[emp['personnel']] = User.objects.get(username=emp['personnel'])
    
    print()
    
    # 4. Создать тестовые задачи
    print("4️⃣ Создание тестовых задач...")
    
    for personnel, user in list(users.items())[:3]:
        tasks = [
            {
                'title': f'Задача 1 для {user.first_name}',
                'description': f'Это первая задача для {user.first_name}. Нажмите кнопку 📎 Файлы для тестирования загрузки отчётов.',
            },
            {
                'title': f'Задача 2 для {user.first_name}',
                'description': f'Это вторая задача для {user.first_name}. Здесь можно загружать файлы.',
            },
        ]
        
        for task_data in tasks:
            try:
                Task.objects.create(
                    user=user,
                    title=task_data['title'],
                    description=task_data['description'],
                    created_by=admin_user
                )
            except:
                pass
        
        print(f"   ✅ Задачи для {user.first_name} созданы")
    
    print("\n" + "="*60)
    print("✨ БАЗА ДАННЫХ ВОССТАНОВЛЕНА!")
    print("="*60)
    print("\n📝 ВАЖНО! Данные для входа:\n")
    print("👨‍💼 Сотрудники (все используют пароль: 12345678):")
    for emp in employees_data:
        print(f"   Логин: {emp['personnel']:>3} | {emp['first']} {emp['last']}")
    
    print("\n🔐 Администратор:")
    print(f"   Логин: admin")
    print(f"   Пароль: admin123")
    print(f"   Веб-панель: http://127.0.0.1:8000/admin/")
    print("\n" + "="*60)

if __name__ == '__main__':
    restore_database()
