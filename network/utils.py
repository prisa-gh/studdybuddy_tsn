from datetime import timedelta

from django.db.models import Q, Count
from .models import UserProfile, StudyInvite, AvailabilitySlot


def get_suggested_study_buddies(user_profile):
    # Exclude users already invited or connected
    excluded_ids = set(
        StudyInvite.objects.filter(sender=user_profile).values_list('receiver_id', flat=True)
    ).union(
        StudyInvite.objects.filter(receiver=user_profile).values_list('sender_id', flat=True)
    )
    excluded_ids.add(user_profile.id)

    # Find users sharing at least one course
    shared_course_users = UserProfile.objects \
        .filter(courses__in=user_profile.courses.all()) \
        .exclude(id__in=excluded_ids) \
        .annotate(shared_courses=Count('courses')) \
        .order_by('-shared_courses') \
        .distinct()

    # Get user's availability
    user_avail = AvailabilitySlot.objects.filter(user_profile=user_profile)

    suggestions = []

    for other in shared_course_users:
        other_avail = AvailabilitySlot.objects.filter(user_profile=other)
        common_slots = get_common_time_slots(user_avail, other_avail)
        if common_slots and compatible_styles(user_profile, other):
            # derive unique weekdays
            weekdays = sorted(set(slot[0] for slot in common_slots))
            suggestions.append({
                'profile': other,
                'slots': common_slots,
                'weekdays': weekdays,
            })

    return suggestions

def get_common_time_slots(user_slots, other_slots):
    matches = []
    for slot1 in user_slots:
        for slot2 in other_slots:
            if slot1.weekday == slot2.weekday:
                if slot1.start_hour < slot2.end_hour and slot2.start_hour < slot1.end_hour:
                    start = max(slot1.start_hour, slot2.start_hour)
                    end = min(slot1.end_hour, slot2.end_hour)
                    matches.append((slot1.weekday, start, end))
    return matches

def has_overlap(user_slots, other_slots):
    for slot1 in user_slots:
        for slot2 in other_slots:
            if slot1.weekday == slot2.weekday:
                if slot1.start_hour < slot2.end_hour and slot2.start_hour < slot1.end_hour:
                    return True
    return False


def compatible_styles(user1, user2):
    # Match if same style or either is 'mixed'
    return (
        user1.study_style == user2.study_style
        or user1.study_style == 'mixed'
        or user2.study_style == 'mixed'
    )
