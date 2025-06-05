from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

WEEKDAY_CHOICES = [
    ('mon', 'Monday'),
    ('tue', 'Tuesday'),
    ('wed', 'Wednesday'),
    ('thu', 'Thursday'),
    ('fri', 'Friday'),
    ('sat', 'Saturday'),
    ('sun', 'Sunday'),
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    school = models.CharField(max_length=100)
    major = models.CharField(max_length=100)
    year_of_study = models.IntegerField(choices=[(1, '1st'), (2, '2nd'), (3, '3rd'), (4, '4th'), (5, 'Graduate')])

    courses = models.ManyToManyField(Course, through='UserCourse')
    study_style = models.CharField(
        max_length=20,
        choices=[
            ('quiet', 'Quiet'),
            ('discussion', 'Discussion'),
            ('flashcards', 'Flashcards'),
            ('mixed', 'Mixed'),
        ],
        default='mixed'
    )

    available_weekdays = ArrayField(
        models.CharField(choices=WEEKDAY_CHOICES),
        default=list,
        max_length=50,  # Enough to hold all combinations
        blank=True,
        help_text="Select the days you're available to study on."
    )

    profile_pic = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.username

    @property
    def profile_pic_url(self):
        if self.profile_pic and hasattr(self.profile_pic, 'url'):
            return self.profile_pic.url
        return '/media/profile_pics/default.png'  # Adjust path if your setup differs


class UserCourse(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_profile', 'course')


class StudyBuddyInvite(models.Model):
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_invites')
    receiver = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='received_invites')
    invite_message = models.TextField(default="Hello! I want to invite you to study with me.", blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('sender', 'receiver')


class StudyBuddy(models.Model):
    participant_one = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='participant_one')
    participant_two = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='participant_two')

    class Meta:
        unique_together = ('participant_one', 'participant_two')