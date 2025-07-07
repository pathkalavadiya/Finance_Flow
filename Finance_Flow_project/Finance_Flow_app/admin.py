from django.contrib import admin
from .models import *
# Register your models here.
class Reg_(admin.ModelAdmin):
    list_display = ['id','name','email','mob','add']

admin.site.register(Registration,Reg_)