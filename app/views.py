from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from .forms import CustomUserCreationForm, TaskForm
from .models import Invite, Task, CustomUser, Message, MoveInfo
from django.core.mail import send_mail, BadHeaderError, EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from datetime import date
import calendar as pycal
import uuid, json
from urllib.parse import urlencode
from django.conf import settings


# --- ログイン処理 ---
def login_view(request):
    if request.method == "POST":
        email = request.POST.get('username')  # フォームのnameに合わせる
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)  # ログイン処理
            return redirect('home')  # ホーム画面へ
        else:
            messages.error(request, "メールアドレスまたはパスワードが間違っています")
    return render(request, 'login.html')


# --- ホーム・共通画面 ---
@login_required
def home_view(request):
    user = request.user
    
    move_info = user.move_info if user.move_info else None
    move_date = move_info.move_date if move_info else None
    
    total_tasks = Task.objects.filter(move_info=move_info).count() if move_info else 0
    completed_tasks = Task.objects.filter(move_info=move_info, is_completed=True).count() if move_info else 0
    
    # タスクが1件もない場合は0%にする
    if total_tasks == 0:
        progress_rate = 0
    else:
        progress_rate = int((completed_tasks / total_tasks) * 100)
        
    is_move_date_set = move_date is not None
    
    return render(request, 'home.html', {
        "move_date": move_date,
        "progress_rate": progress_rate,
        "is_move_date_set": is_move_date_set,
    })


@login_required
def task_view(request):
    return render(request, 'task.html')


@login_required
def mypage_view(request):
    return render(request, 'mypage.html')


@login_required
def account_manage_view(request):
    """アカウント管理画面（名前・メール・引越し予定日を編集）"""
    user = request.user

    move_info = user.move_info
    
    if request.method == "POST" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        full_name = request.POST.get("full_name", "").strip()
        user.full_name = full_name
        user.save(update_fields=["full_name"])
        return JsonResponse({"status": "ok"})
    
    elif request.method == "POST":
        full_name = request.POST.get("full_name") or user.full_name
        email = request.POST.get("email") or user.email
        move_date = request.POST.get("move_date")
        
        # 入力値を反映
        user.full_name = full_name
        user.email = email
        user.save()
        
        if move_date:
            if not user.move_info:
                move_info = MoveInfo.objects.create(
                    owner=user,
                    move_date=move_date,
                    updated_by=user,
                )
                user.move_info = move_info
                user.save(update_fields=["move_info"])
            else:
                user.move_info.move_date = move_date
                user.move_info.updated_by = user
                user.move_info.save(update_fields=["move_date", "updated_by"])

        messages.success(request, "アカウント情報を更新しました。")
        return redirect("account_manage")
    
    return render(request, 'account_manage.html', {
        "user": user,
        "move_date": move_info.move_date if move_info else None
        })


@login_required
def member_list_view(request):
    """登録メンバー一覧を表示（同じ引越し MoveInfo を共有しているユーザー）"""
    
    user = request.user
    
    if not user.move_info:
        return redirect("invite_member")
    
    members = CustomUser.objects.filter(move_info=user.move_info)
    
    is_owner = (user == user.move_info.owner)
    
    return render(
        request,
        "member_list.html",
        {
            "members": members,
            "is_owner": is_owner,
            "current_user": user,
        }
    )


# --- メンバー招待ページ ---
@login_required
def invite_member_view(request):
    user = request.user

    # MoveInfo がない → homeへ
    if not user.move_info:
        return redirect("home")
    
    # owner 以外 → homeへ
    if user.move_info.owner != user:
        return redirect("home")
    
    # owner のみ到達できる
    return render(request, 'registration/invite_member.html')


