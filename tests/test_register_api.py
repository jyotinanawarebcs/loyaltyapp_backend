import pytest
import time
from django.urls import reverse
from rest_framework import status
from StitchCarbackendapp.models import CustomUser

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "username,email,phone,password,confirm_password,expected_status",
    [
        # ✅ Positive
        ("Alice", "alice@example.com", "9876543210", "StrongPass123", "StrongPass123", 201),
        # ❌ Duplicate email
        ("Bob", "alice@example.com", "9876543211", "StrongPass123", "StrongPass123", 400),
        # ❌ Invalid username (numbers)
        ("Bob123", "bob@example.com", "9876543212", "StrongPass123", "StrongPass123", 400),
        # ❌ Password mismatch
        ("Charlie", "charlie@example.com", "9876543213", "abc", "xyz", 400),
    ],
)
def test_register_api(api_client, create_test_user, username, email, phone, password, confirm_password, expected_status):
    """Parameterized +ve & -ve Register API tests"""
    url = reverse("register")

    # pre-create user for duplicate email case
    if email == "alice@example.com" and username != "Alice":
         create_test_user(username="Alice", email="alice@example.com")
    data = {
        "username": username,
        "email": email,
        "phone_number": phone,
        "password": password,
        "confirm_password": confirm_password,
    }

    response = api_client.post(url, data, format="json")

    assert response.status_code == expected_status

    if expected_status == status.HTTP_201_CREATED:
        assert CustomUser.objects.filter(email=email).exists()
        assert "user" in response.data
     
        print(f"✅ User {username} created. Sleeping 60s so you can inspect DB...")
        time.sleep(60)
    else:
        assert not CustomUser.objects.filter(email=email, username=username).exists()


def test_username_must_be_alpha(api_client):
    """Negative: username must be only letters"""
    url = reverse("register")
    payload = {
        "username": "Test123",
        "email": "t@example.com",
        "phone_number": "9999999999",
        "password": "StrongPass123",
        "confirm_password": "StrongPass123",
    }
    res = api_client.post(url, payload, format="json")
    assert res.status_code == 400
    assert "Username must contain only letters" in str(res.data)


def test_password_mismatch(api_client):
    """Negative: confirm_password validation"""
    url = reverse("register")
    payload = {
        "username": "ValidUser",
        "email": "valid@example.com",
        "phone_number": "8888888888",
        "password": "abc",
        "confirm_password": "xyz",
    }
    res = api_client.post(url, payload, format="json")
    assert res.status_code == 400
    assert "Passwords do not match" in str(res.data)


def test_intentional_fail(api_client):
    """❌ Intentionally fail to show pytest failure report"""
    url = reverse("register")
    data = {
        "username": "Eve",
        "email": "eve@example.com",
        "phone_number": "1111111111",
        "password": "Pass12345",
        "confirm_password": "Pass12345",
    }
    response = api_client.post(url, data, format="json")

    # ❌ Intentional fail: Expect wrong code (400 instead of 201)
    assert response.status_code == 400, "Intentional fail for coverage demo"
