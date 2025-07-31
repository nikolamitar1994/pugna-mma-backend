#!/usr/bin/env python3
"""
Quick script to check recent fight data for ending times and winner issues
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('/mnt/wsl/docker-desktop-bind-mounts/Ubuntu/351f0834473bf4d2e391b5acf0ea9c949254dbec9244c1e72e733cbf7c7b0651')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mma_backend.settings')
django.setup()

from events.models import Event, Fight
from fighters.models import Fighter

def main():
    # Get the most recent event (likely UFC 312)
    recent_event = Event.objects.order_by('-created_at').first()
    print(f'Most recent event: {recent_event.name}')
    print(f'Event date: {recent_event.date}')
    print(f'Total fights: {Fight.objects.filter(event=recent_event).count()}')
    print()

    # Check ending times and winner assignment
    fights = Fight.objects.filter(event=recent_event).order_by('fight_order')
    issues_found = []
    
    for fight in fights:
        participants = fight.participants.all()
        f1 = participants.filter(corner='red').first()
        f2 = participants.filter(corner='blue').first()
        
        print(f'Fight {fight.fight_order}: {f1.fighter.get_full_name()} vs {f2.fighter.get_full_name()}')
        print(f'  Winner: {fight.winner.get_full_name() if fight.winner else "None"}')
        print(f'  Method: {fight.method} ({fight.method_details})')
        print(f'  Ending: Round {fight.ending_round}, Time: "{fight.ending_time}"')
        print(f'  Results: {f1.fighter.get_full_name()}={f1.result}, {f2.fighter.get_full_name()}={f2.result}')
        
        # Check for issues
        if not fight.ending_time or fight.ending_time.strip() == "":
            issues_found.append(f"Fight {fight.fight_order}: Missing ending time")
        
        if fight.ending_round == 1 and fight.method and "decision" not in fight.method.lower():
            issues_found.append(f"Fight {fight.fight_order}: Suspicious ending round (Round 1 for non-decision)")
        
        # Check if winner is marked correctly
        if fight.winner:
            winner_participant = participants.filter(fighter=fight.winner).first()
            if winner_participant and winner_participant.result != 'win':
                issues_found.append(f"Fight {fight.fight_order}: Winner {fight.winner.get_full_name()} has result '{winner_participant.result}' instead of 'win'")
        else:
            issues_found.append(f"Fight {fight.fight_order}: No winner assigned!")
        print()
    
    print("=" * 50)
    print("ISSUES SUMMARY:")
    if issues_found:
        for issue in issues_found:
            print(f"⚠️  {issue}")
    else:
        print("✅ No issues found!")

if __name__ == "__main__":
    main()