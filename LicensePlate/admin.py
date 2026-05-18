from django.contrib import admin
from .models import (
    Country,  
    Vehicle,
    Owner,
    DrivingLicense,
    Insurance,
    Documents,
    Violation,
    
)

admin.site.register(Country)
admin.site.register(Vehicle)
admin.site.register(Owner)
admin.site.register(DrivingLicense)
admin.site.register(Insurance)
admin.site.register(Documents)
admin.site.register(Violation)
