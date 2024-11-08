from django.contrib import admin
from accounts.models import User


@admin.register(User)
class AccountsAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'profile_image', 'residence_area', 'gender', 'age')