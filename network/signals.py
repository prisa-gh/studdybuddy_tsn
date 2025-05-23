from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, StudyInvite, StudySession


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            school='',
            major='',
            year_of_study=0
            )

@receiver(post_save, sender=StudyInvite)
def create_study_session(sender, instance, created, **kwargs):
    if instance.status == 'accepted':
        sender_study_style = instance.sender.study_style
        receiver_study_style = instance.receiver.study_style

        if sender_study_style == receiver_study_style and sender_study_style != 'mixed':
            study_style = sender_study_style
        elif sender_study_style != 'mixed' and receiver_study_style == 'mixed':
            study_style = sender_study_style
        elif sender_study_style == 'mixed' and receiver_study_style != 'mixed':
            study_style = receiver_study_style
        else:
            study_style = 'mixed'
        if not hasattr(instance, 'studysession'):

            StudySession.objects.create(
                participant_one=instance.sender,
                participant_two=instance.receiver,
                start_time=instance.selected_start,
                end_time=instance.selected_end,
                study_style=study_style
            )