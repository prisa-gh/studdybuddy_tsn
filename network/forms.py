from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile, WEEKDAY_CHOICES, Course, User



class UserProfileForm(forms.ModelForm):
    available_weekdays = forms.MultipleChoiceField(
        required=False,
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Which days can you usually study?"
    )

    enrolled_courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(),
        required=False,

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
            'enrolled_courses',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'maxlength': '500', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set available weekdays initial value
        if self.instance and self.instance.available_weekdays:
            self.initial['available_weekdays'] = self.instance.available_weekdays

        # FIX: Set queryset to all courses for enrolled_courses
        self.fields['enrolled_courses'].queryset = Course.objects.all()
        # Optionally, check the instance's current courses:
        if self.instance.pk:
            self.initial['enrolled_courses'] = self.instance.courses.all()

    def clean_available_weekdays(self):
        # This will ensure the data goes in as a list, suitable for ArrayField
        return self.cleaned_data.get('available_weekdays', [])

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    school = forms.CharField(max_length=100)
    major = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "school", "major")

