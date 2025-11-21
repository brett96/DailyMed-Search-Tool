"""
Django views for the search application.
"""
from django.shortcuts import render


def search_page(request):
    """
    Main search page view.
    """
    return render(request, 'search/search.html')

