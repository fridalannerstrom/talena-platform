from django.shortcuts import render
from django.http import JsonResponse

def home(request):
    return JsonResponse({"app": "Talena", "status": "alive"})

def health(request):
    return JsonResponse({"status": "ok"})