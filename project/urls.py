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
from project_app.views import lending, update_loan_status
from project_app.views import reports, export_report
from project_app.views import analytics, chart_data
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lending, name='lending'),
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('expense/', expense, name='expense'),
    path('profile/', profile, name='profile'),
    path('income/', income, name='income'),
    path('lending/', lending, name='lending'),
    path('lending/update-status/<int:loan_id>/', update_loan_status, name='update_loan_status'),
    path('reports/', reports, name='reports'),
    path('export-report/', export_report, name='export_report'),
    path('analytics/', analytics, name='analytics'),
    path('chart-data/', chart_data, name='chart_data'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)