import pytest
from rest_framework.test import APIClient
from StitchCarbackendapp.models import CustomUser


@pytest.fixture
def api_client():
    """Reusable API client for all tests"""
    return APIClient()


@pytest.fixture
@pytest.mark.django_db
def create_test_user():
    """Reusable user fixture"""
    def make_user(**kwargs):
        defaults = {
            "username": "defaultuser",
            "email": "default@example.com",
            "phone_number": "9999999999",
        }
        defaults.update(kwargs)
        user = CustomUser.objects.create_user(**defaults, password="StrongPass123")
        return user
    return make_user
