<<<<<<< HEAD
from django.urls import path 
from . import views 

urlpatterns = [
   
   
    path('register/', views.register, name='register'),
    # path('login/', views.login, name='login'),
    # path('logout/', views.logout, name='logout'),
    
=======
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="Finance_Flow_app"),
    path('add-expense/', views.add_expense, name="add_expense"),
>>>>>>> c62aaeeeba9b988c71292dc8499b3f225fdc63fc
]