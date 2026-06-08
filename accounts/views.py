from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AccountSettingsForm,
    UserLoginForm,
    UserRegisterForm,
    UserSettingsForm,
    UserUpdateForm,
    VerificationRequestForm,
)
from .models import User, UserSettings, VerificationRequest


@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
        messages.error(request, "Please fix the highlighted profile details.")
    else:
        form = UserUpdateForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


def register(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            UserSettings.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, "Account created successfully. Let's set up your ScoutKE experience.")
            return onboarding_redirect(user)
        messages.error(request, "Please fix the highlighted signup details.")
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect_user_by_role(request.user)

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}.")
            return redirect_user_by_role(user)
        messages.error(request, "Check your username and password, then try again.")
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def settings_view(request):
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
    account_form = AccountSettingsForm(instance=request.user)
    settings_form = UserSettingsForm(instance=user_settings)
    password_form = PasswordChangeForm(request.user)
    latest_verification = request.user.verification_requests.first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'account':
            account_form = AccountSettingsForm(request.POST, request.FILES, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                messages.success(request, "Account settings updated.")
                return redirect('settings')
            messages.error(request, "Please fix the highlighted account details.")

        elif action == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                return redirect('settings')
            messages.error(request, "Please fix the highlighted password details.")

        elif action == 'preferences':
            settings_form = UserSettingsForm(request.POST, instance=user_settings)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Preferences saved.")
                return redirect('settings')
            messages.error(request, "Please fix the highlighted preference details.")

    return render(request, 'accounts/settings.html', {
        'account_form': account_form,
        'settings_form': settings_form,
        'password_form': password_form,
        'latest_verification': latest_verification,
    })


@login_required
def request_verification(request):
    if request.user.role not in ("scout", "club"):
        messages.error(request, "Verification is currently available for scouts and clubs.")
        return redirect("settings")

    if request.user.is_verified_account:
        messages.info(request, "Your account is already verified.")
        return redirect("settings")

    if request.user.verification_status == User.VERIFICATION_PENDING:
        messages.info(request, "Your verification request is already waiting for staff review.")
        return redirect("settings")

    if request.method == "POST":
        form = VerificationRequestForm(request.POST)
        if form.is_valid():
            verification = form.save(commit=False)
            verification.user = request.user
            verification.save()
            request.user.verification_status = User.VERIFICATION_PENDING
            request.user.save(update_fields=["verification_status"])
            messages.success(request, "Verification request sent. Staff will review your details.")
            return redirect("settings")
        messages.error(request, "Please fix the highlighted verification details.")
    else:
        form = VerificationRequestForm()

    return render(request, "accounts/verification_request.html", {"form": form})


@login_required
def verification_queue(request):
    if not request.user.is_staff:
        messages.error(request, "Only staff can review verification requests.")
        return redirect("feed")

    status = request.GET.get("status", VerificationRequest.STATUS_PENDING)
    requests = VerificationRequest.objects.select_related("user", "reviewed_by")
    if status in dict(VerificationRequest.STATUS_CHOICES):
        requests = requests.filter(status=status)
    else:
        status = "all"

    return render(request, "accounts/verification_queue.html", {
        "verification_requests": requests,
        "current_status": status,
    })


@login_required
def review_verification_request(request, request_id, action):
    if not request.user.is_staff:
        messages.error(request, "Only staff can review verification requests.")
        return redirect("feed")

    verification = get_object_or_404(VerificationRequest, id=request_id)
    if request.method != "POST":
        return redirect("verification_queue")

    if action == "approve":
        verification.approve(request.user)
        messages.success(request, f"{verification.user.username} is now verified.")
    elif action == "reject":
        verification.reject(request.user)
        messages.success(request, f"{verification.user.username}'s request was rejected.")
    else:
        messages.error(request, "Unknown verification action.")

    return redirect("verification_queue")


def redirect_user_by_role(user):
    if user.role == 'player':
        return redirect('dashboard')
    if user.role == 'scout':
        return redirect('scout_dashboard')
    if user.role == 'club':
        return redirect('club_dashboard')
    return redirect('feed')


def onboarding_redirect(user):
    if user.role == 'player':
        return redirect('update_profile')
    if user.role == 'scout':
        return redirect('talent_radar')
    if user.role == 'club':
        return redirect('club_dashboard')
    return redirect('feed')
