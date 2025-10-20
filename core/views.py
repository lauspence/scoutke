from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to ScoutKe!")  
    # Later we can replace this with render(request, "core/home.html")

def club_dashboard(request):
    return render(request, 'core/club_dashboard.html')
