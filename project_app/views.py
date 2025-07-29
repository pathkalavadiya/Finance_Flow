import csv
from django.shortcuts import render, redirect, redirect
from django.db.models import Sum, Count
from .models import Registration, Expense, Income, Lending
from django.http import HttpResponse, JsonResponse
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from datetime import datetime, date, timedelta
from functools import wraps
from django.db import OperationalError
import json

# Login required decorator
def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'entry_email' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

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
    return redirect('lending')


@login_required
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


@login_required
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


@login_required
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


@login_required
def profile(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    return render(request, 'profile.html', {'user': user})


def lending(request):
    user = None
    loans = []
    total_lent = 0
    total_received = 0
    is_logged_in = False
    
    # Check if user is logged in
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
        is_logged_in = True
        
        if user:
            if request.method == 'POST':
                # Handle loan creation
                borrower_name = request.POST.get('borrower_name')
                borrower_phone = request.POST.get('borrower_phone')
                borrower_email = request.POST.get('borrower_email')
                amount = request.POST.get('amount')
                currency = request.POST.get('currency', 'USD')
                description = request.POST.get('description')
                interest_rate = request.POST.get('interest_rate', 0)
                loan_date = request.POST.get('loan_date')
                due_date = request.POST.get('due_date')
                
                try:
                    # Create new loan
                    Lending.objects.create(
                        user=user,
                        borrower_name=borrower_name,
                        borrower_phone=borrower_phone,
                        borrower_email=borrower_email,
                        amount=amount,
                        currency=currency,
                        description=description,
                        interest_rate=interest_rate,
                        loan_date=loan_date,
                        due_date=due_date
                    )
                    
                    return render(request, 'lending.html', {
                        'success': True,
                        'message': 'Loan created successfully!',
                        'user': user,
                        'is_logged_in': is_logged_in
                    })
                except OperationalError:
                    return render(request, 'lending.html', {
                        'error': 'Database table not ready. Please run migrations first.',
                        'user': user,
                        'is_logged_in': is_logged_in
                    })
            
            try:
                # Get all loans for the user
                loans = Lending.objects.filter(user=user).order_by('-created_at')
                
                # Calculate totals
                active_loans = loans.filter(status='active')
                paid_loans = loans.filter(status='paid')
                
                total_lent = active_loans.aggregate(total=Sum('amount'))['total'] or 0
                total_received = paid_loans.aggregate(total=Sum('amount'))['total'] or 0
            except OperationalError:
                # Database table doesn't exist yet
                loans = []
                total_lent = 0
                total_received = 0
    
    context = {
        'user': user,
        'loans': loans,
        'total_lent': total_lent,
        'total_received': total_received,
        'today': date.today(),
        'is_logged_in': is_logged_in
    }
    return render(request, 'lending.html', context)


@login_required
def update_loan_status(request, loan_id):
    if 'entry_email' not in request.session:
        return redirect('login')
    
    user = Registration.objects.filter(email=request.session['entry_email']).first()
    if not user:
        return redirect('login')
    
    try:
        loan = Lending.objects.get(id=loan_id, user=user)
        new_status = request.POST.get('status')
        if new_status in ['active', 'paid', 'overdue', 'cancelled']:
            loan.status = new_status
            loan.save()
    except (Lending.DoesNotExist, OperationalError):
        pass
    
    return redirect('lending')


@login_required
def reports(request):
    user = None
    expenses = []
    incomes = []
    total_income = 0
    total_expense = 0
    net_balance = 0
    
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
        
        if user:
            # Get all expenses and incomes for the user
            expenses = Expense.objects.filter(user=user).order_by('-created_at')
            incomes = Income.objects.filter(user=user).order_by('-created_at')
            
            # Calculate totals
            total_income = incomes.aggregate(total=Sum('amount'))['total'] or 0
            total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0
            net_balance = total_income - total_expense
            
            # Get category-wise breakdowns
            expense_categories = expenses.values('category').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')
            
            income_categories = incomes.values('category').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')
    
    context = {
        'user': user,
        'expenses': expenses,
        'incomes': incomes,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
        'expense_categories': expense_categories,
        'income_categories': income_categories,
    }
    return render(request, 'reports.html', context)


@login_required
def export_report(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    if not user:
        return HttpResponse('Unauthorized', status=401)

    # Prepare CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="finance_report.csv"'
    writer = csv.writer(response)

    # Write headers
    writer.writerow(['Type', 'Amount', 'Category', 'Description', 'Currency', 'Date'])

    # Write incomes
    incomes = Income.objects.filter(user=user).order_by('-created_at')
    for income in incomes:
        writer.writerow([
            'Income',
            income.amount,
            income.category,
            income.description,
            income.currency,
            income.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    # Write expenses
    expenses = Expense.objects.filter(user=user).order_by('-created_at')
    for expense in expenses:
        writer.writerow([
            'Expense',
            expense.amount,
            expense.category,
            expense.description,
            expense.currency,
            expense.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response


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

