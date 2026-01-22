import os
import django
import random
import sys

# Setup Django environment
# Assumes the script is in the project root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project_Zhihui.settings')
django.setup()

from user.models import User

def update_avatars():
    """
    Update all users' avatars to one of the 5 default avatars randomly.
    Path format: avatars/default/avatar_x.svg
    """
    default_avatars = [
        'avatars/default/avatar_1.svg',
        'avatars/default/avatar_2.svg',
        'avatars/default/avatar_3.svg',
        'avatars/default/avatar_4.svg',
        'avatars/default/avatar_5.svg',
    ]

    print("Checking default avatars existence...")
    base_media_path = os.path.join(os.getcwd(), 'media')
    for avatar_path in default_avatars:
        full_path = os.path.join(base_media_path, avatar_path)
        if not os.path.exists(full_path):
            print(f"Warning: Avatar file not found at {full_path}")
        else:
            # print(f"Confirmed: {full_path}")
            pass

    users = User.objects.all()
    count = users.count()
    print(f"Found {count} users. Updating avatars...")

    updated_count = 0
    for user in users:
        # Randomly select an avatar
        selected_avatar = random.choice(default_avatars)
        
        # Update the avatar field
        # We store the relative path to MEDIA_ROOT
        user.avatar = selected_avatar
        user.save(update_fields=['avatar'])
        updated_count += 1
        
        if updated_count % 100 == 0:
            print(f"Updated {updated_count} users...")

    print(f"Successfully updated {updated_count} users with random default avatars.")

if __name__ == '__main__':
    try:
        update_avatars()
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
