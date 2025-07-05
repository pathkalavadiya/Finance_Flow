from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="Finance_Flow_app"),
    path('add-expense/', views.add_expense, name="add_expense"),
]