from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django import forms
from .models import (Course,
                     UserProfile,
                     UserCourse,
                     StudyBuddyInvite,
                     StudyBuddy,
                     WEEKDAY_CHOICES)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class UserProfileAdminForm(forms.ModelForm):
    available_weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Which days can you usually study?",
    )

    class Meta:
        model = UserProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.available_weekdays:
            self.initial['available_weekdays'] = self.instance.available_weekdays

    def clean_available_weekdays(self):
        # Always returns a list suitable for ArrayField
        return self.cleaned_data.get('available_weekdays', [])

# --- Inline for UserProfile in User admin ---
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    form = UserProfileAdminForm
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


# Unregister default User and re-register with profile inline
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(Course)
admin.site.register(UserCourse)
admin.site.register(StudyBuddyInvite)
admin.site.register(StudyBuddy)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('user', 'school', 'major', 'year_of_study', 'study_style')
