"""
URL configuration for API endpoints.
"""
from django.urls import path
from . import api_views

urlpatterns = [
    path('drug-autocomplete/', api_views.drug_autocomplete, name='drug-autocomplete'),
    path('search/', api_views.search_drugs, name='search'),
    path('excipient-categories/', api_views.excipient_categories, name='excipient-categories'),
]

