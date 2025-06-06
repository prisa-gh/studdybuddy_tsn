from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='network/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    path('invite/<int:receiver_id>/', views.send_invite, name='send_invite'),
    path('invite/accept/<int:invite_id>/', views.accept_invite, name='accept_invite'),
    path('invite/reject/<int:invite_id>/', views.reject_invite, name='reject_invite'),

    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/study_buddies/', views.view_study_buddies, name='study_buddies'),

    path('direct_messages/', views.direct_message_inbox, name='direct_message_inbox'),
    path('events/', views.events_page, name='events_page'),

    path('study_graph/', views.study_graph, name='study_graph'),
    path('study_graph/image/', views.study_graph_image, name='study_graph_image'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

