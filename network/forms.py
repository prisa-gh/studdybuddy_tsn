from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'profile_pic',
            'school',
            'major',
            'year_of_study',
            'study_style',
            'prefers_group',
            'bio',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'maxlength': '500', 'rows': 4}),
        }