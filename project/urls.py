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
from django.urls import path, include
from project_app.views import register, login
from project_app.views import dashboard, lending
from project_app.views import expense
from project_app.views import profile
from project_app.views import income
from project_app.views import logout
from project_app.views import transaction_history

from project_app.views import reports, export_report, generate_report, generate_custom_report
from project_app.views import analytics, chart_data
from project_app.views import landing, subscribe_newsletter
from project_app.views import notifications_data
from project_app.views import export_profile_data, delete_account

# Edit and Delete Transaction Views
from project_app.views import edit_income, edit_expense, delete_income, delete_expense

# Group Split Money Views
from project_app.views import groups, create_group, group_detail, add_group_expense, group_balances, add_group_member, delete_group

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing, name='landing'),
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('lending/', lending, name='lending'),
    path('expense/', expense, name='expense'),
    path('profile/', profile, name='profile'),
    path('income/', income, name='income'),
    path('transactions/', transaction_history, name='transaction_history'),

    path('reports/', reports, name='reports'),
    path('export-report/', export_report, name='export_report'),
    path('generate-report/', generate_report, name='generate_report'),
    path('generate-custom-report/', generate_custom_report, name='generate_custom_report'),
    path('analytics/', analytics, name='analytics'),
    path('chart-data/', chart_data, name='chart_data'),
    path('notifications-data/', notifications_data, name='notifications_data'),
    path('subscribe-newsletter/', subscribe_newsletter, name='subscribe_newsletter'),
    path('accounts/', include('allauth.urls')),
    # Profile actions
    path('profile/export/', export_profile_data, name='export_profile_data'),
    path('profile/delete/', delete_account, name='delete_account'),
    
    # Edit and Delete Transaction URLs
    path('income/edit/<int:income_id>/', edit_income, name='edit_income'),
    path('expense/edit/<int:expense_id>/', edit_expense, name='edit_expense'),
    path('income/delete/<int:income_id>/', delete_income, name='delete_income'),
    path('expense/delete/<int:expense_id>/', delete_expense, name='delete_expense'),
    
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