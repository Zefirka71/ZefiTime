from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .models import EmployeeProfile

class PersonnelNumberBackend(ModelBackend):
    """
    Позволяет входить в систему, используя Табельный номер вместо Username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Ищем профиль с таким табельным номером
            profile = EmployeeProfile.objects.get(personnel_number=username)
            user = profile.user
            # Проверяем пароль стандартным способом
            if user.check_password(password):
                return user
        except EmployeeProfile.DoesNotExist:
            return None
        return None