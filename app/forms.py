import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Task
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
        password = self.cleaned_data.get("password1") or ""
        errors = []
        
        # 10文字以上
        if len(password) < 10:
            errors.append("パスワードは10文字以上で入力してください。")
        
        # 大文字
        if not re.search(r"[A-Z]", password):
            errors.append("パスワードに大文字を含めてください。")
        
        # 小文字
        if not re.search(r"[a-z]", password):
            errors.append("パスワードに小文字を含めてください。")
        
        # 数字
        if not re.search(r"\d", password):
            errors.append("パスワードに数字を含めてください。")
        
        # 記号
        if not re.search(r"[!%@$#&]", password):
            errors.append("パスワードに記号（!, %, @, #, $, &）を含めてください。")
            
        if errors:
            raise forms.ValidationError(errors)
        
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
        error_messages={'required': '日付を入力してください'},
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'type': 'time'})
    )
    
    end_time = forms.TimeField(
        required=False,
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
        
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        # どちらも未選択
        if not task_mode:
            raise forms.ValidationError("「選択式」か「自由入力」を選んでください")

        # ★タスク未入力を1つのエラーにまとめる
        if task_mode == "select" and not task_name:
            raise forms.ValidationError("タスクを入力してください")
        if task_mode == "custom" and not custom_task:
            raise forms.ValidationError("タスクを入力してください")
                
        if start_time and end_time:
            if end_time <= start_time:
                self.add_error("end_time", "終了時刻は開始時刻より後の時間を指定してください")

        return cleaned_data
        
        
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