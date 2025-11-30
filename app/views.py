from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.db.models import Count
from .forms import CustomUserCreationForm, TaskForm, MoveGroupForm
from .models import Invite, Task, CustomUser, Message, MoveInfo, MoveGroup
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from datetime import date
import calendar as pycal
import uuid, json


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
    if request.user.group is None:
        return redirect("create_group")

    user = request.user
    move_info = MoveInfo.objects.filter(group=request.user.group).first()
    
    move_date = None
    if move_info and move_info.move_date:
        move_date = move_info.move_date
    
    total_tasks = Task.objects.filter(group=user.group).count()
    completed_tasks = Task.objects.filter(group=user.group, is_completed=True).count() # 完了済みタスク数
    
    # タスクが1件もない場合は0%にする
    if total_tasks == 0:
        progress_rate = 0
    else:
        progress_rate = int((completed_tasks / total_tasks) * 100)
    
    return render(request, 'home.html', {
        "move_date": move_date,
        "progress_rate": progress_rate,
    })


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
    """アカウント管理画面（名前・メール・引越し予定日を編集）"""
    user = request.user
    move_info, created = MoveInfo.objects.get_or_create(group=user.group)
    
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
            move_info.move_date = move_date
            move_info.updated_by = user
            move_info.save()
        
        messages.success(request, "アカウント情報を更新しました。")
        return redirect("account_manage")
    
    return render(request, 'account_manage.html', {
        "user": user,
        "move_date": move_info.move_date
        })


@login_required
def member_list_view(request):
    """登録メンバー一覧を表示（同じグループだけ）"""
    
    group = request.user.group
    
    if not group:
        return redirect("create_group")
    
    members = CustomUser.objects.filter(group=group)
    
    return render(request, "member_list.html", { "members": members,})


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
        # 無効なリンク
            return render(request, 'registration/invite_invalid.html')
        
        invite.refresh_from_db()  # 最新状態を取得（管理画面で変更した直後でも反映される）

        print("=== 招待リンクチェック ===")
        print("コード:", invite.code)
        print("期限:", invite.expires_at)
        print("現在:", timezone.now())
        print("期限切れ判定:", invite.is_expired())
        print("使用済み判定:", invite.is_used)
        print("=========================")

        # 有効期限チェック
        if invite.is_expired():
            return render(request, 'registration/invite_expired.html')

        # 使用済みチェック
        if invite.is_used:
            return render(request, 'registration/invite_used.html')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        print("postを受信しました")
        
        if form.is_valid():
            print("フォーム有効です")
            user = form.save(commit=False)
            user.full_name = form.cleaned_data['full_name']
            
            user.save()
            
            # 招待リンク経由 → グループに参加させる
            if invite:
                user.group = invite.inviter.group
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
    

@login_required
def save_message_view(request):
    """モーダルからのメッセージ登録処理"""
    if request.method == 'POST':
        receiver_email = request.POST.get('receiver_email')
        content = request.POST.get('content')

        receiver = CustomUser.objects.filter(email=receiver_email).first()
        if receiver and content:
            Message.objects.create(sender=request.user, receiver=receiver, content=content)
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

        send_mail(
            subject="【引越しGO】メールアドレス確認のお願い",
            message=f"{user.username} さん\n\n以下のリンクをクリックしてメールアドレス変更を完了してください。\n\n{confirm_url}\n\nこのメールに覚えがない場合は無視してください。",
            from_email="noreply@hikkoshi-go.com",
            recipient_list=[new_email],
        )

        # 確認メール送信（開発中はコンソール出力）
        print(f"確認メールを {new_email} 宛に送信しました。")

        # 成功メッセージを一時保存してリダイレクト
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
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.group = request.user.group
            
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
    tasks = Task.objects.filter(group=request.user.group).order_by('date')
    return render(request, 'task_list.html', {'tasks': tasks})


@login_required
def toggle_task_completion(request, task_id):
    """タスク完了／未完を切り替える"""
    task = get_object_or_404(Task, id=task_id)
    task.is_completed = not task.is_completed
    task.save()
    return JsonResponse({'status': 'ok', 'is_completed': task.is_completed})


