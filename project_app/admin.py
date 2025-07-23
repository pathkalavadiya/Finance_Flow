from django.contrib import admin
from .models import Registration, Expense

class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone_no", "address")

admin.site.register(Registration, RegistrationAdmin)
admin.site.register(Expense)


