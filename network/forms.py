from django import forms
from .models import UserProfile, WEEKDAY_CHOICES

class UserProfileForm(forms.ModelForm):
    available_weekdays = forms.MultipleChoiceField(
        required=False,
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Which days can you usually study?"
    )

    class Meta:
        model = UserProfile
        fields = [
            'profile_pic',
            'school',
            'major',
            'year_of_study',
            'study_style',
            'bio',
            'available_weekdays',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'maxlength': '500', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.available_weekdays:
            self.initial['available_weekdays'] = self.instance.available_weekdays

    def clean_available_weekdays(self):
        # This will ensure the data goes in as a list, suitable for ArrayField
        return self.cleaned_data.get('available_weekdays', [])
