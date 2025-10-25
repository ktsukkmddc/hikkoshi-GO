from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import uuid


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
    
class CustomUser(AbstractUser):
    """拡張ユーザーモデル"""
    username = None
    invite_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True)  # メールを必須＆一意に
    # 今後の拡張用（例：電話番号など）
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    
class Invite(models.Model):
    """招待リンク管理モデル"""
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # 誰が招待したか
        on_delete=models.CASCADE,
        related_name='sent_invites'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)  # 有効期限
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
        inviter_email = self.inviter.email if self.inviter else "Unknown"
        return f"{self.code}（by {self.inviter.email}）"
    

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

    def __str__(self):
        return f"{self.sender} → {self.receiver}: {self.content[:15]}"