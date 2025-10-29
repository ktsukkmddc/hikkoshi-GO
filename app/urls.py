from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import EmailAuthenticationForm
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html',
        authentication_form=EmailAuthenticationForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', views.signup_view, name='signup'),
    
    # === ログイン必須ページ ===
    path('home/', login_required(views.home_view), name='home'),
    path('task/', login_required(views.task_view), name='task'),
    path('calendar/', login_required(views.calendar_view), name='calendar'),
    path('mypage/', login_required(views.mypage_view), name='mypage'),
    path('account/', login_required(views.account_manage_view), name='account_manage'),
    
    # === パスワード変更 ===
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    
    # === メンバー関連 ===
    path('invite_member/', login_required(views.invite_member_view), name='invite_member'),
    path('generate_invite_url/', login_required(views.generate_invite_url), name='generate_invite_url'),
    path('member_list/', login_required(views.member_list_view), name='member_list'),
    
    # === メッセージ関連 ===
    path('message/', login_required(views.message_view), name='message'),
    path('save_message/', login_required(views.save_message_view), name='save_message'),
    
    # === メールアドレス変更 ===
    path('change_email/', login_required(views.change_email_view), name='change_email'),
    path('change_email/done/', login_required(views.change_email_done_view), name='change_email_done'),
    path('confirm_email/<uuid:token>/', views.confirm_email_view, name='confirm_email'),
    
    # === トップはログイン画面へ ===
    path('', lambda request: redirect('login'), name='root_redirect'),
    
    # === パスワードリセット ===
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html'
    ), name='password_reset'),
]