from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from .forms import CustomUserCreationForm
from .models import Invite
import uuid


# --- ログイン処理 ---
def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')  # フォームのnameに合わせる
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)  # ログイン処理
            return redirect('home')  # ホーム画面へ
        else:
            messages.error(request, "メールアドレスまたはパスワードが間違っています")
    return render(request, 'login.html')


# --- ホーム・共通画面 ---
@login_required
def home_view(request):
    return render(request, 'home.html')

@login_required
def task_view(request):
    return render(request, 'task.html')

@login_required
def calendar_view(request):
    return render(request, 'calendar.html')

@login_required
def mypage_view(request):
    return render(request, 'mypage.html')

@login_required
def account_manage_view(request):
    return render(request, 'account_manage.html')

@login_required
def member_list_view(request):
    return render(request, 'member_list.html')

def message_view(request):
    return render(request, 'registration/message.html')


# --- メンバー招待ページ ---
@login_required
def invite_member_view(request):
    return render(request, 'registration/invite_member.html')


# --- 招待URL生成（有効期限付き・一度限り） ---
@login_required
def generate_invite_url(request):
    """UUID付き招待URLを生成して返す（24時間有効・一度限り）"""
    if request.method == "POST":
        invite = Invite.objects.create(inviter=request.user)
        invite_url = request.build_absolute_uri(
            reverse('signup')
        ) + f"?invite={invite.code}"
        return JsonResponse({'invite_url': invite_url})
    return JsonResponse({'error': 'Invalid request'}, status=400)


# --- 新規登録（招待コード付き対応） ---
def signup_view(request):
    """新規登録ビュー（招待コード付き対応）"""
    invite_code = request.GET.get('invite')  # URLの?invite=UUIDを取得
    invite = None

    if invite_code:
        try:
            invite = Invite.objects.get(code=invite_code)
        except Invite.DoesNotExist:
            return render(request, 'registration/invite_error.html', {
                'message': 'この招待リンクは無効です。'
            })

        # 有効期限チェック
        if invite.is_expired():
            return render(request, 'registration/invite_error.html', {
                'message': 'この招待リンクは期限切れです。'
            })

        # 使用済みチェック
        if invite.is_used:
            return render(request, 'registration/invite_error.html', {
                'message': 'この招待リンクはすでに使用されています。'
            })

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        print("postを受信しました")
        
        if form.is_valid():
            print("フォーム有効です")
            user = form.save(commit=False)
            
            # invite_codeをユーザーにセット（保存前に）
            if invite_code:
                user.invite_code = invite_code
            user.save()
            
            # 招待があれば使用済みにする
            if invite:
                invite.is_used = True  # 使用済みにする
                invite.save()
                
            login(request, user)
            return redirect('home')
        else:
            print("フォームエラー:",form.errors)
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/signup.html', {
        'form': form,
        'invite_code': invite_code  # HTML側にも渡す
    })