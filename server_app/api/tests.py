import time
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from .models import EmployeeProfile, WorkLog, Task, TaskAttachment, Notification
from .authentication import PersonnelNumberBackend


def make_user(username, password="testpass123", personnel_number=None):
    user = User.objects.create_user(username=username, password=password)
    EmployeeProfile.objects.create(
        user=user,
        personnel_number=personnel_number or username,
        position="Employee",
    )
    return user


# ── TC-01..03  EmployeeProfile.is_online() ───────────────────────────────────

class EmployeeProfileIsOnlineTest(TestCase):
    def setUp(self):
        self.user = make_user("001")
        self.profile = self.user.profile

    def test_is_online_with_recent_activity(self):          # TC-01
        self.profile.last_activity = timezone.now()
        self.profile.save()
        self.assertTrue(self.profile.is_online())

    def test_is_online_with_old_activity(self):             # TC-02
        self.profile.last_activity = timezone.now() - timedelta(minutes=10)
        self.profile.save()
        self.assertFalse(self.profile.is_online())

    def test_is_online_without_activity(self):              # TC-03
        self.profile.last_activity = None
        self.profile.save()
        self.assertFalse(self.profile.is_online())


# ── TC-04..10  TaskAttachment.validate_extension / validate_file_size ────────

class TaskAttachmentValidationTest(TestCase):
    def test_allowed_extension_pdf(self):                   # TC-04
        valid, _ = TaskAttachment.validate_extension("report.pdf")
        self.assertTrue(valid)

    def test_allowed_extension_docx(self):                  # TC-05
        valid, _ = TaskAttachment.validate_extension("contract.docx")
        self.assertTrue(valid)

    def test_blocked_extension_exe(self):                   # TC-06
        valid, msg = TaskAttachment.validate_extension("virus.exe")
        self.assertFalse(valid)
        self.assertIn(".exe", msg)

    def test_blocked_extension_py(self):                    # TC-07
        valid, msg = TaskAttachment.validate_extension("script.py")
        self.assertFalse(valid)

    def test_unknown_extension_rejected(self):              # TC-08
        valid, _ = TaskAttachment.validate_extension("audio.mp3")
        self.assertFalse(valid)

    def test_file_size_within_limit(self):                  # TC-09
        valid, _ = TaskAttachment.validate_file_size(5 * 1024 * 1024)
        self.assertTrue(valid)

    def test_file_size_exceeds_limit(self):                 # TC-10
        valid, msg = TaskAttachment.validate_file_size(15 * 1024 * 1024)
        self.assertFalse(valid)
        self.assertIn("10MB", msg)


# ── TC-11  Сигнал: уведомление при создании задачи ───────────────────────────

class NotificationSignalTest(TestCase):
    def setUp(self):
        self.employee = make_user("emp_signal")
        self.admin = User.objects.create_user(username="admin_sig", password="pass")

    def test_notification_created_on_new_task(self):        # TC-11
        task = Task.objects.create(
            user=self.employee,
            title="Подготовить отчёт",
            created_by=self.admin,
        )
        qs = Notification.objects.filter(user=self.employee, task=task)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().notification_type, "new_task")


# ── TC-12..13  WorkLog API ────────────────────────────────────────────────────

class WorkLogAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user("emp_wl")
        self.client.force_authenticate(user=self.user)

    def test_create_worklog_returns_201(self):              # TC-12
        response = self.client.post(
            "/api/worklog/",
            {"event": "START", "timestamp": time.time()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(WorkLog.objects.filter(user=self.user).count(), 1)

    def test_worklog_list_filtered_by_owner(self):          # TC-13
        other = make_user("other_wl")
        WorkLog.objects.create(user=self.user, event="START", timestamp=time.time())
        WorkLog.objects.create(user=other, event="START", timestamp=time.time())
        response = self.client.get("/api/worklog/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


# ── TC-14..15  /api/users/me/ ─────────────────────────────────────────────────

class UserMeAPITest(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.user = make_user("emp_me")

    def test_unauthenticated_request_returns_401(self):     # TC-14
        response = self.api_client.get("/api/users/me/")
        self.assertEqual(response.status_code, 401)

    def test_me_returns_personnel_number(self):             # TC-15
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get("/api/users/me/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("personnel_number", response.data)


# ── TC-16..17  PersonnelNumberBackend ────────────────────────────────────────

class PersonnelNumberBackendTest(TestCase):
    def setUp(self):
        self.backend = PersonnelNumberBackend()
        self.user = make_user("emp_auth", password="secret123", personnel_number="TAB-001")

    def test_authenticate_with_personnel_number(self):      # TC-16
        result = self.backend.authenticate(None, username="TAB-001", password="secret123")
        self.assertEqual(result, self.user)

    def test_authenticate_wrong_password_returns_none(self):  # TC-17
        result = self.backend.authenticate(None, username="TAB-001", password="wrong")
        self.assertIsNone(result)
