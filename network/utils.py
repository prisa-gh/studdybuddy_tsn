from django.db.models import Q, Count
from datetime import timedelta
from .models import UserProfile, StudyBuddyInvite, StudyBuddy

import networkx as nx
import matplotlib.pyplot as plt

# network/utils.py

def build_study_network_graph():
    G = nx.Graph()
    # Add nodes for all users
    users = UserProfile.objects.all()
    for user in users:
        G.add_node(user.id, label=user.user.username)



    # Add edges from study sessions (accepted connections)
    study_buddies = StudyBuddy.objects.all()
    for study_buddy in study_buddies:
        G.add_edge(study_buddy.participant_one.id, study_buddy.participant_two.id, type='study_buddy')

    # Add directed edges for all invites (optional: only show pending or all)
    invites = StudyBuddyInvite.objects.all()
    for invite in invites:
        G.add_edge(invite.sender.id, invite.receiver.id, type='invite', status=invite.status)

    print(f"Graph nodes: {G.nodes}")
    print(f"Graph edges: {G.edges}")
    return G


def draw_study_network_graph(G):
    pos = nx.spring_layout(G)
    edge_colors = ['green' if d.get('type') == 'session' else 'blue' for _,_,d in G.edges(data=True)]
    nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'),
            edge_color=edge_colors, node_size=800, node_color='lightgray')
    plt.show()

def get_suggested_study_buddies(user_profile):
    print("=" * 40)
    print(f"Debug for get_suggested_study_buddies for user {user_profile} (id={user_profile.id})")

    # Exclude users already invited or connected
    excluded_ids = set(
        StudyBuddyInvite.objects.filter(sender=user_profile).values_list('receiver_id', flat=True)
    ).union(
        StudyBuddyInvite.objects.filter(receiver=user_profile).values_list('sender_id', flat=True)
    )
    excluded_ids.add(user_profile.id)
    print(f"Excluded user IDs (already invited or self): {excluded_ids}")

    # Find users sharing at least one course
    shared_course_users = UserProfile.objects \
        .filter(courses__in=user_profile.courses.all()) \
        .exclude(id__in=excluded_ids) \
        .annotate(shared_courses=Count('courses')) \
        .order_by('-shared_courses') \
        .distinct()

    print(f"Found {shared_course_users.count()} users sharing courses with you:")

    my_weekdays =  list(user_profile.available_weekdays)
    # Get user's availability
    compatible_days = UserProfile.objects \
        .filter(available_weekdays__overlap=user_profile.available_weekdays) \
        .exclude(id__in=excluded_ids) \
        .annotate(shared_days=Count('available_weekdays')) \
        .order_by('-shared_days') \
        .distinct()
    print(f"Your availability days: {len(compatible_days)}")

    my_courses = set(c.code for c in user_profile.courses.all())
    my_days = set(user_profile.available_weekdays)

    suggestions = []

    for other_user_profile in shared_course_users and compatible_days:
        if not compatible_styles(user_profile, other_user_profile):
            print("    Skipped: Incompatible study styles.")
            continue
        other_courses = set(c.code for c in other_user_profile.courses.all())
        overlapping_courses = my_courses & other_courses  # set intersection

        other_days = set(other_user_profile.available_weekdays)
        overlapping_days = my_days & other_days

        study_style_match = (user_profile.study_style == other_user_profile.study_style or
                             user_profile.study_style == 'mixed' or
                             other_user_profile.study_style == 'mixed')

        suggestions.append({
            'profile': other_user_profile,
            'courses': overlapping_courses,
            'days': overlapping_days,
            'style_match': study_style_match,
            'user_study_style': user_profile.study_style,
            'other_study_style': other_user_profile.study_style,
        })

    print(f"\nTotal suggestions made: {len(suggestions)}")
    for suggestion in suggestions:
        print(f"Study buddy suggestions: {suggestion['profile'].user.username} - courses: {suggestion['courses']}, days: {suggestion['days']}")

    return suggestions


def get_foaf_recommendations(user_profile):
    G = build_study_network_graph()
    user_id = user_profile.id
    if user_id not in G:
        return []

    # Get direct buddies
    direct_buddies = set(G.neighbors(user_id))
    print(f"User {user_profile} (id={user_id}) has {len(direct_buddies)} direct buddies.")
    print(f"Direct buddies: {direct_buddies}")

    # To keep only "first instance" of each FOAF, use a set to mark collected
    foafs = []
    seen = set()
    for buddy_id in direct_buddies:
        for foaf_id in G.neighbors(buddy_id):
            if (
                foaf_id != user_id and                 # not self
                foaf_id not in direct_buddies and      # not a direct buddy
                foaf_id not in seen                    # not already collected via another buddy
            ):
                seen.add(foaf_id)
                mutual_buddies_ids = direct_buddies.intersection(G.neighbors(foaf_id))
                # Retrieve usernames for mutual buddies
                mutual_buddies = UserProfile.objects.filter(id__in=mutual_buddies_ids).select_related("user")
                buddy_names = [b.user.username for b in mutual_buddies]
                # Accumulate all data as a dictionary

                foafs.append({
                    "id": foaf_id,
                    "buddy_names": buddy_names,
                    "name": UserProfile.objects.get(id=foaf_id).user.username,
                })

                print(f"Added FOAF: {foaf_id} via buddy {buddy_id}")

    # Exclude users already invited (pending/rejected)
    invited_ids = set(
        user_profile.sent_invites.values_list('receiver_id', flat=True)
    ).union(
        user_profile.received_invites.values_list('sender_id', flat=True)
    )

    # Filter out those already invited
    foafs = [foaf for foaf in foafs if foaf["id"] not in invited_ids]

    print(f"Final FOAF: {foafs} ")
    return foafs

def compatible_styles(user1, user2):
    # Match if same style or either is 'mixed'
    return (
        user1.study_style == user2.study_style
        or user1.study_style == 'mixed'
        or user2.study_style == 'mixed'
    )

