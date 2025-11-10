from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('driver','Driver'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class Vehicle(models.Model):
    STATUS_CHOICES = [('active','Active'),('inactive','Inactive'),('maintenance','Maintenance')]
    registration_no = models.CharField(max_length=30, unique=True)
    make = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_driver = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_vehicles')

    latitude  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.registration_no

class MaintenanceLog(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_logs')
    description = models.TextField()
    date = models.DateField()
    next_due = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.vehicle} - {self.date}"

class FuelLog(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='fuel_logs')
    date = models.DateField()
    liters = models.DecimalField(max_digits=8, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    odometer = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
