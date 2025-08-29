# admin.py
from django.contrib import admin
from .models import Book

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'date', 'time', 'hours', 'total_price', 'status', 'payment_status')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('date', 'time', 'status', 'payment_status')
