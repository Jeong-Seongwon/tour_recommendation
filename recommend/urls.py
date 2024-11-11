from django.urls import path
from recommend import views

app_name = 'recommend'
urlpatterns = [
    path('tour/', views.tour_view, name='tour'),
    path('pop_tours/', views.pop_tours_view, name='pop_tours'),
    path('customer/', views.customer_view, name='customer'),
    path('recommend_tours/', views.recommend_tours_view, name='recommend_tours'),
    path('tour_info/<int:id>/', views.tour_info_view, name='tour_info'),

    path('planned-visits/', views.planned_visits, name='planned_visits'),
    path('visit/<int:visit_id>/add/', views.add_to_planned_visits, name='add_to_planned_visits'),
    path('visit/<int:visit_id>/remove/', views.remove_from_planned_visits, name='remove_from_planned_visits'),
    path('create-travel/', views.create_travel_from_planned_visits, name='create_travel_from_planned_visits'),

    path('travel/<slug:travel_id>/', views.travel_detail, name='travel_detail'),
    path('travel/', views.travel_detail, name='travel_detail'),
]
