import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Task

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
        required=False
    )
    
    class Meta:
        model = Task
        fields = ['task_name', 'custom_task', 'date', 'start_time', 'end_time', 'memo']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }