import sqlite3
import uuid
from datetime import datetime

from modules.app_paths import local_data_db_path


class DatabaseManager:
    def __init__(self, db_name=None):
        self.db_name = db_name if db_name is not None else local_data_db_path()
        self.create_tables()

    def create_tables(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Таблица событий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS work_logs (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    readable_time TEXT NOT NULL,
                    is_synced INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица настроек (Имя, Токен, Тема и т.д.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Таблица задач (для будущего дашборда)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    status TEXT DEFAULT 'pending', -- pending, done
                    created_at TEXT
                )
            ''')
            conn.commit()

    # --- УНИВЕРСАЛЬНЫЕ МЕТОДЫ НАСТРОЕК ---
    
    def get_setting(self, key):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def set_setting(self, key, value):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    # --- МЕТОДЫ ЛОГОВ ---
    def log_event(self, event_type):
        event_id = str(uuid.uuid4())
        now = datetime.now()
        timestamp = now.timestamp()
        readable_time = now.strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO work_logs VALUES (?, ?, ?, ?, 0)', 
                           (event_id, event_type, timestamp, readable_time))
            conn.commit()

    def get_unsynced_logs(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM work_logs WHERE is_synced = 0')
            return cursor.fetchall()

    def get_weekly_hours(self):
        """Получить часы работы за последние 7 дней с правильной привязкой к датам"""
        from datetime import datetime, timedelta
        
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            
            # Получаем ВСЕ логи
            cursor.execute('''
                SELECT timestamp, event_type FROM work_logs 
                ORDER BY timestamp
            ''')
            
            logs = cursor.fetchall()
        
        # Инициализируем словарь дней с нулевыми часами
        days_dict = {}
        now = datetime.now()
        day_labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        
        # Находим диапазон дат (от первого лога до сегодня или последние 7 дней)
        min_date = None
        max_date = now.date()
        
        if logs:
            min_date = datetime.fromtimestamp(logs[0][0]).date()
        
        # Если логи есть, начинаем с даты первого лога, иначе с последних 7 дней
        if min_date:
            start_date = min_date
        else:
            start_date = now.date() - timedelta(days=6)
        
        # Заполняем словарь всеми днями от start_date до max_date
        current_date = start_date
        while current_date <= max_date:
            day_key = current_date.strftime('%Y-%m-%d')
            days_dict[day_key] = 0
            current_date += timedelta(days=1)
        
        # Подсчитываем часы между start/resume и stop/pause событиями
        current_start = None
        for timestamp, event_type in logs:
            log_datetime = datetime.fromtimestamp(timestamp)
            log_date_key = log_datetime.date().strftime('%Y-%m-%d')
            
            event_lower = event_type.lower() if event_type else ''
            
            if event_lower in ['start', 'resume']:
                current_start = timestamp
            elif event_lower in ['stop', 'pause'] and current_start:
                hours_worked = (timestamp - current_start) / 3600
                if log_date_key in days_dict:
                    days_dict[log_date_key] += hours_worked
                current_start = None
        
        # Преобразуем в список часов с правильными днями недели
        hours = []
        labels = []
        for date_key in sorted(days_dict.keys()):
            day_obj = datetime.strptime(date_key, '%Y-%m-%d').date()
            weekday_idx = day_obj.weekday()
            label = day_labels[weekday_idx]
            labels.append(label)
            hours.append(round(days_dict[date_key], 2))
        
        # Берем последние 7 дней для отображения
        if len(hours) > 7:
            hours = hours[-7:]
            labels = labels[-7:]
        
        return hours

    def mark_logs_as_synced(self, event_ids):
        if not event_ids: return
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            query = f"UPDATE work_logs SET is_synced = 1 WHERE event_id IN ({','.join(['?']*len(event_ids))})"
            cursor.execute(query, event_ids)
            conn.commit()

    def sync_log_from_server(self, event_type, timestamp):
        """Сохранить лог, полученный с сервера (избегаем дублей)"""
        event_id = str(uuid.uuid4())
        readable_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            # Проверяем по timestamp И event_type - это уникальная комбинация
            cursor.execute(
                'SELECT COUNT(*) FROM work_logs WHERE ABS(timestamp - ?) < 1 AND event_type = ?', 
                (timestamp, event_type)
            )
            if cursor.fetchone()[0] == 0:
                # Логируем только если этого лога еще нет
                cursor.execute('INSERT INTO work_logs VALUES (?, ?, ?, ?, 1)', 
                              (event_id, event_type, timestamp, readable_time))
                conn.commit()
                return True
        return False
            
    # --- МЕТОДЫ ЗАДАЧ (НОВОЕ) ---
    def add_task(self, text):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute("INSERT INTO tasks (text, status, created_at) VALUES (?, 'pending', ?)", (text, created_at))
            conn.commit()
            
    def get_tasks(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, text, status FROM tasks ORDER BY id DESC")
            return cursor.fetchall()
            
    def delete_task(self, task_id):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            conn.commit()