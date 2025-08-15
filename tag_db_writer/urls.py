from django.urls import path
from .views import general_match_view

urlpatterns = [
    path('api/general-match/', general_match_view, name='general_match'),
]