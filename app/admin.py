# app/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Invite, Message, MoveInfo, Task

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'full_name', 'invite_code', 'is_staff', 'is_active')
    search_fields = ('email', 'full_name')
    ordering = ('email',)
    
    readonly_fields = ('invite_code',)
    
    # username を使わない構成に修正
    fieldsets = (
        (None, {'fields': ('email', 'password', 'full_name', 'invite_code')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

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
    
admin.site.register(MoveInfo)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('created_by', 'task_name', 'is_completed', 'created_at')  # 表示カラムを指定
    list_filter = ('is_completed',)
    search_fields = ('task_name', 'created_by__email')