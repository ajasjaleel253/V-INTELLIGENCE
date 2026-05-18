# LicensePlate/models.py
from django.db import models

class OwnerAccount(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  

    def __str__(self):
        return self.email