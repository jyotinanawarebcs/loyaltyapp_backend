import pytest
from rest_framework import status
from django.urls import reverse
from StitchCarbackendapp.models import Service

pytestmark = pytest.mark.django_db(transaction=True)

# ------------------------------------------------------------
# FIXTURES
# ------------------------------------------------------------
@pytest.fixture
def create_admin_user(db, django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass"
    )

@pytest.fixture
def create_normal_user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="user", email="user@example.com", password="userpass"
    )

@pytest.fixture
def sample_service(db):
    return Service.objects.create(
        title="Car Wash",
        description="Full car wash and interior cleaning",
        price=499
    )

# ------------------------------------------------------------
# PUBLIC SERVICE LIST (ALLOW ANY)
# ------------------------------------------------------------
def test_service_list_public(api_client, sample_service):
    """✅ Anyone can view service list"""
    url = reverse("service-list")  # ✅ Correct name
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) > 0
    assert response.data[0]["title"] == "Car Wash"

# ------------------------------------------------------------
# PUBLIC SERVICE RETRIEVE (ALLOW ANY)
# ------------------------------------------------------------
def test_service_retrieve_public(api_client, sample_service):
    """✅ Anyone can view single service"""
    url = reverse("service-detail", args=[sample_service.id])  # ✅ Correct name
    response = api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Car Wash"

# ------------------------------------------------------------
# CREATE SERVICE (ADMIN ONLY)
# ------------------------------------------------------------
def test_service_create_admin(api_client, create_admin_user):
    """✅ Admin can create a new service"""
    api_client.force_authenticate(user=create_admin_user)
    url = reverse("service-list")  # ✅ Correct name
    payload = {
        "title": "Tyre Replacement",
        "description": "Change and balance tyres",
        "price": 1200
    }
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert Service.objects.filter(title="Tyre Replacement").exists()

# ------------------------------------------------------------
# CREATE SERVICE (NON-ADMIN)
# ------------------------------------------------------------
def test_service_create_non_admin(api_client, create_normal_user):
    """❌ Non-admin cannot create a service"""
    api_client.force_authenticate(user=create_normal_user)
    url = reverse("service-list")  # ✅ Correct name
    payload = {
        "title": "Tyre Repair",
        "description": "Quick puncture repair",
        "price": 200
    }
    response = api_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert not Service.objects.filter(title="Tyre Repair").exists()

# ------------------------------------------------------------
# UPDATE SERVICE (ADMIN ONLY)
# ------------------------------------------------------------
def test_service_update_admin(api_client, create_admin_user, sample_service):
    """✅ Admin can update service"""
    api_client.force_authenticate(user=create_admin_user)
    url = reverse("service-detail", args=[sample_service.id])  # ✅ Correct name
    response = api_client.patch(url, {"price": 599}, format="json")
    assert response.status_code == status.HTTP_200_OK
    sample_service.refresh_from_db()
    assert sample_service.price == 599

# ------------------------------------------------------------
# DELETE SERVICE (ADMIN ONLY)
# ------------------------------------------------------------
def test_service_delete_admin(api_client, create_admin_user, sample_service):
    """✅ Admin can delete service"""
    api_client.force_authenticate(user=create_admin_user)
    url = reverse("service-detail", args=[sample_service.id])  # ✅ Correct name
    response = api_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Service.objects.filter(id=sample_service.id).exists()

# ------------------------------------------------------------
# DELETE SERVICE (NON-ADMIN)
# ------------------------------------------------------------
def test_service_delete_non_admin(api_client, create_normal_user, sample_service):
    """❌ Non-admin cannot delete"""
    api_client.force_authenticate(user=create_normal_user)
    url = reverse("service-detail", args=[sample_service.id])  # ✅ Correct name
    response = api_client.delete(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Service.objects.filter(id=sample_service.id).exists()

def test_intentional_fail_for_demo(sample_service):
    """❌ This one is expected to fail intentionally"""
    assert sample_service.price == 999  # wrong on purpose
