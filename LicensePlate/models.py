from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=50, unique=True)
    iso_code = models.CharField(max_length=3, unique=True)  
    phone_code = models.CharField(max_length=5)             
    driving_side = models.CharField(
        max_length=5,
        choices=[('L', 'Left'), ('R', 'Right')]
    )

    def __str__(self):
        return self.name


class Vehicle(models.Model):

    country = models.ForeignKey(Country, on_delete=models.PROTECT)

    license_plate = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20)
    manufacturer = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    variant = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20)
    fuel_type = models.CharField(max_length=20)
    registration_year = models.IntegerField()
    registration_valid = models.BooleanField(default=True)
    engine_capacity = models.IntegerField()
    emission_norm = models.CharField(max_length=20)
    chassis_number = models.CharField(max_length=50)
    engine_number = models.CharField(max_length=50)

    def __str__(self):
        return self.license_plate
    
    @property
    def has_violation(self):
        """Returns True if there are any unpaid fines."""
        return self.violation_set.filter(is_paid=False).exists()

from django.contrib.auth.models import User

class Owner(models.Model):
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)

    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=50, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField()

    def __str__(self):
        return self.full_name


class DrivingLicense(models.Model):
    owner = models.OneToOneField(Owner, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=30)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    license_class = models.CharField(max_length=10)
    issuing_authority = models.CharField(max_length=50)


class Insurance(models.Model):
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE)
    provider = models.CharField(max_length=50)
    policy_number = models.CharField(max_length=50)
    policy_type = models.CharField(max_length=30)
    start_date = models.DateField()
    expiry_date = models.DateField()
    active = models.BooleanField(default=True)


class Documents(models.Model):
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, related_name="documents")
    registration_certificate = models.BooleanField(default=False)
    insurance_document = models.BooleanField(default=False)
    pollution_certificate = models.BooleanField(default=False)
    fitness_certificate = models.CharField(max_length=20, choices=[
        ('Valid', 'Valid'),
        ('Due Soon', 'Due Soon'),
        ('Expired', 'Expired')
    ], default='Valid')

    def __str__(self):
        return f"Documents for {self.vehicle.license_plate}"
    


class Violation(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    violation_type = models.CharField(
        max_length=100,
        choices=[
            ("speeding", "Over Speeding"),
            ("signal", "Signal Jump"),
            ("helmet", "No Helmet"),
        ]
    )
    violation_date = models.DateField()
    fine_amount = models.IntegerField()
    accident = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.get_violation_type_display()}"

