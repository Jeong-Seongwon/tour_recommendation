from django.urls import path
from recommend import views

app_name = 'recommend'
urlpatterns = [
    path('tour/', views.tour_view, name='tour'),
    path('pop_tours/', views.pop_tours_view, name='pop_tours'),
    path('customer/', views.customer_view, name='customer'),
    path('recommend_tours/', views.recommend_tours_view, name='recommend_tours'),
    path('tour_info/<int:id>/', views.tour_info_view, name='tour_info'),
]
