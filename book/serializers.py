from rest_framework import serializers
from .models import Book
from django.contrib.auth.models import User

PRICE_PER_HOUR = 1500  # <--- add this

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'name', 'email', 'phone', 'date', 'time', 'hours', 'total_price', 'user', 'status', 'payment_status', 'created_at', 'updated_at']
        read_only_fields = ['user', 'total_price', 'status', 'payment_status', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Calculate total price
        hours = validated_data.get("hours", 0)
        validated_data["total_price"] = hours * PRICE_PER_HOUR
        return super().create(validated_data)
