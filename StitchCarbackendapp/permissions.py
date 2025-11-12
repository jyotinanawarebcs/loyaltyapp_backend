from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsCustomerOrReadOnly(BasePermission):
    """
    Read: Everyone (including guest)
    Write (POST/PUT/DELETE): Only logged-in customers
    Admin can access all
    """
    def has_permission(self, request, view):
        # Allow read-only requests for everyone
        if request.method in SAFE_METHODS:
            return True

        # Allow write only to authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read-only allowed always
        if request.method in SAFE_METHODS:
            return True

        # Admin can do anything
        if request.user.is_staff:
            return True

        # Only owner can modify their booking
        return obj.customer.user == request.user
