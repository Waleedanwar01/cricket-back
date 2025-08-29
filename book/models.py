from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class Book(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True)
    phone = models.CharField(max_length=20)
    date = models.DateField()
    time = models.TimeField()
    hours = models.PositiveIntegerField()
    total_price = models.PositiveIntegerField(default=0)
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="unpaid")
    canceled_at = models.DateTimeField(null=True, blank=True)
    confirmation_token = models.CharField(max_length=128, null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True)  # record kab create hua
    updated_at = models.DateTimeField(
        auto_now=True)      # record kab update hua

    def __str__(self):
        return f"{self.name} - {self.date} {self.time} ({self.hours} hrs)"
