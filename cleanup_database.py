#!/usr/bin/env python3
"""
Clean up UFC/MMA database - removes all events and fighters
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/351f0834473bf4d2e391b5acf0ea9c949254dbec9244c1e72e733cbf7c7b0651')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings')
django.setup()

from django.db import transaction
from events.models import Event, EventNameVariation, Fight, FightParticipant
from fighters.models import Fighter, FighterNameVariation
from organizations.models import WeightClass

def cleanup_database():
    """Clean up all events and fighters from the database"""
    
    print("🧹 UFC/MMA Database Cleanup")
    print("=" * 50)
    
    # Count existing records
    event_count = Event.objects.count()
    fighter_count = Fighter.objects.count()
    fight_count = Fight.objects.count()
    
    print(f"Current database state:")
    print(f"  - Events: {event_count}")
    print(f"  - Fighters: {fighter_count}")
    print(f"  - Fights: {fight_count}")
    print()
    
    # Confirm deletion
    response = input("⚠️  This will DELETE all events and fighters. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cleanup cancelled")
        return
    
    print()
    print("🗑️  Starting cleanup...")
    
    try:
        with transaction.atomic():
            # Delete in correct order to handle foreign key constraints
            
            # 1. Delete fight participants (many-to-many)
            deleted = FightParticipant.objects.all().delete()
            print(f"  ✅ Deleted {deleted[0]} fight participants")
            
            # 2. Delete fights
            deleted = Fight.objects.all().delete()
            print(f"  ✅ Deleted {deleted[0]} fights")
            
            # 3. Delete event name variations
            deleted = EventNameVariation.objects.all().delete()
            print(f"  ✅ Deleted {deleted[0]} event name variations")
            
            # 4. Delete events
            deleted = Event.objects.all().delete()
            print(f"  ✅ Deleted {deleted[0]} events")
            
            # 5. Delete fighter name variations
            deleted = FighterNameVariation.objects.all().delete()
            print(f"  ✅ Deleted {deleted[0]} fighter name variations")
            
            # 6. Delete fighters
            deleted = Fighter.objects.all().delete()
            print(f"  ✅ Deleted {deleted[0]} fighters")
            
            # Optional: Keep weight classes as they're reference data
            keep_weight_classes = input("\n💭 Keep weight classes? (yes/no) [default: yes]: ").strip().lower()
            if keep_weight_classes == 'no':
                deleted = WeightClass.objects.all().delete()
                print(f"  ✅ Deleted {deleted[0]} weight classes")
            else:
                print("  ℹ️  Keeping weight classes")
            
            print()
            print("✨ Database cleanup completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return
    
    # Show final state
    print()
    print("Final database state:")
    print(f"  - Events: {Event.objects.count()}")
    print(f"  - Fighters: {Fighter.objects.count()}")
    print(f"  - Fights: {Fight.objects.count()}")
    print()
    print("🎯 Database is now clean and ready for fresh scraping!")

if __name__ == "__main__":
    cleanup_database()