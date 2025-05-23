from datetime import timedelta

from django.db.models import Q, Count
from .models import UserProfile, StudyInvite, AvailabilitySlot


def get_suggested_study_buddies(user_profile, min_duration=timedelta(hours=1)):
    print("=" * 40)
    print(f"Debug for get_suggested_study_buddies for user {user_profile} (id={user_profile.id})")

    """
    Suggests study buddies for the given user_profile based on:
    - Shared courses
    - Not already invited or already has a session
    - At least one overlapping availability slot
    - Compatible study styles
    """
    # Exclude users already invited or connected
    excluded_ids = set(
        StudyInvite.objects.filter(sender=user_profile).values_list('receiver_id', flat=True)
    ).union(
        StudyInvite.objects.filter(receiver=user_profile).values_list('sender_id', flat=True)
    )
    excluded_ids.add(user_profile.id)
    print(f"Excluded user IDs (already invited or self): {excluded_ids}")

    my_courses = list(user_profile.courses.all())
    print(f"Your courses: {[c.code for c in my_courses]}")

    # Find users sharing at least one course
    shared_course_users = UserProfile.objects \
        .filter(courses__in=user_profile.courses.all()) \
        .exclude(id__in=excluded_ids) \
        .annotate(shared_courses=Count('courses')) \
        .order_by('-shared_courses') \
        .distinct()

    print(f"Found {shared_course_users.count()} users sharing courses with you:")

    # Get user's availability
    user_avail = AvailabilitySlot.objects.filter(user_profile=user_profile)
    print(f"Your availability slots: {len(user_avail)}")

    suggestions = []

    for other_user_profile in shared_course_users:
        print(f"\nChecking available slots for {other_user_profile} (id={other_user_profile.id})")
        other_avail = AvailabilitySlot.objects.filter(user_profile=other_user_profile)
        # Here, get_common_time_slots must be the corrected one using start_hour.weekday()

        print(f"  {other_user_profile}'s availability slots: {len(other_avail)}")
        common_slots = get_common_time_slots(user_avail, other_avail)
        print(f"  Found {len(common_slots)} common slots.")
        if not common_slots:
            print("    Skipped: No common time slots.")
            continue

        # Make sure compatible_styles is implemented and available in this module
        if not compatible_styles(user_profile, other_user_profile):
            print("    Skipped: Incompatible study styles.")
            continue

        weekdays = sorted(set(slot[0] for slot in common_slots))
        suggestions.append({
            'profile': other_user_profile,
            'slots': common_slots,
            'weekdays': weekdays,
        })


    print(f"\nTotal suggestions made: {len(suggestions)}")
    print("=" * 40)

    return suggestions


def get_common_time_slots(user_slots, other_slots, min_duration=timedelta(hours=1)):
    """
    Returns a list of tuples (weekday, start, end) of overlapping time slots
    between two users. Only returns overlaps of at least min_duration (default 1 hour).
    Assumes each slot has attributes: weekday, start_hour, end_hour (all datetimes or times).
    """
    matches = []
    for slot1 in user_slots:
        for slot2 in other_slots:
            if slot1.start_hour.date() == slot2.start_hour.date():
                # Overlap check
                start = max(slot1.start_hour, slot2.start_hour)
                end = min(slot1.end_hour, slot2.end_hour)
                if start < end and (end - start) >= min_duration:
                    matches.append((slot1.start_hour.weekday(), start, end))
    return matches


def compatible_styles(user1, user2):
    # Match if same style or either is 'mixed'
    return (
        user1.study_style == user2.study_style
        or user1.study_style == 'mixed'
        or user2.study_style == 'mixed'
    )

