from django.urls import path
from chart import views

app_name = 'chart'
urlpatterns = [
    path('', views.chart_view, name='chart'),
    path('travel_statistics/', views.travel_statistics, name='travel_statistics'),
    path('user_travel_statistics/', views.user_travel_statistics, name='user_travel_statistics')
]
