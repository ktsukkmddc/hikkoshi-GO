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