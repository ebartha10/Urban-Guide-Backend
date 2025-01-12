"""
URL configuration for urbanGuideBackend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from .views import *
from django.conf.urls.static import static
from django.conf import settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Login endpoint
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh token endpoint
    path('api/protected/', protected_view, name='protected_view'),
    path('api/register/', register_user, name='register_user'),  # Registration
    # Profile creation
    path('api/profile/create/', UserProfileCreateView.as_view(), name='create_profile'),

    # Profile update
    path('api/profile/update/', UserProfileUpdateView.as_view(), name='update_profile'),
    path('api/places/', views.get_places, name='get_places'),
    path('api/schedule/create/', views.create_schedule, name='create_schedule'),
    path('api/schedule/get_active_schedule/', views.get_active_schedule, name='get_active_schedule'),
    path('api/schedule/get_next_venue/', views.get_next_venue, name='get_next_venue'),
    path('api/schedule/check_in/', views.start_visit, name='start_visit'),
    path('api/schedule/check_out/', views.end_visit, name='end_visit'),
    path('api/schedule/history/', views.get_schedule_history, name='get_schedule_history'),
    path('api/profile/get/', views.get_user_profile, name='get_profile'),
    path('api/places/details/<str:place_id>/', views.get_place_details, name='get_place_details'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
