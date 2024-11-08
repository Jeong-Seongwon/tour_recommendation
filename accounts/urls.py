from django.urls import path

from accounts import views

app_name = "accounts"
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/reset_image/', views.reset_profile_image_view, name='reset_profile_image'),
]
