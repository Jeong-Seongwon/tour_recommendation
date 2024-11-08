from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User
from django.contrib.auth.forms import UserChangeForm

class SignUpForm(forms.Form):
    username = forms.CharField()
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    profile_image = forms.ImageField(required=False)
    short_description = forms.CharField(required=False)
    residence_area = forms.CharField(required=False)

    GENDER_CHOICES = [('남', '남'), ('여', '여')]
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.RadioSelect,
        label="성별",
        required=False
    )

    age = forms.IntegerField(required=False, label="나이")

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError(f'입력한 사용자명({username})은 이미 사용 중입니다.')
        return username
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 != password2:
            self.add_error("password2", "비밀번호와 비밀번호 확인란의 값이 다릅니다.")

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password1'],
            profile_image=self.cleaned_data.get('profile_image'),
            short_description=self.cleaned_data.get('short_description'),
            residence_area=self.cleaned_data.get('residence_area'),
            gender=self.cleaned_data.get('gender'),
            age=self.cleaned_data.get('age'),
        )
        return user

class LoginForm(forms.Form):
    username = forms.CharField(
        min_length=3,
        widget=forms.TextInput(attrs={"placeholder": "사용자명 (3자리 이상)"}),
    )
    password = forms.CharField(
        min_length=4,
        widget=forms.PasswordInput(attrs={"placeholder": "비밀번호 (4자리 이상)"}),
    )

class ProfileUpdateForm(UserChangeForm):
    new_password = forms.CharField(
        label='새 비밀번호',
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': '새 비밀번호를 입력하세요'})
    )
    confirm_password = forms.CharField(
        label='비밀번호 확인',
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': '비밀번호를 다시 입력하세요'})
    )
    current_password = forms.CharField(
        label='현재 비밀번호',
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': '현재 비밀번호를 입력하세요'})
    )

    class Meta:
        model = User
        fields = ('email', 'short_description', 'profile_image', 'residence_area', 'gender', 'age')

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        # 현재 비밀번호 확인
        if not self.instance.check_password(current_password):
            raise forms.ValidationError("현재 비밀번호가 올바르지 않습니다.")

        # 새 비밀번호와 비밀번호 확인 확인
        if new_password and new_password != confirm_password:
            raise forms.ValidationError("새 비밀번호와 비밀번호 확인이 일치하지 않습니다.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')

        if new_password:  # 새로운 비밀번호가 입력되었다면
            user.set_password(new_password)

        if commit:
            user.save()
        return user
