import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from project_app.models import Registration

# Get user count
user_count = Registration.objects.count()
print(f"Total users in database: {user_count}")

# Format for display
if user_count >= 100:
    display_count = (user_count // 100) * 100
else:
    display_count = user_count

print(f"Display count (rounded): {display_count}+")

# Show all users
users = Registration.objects.all()
print(f"\nRegistered users:")
for user in users:
    print(f"  - {user.name} ({user.email})")
