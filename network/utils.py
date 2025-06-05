from django.db.models import Q, Count
from datetime import timedelta

from networkx.drawing import spring_layout

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



def draw_study_network_graph(G, user_node=None, buddy_nodes=None, recommendation_nodes=None):
    if buddy_nodes is None:
        buddy_nodes = []
    if recommendation_nodes is None:
        recommendation_nodes = []

    pos = nx.spring_layout(G)
    node_colors = []
    for n in G.nodes():
        if str(n) == str(user_node):
            node_colors.append('#FFD600')     # Gold for user
        elif str(n) in [str(b) for b in buddy_nodes]:
            node_colors.append('#1976d2')     # Blue for buddies
        elif str(n) in [str(r) for r in recommendation_nodes]:
            node_colors.append('#FFAB40')     # Faint orange for recommendations
        else:
            node_colors.append('lightgray')

    edge_colors = ['green' if d.get('type') == 'session' else 'blue' for _, _, d in G.edges(data=True)]
    nx.draw(
        G, pos=spring_layout(G, k=0.8),
        with_labels=True, labels=nx.get_node_attributes(G, 'label'),
        edge_color=edge_colors,
        node_size=800,
        node_color=node_colors,
        linewidths=2,
        edgecolors='black'
    )
    plt.tight_layout()

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
        .distinct()

    print(f"Found {shared_course_users.count()} users sharing courses with you:")

    compatible_days = UserProfile.objects \
        .filter(available_weekdays__overlap=user_profile.available_weekdays) \
        .exclude(id__in=excluded_ids) \
        .distinct()

    print(f"Your availability days: {len(compatible_days)}")

    shared_course_ids = set(shared_course_users.values_list("id", flat=True))
    compatible_day_ids = set(compatible_days.values_list("id", flat=True))
    matching_user_ids = shared_course_ids & compatible_day_ids

    matches = UserProfile.objects.filter(id__in=matching_user_ids)

    my_courses = set(c.code for c in user_profile.courses.all())
    my_days = set(user_profile.available_weekdays)

    suggestions = []

    for other_user_profile in matches:
        if not compatible_styles(user_profile, other_user_profile):
            print("    Skipped: Incompatible study styles.")
            continue


        shared_courses = other_user_profile.courses.filter(id__in=user_profile.courses.values_list('id', flat=True))
        shared_days = list(set(user_profile.available_weekdays) & set(other_user_profile.available_weekdays))
        study_style = ""
        suggestions.append({
            "profile": other_user_profile,
            "shared_courses": shared_courses,
            "shared_days": shared_days,
        })


    print(f"\nTotal suggestions made: {len(suggestions)}")
    for suggestion in suggestions:
        print(f"Study buddy suggestions: {suggestion['profile'].user.username} - courses: {suggestion['shared_courses']}, days: {suggestion['shared_days']}")

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

