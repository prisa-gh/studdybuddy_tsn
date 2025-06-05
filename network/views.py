from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import HttpResponse

import io
from .models import UserProfile, StudyBuddyInvite, StudyBuddy, WEEKDAY_CHOICES, UserCourse
from .forms import UserProfileForm, RegisterForm

from .utils import build_study_network_graph, draw_study_network_graph, get_suggested_study_buddies, get_foaf_recommendations



def home(request):
    return render(request, 'network/home.html')



def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            school = form.cleaned_data.get("school")
            major = form.cleaned_data.get("major")
            # Fill UserProfile with extra fields
            UserProfile.objects.filter(user=user).update(school=school, major=major)
            login(request, user)
            return redirect("dashboard")
    else:
        form = RegisterForm()
    return render(request, "network/register.html", {"form": form})

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

    if not user_profile.courses or not user_profile.available_weekdays:
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

    return render(
        request,
        'network/study_buddies.html',
        {'study_buddies': study_buddies,
         'user_profile': user_profile,})


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
            # Handle enrolled courses
            new_courses = form.cleaned_data['enrolled_courses']
            current_courses = profile.courses.all()

            # Add new UserCourse objects
            for course in new_courses:
                UserCourse.objects.get_or_create(user_profile=profile, course=course)
            # Remove stale ones (Optional)
            for course in current_courses:
                if course not in new_courses:
                    UserCourse.objects.filter(user_profile=profile, course=course).delete()

            # Save available_weekdays separately if you store as list
            profile.available_weekdays = form.cleaned_data['available_weekdays']
            profile.save()

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


# views.py



@login_required
def study_graph_image(request):
    import matplotlib.pyplot as plt

    user = request.user
    user_profile = UserProfile.objects.get(user=user)
    user_id = str(user_profile.pk)
    G = build_study_network_graph()

    # Gather study buddies
    buddy_qs = StudyBuddy.objects.filter(
        Q(participant_one=user_profile) | Q(participant_two=user_profile)
    )
    buddy_profiles = set()
    for sb in buddy_qs:
        if sb.participant_one == user_profile:
            buddy_profiles.add(sb.participant_two.pk)
        else:
            buddy_profiles.add(sb.participant_one.pk)
    buddies = [str(pk) for pk in buddy_profiles]

    # Gather recommendations (suggested buddies + FOAFs)
    suggested_profiles = [str(sug['profile'].pk) for sug in get_suggested_study_buddies(user_profile)]
    print(get_foaf_recommendations(user_profile)[0].keys())  # Shows dict keys in your server log
    foaf_profiles = [str(foaf['id']) for foaf in get_foaf_recommendations(user_profile)]
    recommendations = list(set(suggested_profiles + foaf_profiles) - set(buddies) - {user_id})

    # Draw and return as image
    buf = io.BytesIO()
    draw_study_network_graph(
        G,
        user_node=user_id,
        buddy_nodes=buddies,
        recommendation_nodes=recommendations
    )
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return HttpResponse(buf.getvalue(), content_type='image/png')

@login_required
def study_graph(request):
    return render(request, "study_graph.html")