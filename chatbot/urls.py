from django.urls import path
from chatbot import views

app_name = 'chatbot'
urlpatterns = [
    path('', views.chatbot, name='chatbot'),
    path('search_tourist_spot/', views.search_tourist_spot, name='search_tourist_spot'),
]
