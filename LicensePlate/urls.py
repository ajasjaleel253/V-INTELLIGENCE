from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home_page'), 
    path('scanner/', views.license_plate_detection, name='vehicle_intelligence'),
    path('detect/', views.license_plate_detection, name='uploaded_image'),
]