from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload_video, name='upload_video'),
    path('video/<int:video_id>/', views.video_detail, name='video_detail'),
    path('video/<int:video_id>/verify/', views.verification_dashboard, name='vehicle_verification_list'),
    path('vehicle/<str:license_plate>/', views.vehicle_details, name='vehicle_details'),
    path('search/', views.vehicle_search, name='vehicle_search'),
]