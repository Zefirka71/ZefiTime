"""
UI-тесты Django Admin через Selenium + Page Object Model.
Запуск (из server_app/, venv активирован):
    pip install selenium
    python manage.py test api.tests_selenium
Microsoft Edge должен быть установлен; msedgedriver управляется автоматически (Selenium 4.6+).
"""
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ── Page Objects ─────────────────────────────────────────────────────────────

class AdminLoginPage:
    """Страница входа Django Admin (/admin/login/)."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def navigate(self):
        self.driver.get(f"{self.base_url}/admin/login/")
        return self

    def enter_credentials(self, username, password):
        self.driver.find_element(By.ID, "id_username").clear()
        self.driver.find_element(By.ID, "id_username").send_keys(username)
        self.driver.find_element(By.ID, "id_password").clear()
        self.driver.find_element(By.ID, "id_password").send_keys(password)
        return self

    def submit(self):
        self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        return self

    def get_error_text(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, ".errornote").text
        except Exception:
            return None

    def is_login_page(self):
        return "login" in self.driver.current_url


class AdminDashboardPage:
    """Главная страница Django Admin (/admin/)."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def get_page_title(self):
        return self.driver.title

    def is_authenticated(self):
        return (
            "/admin/" in self.driver.current_url
            and "login" not in self.driver.current_url
        )

    def go_to_employee_list(self):
        self.driver.get(f"{self.base_url}/admin/api/employeeprofile/")
        return EmployeeProfileListPage(self.driver, self.base_url)


class EmployeeProfileListPage:
    """Страница списка профилей сотрудников (/admin/api/employeeprofile/)."""

    def __init__(self, driver, base_url):
        self.driver = driver
        self.base_url = base_url

    def is_loaded(self):
        wait = WebDriverWait(self.driver, 5)
        try:
            wait.until(EC.presence_of_element_located((By.ID, "changelist")))
            return True
        except Exception:
            return False

    def get_page_header(self):
        try:
            return self.driver.find_element(By.CSS_SELECTOR, "#content h1").text
        except Exception:
            return ""


# ── Tests ─────────────────────────────────────────────────────────────────────

class AdminUITest(StaticLiveServerTestCase):
    """
    Четыре UI-тест-кейса (UI-TC-01 … UI-TC-04).
    Тестовая БД создаётся/удаляется автоматически.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,800")
        cls.driver = webdriver.Edge(options=options)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_ui",
            password="AdminPass123!",
            email="admin@test.local",
        )
        self.login_page = AdminLoginPage(self.driver, self.live_server_url)

    # UI-TC-01
    def test_successful_admin_login(self):
        """Вход с верными данными перенаправляет на /admin/."""
        self.login_page.navigate().enter_credentials(
            "admin_ui", "AdminPass123!"
        ).submit()
        dashboard = AdminDashboardPage(self.driver, self.live_server_url)
        self.assertTrue(dashboard.is_authenticated())

    # UI-TC-02
    def test_wrong_password_shows_error(self):
        """Вход с неверным паролем отображает сообщение об ошибке."""
        self.login_page.navigate().enter_credentials(
            "admin_ui", "WrongPassword"
        ).submit()
        self.assertTrue(self.login_page.is_login_page())
        error = self.login_page.get_error_text()
        self.assertIsNotNone(error, "Сообщение об ошибке не отображается")

    # UI-TC-03
    def test_dashboard_title_contains_django(self):
        """После входа заголовок страницы содержит 'Django'."""
        self.login_page.navigate().enter_credentials(
            "admin_ui", "AdminPass123!"
        ).submit()
        dashboard = AdminDashboardPage(self.driver, self.live_server_url)
        self.assertIn("Django", dashboard.get_page_title())

    # UI-TC-04
    def test_employee_list_page_loads(self):
        """Страница списка профилей сотрудников загружается корректно."""
        self.login_page.navigate().enter_credentials(
            "admin_ui", "AdminPass123!"
        ).submit()
        dashboard = AdminDashboardPage(self.driver, self.live_server_url)
        emp_page = dashboard.go_to_employee_list()
        self.assertTrue(emp_page.is_loaded())
