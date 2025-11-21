"""
URL configuration for dailymed_web project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('search.urls')),
    path('api/', include('search.api_urls')),
]

