from django.contrib import admin
from .models import OwnerAccount # Import your new model here!

# Option 1: The quick and simple way
admin.site.register(OwnerAccount)