@login_required
def member_remove_view(request, user_id):
    user = request.user

    # POST以外は拒否
    if request.method != "POST":
        return redirect("member_list")

    # move_info がない人は不可
    if not user.move_info:
        return redirect("home")

    # オーナー以外は不可
    if user != user.move_info.owner:
        return redirect("member_list")

    # 対象ユーザー取得（同じ move_info の人限定）
    try:
        target = CustomUser.objects.get(
            id=user_id,
            move_info=user.move_info
        )
    except CustomUser.DoesNotExist:
        return redirect("member_list")

    # オーナー本人は解除不可
    if target == user:
        return redirect("member_list")

    # 解除（削除ではない！）
    target.move_info = None
    target.save()

    return redirect("member_list")


# --- 招待URL生成（有効期限付き・一度限り） ---
@login_required
def generate_invite_url(request):
    """UUID付き招待URLを生成して返す（24時間有効・一度限り）"""
    user = request.user
    
    # MoveInfo を持っていない人は招待不可
    if not user.move_info:
        return JsonResponse({'error': 'no_move_info'}, status=400)
    
    move_info = user.move_info
    
    # owner 以外は招待不可
    if move_info.owner != user:
        return JsonResponse({'error': 'permission_denied'}, status=403)
    
    if request.method == "POST":
        invite = Invite.objects.create(move_info=move_info)
        
        params = urlencode({"invite": str(invite.code)})
        invite_url = request.build_absolute_uri(reverse('signup')) + "?" + params
        
        return JsonResponse({'invite_url': invite_url})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def accept_invite_view(request):
    """ログイン済みユーザーが招待コードで MoveInfo に参加する"""
    invite_code = request.GET.get("invite")
    if not invite_code:
        return render(request, "registration/invite_invalid.html")
    
    try:
        uuid.UUID(invite_code)
        invite = Invite.objects.select_related("move_info").get(code=invite_code)
    
    except (ValueError, ValidationError, Invite.DoesNotExist):
        return render(request, "registration/invite_invalid.html")
    
    if invite.is_expired():
        return render(request, "registration/invite_expired.html")
    
    if invite.is_used:
        return render(request, "registration/invite_used.html")
    
    # すでに同じ MoveInfo に参加していたらそのまま
    if request.user.move_info_id == invite.move_info_id:
        return redirect("home")
    
    # 参加（move_info付与）
    request.user.move_info = invite.move_info
    request.user.save(update_fields=["move_info"])
    
    # 招待は1回限りにする
    invite.is_used = True
    invite.save(update_fields=["is_used"])
    
    return redirect("home")


# --- 新規登録（招待コード付き対応） ---
def signup_view(request):
    """新規登録ビュー（招待コード付き対応）
    - 未ログイン: 新規登録フォーム
    - ログイン済み: 招待リンクを踏んだらその場で参加（move_info付与）して home へ
    """
    
    invite_code = request.GET.get('invite')  # URLの?invite=UUIDを取得
    invite = None

    if invite_code:
        try:
            uuid.UUID(invite_code)
            invite = Invite.objects.select_related('move_info').get(code=invite_code)
            
        except (ValueError, ValidationError, Invite.DoesNotExist):
        # 無効なリンク
            return render(request, 'registration/invite_invalid.html')
        
        # 有効期限チェック
        if invite.is_expired():
            return render(request, 'registration/invite_expired.html')

        # 使用済みチェック
        if invite.is_used:
            return render(request, 'registration/invite_used.html')
        
        # ログイン済みなら、今のユーザーをその MoveInfo に参加させる
        if request.user.is_authenticated:
            # すでに同じ move_info に参加済みならそのまま home
            if request.user.move_info_id == invite.move_info_id:
                return redirect('home')
            
            # 参加処理（既存アカウントに move_info を付与）
            request.user.move_info = invite.move_info
            request.user.save(update_fields=["move_info"])
        
            # 招待リンクを使用済みにする（1回限り運用）
            invite.is_used = True
            invite.save(update_fields=['is_used'])
        
            return redirect('home')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            print("フォーム有効です")
            user = form.save(commit=False)
            user.full_name = form.cleaned_data['full_name']
            
            if invite:
                user.move_info = invite.move_info
            
            user.save()
            
            if invite:
                invite.is_used = True
                invite.save(update_fields=['is_used'])
            
            login(request, user)
            return redirect('home')    
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'registration/signup.html', {
        'form': form,
        'invite_code': invite_code  # HTML側にも渡す
    })

    
