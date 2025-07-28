from django.shortcuts import render, redirect, redirect
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear
from django.http import JsonResponse
from datetime import datetime, timedelta
from .models import Registration, Expense, Income
import json
#this is the views file for the Finance Flow project
# Create your views here.
# registration
def register(request):
    if request.method == 'POST':
        register_data = Registration()
        register_data.name = request.POST['name']
        register_data.email = request.POST['email']
        register_data.phone_no = request.POST['mob']
        register_data.password = request.POST['password']
        register_data.confirm_password = request.POST['confirm_password']
        if request.POST['password'] != request.POST['confirm_password']:
            return render(request, 'register.html', {'password_mismatch': "Passwords do not match"})
        register_data.address = request.POST['add']
        try:
            check_register = Registration.objects.get(email=request.POST['email'])
         
            if check_register:
                return render(request, 'register.html', {'register_check_key': "Email already exists"})
        except:
            register_data.save()
            return render(request, 'register.html', {'register_key': "Registration Successful"})
    return render(request, 'register.html')

 
# login
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        check_register = Registration.objects.filter(email=email).first()
        if check_register:
            if check_register.password == password:
                request.session['entry_email'] = check_register.email
                return redirect('dashboard')
            else:
                return render(request, 'login.html', {'login_key_incorrect': "Email or password is wrong"})
        else:
            return render(request, 'login.html', {'not_register': "This email is not registered"})
    return render(request, 'login.html')


# logout
def logout(request):
    if 'entry_email' in request.session:
        del request.session['entry_email']
    return redirect('login')


def dashboard(request):
    user = None
    total_income = 0
    total_expense = 0
    net_balance = 0
    
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
        
        if user:
            # Calculate total income
            income_sum = Income.objects.filter(user=user).aggregate(total=Sum('amount'))
            total_income = income_sum['total'] or 0
            
            # Calculate total expense
            expense_sum = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))
            total_expense = expense_sum['total'] or 0
            
            # Calculate net balance
            net_balance = total_income - total_expense
    
    context = {
        'user': user,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance
    }
    return render(request, 'dashboard.html', context)


def expense(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        currency = request.POST.get('currency')
        category = request.POST.get('category')
        
        # Save to database with user association
        if user:
            Expense.objects.create(
                user=user,
                amount=amount,
                description=description,
                currency=currency,
                category=category
            )
        else:
            # Handle case where user is not logged in
            return redirect('login')
            
        return render(request, 'expense.html', {
            'success': True,
            'amount': amount,
            'description': description,
            'currency': currency,
            'category': category
        })
    return render(request, 'expense.html')


def income(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        currency = request.POST.get('currency')
        category = request.POST.get('category')
        
        # Save to database with user association
        if user:
            Income.objects.create(
                user=user,
                amount=amount,
                description=description,
                currency=currency,
                category=category
            )
        else:
            # Handle case where user is not logged in
            return redirect('login')
            
        return render(request, 'income.html', {
            'success': True,
            'amount': amount,
            'description': description,
            'currency': currency,
            'category': category
        })
    return render(request, 'income.html')


def profile(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    return render(request, 'profile.html', {'user': user})


def analytics(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if not user:
        return redirect('login')
    
    # Get date range (last 12 months)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Monthly income and expense data
    monthly_income = Income.objects.filter(
        user=user,
        created_at__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    monthly_expense = Expense.objects.filter(
        user=user,
        created_at__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')
    
    # Category breakdown
    income_categories = Income.objects.filter(user=user).values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    expense_categories = Expense.objects.filter(user=user).values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    # Recent transactions
    recent_income = Income.objects.filter(user=user).order_by('-created_at')[:5]
    recent_expense = Expense.objects.filter(user=user).order_by('-created_at')[:5]
    
    # Summary statistics
    total_income = Income.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    total_expense = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or 0
    net_balance = total_income - total_expense
    
    # Average monthly income and expense
    avg_monthly_income = total_income / 12 if total_income > 0 else 0
    avg_monthly_expense = total_expense / 12 if total_expense > 0 else 0
    
    context = {
        'user': user,
        'monthly_income': list(monthly_income),
        'monthly_expense': list(monthly_expense),
        'income_categories': list(income_categories),
        'expense_categories': list(expense_categories),
        'recent_income': recent_income,
        'recent_expense': recent_expense,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'avg_monthly_income': avg_monthly_income,
        'avg_monthly_expense': avg_monthly_expense,
    }
    
    return render(request, 'analytics.html', context)


def chart_data(request):
    """API endpoint to get chart data"""
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if not user:
        return JsonResponse({'error': 'User not authenticated'}, status=401)
    
    chart_type = request.GET.get('type', 'monthly')
    
    if chart_type == 'monthly':
        # Get last 12 months data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        monthly_income = Income.objects.filter(
            user=user,
            created_at__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        monthly_expense = Expense.objects.filter(
            user=user,
            created_at__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # Format data for Chart.js
        months = []
        income_data = []
        expense_data = []
        
        # Create a complete 12-month dataset
        for i in range(12):
            date = end_date - timedelta(days=30*i)
            month_key = date.strftime('%Y-%m')
            months.insert(0, date.strftime('%B %Y'))
            
            # Find income for this month
            income_amount = 0
            for item in monthly_income:
                if item['month'].strftime('%Y-%m') == month_key:
                    income_amount = float(item['total'])
                    break
            income_data.insert(0, income_amount)
            
            # Find expense for this month
            expense_amount = 0
            for item in monthly_expense:
                if item['month'].strftime('%Y-%m') == month_key:
                    expense_amount = float(item['total'])
                    break
            expense_data.insert(0, expense_amount)
        
        return JsonResponse({
            'labels': months,
            'datasets': [
                {
                    'label': 'Income',
                    'data': income_data,
                    'borderColor': '#10b981',
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                    'tension': 0.4
                },
                {
                    'label': 'Expense',
                    'data': expense_data,
                    'borderColor': '#ef4444',
                    'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                    'tension': 0.4
                }
            ]
        })
    
    elif chart_type == 'categories':
        # Category breakdown data
        income_categories = Income.objects.filter(user=user).values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        expense_categories = Expense.objects.filter(user=user).values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        return JsonResponse({
            'income': {
                'labels': [item['category'] for item in income_categories],
                'data': [float(item['total']) for item in income_categories]
            },
            'expense': {
                'labels': [item['category'] for item in expense_categories],
                'data': [float(item['total']) for item in expense_categories]
            }
        })
    
    return JsonResponse({'error': 'Invalid chart type'}, status=400)

