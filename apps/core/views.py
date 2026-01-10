from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

def home(request):
    return JsonResponse({"app": "Talena", "status": "alive"})

def health(request):
    return JsonResponse({"status": "ok"})

@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")