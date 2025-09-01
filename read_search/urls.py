# read_search/urls.py
from django.urls import path
from .views import search_api, search_api_v2

urlpatterns = [
    path('read-search/', search_api, name='search_api'),
    path('read-search-v2/', search_api_v2, name='search_api_v2')
]