@login_required
def delete_task_view(request, task_id):
    """タスク削除処理"""
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return JsonResponse({'status': 'ok'})


@login_required
def task_edit_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)  # 権限を絞るなら created_by=request.user を足す
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
        Task.objects.filter(group=request.user.group)
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
        Task.objects.filter(created_by=request.user, date=ymd, group=request.user.group)
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
    members = CustomUser.objects.filter(group=request.user.group).exclude(id=request.user.id)  # 自分以外の全メンバー

    if request.method == "POST":
        receiver_id = request.POST.get("receiver")
        content = request.POST.get("content")

        if receiver_id and content:
            receiver = CustomUser.objects.get(id=receiver_id)
            Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=content,
                group=request.user.group
            )
            return redirect("message_list")  # 一覧ページへ遷移

    return render(request, "message_register.html", {"members": members})


@login_required
def message_list_view(request):
    """メッセージ一覧（掲示板）"""
    query = request.GET.get("q")
    messages = Message.objects.filter(group=request.user.group).order_by('-created_at')  # 新しい順に表示
    
    # キーワードが入力された場合のみフィルタ
    if query:
        messages = messages.filter(
            content__icontains=query
        ) | messages.filter(
            sender__full_name__icontains=query
        ) | messages.filter(
            receiver__full_name__icontains=query
        )

    return render(request, "message_list.html", {"messages": messages})


def portfolio_top_view(request):
    return render(request, "portfolio_top.html")


@login_required
def create_group(request):
    """
    グループ作成ビュー
    ログインユーザーを owner として MoveGroup を作成する
    すでにグループに所属している場合は旧グループを削除して新規作成
    """
    user = request.user
    old_group = user.group
    
    if request.method == "POST":
        form = MoveGroupForm(request.POST)
        if form.is_valid():
            # ① 新しいグループを作成
            new_group = form.save(commit=False)
            new_group.owner = user
            new_group.save()
            
            # ② ユーザーを新グループに所属させる
            user.group = new_group
            user.save()
            
            # ③ 旧グループがあるなら削除（ただし自分が owner の場合のみ）
            if old_group and old_group.owner == user:
                old_group.delete()  # CASCADE で関連データも消える
                
            return redirect("home")
        
    else:
        form = MoveGroupForm()
            
    return render(request, "group_create.html", {"form": form})


@login_required
def invite_view(request, group_id):
    # 招待先グループを取得
    new_group = get_object_or_404(MoveGroup, id=group_id)

    user = request.user

    # すでに同じグループに所属している場合
    if user.group_id == new_group.id:
        messages.info(request, "すでにこのグループに所属しています。")
        return redirect('home')

    # 以前のグループを記録
    old_group = user.group

    # ① ユーザーのグループを新グループに切り替え
    user.group = new_group
    user.save()

    # ② 古いグループ（owner のみ削除処理が必要）
    if old_group:
        # owner が抜けた → グループ削除
        if old_group.owner_id == user.id:
            old_group.delete()

    messages.success(request, f"「{new_group.name}」に参加しました！")
    return redirect('home')


@login_required
def send_invite_email(request):
    """グループ招待メール送信"""
    user = request.user
    group = user.group

    if not group:
        messages.error(request, "先にグループを作成してください。")
        return redirect("create_group")

    if request.method == "POST":
        invite_email = request.POST.get("invite_email")

        # 招待リンク生成
        invite_url = request.build_absolute_uri(
            reverse("invite_group", args=[group.id])
        )

        # メール本文
        subject = "【引越しGO】グループへの招待"
        message = (
            f"{user.full_name} さんからグループへの招待が届いています。\n\n"
            f"以下のリンクをクリックすると参加できます：\n"
            f"{invite_url}\n\n"
            "※このメールに心当たりがない場合は無視してください。"
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email="noreply@hikkoshi-go.com",
                recipient_list=[invite_email],
            )
            messages.success(request, f"{invite_email} へ招待メールを送信しました！")
        except Exception as e:
            messages.error(request, f"メール送信に失敗しました：{e}")

        return redirect("invite_member")

    # GET の場合は招待画面へ
    return redirect("invite_member")