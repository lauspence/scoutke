from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .forms import *



@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profile updated successfully!")
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})


def register(request): 
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save() 
            messages.success(request, "🎉 Account created successfully! Please log in.")
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect_user_by_role(user)
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# helper function
def redirect_user_by_role(user):
    if user.role == 'player':
        return redirect('dashboard')
    elif user.role == 'scout':
        return redirect('scout_dashboard')
    elif user.role == 'club':
        return redirect('club_dashboard')
    else:
        return redirect('home') 
