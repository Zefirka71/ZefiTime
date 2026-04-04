import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
import threading
import queue
from datetime import datetime, timedelta
import os
from PIL import Image

# Графики
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Наши модули
from modules.app_paths import resource_path
from modules.database import DatabaseManager
from modules.api_client import APIClient
from config import APP_NAME

# --- КОНФИГУРАЦИЯ ДИЗАЙНА (ZefiTime Theme) ---
THEME = {
    "bg_main": "#121212",          # Очень темный фон
    "bg_card": "#1E1E2E",          # Цвет карточек/панелей
    "sidebar": "#181825",          # Сайдбар
    "primary": "#7C3AED",          # Основной фиолетовый (кнопки)
    "primary_hover": "#6D28D9",    # Фиолетовый при наведении
    "text_main": "#FFFFFF",        # Белый текст
    "text_sec": "#A1A1AA",         # Серый текст
    "success": "#10B981",          # Зеленый
    "danger": "#EF4444",           # Красный
    "warning": "#F59E0B"           # Оранжевый
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue") # Базовая, но мы перекрасим элементы

class ZefiTimeApp:
    """Класс-менеджер, управляющий переключением окон"""
    def __init__(self):
        self.db = DatabaseManager()
        self.api = None
        self.user_data = None
        
        # Настройки подключения из БД
        self.saved_server = self.db.get_setting("server_url") or "127.0.0.1:8000"
        self.saved_login = self.db.get_setting("api_login") or ""
        
        self.show_login_window()

    def show_login_window(self):
        self.login_window = LoginWindow(self)
        self.login_window.mainloop()

    def show_dashboard(self):
        # Закрываем окно входа и открываем основное
        if hasattr(self, 'login_window'):
            self.login_window.destroy()
        
        # Очищаем старые логи при входе нового пользователя (чтобы не было кэша от других пользователей)
        import sqlite3
        with sqlite3.connect(self.db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_logs")
            conn.commit()
        
        self.dashboard = DashboardWindow(self)
        self.dashboard.mainloop()

# --- ОКНО АВТОРИЗАЦИИ ---
class LoginWindow(ctk.CTk):
    def __init__(self, app_manager):
        super().__init__()
        self.app = app_manager
        self.title(f"{APP_NAME} - Вход")
        self.geometry("400x550")
        self.configure(fg_color=THEME["bg_main"])
        self.resizable(False, False)
        
        # Установка иконки
        icon_path = resource_path("assets", "logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Логотип (картинка)
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(pady=(40, 20))
        
        # Если есть картинка логотипа
        logo_img_path = resource_path("assets", "logo.png")
        if os.path.exists(logo_img_path):
            img = ctk.CTkImage(Image.open(logo_img_path), size=(100, 100))
            lbl_img = ctk.CTkLabel(logo_frame, image=img, text="")
            lbl_img.pack()
        else:
            # Текстовый логотип, если картинки нет
            ctk.CTkLabel(logo_frame, text="Z", font=("Segoe UI", 60, "bold"), text_color=THEME["primary"]).pack()

        ctk.CTkLabel(self, text="ZefiTime", font=("Segoe UI", 28, "bold"), text_color=THEME["text_main"]).pack()
        ctk.CTkLabel(self, text="Вход в систему", font=("Segoe UI", 14), text_color=THEME["text_sec"]).pack(pady=(0, 20))

        # Поля ввода
        self.frame_inputs = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_inputs.pack(padx=40, fill="x")

        self.entry_server = self.create_input("Адрес сервера", self.app.saved_server)
        self.entry_login = self.create_input("Табельный номер", self.app.saved_login)
        self.entry_pass = self.create_input("Пароль", "", show="*")
        self.entry_pass.bind("<Return>", lambda e: self.perform_login())
        self.bind("<Return>", lambda e: self.perform_login())

        self.lbl_error = ctk.CTkLabel(self, text="", text_color=THEME["danger"], font=("Segoe UI", 12))
        self.lbl_error.pack(pady=5)

        self.btn_login = ctk.CTkButton(self, text="Войти", command=self.perform_login, height=45, 
                                       fg_color=THEME["primary"], hover_color=THEME["primary_hover"], 
                                       font=("Segoe UI", 14, "bold"), corner_radius=8)
        self.btn_login.pack(padx=40, pady=20, fill="x")

    def create_input(self, placeholder, value, show=None):
        entry = ctk.CTkEntry(self.frame_inputs, height=45, placeholder_text=placeholder, 
                             fg_color=THEME["bg_card"], border_color=THEME["bg_card"], 
                             text_color="white", show=show)
        if value: entry.insert(0, value)
        entry.pack(pady=5, fill="x")
        return entry

    def perform_login(self):
        server = self.entry_server.get().strip()
        login = self.entry_login.get().strip()
        pwd = self.entry_pass.get().strip()

        if not server or not login or not pwd:
            self.lbl_error.configure(text="Заполните все поля")
            return

        self.btn_login.configure(state="disabled", text="Подключение...")
        self.update()

        api = APIClient(server, login, pwd)
        if api.check_connection():
            # Сохраняем настройки
            self.app.db.set_setting("server_url", server)
            self.app.db.set_setting("api_login", login)
            # В реальном проекте пароль лучше не хранить так просто, или хранить токен
            
            self.app.api = api
            # Подгружаем профиль сразу
            profile = api.get_profile()
            self.app.user_data = profile if profile else {"full_name": login}
            
            self.app.show_dashboard()
        else:
            self.lbl_error.configure(text="Ошибка подключения или неверные данные")
            self.btn_login.configure(state="normal", text="Войти")


# --- ОКНО ДОБАВЛЕНИЯ НОВОЙ ЗАДАЧИ ---
class AddTaskWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Новая задача")
        self.geometry("500x480")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_main"])
        
        # Установка иконки - такая же как у главного приложения
        icon_path = resource_path("assets", "logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        # Центрируем окно относительно родителя
        self.transient(parent)
        self.grab_set()
        
        self.callback = callback
        self.result = None
        
        # --- Заголовок ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header, text="Создание новой задачи", 
            font=("Segoe UI", 18, "bold"), text_color=THEME["text_main"]
        ).pack(anchor="w")
        
        # --- Основной контент (для корректного скроллинга) ---
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Поле названия
        ctk.CTkLabel(
            content, text="Название задачи *",
            font=("Segoe UI", 12), text_color=THEME["text_sec"]
        ).pack(anchor="w", pady=(0, 5))
        
        self.title_entry = ctk.CTkEntry(
            content, placeholder_text="Введите название",
            fg_color=THEME["bg_card"], border_color="#404050",
            text_color=THEME["text_main"], height=40
        )
        self.title_entry.pack(fill="x", pady=(0, 15))
        
        # Поле описания
        ctk.CTkLabel(
            content, text="Описание задачи",
            font=("Segoe UI", 12), text_color=THEME["text_sec"]
        ).pack(anchor="w", pady=(0, 5))
        
        self.desc_entry = ctk.CTkTextbox(
            content, height=140, fg_color=THEME["bg_card"],
            border_color="#404050", text_color=THEME["text_main"],
            border_width=1
        )
        self.desc_entry.pack(fill="both", expand=True, pady=(0, 15))
        
        # --- Кнопки внизу (зафиксированы внизу окна) ---
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=20, side="bottom")
        
        btn_cancel = ctk.CTkButton(
            buttons, text="Отмена", width=110, height=38,
            fg_color="transparent", border_width=1, border_color="#555562",
            hover_color="#2D2D3A", text_color="#CCCCCC", font=("Segoe UI", 12),
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(10, 0))
        
        btn_create = ctk.CTkButton(
            buttons, text="Создать задачу", width=150, height=38,
            fg_color=THEME["primary"], hover_color=THEME["primary_hover"],
            font=("Segoe UI", 12, "bold"),
            command=self._on_create
        )
        btn_create.pack(side="right", padx=(0, 10))
        
        # Фокус на поле названия
        self.title_entry.focus()
        
        # Обработка Enter в поле названия
        self.title_entry.bind("<Return>", lambda e: self._on_create())
        
        # Обработка Enter в поле названия
        self.title_entry.bind("<Return>", lambda e: self._on_create())
    
    def _on_create(self):
        title = self.title_entry.get().strip()
        description = self.desc_entry.get("1.0", "end").strip()
        
        if not title:
            messagebox.showwarning("Ошибка", "Пожалуйста, введите название задачи")
            self.title_entry.focus()
            return
        
        self.result = {"title": title, "description": description}
        if self.callback:
            self.callback(self.result)
        self.destroy()


# --- МОДАЛЬНОЕ ОКНО ДЛЯ УПРАВЛЕНИЯ ВЛОЖЕНИЯМИ ЗАДАЧИ ---
class TaskAttachmentModalWindow(ctk.CTkToplevel):
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.csv', '.xlsx'}
    BLOCKED_EXTENSIONS = {'.exe', '.bat', '.sh', '.py'}
    
    def __init__(self, parent, api, task_id, task_title, on_refresh=None):
        super().__init__(parent)
        self.api = api
        self.task_id = task_id
        self.task_title = task_title
        self.on_refresh = on_refresh
        self.attachments = []
        
        # Конфигурация окна
        self.title(f"Вложения: {task_title}")
        self.geometry("600x500")
        self.configure(fg_color=THEME["bg_main"])
        self.resizable(True, True)
        self.attributes('-topmost', True)  # Всегда поверх
        
        # Заголовок
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(header, text=f"📎 Вложения к задаче", font=("Segoe UI", 16, "bold")).pack(side="left")
        
        # Список вложений
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Кнопки внизу
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkButton(button_frame, text="+ Добавить файл", command=self.add_file_dialog,
                      fg_color=THEME["primary"], hover_color=THEME["primary_hover"]).pack(side="left", padx=5)
        
        ctk.CTkButton(button_frame, text="Закрыть", command=self.destroy,
                      fg_color="#404050", hover_color="#505060").pack(side="right", padx=5)
        
        # Загружаем вложения
        self.load_attachments()
        
        # Выполнить плавное отображение
        self.after(100, self.focus)
    
    def load_attachments(self):
        """Загрузить список вложений для задачи"""
        # Очищаем предыдущий список
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        
        # Загружаем в фоновом потоке
        threading.Thread(target=self._load_attachments_thread, daemon=True).start()
    
    def _load_attachments_thread(self):
        """Получить вложения с сервера"""
        try:
            self.attachments = self.api.get_task_attachments(self.task_id)
            self.after(0, self._display_attachments)
        except Exception as e:
            print(f"Error loading attachments: {e}")
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось загрузить вложения: {e}"))
    
    def _display_attachments(self):
        """Отобразить загруженные вложения"""
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        
        if not self.attachments:
            ctk.CTkLabel(self.scroll_frame, text="Нет вложенных файлов", text_color="gray").pack(pady=20)
            return
        
        for attachment in self.attachments:
            self.draw_attachment_card(attachment)
    
    def draw_attachment_card(self, attachment):
        """Нарисовать карточку одного вложения"""
        card = ctk.CTkFrame(self.scroll_frame, fg_color=THEME["bg_card"], corner_radius=8,
                            border_width=1, border_color="#404050")
        card.pack(fill="x", pady=5)
        
        # Основной контент
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=10, expand=True)
        
        # Левая часть - информация о файле
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        # Имя файла
        ctk.CTkLabel(info_frame, text=f"📄 {attachment['original_filename']}", 
                     font=("Segoe UI", 12, "bold"), text_color="white", anchor="w").pack(fill="x", anchor="w")
        
        # Размер и время
        size_mb = attachment.get('file_size_mb', 0)
        created_at = attachment.get('created_at', '')
        if created_at:
            # Парсим время
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                time_str = dt.strftime("%d.%m.%Y %H:%M")
            except:
                time_str = created_at
        else:
            time_str = '-'
        
        meta_text = f"📦 {size_mb} МБ  |  📅 {time_str}"
        ctk.CTkLabel(info_frame, text=meta_text, font=("Segoe UI", 10), 
                     text_color="#888888", anchor="w").pack(fill="x", anchor="w", pady=(3, 0))
        
        # Правая часть - кнопки действий
        actions = ctk.CTkFrame(content, fg_color="transparent")
        actions.pack(side="right", padx=(10, 0))
        
        # Кнопка скачать
        ctk.CTkButton(actions, text="⬇ Скачать", width=80, height=30, corner_radius=6,
                      fg_color="transparent", border_width=1, border_color=THEME["primary"],
                      text_color=THEME["primary"], font=("Segoe UI", 10),
                      command=lambda aid=attachment['id']: self.download_file(aid, attachment['original_filename'])).pack(side="left", padx=5)
        
        # Кнопка удалить
        ctk.CTkButton(actions, text="✕ Удалить", width=80, height=30, corner_radius=6,
                      fg_color="transparent", border_width=1, border_color=THEME["danger"],
                      text_color=THEME["danger"], font=("Segoe UI", 10),
                      command=lambda aid=attachment['id']: self.delete_file(aid)).pack(side="left", padx=2)
    
    def add_file_dialog(self):
        """Открыть диалог выбора файла"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="Выберите файл для загрузки",
            filetypes=[
                ("Офисные форматы", "*.txt *.pdf *.docx *.csv *.xlsx"),
                ("Текстовые файлы", "*.txt"),
                ("PDF документы", "*.pdf"),
                ("Word документы", "*.docx"),
                ("CSV таблицы", "*.csv"),
                ("Excel таблицы", "*.xlsx"),
                ("Все файлы", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        # Валидация расширения
        import os
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in self.BLOCKED_EXTENSIONS:
            messagebox.showerror("Ошибка", f"Расширение {ext} запрещено по соображениям безопасности")
            return
        
        if ext not in self.ALLOWED_EXTENSIONS:
            messagebox.showerror("Ошибка", f"Расширение {ext} не разрешено.\nДопустимые: {', '.join(self.ALLOWED_EXTENSIONS)}")
            return
        
        # Проверка размера
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10 MB
            messagebox.showerror("Ошибка", "Размер файла превышает 10MB")
            return
        
        # Загружаем файл в фоновом потоке
        threading.Thread(target=self._upload_file_thread, args=(file_path,), daemon=True).start()
    
    def _upload_file_thread(self, file_path):
        """Загрузить файл на сервер"""
        try:
            result = self.api.upload_task_attachment(self.task_id, file_path)
            if result and result != False:
                self.after(0, lambda: messagebox.showinfo("Успех", f"Файл успешно загружен\n{result.get('original_filename', 'файл')}"))
                self.after(0, self.load_attachments)
                if self.on_refresh:
                    self.after(0, self.on_refresh)
            else:
                error_msg = "Не удалось загрузить файл. Проверьте соединение с сервером."
                self.after(0, lambda: messagebox.showerror("Ошибка", error_msg))
        except Exception as e:
            error_msg = str(e)
            print(f"Upload error: {e}")
            self.after(0, lambda: messagebox.showerror("Ошибка загрузки", f"Ошибка при загрузке файла:\n{error_msg}"))
    
    def download_file(self, attachment_id, filename):
        """Скачать файл"""
        from tkinter import filedialog
        import os
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(filename)[1],
            initialfile=filename,
            filetypes=[("Все файлы", "*.*")]
        )
        
        if not save_path:
            return
        
        threading.Thread(target=self._download_file_thread, args=(attachment_id, save_path, filename), daemon=True).start()
    
    def _download_file_thread(self, attachment_id, save_path, filename):
        """Скачать файл в фоновом потоке"""
        try:
            result = self.api.download_task_attachment(attachment_id, save_path)
            if result:
                self.after(0, lambda: messagebox.showinfo("Успех", f"Файл скачан: {save_path}"))
            else:
                self.after(0, lambda: messagebox.showerror("Ошибка", "Не удалось скачать файл"))
        except Exception as e:
            print(f"Download error: {e}")
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка при скачивании: {e}"))
    
    def delete_file(self, attachment_id):
        """Удалить файл"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить этот файл?"):
            threading.Thread(target=self._delete_file_thread, args=(attachment_id,), daemon=True).start()
    
    def _delete_file_thread(self, attachment_id):
        """Удалить файл с сервера"""
        try:
            result = self.api.delete_task_attachment(attachment_id)
            if result:
                self.after(0, lambda: messagebox.showinfo("Успех", "Файл удалён"))
                self.after(0, self.load_attachments)
                if self.on_refresh:
                    self.after(0, self.on_refresh)
            else:
                self.after(0, lambda: messagebox.showerror("Ошибка", "Не удалось удалить файл"))
        except Exception as e:
            print(f"Delete error: {e}")
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка при удалении: {e}"))


