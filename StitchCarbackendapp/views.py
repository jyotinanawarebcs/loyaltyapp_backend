from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets,permissions
from .models import Service
from .serializers import ServiceSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from .models import CustomUser
from .serializers import CustomUserSerializer
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import login
from .serializers import  RegisterSerializer,LoginSerializer,BookingSerializer
from .models import Booking,Customer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.views import APIView
from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.response import Response
from rest_framework.decorators import action

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer



class AdminServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAdminUser]

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
        
class RegisterAPIView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  

            return Response({
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "phone_number": user.phone_number,
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)

class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()  

            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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