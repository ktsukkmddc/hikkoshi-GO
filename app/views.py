from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm


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


# --- 新規登録処理 ---
def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 登録後に自動ログイン
            return redirect('home')  # ホーム画面へ遷移
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


# --- ホーム画面 ---
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
def home(request):
    return render(request, 'home.html')

@login_required
def task(request):
    return render(request, 'task.html')

@login_required
def calendar(request):
    return render(request, 'calendar.html')

@login_required
def mypage_view(request):
    return render(request, 'mypage.html')

# --- マイページ ---
@login_required
def account_manage_view(request):
    return render(request, 'account_manage.html')

@login_required
def invite_member_view(request):
    return render(request, 'invite_member.html')

@login_required
def member_list_view(request):
    return render(request, 'member_list.html')

def message_view(request):
    return render(request, 'registration/message.html')

def invite_member_view(request):
    return render(request, 'registration/invite_member.html')

# app/views.py
import uuid
from django.shortcuts import render

def invite_member_view(request):
    invite_url = None  # 初期値（最初は空）
    
    if request.method == "POST":
        # ランダムなUUIDを生成
        unique_id = uuid.uuid4()
        # 招待リンクを生成（実際のURL構成に合わせて修正OK）
        invite_url = f"https://example.com/invite/{unique_id}"

    return render(request, "registration/invite_member.html", {"invite_url": invite_url})