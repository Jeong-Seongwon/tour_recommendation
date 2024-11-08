from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from accounts.forms import LoginForm, SignUpForm, ProfileUpdateForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User

def login_view(request):
    if request.user.is_authenticated:
        return redirect(reverse("main"))

    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect(reverse("main"))
            else:
                form.add_error(None, "입력한 자격증명에 해당하는 사용자가 없습니다.")
        return render(request, "accounts/login.html", {"form": form})
    else:
        form = LoginForm()
        return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect(reverse("main"))

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST, files=request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("main"))
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})

def profile_view(request):
    return render(request, "accounts/profile.html", {"user": request.user})

@login_required
def edit_profile_view(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            current_password = form.cleaned_data.get("current_password")
            new_password = form.cleaned_data.get("new_password")

            # 현재 비밀번호 검증
            if request.user.check_password(current_password):
                # 비밀번호 변경
                if new_password:
                    request.user.set_password(new_password)
                request.user.email = form.cleaned_data.get("email")
                request.user.short_description = form.cleaned_data.get("short_description")
                if 'profile_image' in request.FILES:
                    request.user.profile_image = request.FILES['profile_image']
                request.user.save()

                # 새로운 세션으로 인증 정보 갱신
                update_session_auth_hash(request, request.user)

                return redirect('accounts:profile')
            else:
                form.add_error('current_password', "현재 비밀번호가 올바르지 않습니다.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "accounts/edit_profile.html", {
        'form': form,
        'username': request.user.username,  # username 추가
    })

@login_required
def reset_profile_image_view(request):
    user = request.user
    user.profile_image.delete(save=False)  # 기존 이미지를 삭제
    # user.profile_image = 'accounts/images/default_profile.png'  # 기본 이미지 경로 설정
    user.save()
    return redirect(reverse('accounts:edit_profile'))  # 프로필 수정 페이지로 리디렉션