# --- ОСНОВНОЕ ОКНО ---
class DashboardWindow(ctk.CTk):
    def __init__(self, app_manager):
        super().__init__()
        self.app = app_manager
        self.title("ZefiTime - Dashboard")
        self.geometry("1100x700")
        self.configure(fg_color=THEME["bg_main"])
        
        icon_path = resource_path("assets", "logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.is_running = False
        self.start_time = None
        self.elapsed_time = 0

        # Настройки Anti-AFK из профиля пользователя
        profile = self.app.user_data or {}
        self.anti_afk_enabled = bool(profile.get("anti_afk_enabled", False))
        try:
            self.anti_afk_idle_minutes = int(profile.get("anti_afk_idle_minutes") or 15)
        except (TypeError, ValueError):
            self.anti_afk_idle_minutes = 15
        try:
            self.anti_afk_grace_seconds = int(profile.get("anti_afk_grace_seconds") or 30)
        except (TypeError, ValueError):
            self.anti_afk_grace_seconds = 30

        # Переводим в секунды и инициализируем состояние отслеживания
        self.anti_afk_idle_seconds = max(1, self.anti_afk_idle_minutes * 60)
        self.last_input_time = time.time()
        self._afk_warning_shown = False
        self._afk_window = None
        self._afk_countdown = 0

        # Сетка: Сайдбар (0) + Контент (1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_content_area()

        # Запуск таймеров
        self.update_timer_loop()
        self.check_connection_loop()
        self.check_notifications_loop()

        # Глобальные бинды для отслеживания активности пользователя (Anti-AFK)
        self.bind_all("<Key>", self._on_user_activity)
        self.bind_all("<Motion>", self._on_user_activity)
        self.bind_all("<Button>", self._on_user_activity)

        # Запускаем цикл проверки Anti-AFK
        self._start_anti_afk_loop()
        
        # Открываем первую вкладку
        self.show_dashboard_tab()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=THEME["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) # Фиксируем ширину

        # Лого
        sidebar_title = self._build_sidebar_title()
        ctk.CTkLabel(
            self.sidebar,
            text=sidebar_title,
            font=("Segoe UI", 18, "bold"),
            text_color=THEME["primary"],
            justify="center"
        ).pack(pady=(24, 28), padx=10)

        # Меню
        self.btn_menu_dash = self.create_menu_btn("📊 Дашборд", self.show_dashboard_tab)
        self.btn_menu_tracker = self.create_menu_btn("⏱ Трекер", self.show_tracker_tab)
        
        # Контейнер для кнопки задач с badge
        self.tasks_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.tasks_btn_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_menu_tasks = ctk.CTkButton(self.tasks_btn_frame, text="✓ Задачи", command=self.show_tasks_tab,
                                           fg_color="transparent", text_color=THEME["text_sec"], hover_color=THEME["bg_card"],
                                           anchor="w", height=45, font=("Segoe UI", 14), corner_radius=8)
        self.btn_menu_tasks.pack(side="left", fill="both", expand=True)
        
        # Badge для непрочитанных задач (маленький красный кружок)
        self.tasks_badge = ctk.CTkLabel(self.tasks_btn_frame, text="", font=("Segoe UI", 7, "bold"),
                                       fg_color=THEME["danger"], text_color="white", width=16, height=16,
                                       corner_radius=8)
        # По умолчанию скрываем
        self.tasks_badge.pack_forget()
        
        self.btn_menu_profile = self.create_menu_btn("👤 Профиль", self.show_profile_tab)

        # Статус соединения внизу
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.pack(side="bottom", pady=20, padx=20, fill="x")
        
        self.lbl_status_dot = ctk.CTkLabel(self.status_frame, text="●", font=("Arial", 16), text_color="gray")
        self.lbl_status_dot.pack(side="left")
        self.lbl_status_text = ctk.CTkLabel(self.status_frame, text="Offline", font=("Segoe UI", 12), text_color="gray")
        self.lbl_status_text.pack(side="left", padx=5)
        
        # Инициализируем badge
        self.update_tasks_badge()

    def _build_sidebar_title(self):
        """Сформировать заголовок в сайдбаре: ZefiTime + сотрудник."""
        profile = self.app.user_data or {}
        full_name = (profile.get("full_name") or "").strip()
        personnel_number = (profile.get("personnel_number") or "").strip()

        if full_name and personnel_number:
            return f"\n{full_name} ({personnel_number})"
        if full_name:
            return f"\n{full_name}"
        if personnel_number:
            return f"\nТаб. № {personnel_number}"
        return "ZefiTime"

    def create_menu_btn(self, text, cmd):
        btn = ctk.CTkButton(self.sidebar, text=text, command=cmd, 
                            fg_color="transparent", text_color=THEME["text_sec"], hover_color=THEME["bg_card"], 
                            anchor="w", height=45, font=("Segoe UI", 14), corner_radius=8)
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    def setup_content_area(self):
        self.main_area = ctk.CTkFrame(self, fg_color=THEME["bg_main"], corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def clear_content(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    # ==========================
    # Вкладка 1: ДАШБОРД (Статистика)
    # ==========================
    def show_dashboard_tab(self):
        self.clear_content()
        self.highlight_menu(self.btn_menu_dash)
        
        title = ctk.CTkLabel(self.main_area, text="Обзор эффективности", font=("Segoe UI", 24, "bold"), text_color="white")
        title.pack(anchor="w", pady=(0, 20))

        # Верхние карточки (Grid)
        cards_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        cards_frame.pack(fill="x", pady=10)

        # Получаем данные (в реале - из API)
        tasks = self.app.api.get_tasks() or []
        done = sum(1 for t in tasks if t['is_completed'])
        total = len(tasks)
        
        self.create_stat_card(cards_frame, "Всего задач", str(total), "#3B82F6", 0)
        self.create_stat_card(cards_frame, "Выполнено", str(done), "#10B981", 1)
        self.create_stat_card(cards_frame, "В работе", str(total - done), "#F59E0B", 2)
        
        # Графики (Matplotlib) - сохраняем ссылки на виджеты
        charts_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        charts_frame.pack(fill="both", expand=True, pady=20)
        
        # 1. Круговая диаграмма задач
        self.pie_chart_container = ctk.CTkFrame(charts_frame, fg_color=THEME["bg_card"], corner_radius=15)
        self.pie_chart_container.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.draw_pie_chart(self.pie_chart_container, done, total-done)
        
        # 2. Гистограмма часов - контейнер зафиксирован
        self.bar_chart_container = ctk.CTkFrame(charts_frame, fg_color=THEME["bg_card"], corner_radius=15)
        self.bar_chart_container.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.draw_bar_chart(self.bar_chart_container)
        
        # Синхронизируем логи с сервера и обновляем диаграмму
        def sync_and_refresh():
            self.app.api.sync_logs_from_server(self.app.db)
            # После синхронизации обновляем только содержимое контейнера
            self.after(500, self.refresh_bar_chart)
        
        threading.Thread(target=sync_and_refresh, daemon=True).start()

    def create_stat_card(self, parent, title, value, color, col_idx):
        card = ctk.CTkFrame(parent, fg_color=THEME["bg_card"], corner_radius=10)
        card.grid(row=0, column=col_idx, sticky="ew", padx=5)
        parent.grid_columnconfigure(col_idx, weight=1)
        
        ctk.CTkLabel(card, text=title, text_color="gray", font=("Segoe UI", 12)).pack(pady=(15, 5), padx=15, anchor="w")
        ctk.CTkLabel(card, text=value, text_color=color, font=("Segoe UI", 28, "bold")).pack(pady=(0, 15), padx=15, anchor="w")

    def draw_pie_chart(self, parent, done, active):
        frame = ctk.CTkFrame(parent, fg_color=THEME["bg_card"], corner_radius=15)
        frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(frame, text="Статус задач", font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        if done == 0 and active == 0:
            ctk.CTkLabel(frame, text="Нет данных", text_color="gray").pack(expand=True)
            return

        fig = plt.Figure(figsize=(4, 3), dpi=100, facecolor=THEME["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg_card"])
        
        sizes = [done, active]
        labels = ['Готово', 'В работе']
        colors = ['#10B981', '#3B82F6']
        
        # Создаем кольцевую диаграмму (donut chart) с современным стилем
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            autopct='%1.1f%%', 
            startangle=90, 
            colors=colors,
            textprops=dict(color="white", fontsize=10, weight='bold'),
            wedgeprops=dict(antialiased=True)
        )
        
        # Добавляем кольцо в центр для создания эффекта donut
        centre_circle = plt.Circle((0, 0), 0.75, fc=THEME["bg_card"])
        fig.gca().add_artist(centre_circle)
        
        # Стилизуем текст
        for text in texts:
            text.set_color("white")
            text.set_fontsize(11)
            text.set_weight('bold')
        
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(9)
            autotext.set_weight('bold')

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def draw_bar_chart(self, parent):
        # Очищаем старое содержимое контейнера
        for widget in parent.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(parent, text="Активность (часы)", font=("Segoe UI", 16, "bold")).pack(pady=10)

        # Получаем часы и метки дней за последние 7 дней из БД
        hours = self.app.db.get_weekly_hours()

        fig = plt.Figure(figsize=(4, 3), dpi=100, facecolor=THEME["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg_card"])
        
        # Генерируем метки (0, 1, 2... или дни недели)
        if isinstance(hours, tuple):
            hours, labels = hours
        else:
            # Если вернулись только часы (для обратной совместимости)
            labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][:len(hours)]
        
        bars = ax.bar(labels, hours, color=THEME["primary"])
        ax.tick_params(colors='white', which='both')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Устанавливаем пределы оси Y для лучшей визуализации
        max_hours = max(hours) if hours else 8
        ax.set_ylim(0, max(max_hours * 1.2, 8))
        
        # Добавляем значения над столбцами
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}', ha='center', va='bottom', color='white', fontsize=9)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def refresh_bar_chart(self):
        """Обновить диаграмму после синхронизации логов"""
        if hasattr(self, 'bar_chart_container'):
            self.draw_bar_chart(self.bar_chart_container)

    # ==========================
    # Вкладка 2: ТРЕКЕР
    # ==========================
    def show_tracker_tab(self):
        self.clear_content()
        self.highlight_menu(self.btn_menu_tracker)
        
        # Центрирование контента
        container = ctk.CTkFrame(self.main_area, fg_color="transparent")
        container.pack(expand=True)

        # Таймер круглый (имитация) или большой текст
        self.lbl_timer = ctk.CTkLabel(container, text="00:00:00", font=("Consolas", 80, "bold"), text_color="white")
        self.lbl_timer.pack(pady=40)

        self.lbl_state_text = ctk.CTkLabel(container, text="Готов к работе", font=("Segoe UI", 18), text_color=THEME["text_sec"])
        self.lbl_state_text.pack(pady=(0, 40))

        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.pack()

        self.btn_start = self.create_action_btn(btn_box, "НАЧАТЬ", self.start_work, THEME["success"])
        self.btn_pause = self.create_action_btn(btn_box, "ПАУЗА", self.pause_work, THEME["warning"])
        self.btn_stop = self.create_action_btn(btn_box, "СТОП", self.finish_work, THEME["danger"])
        
        self.update_ui_state()

    def create_action_btn(self, parent, text, cmd, color):
        btn = ctk.CTkButton(parent, text=text, command=cmd, width=120, height=50, 
                            corner_radius=25, fg_color=color, font=("Segoe UI", 14, "bold"))
        btn.pack(side="left", padx=10)
        return btn

    # ==========================
    # Вкладка 3: ЗАДАЧИ
    # ==========================
    def show_tasks_tab(self):
        self.clear_content()
        self.highlight_menu(self.btn_menu_tasks)

        header = ctk.CTkFrame(self.main_area, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(header, text="Мои задачи", font=("Segoe UI", 24, "bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Добавить", command=self.add_task_dialog, 
                      fg_color=THEME["primary"], width=100).pack(side="right")

        self.scroll_tasks = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        self.scroll_tasks.pack(fill="both", expand=True)
        
        # Показываем загрузчик пока грузятся задачи
        loading_label = ctk.CTkLabel(self.scroll_tasks, text="⏳ Загрузка задач...", text_color="gray")
        loading_label.pack(pady=20)
        
        # Загружаем задачи в фоновом потоке
        def load_tasks():
            try:
                threading.Thread(target=self._load_tasks_thread, daemon=True).start()
            except Exception as e:
                print(f"Error loading tasks: {e}")
        
        self.after(0, load_tasks)
        
        # Отмечаем все уведомления как прочитанные когда открыли вкладку
        self.app.api.mark_all_notifications_as_read()
        self.update_tasks_badge()

    def _load_tasks_thread(self):
        """Загружает задачи в фоновом потоке"""
        try:
            tasks = self.app.api.get_tasks()
            self.after(0, lambda: self._display_tasks(tasks))
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            self.after(0, lambda: self._display_tasks([]))

    def _display_tasks(self, tasks):
        """Отображает загруженные задачи (вызывается из главного потока)"""
        for w in self.scroll_tasks.winfo_children(): w.destroy()
        
        if not tasks:
            ctk.CTkLabel(self.scroll_tasks, text="Список задач пуст", text_color="gray").pack(pady=20)
            return

        for task in tasks:
            self.draw_task_card(task)

    def refresh_tasks(self):
        """Перезагружает задачи (для кнопок обновления)"""
        if hasattr(self, 'scroll_tasks') and self.scroll_tasks.winfo_exists():
            self._load_tasks_thread()

    def draw_task_card(self, task):
        from datetime import datetime
        import customtkinter as ctk

        # --- 1. Определение стилей ---
        is_completed = task.get('is_completed', False)
        is_overdue = not is_completed and task.get('is_overdue', False)

        if is_completed:
            card_color = "#1E1E24"
            border_color = "#2A2A32"
        elif is_overdue:
            card_color = "#2D1F1F"
            border_color = THEME["danger"]
        else:
            card_color = THEME["bg_card"]
            border_color = "#404050"

        # Основная карточка
        card = ctk.CTkFrame(self.scroll_tasks, fg_color=card_color, corner_radius=10,
                            border_width=1, border_color=border_color)
        card.pack(fill="x", pady=4, padx=10)

        # ==========================================
        # ПЕРЕХОДИМ НА УМНЫЙ .pack() ИЗ 3 БЛОКОВ
        # ==========================================

        # БЛОК 1: Чекбокс (Левый край, прижат к верху -> anchor="n")
        chk_var = ctk.BooleanVar(value=is_completed)
        chk = ctk.CTkCheckBox(card, text="", variable=chk_var, corner_radius=50, width=20, height=20,
                              command=lambda t=task['id'], v=chk_var: self.toggle_task(t, v))
        chk.pack(side="left", padx=(15, 10), pady=12, anchor="n")

        # БЛОК 2: Действия (Правый край, прижат к верху -> anchor="ne")
        # ВАЖНО: Правый блок пакуется ДО центрального, чтобы занять свой край
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(side="right", padx=(10, 15), pady=12, anchor="ne")

        btn_file = ctk.CTkButton(
            actions, text="📎 Файлы", width=70, height=28, corner_radius=6,
            fg_color="transparent", border_width=1, border_color="#555562",
            hover_color="#2D2D3A", text_color="#CCCCCC", font=("Segoe UI", 11),
            command=lambda t=task['id']: self.upload_file_action(t)
        )
        btn_file.pack(side="left", padx=(0, 5))

        if task.get('can_delete', True):
            btn_delete = ctk.CTkButton(
                actions, text="✕", width=28, height=28, corner_radius=6,
                fg_color="transparent", text_color="#888888",
                hover_color=THEME["danger"], font=("Segoe UI", 12, "bold"),
                command=lambda t=task['id']: self.delete_task(t)
            )
            btn_delete.pack(side="left")

        # БЛОК 3: Инфо-блок (Центр, занимает ВСЁ оставшееся пространство)
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, pady=12)

        # --- Наполнение центрального блока (сверху вниз) ---
        title_color = "#888888" if is_completed else "white"
        font_title = ("Segoe UI", 14, "normal" if is_completed else "bold")
        
        ctk.CTkLabel(
            info, text=task['title'], font=font_title, text_color=title_color,
            anchor="w", justify="left", wraplength=400 
        ).pack(fill="x", anchor="w")

        if task.get('description'):
            ctk.CTkLabel(
                info, text=task['description'], font=("Segoe UI", 12),
                text_color="#666666" if is_completed else "gray",
                anchor="w", justify="left", wraplength=400
            ).pack(fill="x", anchor="w", pady=(2, 0))

        if task.get('deadline'):
            meta_frame = ctk.CTkFrame(info, fg_color="transparent")
            meta_frame.pack(fill="x", anchor="w", pady=(5, 0))

            try:
                deadline_dt = datetime.fromisoformat(task['deadline'].replace('Z', '+00:00'))
                deadline_text = deadline_dt.strftime("%d.%m.%Y %H:%M")
                
                ctk.CTkLabel(
                    meta_frame, text=f"📅 {deadline_text}", font=("Segoe UI", 11),
                    text_color=THEME["danger"] if is_overdue else "#888888", anchor="w"
                ).pack(side="left", padx=(0, 15))
            except Exception as e:
                pass

    def add_task_dialog(self):
        """Открыть окно для добавления новой задачи"""
        def on_task_created(result):
            if result:
                threading.Thread(
                    target=self._create_task_thread, 
                    args=(result["title"], result.get("description", "")),
                    daemon=True
                ).start()
        
        AddTaskWindow(self, on_task_created)
    
    def _create_task_thread(self, title, description=""):
        # Вызываем реальный метод создания задачи через API
        try:
            self.app.api.create_task(title, description)
            time.sleep(0.3)
            self.after(0, self.refresh_tasks)
        except Exception as e:
            print(f"Error creating task: {e}")
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось создать задачу: {e}"))


    def delete_task(self, task_id):
        """Удаление задачи (если пользователь её создал)"""
        threading.Thread(target=self._delete_task_thread, args=(task_id,)).start()
    
    def _delete_task_thread(self, task_id):
        self.app.api.delete_task(task_id)
        time.sleep(0.3)
        self.after(0, self.refresh_tasks)

    def toggle_task(self, task_id, var):
        status = var.get()
        threading.Thread(target=self.app.api.update_task_status, args=(task_id, status)).start()
        # Можно добавить визуальное зачеркивание

    def upload_file_action(self, task_id):
        """Открыть модальное окно для управления вложениями"""
        # Открыть модальное окно (название задачи получится от сервера или используем общее)
        attachment_modal = TaskAttachmentModalWindow(
            self, 
            self.app.api, 
            task_id, 
            f"Задача #{task_id}",
            on_refresh=self.refresh_tasks
        )
    
    # ==========================
    # Вкладка 4: ПРОФИЛЬ
    # ==========================
    def show_profile_tab(self):
        self.clear_content()
        self.highlight_menu(self.btn_menu_profile)
        
        profile = self.app.user_data or {}
        
        # Карточка профиля
        card = ctk.CTkFrame(self.main_area, fg_color=THEME["bg_card"], corner_radius=20)
        card.pack(fill="x", pady=20, padx=40)
        
        # Аватарка (кружок с буквами)
        initials = profile.get('full_name', '??')[:1]
        avatar = ctk.CTkFrame(card, width=80, height=80, corner_radius=40, fg_color=THEME["primary"])
        avatar.pack(pady=20)
        ctk.CTkLabel(avatar, text=initials, font=("Segoe UI", 30, "bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text=profile.get('full_name', 'Сотрудник'), font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(card, text=f"{profile.get('position', 'Должность')} | {profile.get('department', 'Отдел')}", 
                     text_color="gray", font=("Segoe UI", 14)).pack(pady=(5, 20))
        
        # Инфо поля
        info_box = ctk.CTkFrame(card, fg_color="transparent")
        info_box.pack(pady=20, fill="x", padx=40)
        
        self.create_info_row(info_box, "Табельный номер:", profile.get('personnel_number', '-'))
        
        # Получаем название компании с сервера
        company_info = self.app.api.get_company_info()
        company_name = company_info.get('company_name', 'ООО Моя Компания')
        self.create_info_row(info_box, "Компания:", company_name)

    def create_info_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text=label, width=150, anchor="w", text_color="gray").pack(side="left")
        ctk.CTkLabel(row, text=value, anchor="w", font=("Segoe UI", 14, "bold")).pack(side="left")

    # ==========================
    # ЛОГИКА ТАЙМЕРА И СИНХРОНИЗАЦИИ
    # ==========================
    def highlight_menu(self, active_btn):
        # Сброс цветов кнопок
        for btn in [self.btn_menu_dash, self.btn_menu_tracker, self.btn_menu_tasks, self.btn_menu_profile]:
            btn.configure(fg_color="transparent", text_color=THEME["text_sec"])
        # Подсветка активной
        active_btn.configure(fg_color=THEME["bg_card"], text_color=THEME["primary"])

    def start_work(self):
        if not self.is_running:
            if self.elapsed_time == 0: self.app.db.log_event("START")
            else: self.app.db.log_event("RESUME")
            self.is_running = True
            # При старте/возобновлении сбрасываем таймер неактивности
            self.last_input_time = time.time()
            self._cancel_afk_warning()
            self.start_time = time.time() - self.elapsed_time
            self.update_ui_state()

    def pause_work(self):
        if self.is_running:
            self.app.db.log_event("PAUSE")
            self.is_running = False
            self.elapsed_time = time.time() - self.start_time
            # При паузе отменяем возможное окно Anti-AFK
            self._cancel_afk_warning()
            self.update_ui_state()

    def finish_work(self):
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time
        if self.elapsed_time > 0:
            self.app.db.log_event("STOP")
        self.is_running = False
        self.elapsed_time = 0
        self.lbl_timer.configure(text="00:00:00")
        # При завершении смены отменяем возможное окно Anti-AFK
        self._cancel_afk_warning()
        self.update_ui_state()

    def update_ui_state(self):
        # Доступность кнопок (нужно обновлять только если мы на вкладке трекера)
        if not hasattr(self, 'btn_start') or not self.btn_start.winfo_exists(): 
            return 
        
        if self.is_running:
            self.lbl_state_text.configure(text="В процессе работы...", text_color=THEME["success"])
            self.btn_start.configure(state="disabled", fg_color="gray")
            self.btn_pause.configure(state="normal", fg_color=THEME["warning"])
            self.btn_stop.configure(state="normal", fg_color=THEME["danger"])
        else:
            self.btn_pause.configure(state="disabled", fg_color="gray")
            self.btn_stop.configure(state="disabled", fg_color="gray")
            if self.elapsed_time > 0:
                self.lbl_state_text.configure(text="Пауза", text_color=THEME["warning"])
                self.btn_start.configure(state="normal", text="ПРОДОЛЖИТЬ", fg_color=THEME["success"])
                self.btn_stop.configure(state="normal", fg_color=THEME["danger"])
            else:
                self.lbl_state_text.configure(text="Смена закрыта", text_color="gray")
                self.btn_start.configure(state="normal", text="НАЧАТЬ СМЕНУ", fg_color=THEME["success"])

    def update_timer_loop(self):
        if self.is_running:
            c = time.time() - self.start_time
            h, r = divmod(c, 3600)
            m, s = divmod(r, 60)
            # Обновляем таймер только если он создан и видим (мы на вкладке трекера)
            if hasattr(self, 'lbl_timer') and self.lbl_timer.winfo_exists():
                try:
                    self.lbl_timer.configure(text=f"{int(h):02}:{int(m):02}:{int(s):02}")
                except tk.TclError as e:
                    print(f"Timer update error: {e}")
        self.after(100, self.update_timer_loop)

    # ==========================
    # Anti-AFK: отслеживание неактивности и автопауза
    # ==========================
    def _on_user_activity(self, event=None):
        """Обновляет время последней активности пользователя."""
        self.last_input_time = time.time()
        # Если пользователь шевельнулся, когда висело предупреждение — считаем, что он вернулся к работе
        if self._afk_warning_shown:
            self._cancel_afk_warning()

    def _start_anti_afk_loop(self):
        """Запускает циклическую проверку неактивности (если включено для сотрудника)."""
        self.after(1000, self._anti_afk_loop)

    def _anti_afk_loop(self):
        try:
            if self.anti_afk_enabled and self.is_running:
                idle_seconds = time.time() - self.last_input_time
                # Если пользователь давно не проявлял активность и предупреждение еще не показано
                if idle_seconds >= self.anti_afk_idle_seconds and not self._afk_warning_shown:
                    self._show_afk_warning()
        except Exception as e:
            print(f"Anti-AFK loop error: {e}")
        finally:
            # Продолжаем цикл независимо от ошибок
            self.after(1000, self._anti_afk_loop)

    def _show_afk_warning(self):
        """Показывает поверх всех окон предупреждение о скорой паузе."""
        if self._afk_warning_shown:
            return
        if not self.anti_afk_enabled or not self.is_running:
            return

        self._afk_warning_shown = True
        # Инициализируем обратный отсчет
        try:
            self._afk_countdown = int(self.anti_afk_grace_seconds)
        except (TypeError, ValueError):
            self._afk_countdown = 30
        if self._afk_countdown <= 0:
            self._afk_countdown = 30

        win = ctk.CTkToplevel(self)
        self._afk_window = win
        win.attributes("-topmost", True)
        try:
            win.attributes("-toolwindow", True)
        except Exception:
            # На некоторых платформах может не поддерживаться
            pass

        win.title("Отсутствие активности")
        width, height = 420, 200
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.resizable(False, False)
        win.configure(fg_color=THEME["bg_card"])

        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        title_lbl = ctk.CTkLabel(
            container,
            text="Мы не видим активности",
            font=("Segoe UI", 18, "bold"),
            text_color="white",
        )
        title_lbl.pack(pady=(0, 10))

        msg_lbl = ctk.CTkLabel(
            container,
            text=(
                "Если вы не вернетесь к работе, "
                "через несколько секунд таймер будет автоматически поставлен на паузу."
            ),
            font=("Segoe UI", 12),
            text_color=THEME["text_sec"],
            wraplength=360,
            justify="center",
        )
        msg_lbl.pack(pady=(0, 10))

        self._afk_countdown_label = ctk.CTkLabel(
            container,
            text=f"Таймер будет поставлен на паузу через {self._afk_countdown} с.",
            font=("Segoe UI", 12, "bold"),
            text_color=THEME["warning"],
        )
        self._afk_countdown_label.pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(pady=(5, 0))

        btn_continue = ctk.CTkButton(
            btn_frame,
            text="Я работаю, продолжить",
            command=self._on_afk_continue,
            fg_color=THEME["success"],
            width=160,
        )
        btn_continue.pack(side="left", padx=5)

        btn_pause = ctk.CTkButton(
            btn_frame,
            text="Поставить на паузу сейчас",
            command=self._on_afk_pause_now,
            fg_color=THEME["danger"],
            width=160,
        )
        btn_pause.pack(side="left", padx=5)

        # Закрытие окна крестиком = считаем, что пользователь вернулся
        win.protocol("WM_DELETE_WINDOW", self._on_afk_continue)

        # Стартуем обратный отсчет
        self._update_afk_countdown()

    def _update_afk_countdown(self):
        """Обновляет текст обратного отсчета и при необходимости ставит паузу."""
        if not self._afk_warning_shown:
            return

        win = self._afk_window
        if not win or not win.winfo_exists():
            self._afk_warning_shown = False
            return

        if self._afk_countdown <= 0:
            # Время вышло — ставим на паузу
            self._cancel_afk_warning()
            if self.is_running:
                self.pause_work()
            return

        if hasattr(self, "_afk_countdown_label"):
            self._afk_countdown_label.configure(
                text=f"Таймер будет поставлен на паузу через {self._afk_countdown} с."
            )

        self._afk_countdown -= 1
        self.after(1000, self._update_afk_countdown)

    def _cancel_afk_warning(self):
        """Отменяет текущее предупреждение Anti-AFK, если оно есть."""
        self._afk_warning_shown = False
        self._afk_countdown = 0
        win = self._afk_window
        self._afk_window = None
        if win is not None:
            try:
                if win.winfo_exists():
                    win.destroy()
            except Exception:
                pass

    def _on_afk_continue(self):
        """Пользователь подтвердил, что он на месте."""
        self.last_input_time = time.time()
        self._cancel_afk_warning()

    def _on_afk_pause_now(self):
        """Пользователь явно запросил постановку на паузу."""
        self._cancel_afk_warning()
        if self.is_running:
            self.pause_work()

    def check_connection_loop(self):
        """Реальная проверка связи"""
        if not hasattr(self, '_status_queue'):
            self._status_queue = queue.Queue()
        
        def check():
            try:
                if self.app.api.check_connection(): # Быстрая проверка (можно оптимизировать пингом)
                    self._status_queue.put(True)
                    # Фоновая отправка логов
                    unsynced = self.app.db.get_unsynced_logs()
                    if unsynced:
                        synced_ids = self.app.api.upload_logs(unsynced)
                        if synced_ids:
                            self.app.db.mark_logs_as_synced(synced_ids)
                else:
                    self._status_queue.put(False)
            except Exception as e:
                print(f"Connection check error: {e}")
                self._status_queue.put(False)
        
        # Проверить очередь статусов
        try:
            while True:
                status = self._status_queue.get_nowait()
                self.set_status(status)
        except queue.Empty:
            pass
        
        threading.Thread(target=check, daemon=True).start()
        self.after(10000, self.check_connection_loop) # Каждые 10 сек

    def set_status(self, online):
        if online:
            self.lbl_status_dot.configure(text_color=THEME["success"])
            self.lbl_status_text.configure(text="Online")
        else:
            self.lbl_status_dot.configure(text_color=THEME["danger"])
            self.lbl_status_text.configure(text="Offline")

    def update_tasks_badge(self):
        """Обновляет количество непрочитанных уведомлений на badge"""
        unread_count = self.app.api.get_unread_notifications_count()
        
        if unread_count > 0:
            # Показываем badge только если есть непрочитанные
            if unread_count > 99:
                self.tasks_badge.configure(text="99+")
            else:
                self.tasks_badge.configure(text=str(unread_count))
            self.tasks_badge.pack(side="right", padx=5)
        else:
            # Скрываем badge если нет непрочитанных
            self.tasks_badge.pack_forget()

    def show_notification_toast(self, title, message, duration=5000):
        """Показывает toast-уведомление в правом нижнем углу"""
        # Создаем окно-уведомление
        toast = ctk.CTkToplevel(self)
        toast.attributes('-topmost', True)
        toast.attributes('-toolwindow', True)  # Не показываем в таскбаре
        
        # Геометрия: высота 110px, ширина 320px, отступ 20px от края
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - 340
        y = screen_height - 130
        
        toast.geometry(f"320x110+{x}+{y}")
        toast.resizable(False, False)
        toast.configure(fg_color=THEME["bg_card"], corner_radius=10)
        
        # Контейнер с отступом
        container = ctk.CTkFrame(toast, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=12, pady=12)
        
        # Заголовок с иконкой
        title_frame = ctk.CTkFrame(container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(title_frame, text="🔔", font=("Segoe UI", 14)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(title_frame, text=title, font=("Segoe UI", 11, "bold"), text_color="white").pack(side="left", fill="x", expand=True)
        
        # Сообщение
        ctk.CTkLabel(container, text=message, font=("Segoe UI", 10), text_color=THEME["text_sec"], 
                    wraplength=280, justify="left").pack(anchor="w")
        
        # Плавное закрытие через duration
        def fade_close():
            try:
                if toast.winfo_exists():
                    toast.destroy()
            except:
                pass
        
        toast.after(duration, fade_close)
        
        # Закрытие при клике
        def on_click(event):
            try:
                toast.destroy()
            except:
                pass
        
        toast.bind("<Button-1>", on_click)

    def check_notifications_loop(self):
        """Проверяет наличие новых уведомлений каждые N секунд"""
        if not hasattr(self, '_shown_notifications'):
            self._shown_notifications = set()  # Для отслеживания показанных уведомлений
        
        def check():
            try:
                if self.app.api.is_connected:
                    notifications = self.app.api.get_notifications()
                    if notifications:
                        # Ищем непрочитанные уведомления (новые задачи)
                        new_unread = [n for n in notifications if not n.get('is_read') and n.get('notification_type') == 'new_task']
                        
                        for notif in new_unread:
                            notif_id = notif.get('id')
                            # Показываем уведомление только если мы его еще не показывали
                            if notif_id and notif_id not in self._shown_notifications:
                                self._shown_notifications.add(notif_id)
                                self.show_notification_toast(
                                    notif.get('title', 'Новая задача'),
                                    notif.get('message', '')
                                )
                                # Обновляем badge
                                self.update_tasks_badge()
                                break  # Показываем только одно уведомление за раз
            except Exception as e:
                print(f"Notification check error: {e}")
        
        threading.Thread(target=check, daemon=True).start()
        self.after(3000, self.check_notifications_loop)  # Проверяем каждые 3 сек

if __name__ == "__main__":
    app = ZefiTimeApp()