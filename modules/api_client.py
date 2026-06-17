import requests
from requests.auth import HTTPBasicAuth


class APIClient:
    def __init__(self, server_url, login, password):
        raw = (server_url or "").strip()
        scheme = "http"
        if raw.lower().startswith("https://"):
            scheme = "https"
            raw = raw[8:]
        elif raw.lower().startswith("http://"):
            scheme = "http"
            raw = raw[7:]
        host_part = raw.split("/", 1)[0].strip()
        self.base_url = f"{scheme}://{host_part}"

        self.auth = HTTPBasicAuth(login, password)
        self.is_connected = False
        self.session = requests.Session()
        self.session.auth = self.auth
        # Явно запрашиваем сжатие ответов; requests автоматически распакует их.
        self.session.headers.update({
            "Accept": "application/json, */*",
            "Accept-Encoding": "gzip, deflate",
        })

    def check_connection(self):
        """Проверка связи с сервером"""
        try:
            response = self.session.get(f"{self.base_url}/api/users/me/", timeout=3)
            self.is_connected = (response.status_code == 200)
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def get_profile(self):
        """Получение данных сотрудника"""
        if not self.is_connected: return None
        try:
            response = self.session.get(f"{self.base_url}/api/users/me/", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def upload_logs(self, logs):
        """Отправка логов на сервер. logs - это список кортежей из БД"""
        if not self.is_connected: return []
        url = f"{self.base_url}/api/worklog/"
        synced_ids = []
        
        for log in logs:
            # В database.py порядок полей: event_id(0), event_type(1), timestamp(2)...
            # Поэтому берем log[0] (ID), log[1] (тип) и log[2] (timestamp)
            payload = {
                "event": log[1], 
                "timestamp": log[2]
            }
            try:
                r = self.session.post(url, json=payload, timeout=2)
                if r.status_code == 201:
                    synced_ids.append(log[0])  # Добавляем event_id успешно отправленного лога
            except:
                # Если ошибка сети при отправке одного лога - прерываем цикл
                break
        
        return synced_ids

    def get_tasks(self):
        """Получение списка задач"""
        if not self.is_connected: return []
        try:
            response = self.session.get(f"{self.base_url}/api/tasks/", timeout=5)
            if response.status_code == 200:
                tasks = response.json()
                # Получаем текущего пользователя чтобы определить может ли он удалять задачи
                profile = self.get_profile()
                if profile:
                    user_id = profile.get('id')
                    for task in tasks:
                        # can_delete = True если created_by == user_id
                        task['can_delete'] = task.get('created_by') == user_id
                return tasks
        except:
            pass
        return []

    def create_task(self, title, description=""):
        """Создание новой задачи"""
        if not self.is_connected: return False
        url = f"{self.base_url}/api/tasks/"
        payload = {"title": title, "description": description, "is_completed": False}
        try:
            response = self.session.post(url, json=payload, timeout=5)
            return response.status_code == 201
        except Exception as e:
            print(f"Error create_task: {e}")
            return False

    def update_task_status(self, task_id, is_completed):
        """Обновление статуса задачи"""
        if not self.is_connected: return False
        url = f"{self.base_url}/api/tasks/{task_id}/"
        payload = {"is_completed": is_completed}
        try:
            self.session.patch(url, json=payload, timeout=5)
        except:
            pass

    def delete_task(self, task_id):
        """Удаление задачи (только если пользователь её создал)"""
        if not self.is_connected: return False
        url = f"{self.base_url}/api/tasks/{task_id}/"
        try:
            response = self.session.delete(url, timeout=5)
            return response.status_code == 204
        except Exception as e:
            print(f"Error delete_task: {e}")
            return False

    def get_dashboard_stats(self):
        """Получение статистики для графиков"""
        if not self.is_connected: return {}
        try:
            response = self.session.get(f"{self.base_url}/api/users/dashboard_stats/", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Stats Error: {e}")
        return {}
    
    def sync_logs_from_server(self, db_manager):
        """Синхронизировать логи с сервера на локальную БД"""
        if not self.is_connected: return False
        try:
            response = self.session.get(f"{self.base_url}/api/worklog/", timeout=5)
            if response.status_code == 200:
                logs = response.json()
                # Сохраняем логи в локальную БД
                for log in logs:
                    # log содержит: id, user, event, timestamp, created_at, client_version
                    db_manager.sync_log_from_server(log['event'], log['timestamp'])
                print(f"✓ Синхронизировано {len(logs)} логов с сервера")
                return True
        except Exception as e:
            print(f"Sync logs error: {e}")
        return False
    
    def get_company_info(self):
        """Получить информацию о компании"""
        if not self.is_connected: return {"company_name": "ООО Моя Компания"}
        try:
            response = self.session.get(f"{self.base_url}/api/users/company_info/", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Company info error: {e}")
        return {"company_name": "ООО Моя Компания"}

    def get_notifications(self):
        """Получить все уведомления"""
        if not self.is_connected: return []
        try:
            response = self.session.get(f"{self.base_url}/api/notifications/", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Get notifications error: {e}")
        return []

    def get_unread_notifications_count(self):
        """Получить количество непрочитанных уведомлений"""
        if not self.is_connected: return 0
        try:
            response = self.session.get(f"{self.base_url}/api/notifications/unread_count/", timeout=5)
            if response.status_code == 200:
                return response.json().get('unread_count', 0)
        except Exception as e:
            print(f"Get unread count error: {e}")
        return 0

    def mark_notification_as_read(self, notification_id):
        """Отметить уведомление как прочитанное"""
        if not self.is_connected: return False
        url = f"{self.base_url}/api/notifications/{notification_id}/mark_as_read/"
        try:
            response = self.session.post(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Mark notification as read error: {e}")
        return False

    def mark_all_notifications_as_read(self):
        """Отметить все уведомления как прочитанные"""
        if not self.is_connected: return False
        url = f"{self.base_url}/api/notifications/mark_all_as_read/"
        try:
            response = self.session.post(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Mark all notifications as read error: {e}")
        return False

    def delete_notification(self, notification_id):
        """Удалить уведомление"""
        if not self.is_connected: return False
        url = f"{self.base_url}/api/notifications/{notification_id}/"
        try:
            response = self.session.delete(url, timeout=5)
            return response.status_code == 204
        except Exception as e:
            print(f"Delete notification error: {e}")
        return False

    # ===== РАБОТА С ПРИКРЕПЛЁННЫМИ ФАЙЛАМИ =====
    
    def get_task_attachments(self, task_id):
        """Получить список вложений для задачи"""
        if not self.is_connected: return []
        url = f"{self.base_url}/api/attachments/by_task/"
        try:
            params = {'task_id': task_id}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Get attachments error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"Get attachments error: {e}")
            return []
    
    def upload_task_attachment(self, task_id, file_path):
        """Загрузить файл к задаче"""
        if not self.is_connected: 
            raise Exception("Нет соединения с сервером")
        
        url = f"{self.base_url}/api/attachments/upload/"
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'task_id': task_id}
                response = self.session.post(url, files=files, data=data, timeout=30)
                
                print(f"Upload response status: {response.status_code}")
                print(f"Upload response: {response.text}")
                
                if response.status_code == 201:
                    return response.json()
                else:
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_text = error_json.get('error', error_text)
                    except:
                        pass
                    raise Exception(f"Ошибка сервера ({response.status_code}): {error_text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка соединения: {str(e)}")
        except Exception as e:
            print(f"Upload attachment error: {e}")
            raise
    
    def delete_task_attachment(self, attachment_id):
        """Удалить вложение задачи"""
        if not self.is_connected: return False
        url = f"{self.base_url}/api/attachments/{attachment_id}/"
        try:
            response = self.session.delete(url, timeout=10)
            return response.status_code == 204
        except Exception as e:
            print(f"Delete attachment error: {e}")
            return False
    
    def download_task_attachment(self, attachment_id, save_path=None):
        """Скачать файл задачи"""
        if not self.is_connected: return None
        url = f"{self.base_url}/api/attachments/{attachment_id}/download/"
        try:
            response = self.session.get(url, timeout=30, stream=True)
            if response.status_code == 200:
                if save_path:
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return True
                return response.content
            else:
                print(f"Download error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Download attachment error: {e}")
            return None