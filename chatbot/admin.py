from django.contrib import admin
from chatbot.models import TouristSpot


@admin.register(TouristSpot)
class ChatbotAdmin(admin.ModelAdmin):
    list_display = ('touristspot_name', 'main_cate', 'second_cate', 'third_cate', 'description', 'tags')