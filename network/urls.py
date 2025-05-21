from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('invite/<int:receiver_id>/', views.send_invite, name='send_invite'),
    path('invite/accept/<int:invite_id>/', views.accept_invite, name='accept_invite'),
    path('invite/reject/<int:invite_id>/', views.reject_invite, name='reject_invite'),
    path('login/', auth_views.LoginView.as_view(template_name='network/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

