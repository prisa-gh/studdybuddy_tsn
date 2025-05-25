from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, StudyBuddyInvite, StudyBuddy


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            school='',
            major='',
            year_of_study=0
            )

@receiver(post_save, sender=StudyBuddyInvite)
def create_study_session(sender, instance, created, **kwargs):
    if instance.status == 'accepted' and not hasattr(instance, 'studysession'):
        StudyBuddy.objects.create(
            participant_one=instance.sender,
            participant_two=instance.receiver,
        )