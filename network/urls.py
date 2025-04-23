from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('invite/<int:receiver_id>/', views.send_invite, name='send_invite'),
    path('invite/accept/<int:invite_id>/', views.accept_invite, name='accept_invite'),
    path('invite/reject/<int:invite_id>/', views.reject_invite, name='reject_invite'),
    path('login/', auth_views.LoginView.as_view(template_name='network/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
]
