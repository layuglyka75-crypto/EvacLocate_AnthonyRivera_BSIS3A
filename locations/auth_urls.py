from django.urls import path

from .views import AdminLoginView, UserLoginView, register_admin

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('admin-login/', AdminLoginView.as_view(), name='admin-login'),
    path('admin-register/', register_admin, name='admin-register'),
]
