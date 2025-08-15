from django.urls import path
from . import views

app_name = 'process_pdf'

urlpatterns = [
    path('process-pdf/', views.upload_pdf, name='upload_pdf'),
]