@login_required
def save_message_view(request):
    """モーダルからのメッセージ登録処理"""
    if request.method == 'POST':
        receiver_email = request.POST.get('receiver_email')
        content = request.POST.get('content')

        receiver = CustomUser.objects.filter(email=receiver_email, move_info=request.user.move_info).first()
        if receiver and content:
            Message.objects.create(sender=request.user, receiver=receiver, content=content, move_info=request.user.move_info)
        return redirect('member_list')


@login_required
def change_email_view(request):
    user = request.user
    
    """メールアドレス変更フォーム"""
    if request.method == "POST":
        new_email = request.POST.get("new_email")
        password = request.POST.get("password")
        password_confirm = request.POST.get("password_confirm")

        if password != password_confirm:
            messages.error(request, "パスワードが一致しません。")
            return render(request, "change_email.html")
        
        # トークン生成
        token = uuid.uuid4()
        user.new_email = new_email
        user.email_change_token = token
        user.save()

        # 確認メール送信
        current_site = get_current_site(request)
        confirm_url = f"http://{current_site.domain}{reverse('confirm_email', args=[token])}"
        
        try:
            email = EmailMessage(
                subject="【引越しGO】メールアドレス確認のお願い",
                body=(
                    f"{user.full_name or user.email} さん\n\n"
                    f"以下のリンクをクリックしてメールアドレス変更を完了してください。\n\n"
                    f"{confirm_url}\n\n"
                    "このメールに覚えがない場合は無視してください。"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[new_email],
            )
            email.send(fail_silently=False)
        except Exception as e:
            messages.error(request, f"メール送信に失敗しました: {e}")
            return redirect("change_email")
            
        messages.success(request, f"{new_email} 宛に確認メールを送信しました。")
        return redirect("change_email_done")
        
    return render(request, "change_email.html", {"user": user})


@login_required
def change_email_done_view(request):
    """確認メール送信完了画面"""
    return render(request, "change_email_done.html")

def confirm_email_view(request, token):
    """メールアドレス確認リンクからアクセス"""
    user = get_object_or_404(CustomUser, email_change_token=token)

    if user.new_email:
        user.email = user.new_email
        user.new_email = None
        user.email_change_token = None
        user.save()
        messages.success(request, "メールアドレスを更新しました。")

    return render(request, "confirm_email_done.html")


@login_required
def task_create_view(request):
    user = request.user
    
    if not user.move_info:
        return redirect("home")
    
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = user
            task.move_info = user.move_info
            
            # ▼ ラジオボタンの選択に従って保存
            task_mode = form.cleaned_data.get("task_mode")
            
            if task_mode == "select":
                task.task_name = form.cleaned_data.get("task_name")
                task.custom_task = ""
                
            elif task_mode == "custom":
                task.task_name = form.cleaned_data.get("custom_task")

            task.save()
            return redirect('task_list')
        else:
            print("フォームエラー:", form.errors)
    else:
        form = TaskForm()

    return render(request, 'task_create.html', {'form': form})


@login_required
def task_list_view(request):
    user = request.user
    
    if user.move_info:
        tasks = Task.objects.filter(move_info=user.move_info).order_by("date")
    else:
        tasks = Task.objects.none()
    
    return render(request, 'task_list.html', {'tasks': tasks, 'has_move_info': bool(user.move_info)})


@login_required
def toggle_task_completion(request, task_id):
    """タスク完了／未完を切り替える"""
    task = get_object_or_404(Task, id=task_id, move_info=request.user.move_info)
    
    task.is_completed = not task.is_completed
    task.save()
    
    return JsonResponse({'status': 'ok', 'is_completed': task.is_completed})


@login_required
def delete_task_view(request, task_id):
    """タスク削除処理"""
    task = get_object_or_404(Task, id=task_id, move_info=request.user.move_info)
    task.delete()
    return JsonResponse({'status': 'ok'})


@login_required
def task_edit_view(request, task_id):
    task = get_object_or_404(Task, id=task_id, move_info=request.user.move_info)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm(instance=task)

    return render(request, 'task_edit.html', {'form': form})


@login_required
def calendar_view(request):
    """全てのタスクをカレンダーに反映"""
    
    from datetime import datetime, timedelta, timezone
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).date()
    
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # 日曜始まりのカレンダー
    cal = pycal.Calendar(firstweekday=6)
    weeks = cal.monthdatescalendar(year, month)
    
    # 「全タスク」を取得（期間指定なし）
    tasks = (
        Task.objects.filter(move_info=request.user.move_info,)
        .values('date', 'task_name', 'start_time', 'end_time', 'memo')
    )
    
    # JSON化
    tasks_data = list(tasks)
    context = {
        'year': year,
        'month': month,
        'weeks': weeks,
        'tasks_json': mark_safe(json.dumps(tasks_data, default=str)),
        'today': today,
    }
        
    return render(request, 'calendar.html', context)


