import base64
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from behave import given, when, then
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from api.models import EmployeeProfile, WorkLog


# ── helpers ──────────────────────────────────────────────────────────────────

def _basic_auth(username, password):
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"HTTP_AUTHORIZATION": f"Basic {creds}"}


def _make_employee(personnel_number, password):
    username = f"user_{personnel_number}"
    user = User.objects.create_user(username=username, password=password)
    EmployeeProfile.objects.create(
        user=user,
        personnel_number=personnel_number,
        position="Employee",
    )
    return user


# ── authentication.feature ───────────────────────────────────────────────────

@given('the employee with personnel number "{number}" and password "{pwd}" exists')
def step_create_employee(context, number, pwd):
    _make_employee(number, pwd)


@when('the client requests GET "{url}" with credentials "{number}" and "{pwd}"')
def step_get_with_credentials(context, url, number, pwd):
    client = APIClient()
    context.response = client.get(url, **_basic_auth(number, pwd))


@when('the client requests GET "{url}" without credentials')
def step_get_without_credentials(context, url):
    client = APIClient()
    context.response = client.get(url)


@then('the response status should be {code:d}')
def step_check_status(context, code):
    assert context.response.status_code == code, (
        f"Expected {code}, got {context.response.status_code}: {context.response.data}"
    )


@then('the response JSON should contain key "{key}"')
def step_check_json_key(context, key):
    assert key in context.response.data, (
        f"Key '{key}' not found in response: {context.response.data}"
    )


# ── worklog.feature ───────────────────────────────────────────────────────────

@given('the client is authenticated as "{number}" with password "{pwd}"')
def step_authenticate_client(context, number, pwd):
    context.auth_headers = _basic_auth(number, pwd)


@given('another employee with personnel number "{number}" and password "{pwd}" exists')
def step_create_other_employee(context, number, pwd):
    context.other_user = _make_employee(number, pwd)


@given('employee "{number}" has an existing worklog entry')
def step_create_worklog_for_other(context, number):
    user = EmployeeProfile.objects.get(personnel_number=number).user
    WorkLog.objects.create(user=user, event="START", timestamp=time.time())


@when('the employee sends a worklog event "{event}" with current timestamp')
def step_send_worklog(context, event):
    client = APIClient()
    context.response = client.post(
        "/api/worklog/",
        {"event": event, "timestamp": time.time()},
        format="json",
        **context.auth_headers,
    )


@when('the employee "{number}" requests the worklog list')
def step_get_worklog_list(context, number):
    client = APIClient()
    context.response = client.get("/api/worklog/", **context.auth_headers)


@when('an unauthenticated client requests the worklog list')
def step_get_worklog_unauthenticated(context):
    client = APIClient()
    context.response = client.get("/api/worklog/")


@then('a WorkLog entry with event "{event}" should exist for employee "{number}"')
def step_check_worklog_created(context, event, number):
    user = EmployeeProfile.objects.get(personnel_number=number).user
    exists = WorkLog.objects.filter(user=user, event=event).exists()
    assert exists, f"No WorkLog with event={event} found for {number}"


@then('the returned list should contain exactly {count:d} entries')
def step_check_list_count(context, count):
    data = context.response.data
    assert len(data) == count, f"Expected {count} entries, got {len(data)}"
