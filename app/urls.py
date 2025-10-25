from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import EmailAuthenticationForm

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html',
        authentication_form=EmailAuthenticationForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('home/', views.home_view, name='home'),
    path('task/', views.task_view, name='task'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('mypage/', views.mypage_view, name='mypage'),
    path('account_manage/', views.account_manage_view, name='account_manage'),
    path('invite_member/', views.invite_member_view, name='invite_member'),
    path('generate_invite_url/', views.generate_invite_url, name='generate_invite_url'),
    path('member_list/', views.member_list_view, name='member_list'),
    path('message/', views.message_view, name='message'),
    path('save_message/', views.save_message_view, name='save_message'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html'
    ), name='password_reset'),
]