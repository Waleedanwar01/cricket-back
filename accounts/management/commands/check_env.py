import os
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Check environment variables'

    def handle(self, *args, **options):
        database_url = os.environ.get("DATABASE_URL", "Not set")
        print(f"DATABASE_URL: {database_url}")
        print(f"DATABASE_URL length: {len(database_url)}")
        print(f"DATABASE_URL repr: {repr(database_url)}")
        
        # Check if it starts with a scheme
        if database_url and "://" in database_url:
            scheme = database_url.split("://")[0]
            print(f"Scheme: {scheme}")
        else:
            print("No scheme found in DATABASE_URL")