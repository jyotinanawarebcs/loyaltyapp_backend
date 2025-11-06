import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from StitchCarbackendapp.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_test_user(db):
    """Reusable fixture to create users easily"""
    def make_user(username="testuser", email="test@example.com", password="StrongPass123", is_staff=False, is_active=True):
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=is_staff,
            is_active=is_active
        )
        return user
    return make_user


@pytest.mark.parametrize(
    "username,password,from_device,expected_status",
    [
        # ✅ Positive (normal user login)
        ("Alice", "StrongPass123", "mobile", 200),
        # ✅ Positive (staff user via web)
        ("Admin", "AdminPass123", "web", 200),
        # ❌ Negative (invalid password)
        ("Alice", "WrongPass", "mobile", 400),
        # ❌ Negative (inactive user)
        ("InactiveUser", "InactivePass", "mobile", 400),
        # ❌ Negative (web login not allowed for non-admin)
        ("Alice", "StrongPass123", "web", 403),
    ],
)
def test_login_api(api_client, create_test_user, username, password, from_device, expected_status):
    """
    ✅ + ❌ Parameterized Login API Tests (Serializer + View)
    Covers:
    - Correct credentials
    - Invalid credentials
    - Disabled user
    - Access denied for normal user on web
    """

    # Create users based on test case
    if username == "Alice":
        create_test_user(username="Alice", email="alice@example.com", password="StrongPass123", is_staff=False)
    elif username == "Admin":
        create_test_user(username="Admin", email="admin@example.com", password="AdminPass123", is_staff=True)
    elif username == "InactiveUser":
        create_test_user(username="InactiveUser", email="inactive@example.com", password="InactivePass", is_active=False)

    url = reverse("login")  # URL name in urls.py

    data = {
        "username": username,
        "password": password,
        "device": from_device
    }

    response = api_client.post(url, data, format="json")

    print(f"\n[DEBUG] {username=} {from_device=} {response.status_code=} {response.data=}")

    assert response.status_code == expected_status

    # ✅ Positive assertions
    if expected_status == 200:
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        assert response.data["user"]["username"] == username

    # ❌ Negative assertions
    else:
        assert "error" in str(response.data) or "Invalid" in str(response.data) or "denied" in str(response.data)


def test_login_missing_fields(api_client):
    """❌ Missing username/password fields"""
    url = reverse("login")
    data = {"username": "", "password": ""}
    response = api_client.post(url, data, format="json")
    assert response.status_code == 400
    assert "Must include username and password" in str(response.data)


def test_invalid_user_login(api_client):
    """❌ Invalid username"""
    url = reverse("login")
    data = {"username": "GhostUser", "password": "somepass"}
    response = api_client.post(url, data, format="json")
    assert response.status_code == 400
    assert "Invalid username or password" in str(response.data)


def test_intentional_fail_login(api_client, create_test_user):
    """❌ Intentional Fail: Expecting wrong code for demo"""
    create_test_user(username="Eve", email="eve@example.com", password="EvePass123")
    url = reverse("login")
    data = {"username": "Eve", "password": "EvePass123"}
    response = api_client.post(url, data, format="json")
    # Intentional wrong expectation
    assert response.status_code == 400, "Intentional fail for coverage demo"
