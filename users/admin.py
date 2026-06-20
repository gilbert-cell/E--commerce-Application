from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'role', 'is_active', 'is_staff', 'is_face_enrolled', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_face_enrolled', 'date_joined')
    search_fields = ('email', 'name')
    readonly_fields = ('date_joined', 'last_login', 'face_embedding')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('email', 'name', 'date_joined', 'last_login')
        }),
        ('Permissions & Roles', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Face Authentication', {
            'fields': ('is_face_enrolled', 'is_verified', 'face_embedding'),
            'classes': ('collapse',)
        }),
    )
