import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Task, MoveGroup
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

User = get_user_model()

TASK_CHOICES = [
    ('荷造り', '荷造り'),
    ('清掃', '清掃'),
    ('手続き', '手続き'),
]

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={"autofocus": True})
    )
    
    password = forms.CharField(
        label="パスワード",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    class Meta:
        model = User
        fields = ['email', 'password']
        
        
class CustomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(label='氏名（フルネーム）', max_length=50, required=True)
    
    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'password1', 'password2']
    
    # パスワードのバリデーションを追加    
    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        
        # 10文字以上
        if len(password) < 10:
            raise forms.ValidationError("パスワードは10文字以上で入力してください。")
        
        # 大文字
        if not re.search(r"[A-Z]", password):
            raise forms.ValidationError("パスワードに大文字を含めてください。")
        
        # 小文字
        if not re.search(r"[a-z]", password):
            raise forms.ValidationError("パスワードに小文字を含めてください。")
        
        # 数字
        if not re.search(r"\d", password):
            raise forms.ValidationError("パスワードに数字を含めてください。")
        
        # 記号
        if not re.search(r"[!%@$#&]", password):
            raise forms.ValidationError("パスワードに記号（!, %, @, #, $, &）を含めてください。")
        
        return password
            

class TaskForm(forms.ModelForm):
    task_name = forms.ChoiceField(
        choices=[('', '選択してください')] + Task.TASK_CHOICES,
        required=False,
    )
    
    custom_task = forms.CharField(
        required=False
    )
    
    date = forms.DateField(
        required=True,
        error_messages={'required': '日付を入力してください。'},
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    start_time = forms.TimeField(
        required=True,
        error_messages={'required': '開始時間を入力してください。'},
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    
    end_time = forms.TimeField(
        required=True,
        error_messages={'required': '終了時間を入力してください。'},
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    
    memo = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3})
    )

    class Meta:
        model = Task
        fields = ['task_name', 'custom_task', 'date', 'start_time', 'end_time', 'memo']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
    
        task_mode = self.data.get("task_mode")  # ラジオボタン値
        task_name = cleaned_data.get("task_name")
        custom_task = cleaned_data.get("custom_task")

        # どちらも未選択
        if not task_mode:
            raise forms.ValidationError("「選択式」か「自由入力」を選んでください。")

        # 選択式の場合 → セレクトが必須
        if task_mode == "select":
            if not task_name:
                self.add_error('task_name', "タスクを選択してください。")

        # 自由入力の場合 → custom_task が必須
        if task_mode == "custom":
            if not custom_task:
                self.add_error('custom_task', "タスクを入力してください。")

        return cleaned_data
    

class MoveGroupForm(forms.ModelForm):
    class Meta:
        model = MoveGroup
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'})
        }
        
        
class CustomPasswordResetForm(PasswordResetForm):

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email,
                  html_email_template_name=None):

        # 件名
        subject = render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())

        # 本文
        body = render_to_string(email_template_name, context)

        # EmailMessage を使う → SendGrid API が動く
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[to_email]
        )
        return email.send()