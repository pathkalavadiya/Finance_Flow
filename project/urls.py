"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', views.Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from project_app.views import register, login
from project_app.views import dashboard
from project_app.views import expense
from project_app.views import profile
from project_app.views import income
from project_app.views import logout

from project_app.views import reports, export_report
from project_app.views import analytics, chart_data

# Group Split Money Views
from project_app.views import groups, create_group, group_detail, add_group_expense, group_balances, add_group_member, delete_group

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('expense/', expense, name='expense'),
    path('profile/', profile, name='profile'),
    path('income/', income, name='income'),

    path('reports/', reports, name='reports'),
    path('export-report/', export_report, name='export_report'),
    path('analytics/', analytics, name='analytics'),
    path('chart-data/', chart_data, name='chart_data'),
    
    # Group Split Money URLs
    path('groups/', groups, name='groups'),
    path('create-group/', create_group, name='create_group'),
    path('group/<int:group_id>/', group_detail, name='group_detail'),
    path('group/<int:group_id>/add-expense/', add_group_expense, name='add_group_expense'),
    path('group/<int:group_id>/balances/', group_balances, name='group_balances'),
    path('group/<int:group_id>/add-member/', add_group_member, name='add_group_member'),
    path('group/<int:group_id>/delete/', delete_group, name='delete_group'),
    

    

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)