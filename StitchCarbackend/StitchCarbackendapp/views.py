from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Booking, Customer, CustomUser
from .serializers import BookingSerializer


class IsCustomerOrReadOnly(permissions.BasePermission):
    """
    Allow safe methods for anyone (or restrict to staff); unsafe methods allowed
    only if user is the booking.customer or staff.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        try:
            return obj.customer.user == request.user
        except Exception:
            return False


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().select_related('customer__user', 'service', 'offer')
    serializer_class = BookingSerializer
    permission_classes = [IsCustomerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['service__title', 'customer__user__username', 'status', 'vehicle_make', 'vehicle_model']
    ordering_fields = ['booking_date', 'appointment_date', 'total_price']
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated and not user.is_staff:
            try:
                customer = Customer.objects.get(user=user)
                return qs.filter(customer=customer)
            except Customer.DoesNotExist:
                return Booking.objects.none()
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        customer_data = self.request.data.get("customer", None)

        # Normal user → assign their own customer
        if user.is_authenticated and not user.is_staff:
            try:
                customer = Customer.objects.get(user=user)
                serializer.save(customer=customer)
                return
            except Customer.DoesNotExist:
                raise PermissionError("No Customer profile found for this user.")

        # Admin → can select customer by ID from dropdown
        if customer_data:
            try:
                # Convert to int in case it's a string
                customer = Customer.objects.get(id=int(customer_data))
                serializer.save(customer=customer)
                return
            except (ValueError, Customer.DoesNotExist):
                raise serializers.ValidationError("Customer not found.")

        # Admin fallback: allow saving without specifying customer (should not happen normally)
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        # Allow only owner or staff
        if not (request.user.is_staff or booking.customer.user == request.user):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        booking.status = 'cancelled'
        booking.save()
        return Response(self.get_serializer(booking).data)

#================================================================================================
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import CustomUser
from .serializers import CustomUserSerializer

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]  # Only logged-in users can view/edit

    # Optional: customize create to handle password
    def perform_create(self, serializer):
        user = serializer.save()
        password = self.request.data.get('password')
        if password:
            user.set_password(password)
            user.save()
