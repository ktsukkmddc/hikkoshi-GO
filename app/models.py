from django.contrib.auth.models import AbstractUser, BaseUserManager, User
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import uuid


# ==========================
# Custom User Manager
# ==========================
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


# ==========================
# Custom User Model
# ==========================   
class CustomUser(AbstractUser):
    """拡張ユーザーモデル"""
    username = None
    invite_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True)  # メールを必須＆一意に
    full_name = models.CharField(max_length=50, blank=True, null=True)  # フルネーム（漢字・かな対応）
    move_date = models.DateField(null=True, blank=True)
    
    move_info = models.ForeignKey(
        "MoveInfo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )
    
    # ===== 旧 MoveGroup 設計（削除予定） =====
    #group = models.ForeignKey(
        #"MoveGroup",
        #on_delete=models.SET_NULL,
        #null=True,
        #blank=True,
        #related_name="members",
        #verbose_name="所属グループ"
    #)
    
    # メール変更用
    new_email = models.EmailField(null=True, blank=True)
    email_change_token = models.UUIDField(default=uuid.uuid4, null=True, blank=True)

    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()

    def __str__(self):
        return self.full_name or self.email


# ==========================
# 招待管理モデル
# ==========================
class Invite(models.Model):
    """招待リンク管理モデル"""
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    move_info = models.ForeignKey(
        "MoveInfo",
        on_delete=models.CASCADE,
        related_name='invites'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_used = models.BooleanField(default=False)  # 使用済みか

    def save(self, *args, **kwargs):
        """初回保存時に有効期限を設定（例：24時間後）"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        """期限切れかどうか"""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invite {self.code} (MoveInfo id={self.move_info_id})"
 
    
# ==========================
# メッセージ管理モデル
# ==========================
class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now)
    
    move_info = models.ForeignKey(
        'MoveInfo',
        on_delete=models.CASCADE,
        related_name='messages'
    )

    def __str__(self):
        return f"{self.sender} → {self.receiver}: {self.content[:15]}"
    
 
# ==========================
# タスク管理モデル（完了／未完対応）
# ==========================   
User = get_user_model()

class Task(models.Model):
    TASK_CHOICES = [
        ('内見', '内見'),
        ('新居の決定', '新居の決定'),
        ('賃貸借契約', '賃貸借契約'),
        ('引越し日決定', '引越し日決定'),
        ('引越し業者選び', '引越し業者選び'),
        ('現住所の賃貸契約解約の連絡', '現住所の賃貸契約解約の連絡'),
        ('引越し業者に依頼', '引越し業者に依頼'),
        ('粗大ごみの収集依頼・不用品の処分', '粗大ごみの収集依頼・不用品の処分'),
        ('梱包資材の準備', '梱包資材の準備'),
        ('固定電話の解約・変更手続き', '固定電話の解約・変更手続き'),
        ('インターネット回線の解約・変更手続き', 'インターネット回線の解約・変更手続き'),
        ('電気の停止手続き', '電気の停止手続き'),
        ('ガスの停止手続き', 'ガスの停止手続き'),
        ('水道の停止手続き', '水道の停止手続き'),
        ('郵便物の転送届', '郵便物の転送届'),
        ('転出届・転入届', '転出届・転入届'),
        ('マイナンバーカードの住所変更', 'マイナンバーカードの住所変更'),
        ('運転免許証の住所変更', '運転免許証の住所変更'),
        ('ガス開栓立ち会い', 'ガス開栓立ち会い'),
    ]
    
    move_info = models.ForeignKey(
        'MoveInfo',
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    
    created_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks"
    )
    
    task_name = models.CharField(max_length=100, blank=True)
    custom_task = models.CharField(max_length=100, blank=True, null=True)  # 自由入力
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    memo = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.custom_task or self.task_name
    
    
# ==========================
# 引越し情報（全ユーザー共通）
# ==========================
class MoveInfo(models.Model):
    owner = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='owned_moveinfos',
    )
    
    move_date = models.DateField(null=True, blank=True)
    updated_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_moveinfo'
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner_name = self.owner.full_name if self.owner else "未設定"
        date = self.move_date.strftime("%Y-%m-%d") if self.move_date else "未設定"
        return f"[管理者: {owner_name}] 引越し日: {date}"
    

# ==========================
# グループ情報
# ==========================    
#class MoveGroup(models.Model):
    #"""引越し用のグループ（1つの引越し単位）"""
    #name = models.CharField("グループ名", max_length=100)
    #owner = models.ForeignKey(
        #settings.AUTH_USER_MODEL,
        #on_delete=models.CASCADE,
        #related_name="owned_groups",
        #verbose_name="作成者"
    #)
    #created_at = models.DateTimeField(auto_now_add=True)

    #def __str__(self):
        #return self.name