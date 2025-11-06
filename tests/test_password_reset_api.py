import pytest
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import status
from StitchCarbackendapp.models import CustomUser, PasswordResetCode

token_generator = PasswordResetTokenGenerator()

pytestmark = pytest.mark.django_db(transaction=True)


# -------------------------- Password Reset Request --------------------------
@pytest.mark.parametrize(
    "email,exists,expected_status",
    [
        ("valid@example.com", True, 200),      # ✅ existing user
        ("fake@example.com", False, 200),      # ✅ should not leak user existence
    ],
)
def test_password_reset_request(api_client, create_test_user, email, exists, expected_status, mocker):
    """
    Test Password Reset Request API
      - If user exists: endpoint returns 200 and email is sent (we mock send_mail)
      - If user does not exist: endpoint still returns 200 (no info leak) and no email is sent
    """
    if exists:
        create_test_user(username="ValidUser", email=email)

    mock_send = mocker.patch("django.core.mail.send_mail", return_value=1)

    url = reverse("password_reset")
    res = api_client.post(url, {"email": email}, format="json")

    assert res.status_code == expected_status
    assert "message" in res.data

    if exists:
        # send_mail should be called when user exists
        assert mock_send.called, "Expected send_mail to be called for existing user"
    else:
        # should not call send_mail for non-existing user
        assert not mock_send.called, "send_mail should NOT be called for non-existing user"


# -------------------------- Password Reset Confirm --------------------------
@pytest.mark.parametrize(
    "valid_token,expected_status",
    [
        (True, 200),   # ✅ valid token -> password reset successful
        (False, 400),  # ❌ invalid token -> error
    ],
)
def test_password_reset_confirm(api_client, create_test_user, valid_token, expected_status):
    """Test Password Reset Confirm API (valid and invalid token)"""
    user = create_test_user(username="ResetUser", email="reset@example.com")

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = (
        PasswordResetTokenGenerator().make_token(user)
        if valid_token else "invalid-token"
    )

    url = reverse("password_reset_confirm")
    payload = {
        "uid": uid,
        "token": token,
        "new_password": "NewPass123",
        "confirm_password": "NewPass123",
    }

    res = api_client.post(url, payload, format="json")
    assert res.status_code == expected_status

    if expected_status == 200:
        # successful reset message
        assert res.data.get("message") == "Password has been reset successfully."
        # ensure password actually changed
        user.refresh_from_db()
        assert user.check_password("NewPass123")
    else:
        assert "error" in res.data


# -------------------------- Password Mismatch --------------------------
def test_password_mismatch_in_reset(api_client, create_test_user):
    """Negative: confirm_password must match"""
    user = create_test_user(username="MismatchUser", email="mismatch@example.com")

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)

    url = reverse("password_reset_confirm")
    payload = {
        "uid": uid,
        "token": token,
        "new_password": "abc",
        "confirm_password": "xyz",
    }

    res = api_client.post(url, payload, format="json")
    assert res.status_code == 400
    # serializer returns confirm_password error mapping
    assert "confirm_password" in str(res.data) or "Passwords do not match" in str(res.data)


# -------------------------- Send Verification Code --------------------------
def test_send_verification_code_success(api_client, create_test_user, mocker):
    """Positive: send verification code creates DB record and triggers email send (mocked)"""
    user = create_test_user(username="OTPUser", email="otp@example.com")

    mock_send = mocker.patch("django.core.mail.send_mail", return_value=1)
    url = reverse("send_verification_code")
    res = api_client.post(url, {"email": user.email}, format="json")

    assert res.status_code == 200
    assert "verification code" in res.data.get("message", "").lower()
    # DB record created
    assert PasswordResetCode.objects.filter(user=user).exists()
    # send_mail called
    assert mock_send.called


# -------------------------- Send Verification Code (no user) --------------------------
def test_send_verification_code_no_user(api_client, mocker):
    """Negative: email not found should return 404"""
    mock_send = mocker.patch("django.core.mail.send_mail", return_value=1)
    url = reverse("send_verification_code")
    res = api_client.post(url, {"email": "nouser@example.com"}, format="json")

    assert res.status_code == 404
    assert "no user" in str(res.data).lower()
    assert not mock_send.called


# -------------------------- Verify Code --------------------------
def test_verify_code_success(api_client, create_test_user):
    """Positive: verify a valid code and return uid & token"""
    user = create_test_user(username="VerifyUser", email="verify@example.com")
    code_obj = PasswordResetCode.objects.create(user=user, code="123456")

    url = reverse("verify_code")
    payload = {"email": user.email, "code": "123456"}
    res = api_client.post(url, payload, format="json")

    assert res.status_code == 200
    assert "verification successful" in res.data.get("message", "").lower()
    assert "uid" in res.data and "token" in res.data


# -------------------------- Verify Code (wrong) --------------------------
@pytest.mark.parametrize(
    "email,code,expected_status",
    [
        ("invalid@example.com", "123456", 400),  # ❌ invalid email
        ("verify@example.com", "999999", 400),   # ❌ wrong code
    ],
)
def test_verify_code_negative(api_client, create_test_user, email, code, expected_status):
    """Negative: invalid email/code"""
    user = create_test_user(username="VerifyUser", email="verify@example.com")
    PasswordResetCode.objects.create(user=user, code="123456")

    url = reverse("verify_code")
    payload = {"email": email, "code": code}
    res = api_client.post(url, payload, format="json")

    assert res.status_code == expected_status
    assert "error" in res.data


# -------------------------- Intentional Fail --------------------------
def test_intentional_fail_password_reset(api_client):
    """❌ Intentional fail to demonstrate pytest failure"""
    url = reverse("password_reset")
    res = api_client.post(url, {"email": "fail@example.com"}, format="json")

    # Intentional wrong expectation
    assert res.status_code == 400, "Intentional fail for demo"
