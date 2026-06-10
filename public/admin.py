from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.

class CustomUserAdmin(UserAdmin):
    model = User
    
    list_display = ['username', 'email', 'student_number', 'is_active', 'is_staff', 'is_superuser']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'student_number']
    
    fieldsets = UserAdmin.fieldsets + (
        ("Informacoes adicionais", {'fields': ('student_number',)}),
    )

admin.site.register(User, CustomUserAdmin)
