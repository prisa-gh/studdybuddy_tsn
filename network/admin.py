from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Course, UserProfile, UserCourse, AvailabilitySlot, StudyInvite


class UserProfileInline(admin.StackedInline):
    model = UserProfile
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
admin.site.register(AvailabilitySlot)
admin.site.register(StudyInvite)
