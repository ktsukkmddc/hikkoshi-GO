# app/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Invite, Message

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'invite_code', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ("code", "created_at", "expires_at", "is_used")
    list_filter = ("is_used",)
    search_fields = ("code",)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "content", "created_at")
    search_fields = ("sender__email", "receiver__email", "content")
    list_filter = ("created_at",)
    ordering = ("-created_at",)  # 新しい順に表示