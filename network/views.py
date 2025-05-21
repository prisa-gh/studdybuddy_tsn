from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import StudyInvite
from .models import UserProfile
from .utils import get_suggested_study_buddies
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

    suggestions = get_suggested_study_buddies(user_profile)
    for suggestion in suggestions:
        profile = suggestion['profile']
        slots = suggestion['slots']
        weekdays = suggestion['weekdays']
        print(f"DEBUG: Profile {profile} — id={profile.id}, score={slots}")

    incoming_invites = StudyInvite.objects.filter(
        receiver=user_profile,
        status='pending'
    ).select_related('sender')

    return render(request, 'network/dashboard.html', {
        'suggestions': suggestions,
        'user_profile': user_profile,
        'incoming_invites': incoming_invites,
        'week_days_map': {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'},
    })


@login_required
def profile_view(request):
    profile = UserProfile.objects.get(user=request.user)
    return render(request, 'network/profile.html', {'profile': profile})


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

    if StudyInvite.objects.filter(sender=sender_profile, receiver=receiver_profile).exists():
        messages.warning(request, "You already sent an invite.")
    else:
        weekday = int(request.POST.get("weekday"))
        start = request.POST.get("start")
        end = request.POST.get("end")

        StudyInvite.objects.create(
            sender=sender_profile,
            receiver=receiver_profile,
            selected_weekday=weekday,
            selected_start=start,
            selected_end=end
        )
        messages.success(request, f"Invite sent to {receiver_profile.user.username} for {start}–{end} on weekday {weekday}")

    return redirect('dashboard')

@login_required
def accept_invite(request, invite_id):
    try:
        invite = StudyInvite.objects.get(id=invite_id, receiver__user=request.user)
        invite.status = 'accepted'
        invite.save()
        messages.success(request, f"Accepted invite from {invite.sender.user.username}")
    except StudyInvite.DoesNotExist:
        messages.error(request, "Invalid invite.")
    return redirect('dashboard')


@login_required
def reject_invite(request, invite_id):
    try:
        invite = StudyInvite.objects.get(id=invite_id, receiver__user=request.user)
        invite.status = 'rejected'
        invite.save()
        messages.info(request, f"Rejected invite from {invite.sender.user.username}")
    except StudyInvite.DoesNotExist:
        messages.error(request, "Invalid invite.")
    return redirect('dashboard')
