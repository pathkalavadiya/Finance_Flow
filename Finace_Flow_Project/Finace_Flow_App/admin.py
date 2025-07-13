from django.apps import AppConfig
from django.contrib import admin
from .models import *

class FinaceFlowAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Finace_Flow_App'

class Reg_(admin.ModelAdmin):
    list_display = ['id','name','email','mob','add']

admin.site.register(Registration,Reg_)