@login_required
def day_tasks_json(request):
    """日付クリックでモーダルに表示するタスク一覧(JSON)"""
    ymd = request.GET.get('date')
    if not ymd:
        return JsonResponse({'tasks': []})

    items = (
        Task.objects.filter(move_info=request.user.move_info, date=ymd)
        .order_by('start_time', 'end_time', 'id')
    )

    data = [
        {
            'id': t.id,
            'title': t.custom_task or t.task_name or '',
            'start_time': t.start_time.strftime('%H:%M') if t.start_time else '',
            'end_time': t.end_time.strftime('%H:%M') if t.end_time else '',
            'memo': t.memo or '',
        }
        for t in items
    ]
    return JsonResponse({'tasks': data})


@login_required
def message_register_view(request):
    """メッセージ登録画面"""
    members = CustomUser.objects.filter(move_info=request.user.move_info).exclude(id=request.user.id)

    if request.method == "POST":
        receiver_id = request.POST.get("receiver")
        content = request.POST.get("content")

        if receiver_id and content:
            receiver = get_object_or_404(CustomUser, id=receiver_id, move_info=request.user.move_info)
            
            Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content,
                move_info=request.user.move_info
            )
            return redirect("message_list")

    return render(request, "message_register.html", {"members": members})


@login_required
def message_list_view(request):
    """メッセージ一覧（掲示板）"""
    query = request.GET.get("q")
    
    messages = Message.objects.filter(move_info=request.user.move_info).order_by('-created_at')
    
    # キーワードが入力された場合のみフィルタ
    if query:
        messages = messages.filter(
            Q(content__icontains=query) |
            Q(sender__full_name__icontains=query) |
            Q(receiver__full_name__icontains=query)
        )

    return render(request, "message_list.html", {"messages": messages})


def portfolio_top_view(request):
    return render(request, "portfolio_top.html")


@login_required
def set_move_date_view(request):
    """
    引越し日を設定する共通View
    - move_info がなければ作成
    - あれば更新
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    user = request.user
    move_date = request.POST.get("move_date")

    if not move_date:
        return JsonResponse({"error": "move_date is required"}, status=400)

    # move_info がない場合は新規作成
    if user.move_info is None:
        move_info = MoveInfo.objects.create(
            owner=user,
            move_date=move_date,
            updated_by=user,
        )
        user.move_info = move_info
        user.save(update_fields=["move_info"])

    # すでにある場合は更新
    else:
        user.move_info.move_date = move_date
        user.move_info.updated_by = user
        user.move_info.save(update_fields=["move_date", "updated_by"])

    return JsonResponse({
        "status": "ok",
        "move_date": move_date
    })