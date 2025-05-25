from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import HttpResponse

import io
from .models import StudyBuddyInvite, StudyBuddy, WEEKDAY_CHOICES
from .models import UserProfile
from .utils import get_suggested_study_buddies, get_foaf_recommendations, build_study_network_graph
from .forms import UserProfileForm



@login_required
def dashboard(request):
    user_profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "school": "",
            "major": "",
            "year_of_study": 1
        }
    )

    if not user_profile.school or not user_profile.major:
        messages.warning(request, "Please complete your profile to get better suggestions.")

    weekday_labels = dict(WEEKDAY_CHOICES)
    user_days = set(user_profile.available_weekdays)
    user_courses = set(user_profile.courses.values_list('id', flat=True))
    suggestions = get_suggested_study_buddies(user_profile)

    # Get pending outgoing invites (sent but not accepted yet)
    outgoing_invites = StudyBuddyInvite.objects.filter(
        sender=user_profile,
        status='pending'
    ).select_related('receiver')


    for suggestion in suggestions:
        profile = suggestion['profile']
        #print(f"DEBUG: Profile {profile} — id={profile.id} -weekdays{weekdays}")

    foaf_dicts = get_foaf_recommendations(user_profile)
    foaf_profiles = UserProfile.objects.filter(id__in=[foaf["id"] for foaf in foaf_dicts]).select_related("user")
    profiles_by_id = {profile.id: profile for profile in foaf_profiles}



    # Attach both profile and buddy_names as an object you can use in template
    foaf_suggestions = []
    for foaf in foaf_dicts:
        profile = profiles_by_id.get(foaf["id"])
        if profile:
            profile.buddy_names = foaf["buddy_names"]
            profile.course_names = [uc.course.name for uc in profile.usercourse_set.select_related('course').all()]
            profile.available_days = profile.available_weekdays  # if you want to rename for template

            foaf_course_qs = profile.courses.all()
            foaf_course_ids = set(foaf_course_qs.values_list('id', flat=True))
            common_ids = user_courses.intersection(foaf_course_ids)
            common_courses = [c.name for c in foaf_course_qs if c.id in common_ids]

            foaf_days = set(profile.available_weekdays or [])
            shared_days_codes = user_days.intersection(foaf_days)
            shared_days_names = [weekday_labels[code] for code in shared_days_codes]

            profile.shared_days = shared_days_names
            profile.common_courses = common_courses

            # Dynamically add attribute
            foaf_suggestions.append(profile)

    for foaf in foaf_suggestions:
        print(foaf.user)
        print(foaf.id)
        print(foaf.major)
        print(foaf.school)
        print(foaf.year_of_study)
        print(foaf.study_style)
        print(foaf.available_weekdays)
        print(foaf.usercourse_set.all())
        print(foaf.bio)
        print(foaf.profile_pic)

        print("=" * 40)


    incoming_invites = StudyBuddyInvite.objects.filter(
        receiver=user_profile,
        status='pending'
    ).select_related('sender')

    return render(request, 'network/dashboard.html', {
        'suggestions': suggestions,
        'user_profile': user_profile,
        'incoming_invites': incoming_invites,
        'week_days_map': {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'},
        'foaf_suggestions': foaf_suggestions,
    })

@login_required
def view_study_buddies(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    study_buddies = StudyBuddy.objects.filter(
    Q(participant_one=user_profile)
    | Q(participant_two=user_profile))

    return render(request, 'network/study_buddies.html', {'study_buddies': study_buddies})


@login_required
def profile_view(request):
    profile = UserProfile.objects.get(user=request.user)
    courses = profile.courses.all()
    course_names = [f"{c.code} - {c.name}" for c in courses]
    return render(request, 'network/profile.html', {
        'profile': profile,
        'course_names': course_names,
    })


@login_required
def profile_edit(request):
    profile = UserProfile.objects.get(user=request.user)
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'network/profile_edit.html', {'form': form})


@require_POST
@login_required
def send_invite(request, receiver_id):
    sender_profile = UserProfile.objects.get(user=request.user)
    receiver_profile = UserProfile.objects.get(id=receiver_id)

    if StudyBuddyInvite.objects.filter(sender=sender_profile, receiver=receiver_profile).exists():
        messages.warning(request, "You already sent an invite.")
    else:
        start = request.POST.get("start")
        end = request.POST.get("end")

        StudyBuddyInvite.objects.create(
            sender=sender_profile,
            receiver=receiver_profile,
        )
        messages.success(request, f"Invite sent to {receiver_profile.user.username} for {start}–{end}")

    return redirect('dashboard')

@login_required
def accept_invite(request, invite_id):
    try:
        invite = StudyBuddyInvite.objects.get(id=invite_id, receiver__user=request.user)
        invite.status = 'accepted'
        invite.save()
        messages.success(request, f"Accepted invite from {invite.sender.user.username}")
    except StudyBuddyInvite.DoesNotExist:
        messages.error(request, "Invalid invite.")
    return redirect('dashboard')


@login_required
def reject_invite(request, invite_id):
    try:
        invite = StudyBuddyInvite.objects.get(id=invite_id, receiver__user=request.user)
        invite.status = 'rejected'
        invite.save()
        messages.info(request, f"Rejected invite from {invite.sender.user.username}")
    except StudyBuddyInvite.DoesNotExist:
        messages.error(request, "Invalid invite.")
    return redirect('dashboard')

@login_required
def study_graph_image(request):
    G = build_study_network_graph()
    import matplotlib.pyplot as plt
    import networkx as nx

    plt.figure(figsize=(8, 6))
    pos = nx.spring_layout(G)
    edge_colors = ['green' if d.get('type') == 'study_buddy' else 'blue' for _,_,d in G.edges(data=True)]
    nx.draw(G, pos, with_labels=True, labels=nx.get_node_attributes(G, 'label'),
            edge_color=edge_colors, node_size=800, node_color='lightgray')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return HttpResponse(buf.read(), content_type='image/png')

@login_required
def study_graph(request):
    return render(request, "study_graph.html")