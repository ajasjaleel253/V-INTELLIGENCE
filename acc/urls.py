from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_login_view, name='root'),
    path('user/login/', views.user_login_view, name='user_login'),
    
    path('staff/login/', views.admin_login_view, name='admin_login'), 
    
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('pay-fine/<int:violation_id>/', views.pay_fine_api, name='pay_fine_api'),
]