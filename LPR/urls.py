from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('system-backdoor/', admin.site.urls), 

    path('', include('acc.urls')),  

    path('hq/', include('LicensePlate.urls')),  

    path('video/', include('alpr.urls')), 
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)