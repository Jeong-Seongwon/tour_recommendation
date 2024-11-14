from django.shortcuts import render
from recommend.models import TRAVEL_PURPOSE_CHOICES

def main(request):
    context = {
        'TRAVEL_PURPOSE_CHOICES': dict(TRAVEL_PURPOSE_CHOICES)
    }
    return render(request, "main.html", context)