import csv
import json
from django.shortcuts import render, redirect, redirect
from django.db.models import Sum, Count
from .models import Registration, Expense, Income, Group, GroupMember, GroupExpense, GroupExpenseSplit
from django.http import HttpResponse, JsonResponse
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from django.views.decorators.csrf import ensure_csrf_cookie
from datetime import datetime, date, timedelta
from functools import wraps
from django.db import OperationalError
from decimal import Decimal
import calendar

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
        # Get form data
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone_no = request.POST.get('mob', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        address = request.POST.get('add', '').strip()
        
        # Basic validation
        if not all([name, email, phone_no, password, confirm_password, address]):
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "All fields are required"})
        
        # Check password match
        if password != confirm_password:
            return render(request, 'authentication/register.html', 
                        {'password_mismatch': "Passwords do not match"})
        
        # Check password length (model constraint is 8 characters)
        if len(password) > 8:
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "Password must be 8 characters or less"})
        
        # Check phone number length
        if len(phone_no) != 10:
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "Phone number must be 10 digits"})
        
        # Check if email already exists
        try:
            check_register = Registration.objects.get(email=email)
            if check_register:
                return render(request, 'authentication/register.html', 
                            {'register_check_key': "Email already exists"})
        except Registration.DoesNotExist:
            # Email doesn't exist, proceed with registration
            try:
                register_data = Registration(
                    name=name,
                    email=email,
                    phone_no=phone_no,
                    password=password,
                    address=address
                )
                register_data.save()
                return render(request, 'authentication/register.html', 
                            {'register_key': "Registration Successful! You can now login."})
            except Exception as e:
                return render(request, 'authentication/register.html', 
                            {'register_check_key': f"Registration failed: {str(e)}"})
    
    return render(request, 'authentication/register.html')

 
# login
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        # Basic validation
        if not email or not password:
            return render(request, 'authentication/login.html', 
                        {'login_key_incorrect': "Please enter both email and password"})
        
        try:
            check_register = Registration.objects.get(email=email)
            if check_register.password == password:
                request.session['entry_email'] = check_register.email
                return redirect('dashboard')
            else:
                return render(request, 'authentication/login.html', 
                            {'login_key_incorrect': "Email or password is incorrect"})
        except Registration.DoesNotExist:
            return render(request, 'authentication/login.html', 
                        {'not_register': "This email is not registered"})
    
    return render(request, 'authentication/login.html')


# logout
def logout(request):
    if 'entry_email' in request.session:
        del request.session['entry_email']
    return redirect('landing')


def landing(request):
    # If logged in, go to dashboard; otherwise show public landing page
    if 'entry_email' in request.session:
        return redirect('dashboard')
    return render(request, 'landing.html')


@login_required
def dashboard(request):
    user = None
    total_income = 0
    total_expense = 0
    net_balance = 0
    max_income = 0
    max_expense = 0
    previous_balance = 0
    balance = 0
    balance_change_percent = 0.0
    
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
            
            # Calculate max income and expense for the chart stats
            max_income = Income.objects.filter(user=user).aggregate(max_amount=Sum('amount'))['max_amount'] or 20239
            max_expense = Expense.objects.filter(user=user).aggregate(max_amount=Sum('amount'))['max_amount'] or 20239
            
            # Progress tracking calculations
            current_date = datetime.now()
            current_month = current_date.strftime('%B %Y')
            
            # Get current month's income and expenses
            current_month_income = Income.objects.filter(
                user=user,
                created_at__year=current_date.year,
                created_at__month=current_date.month
            ).aggregate(total=Sum('amount'))['total'] or 0

            current_month_expense = Expense.objects.filter(
                user=user,
                created_at__year=current_date.year,
                created_at__month=current_date.month
            ).aggregate(total=Sum('amount'))['total'] or 0


            # Get previous month's income
            previous_month = current_date.month - 1 if current_date.month > 1 else 12
            previous_year = current_date.year if current_date.month > 1 else current_date.year - 1
            previous_income = Income.objects.filter(
                user=user,
                created_at__year=previous_year,
                created_at__month=previous_month
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Calculate income change percent
            income_change_percent = 0.0
            if previous_income and previous_income > 0:
                income_change_percent = ((total_income - previous_income) / previous_income) * 100

            # Get previous month's expenses
            previous_expenses = Expense.objects.filter(
                user=user,
                created_at__year=previous_year,
                created_at__month=previous_month
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Calculate expense change percent
            expense_change_percent = 0.0
            if previous_expenses and previous_expenses > 0:
                expense_change_percent = ((total_expense - previous_expenses) / previous_expenses) * 100
                
            # Calculate previous month's balance
            previous_balance = previous_income - previous_expenses
            balance = net_balance
            balance_change_percent = 0.0
            if previous_balance and previous_balance > 0:
                balance_change_percent = ((balance - previous_balance) / previous_balance) * 100
            
            # Set goals/budgets (you can make these configurable later)
            income_goal = 3100  # $3100 monthly income goal
            expense_budget = 2500  # $2500 monthly expense budget
            
            # Calculate progress percentages
            income_progress_percentage = min(int((current_month_income / income_goal) * 100), 100)
            expense_progress_percentage = min(int((current_month_expense / expense_budget) * 100), 100)
            
            # Calculate remaining percentages
            income_remaining_percentage = max(100 - income_progress_percentage, 0)
            expense_remaining_percentage = expense_progress_percentage
            
            # Calculate days left in month
            days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
            days_left = days_in_month - current_date.day
            
            # Get last update timestamps
            last_income = Income.objects.filter(user=user).order_by('-created_at').first()
            last_expense = Expense.objects.filter(user=user).order_by('-created_at').first()
            
            last_income_update = last_income.created_at if last_income else current_date
            last_expense_update = last_expense.created_at if last_expense else current_date
            
            # Sales Report calculations
            # Today's sales (income)
            today_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            today_sales = Income.objects.filter(
                user=user,
                created_at__gte=today_start,
                created_at__lt=today_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # This week's sales (income)
            week_start = current_date - timedelta(days=current_date.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            week_sales = Income.objects.filter(
                user=user,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # This month's sales (income)
            month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            month_sales = Income.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Planned sales targets (you can make these configurable)
            today_planned_sales = 300
            week_planned_sales = 2100
            month_planned_sales = 9000
            
            # Calculate progress percentages
            today_sales_percentage = min(int((today_sales / today_planned_sales) * 100), 100) if today_planned_sales > 0 else 0
            week_sales_percentage = min(int((week_sales / week_planned_sales) * 100), 100) if week_planned_sales > 0 else 0
            month_sales_percentage = min(int((month_sales / month_planned_sales) * 100), 100) if month_planned_sales > 0 else 0
    
    context = {
            'user': user,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_balance': net_balance,
            'max_income': max_income,
            'max_expense': max_expense,
            'current_month': current_month,
            'current_income': current_month_income,
            'current_expense': current_month_expense,
            'income_goal': income_goal,
            'expense_budget': expense_budget,
            'income_progress_percentage': income_progress_percentage,
            'expense_progress_percentage': expense_progress_percentage,
            'income_remaining_percentage': income_remaining_percentage,
            'expense_remaining_percentage': expense_remaining_percentage,
            'days_left': days_left,
            'last_income_update': last_income_update,
            'last_expense_update': last_expense_update,
            'today_sales': today_sales,
            'week_sales': week_sales,
            'month_sales': month_sales,
            'today_planned_sales': today_planned_sales,
            'week_planned_sales': week_planned_sales,
            'month_planned_sales': month_planned_sales,
            'today_sales_percentage': today_sales_percentage,
            'week_sales_percentage': week_sales_percentage,
            'month_sales_percentage': month_sales_percentage,
            'previous_income': previous_income,
            'income_change_percent': income_change_percent,
            'previous_expenses': previous_expenses,
            'expense_change_percent': expense_change_percent,
            'previous_balance': previous_balance,
            'balance': balance,
            'balance_change_percent': balance_change_percent
        }
    return render(request, 'dashboard/dashboard.html', context)


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
            
        return render(request, 'transactions/expense.html', {
            'success': True,
            'amount': amount,
            'description': description,
            'currency': currency,
            'category': category
        })
    return render(request, 'transactions/expense.html')


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
            
        return render(request, 'transactions/income.html', {
            'success': True,
            'amount': amount,
            'description': description,
            'currency': currency,
            'category': category
        })
    return render(request, 'transactions/income.html')


@login_required
def profile(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    return render(request, 'user/profile.html', {'user': user})








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
            
            # Calculate previous period data for comparison
            end_date = datetime.now()
            previous_period_start = end_date - timedelta(days=30)
            previous_period_end = end_date - timedelta(days=1)
            
            previous_income = Income.objects.filter(
                user=user,
                created_at__range=[previous_period_start, previous_period_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            previous_expenses = Expense.objects.filter(
                user=user,
                created_at__range=[previous_period_start, previous_period_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate balance for comparison
            balance = net_balance
    
    context = {
        'user': user,
        'expenses': expenses,
        'incomes': incomes,
        'total_income': total_income,
        'total_expenses': total_expense,  # Changed to match template
        'total_expense': total_expense,
        'net_balance': net_balance,
        'previous_income': previous_income,
        'previous_expenses': previous_expenses,
        'balance': balance,
        'expense_categories': expense_categories,
        'income_categories': income_categories,
    }
    return render(request, 'reports/reports.html', context)


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


@login_required
def analytics(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
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
    
    # Previous month data for comparison
    previous_month = end_date.replace(day=1) - timedelta(days=1)
    previous_month_start = previous_month.replace(day=1)
    
    previous_income = Income.objects.filter(
        user=user,
        created_at__range=[previous_month_start, previous_month]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    previous_expenses = Expense.objects.filter(
        user=user,
        created_at__range=[previous_month_start, previous_month]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    previous_balance = previous_income - previous_expenses
    
    # Current month data
    current_month_start = end_date.replace(day=1)
    current_income = Income.objects.filter(
        user=user,
        created_at__range=[current_month_start, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    current_expenses = Expense.objects.filter(
        user=user,
        created_at__range=[current_month_start, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    balance = current_income - current_expenses
    
    # Average monthly income and expense
    avg_monthly_income = total_income / 12 if total_income > 0 else 0
    avg_monthly_expense = total_expense / 12 if total_expense > 0 else 0
    
    # Convert Decimal objects to float for JSON serialization
    expense_categories_for_json = []
    for category in expense_categories:
        expense_categories_for_json.append({
            'category': category['category'],
            'total': float(category['total'])
        })
    
    income_categories_for_json = []
    for category in income_categories:
        income_categories_for_json.append({
            'category': category['category'],
            'total': float(category['total'])
        })
    
    context = {
        'user': user,
        'monthly_income': list(monthly_income),
        'monthly_expense': list(monthly_expense),
        'income_categories': list(income_categories),
        'expense_categories': list(expense_categories),
        'recent_income': recent_income,
        'recent_expense': recent_expense,
        'total_income': total_income,
        'total_expenses': total_expense,  # Changed to match template
        'total_expense': total_expense,
        'net_balance': net_balance,
        'previous_income': previous_income,
        'previous_expenses': previous_expenses,
        'previous_balance': previous_balance,
        'balance': balance,
        'avg_monthly_income': avg_monthly_income,
        'avg_monthly_expense': avg_monthly_expense,
        'expense_categories_json': json.dumps(expense_categories_for_json),
        'income_categories_json': json.dumps(income_categories_for_json),
    }
    
    return render(request, 'analytics/analytics.html', context)


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
    
    elif chart_type == 'income_sources':
        # Income sources breakdown data
        income_sources = Income.objects.filter(user=user).values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        return JsonResponse({
            'labels': [item['category'] for item in income_sources],
            'data': [float(item['total']) for item in income_sources]
        })
    
    elif chart_type == 'spending_categories':
        # Spending categories breakdown data
        spending_categories = Expense.objects.filter(user=user).values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        return JsonResponse({
            'labels': [item['category'] for item in spending_categories],
            'data': [float(item['total']) for item in spending_categories]
        })
    
    return JsonResponse({'error': 'Invalid chart type'}, status=400)


# Group Split Money Views
@login_required
def groups(request):
    user = Registration.objects.get(email=request.session['entry_email'])
    user_groups = Group.objects.filter(members=user)
    created_groups = Group.objects.filter(created_by=user)
    
    # Combine and remove duplicates
    all_groups = list(user_groups) + list(created_groups)
    unique_groups = list({group.id: group for group in all_groups}.values())
    
    context = {
        'groups': unique_groups,
        'user': user
    }
    return render(request, 'groups/groups.html', context)


@login_required
@ensure_csrf_cookie
def create_group(request):
    user = Registration.objects.get(email=request.session['entry_email'])
    
    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        description = request.POST.get('description', '')
        group_type = request.POST.get('group_type', 'other')
        
        # Create the group
        group = Group.objects.create(
            name=group_name,
            description=description,
            group_type=group_type,
            created_by=user
        )
        
        # Add creator as a member
        GroupMember.objects.create(group=group, member=user, joined_at=datetime.now())
        
        # Add other members
        member_emails = []
        for i in range(1, 11):  # Support up to 10 members
            email = request.POST.get(f'member_email_{i}')
            if email and email.strip():
                member_emails.append(email.strip())
        
        # Add members to the group
        for email in member_emails:
            try:
                member = Registration.objects.get(email=email)
                if member != user:  # Don't add creator again
                    GroupMember.objects.create(group=group, member=member, joined_at=datetime.now())
            except Registration.DoesNotExist:
                # Handle case where email doesn't exist
                pass
        
        return redirect('group_detail', group_id=group.id)
    
    context = {
        'user': user
    }
    return render(request, 'groups/create_group.html', context)


@login_required
def group_detail(request, group_id):
    user = Registration.objects.get(email=request.session['entry_email'])
    
    try:
        group = Group.objects.get(id=group_id)
        # Check if user is a member
        if not group.members.filter(id=user.id).exists() and group.created_by != user:
            return redirect('groups')
        
        # Get all expenses for this group
        expenses = GroupExpense.objects.filter(group=group).order_by('-date')
        
        # Calculate member balances
        member_balances = {}
        for member in group.members.all():
            balance = group.get_member_balance(member)
            member_balances[member] = balance
        
        context = {
            'group': group,
            'expenses': expenses,
            'member_balances': member_balances,
            'user': user
        }
        return render(request, 'groups/group_detail.html', context)
    
    except Group.DoesNotExist:
        return redirect('groups')


@login_required
@ensure_csrf_cookie
def add_group_expense(request, group_id):
    user = Registration.objects.get(email=request.session['entry_email'])
    
    try:
        group = Group.objects.get(id=group_id)
        # Check if user is a member
        if not group.members.filter(id=user.id).exists() and group.created_by != user:
            return redirect('groups')
        
        if request.method == 'POST':
            payer_id = request.POST.get('payer')
            description = request.POST.get('description')
            amount_raw = request.POST.get('amount')
            date = request.POST.get('date')
            included_members = request.POST.getlist('included_members')

            # Basic validations
            error = None
            try:
                amount = Decimal(amount_raw)
                if amount <= 0:
                    error = 'Amount must be greater than 0.'
            except Exception:
                error = 'Please enter a valid amount.'

            if not payer_id:
                error = error or 'Please select who paid.'

            if not included_members:
                error = error or 'Please select at least one member to split the expense.'

            # Ensure payer and included members are part of the group
            if not error:
                if not group.members.filter(id=payer_id).exists():
                    error = 'Selected payer is not a member of this group.'
                else:
                    # Filter included_members to group members only
                    included_member_ids = [m_id for m_id in included_members if group.members.filter(id=m_id).exists()]
                    if not included_member_ids:
                        error = 'Selected members are not in this group.'
                    else:
                        included_members = included_member_ids

            if error:
                context = {
                    'group': group,
                    'user': user,
                    'error': error,
                    'form_values': {
                        'description': description,
                        'amount': amount_raw,
                        'date': date,
                        'payer': payer_id,
                        'included_members': included_members,
                    }
                }
                return render(request, 'groups/add_group_expense.html', context)

            # Create the expense
            expense = GroupExpense.objects.create(
                group=group,
                paid_by_id=payer_id,
                description=description,
                amount=amount,
                date=date
            )

            # Add included members
            for member_id in included_members:
                expense.included_members.add(member_id)

            # Calculate splits (equal split)
            split_amount = amount / len(included_members)

            # Create splits for each member
            for member_id in included_members:
                member = Registration.objects.get(id=member_id)
                GroupExpenseSplit.objects.create(
                    expense=expense,
                    member=member,
                    amount=split_amount
                )

            return redirect('group_detail', group_id=group.id)
        
        context = {
            'group': group,
            'user': user
        }
        return render(request, 'groups/add_group_expense.html', context)
    
    except Group.DoesNotExist:
        return redirect('groups')


@login_required
def group_balances(request, group_id):
    user = Registration.objects.get(email=request.session['entry_email'])
    
    try:
        group = Group.objects.get(id=group_id)
        # Check if user is a member
        if not group.members.filter(id=user.id).exists() and group.created_by != user:
            return redirect('groups')
        
        # Calculate detailed balances and totals
        member_balances = {}
        for member in group.members.all():
            balance = group.get_member_balance(member)
            member_balances[member] = balance

        total_expenses = GroupExpense.objects.filter(group=group).aggregate(total=Sum('amount'))['total'] or 0
        total_positive = sum(b for b in member_balances.values() if b > 0)
        total_negative = sum(b for b in member_balances.values() if b < 0)

        # Build pairwise debt/credit relationships: who owes whom
        from collections import defaultdict
        debt_matrix = defaultdict(lambda: defaultdict(Decimal))  # debtor_id -> creditor_id -> amount

        expenses = GroupExpense.objects.filter(group=group).prefetch_related('included_members')
        for expense in expenses:
            included = list(expense.included_members.all())
            if not included:
                continue
            split_amount = (expense.amount / Decimal(len(included))) if len(included) else Decimal('0')
            for m in included:
                if m.id != expense.paid_by_id:
                    debt_matrix[m.id][expense.paid_by_id] += split_amount

        # Net bilateral debts between each pair
        member_ids = list(group.members.values_list('id', flat=True))
        for i_idx in range(len(member_ids)):
            for j_idx in range(i_idx + 1, len(member_ids)):
                i = member_ids[i_idx]
                j = member_ids[j_idx]
                d_ij = debt_matrix[i].get(j, Decimal('0'))
                d_ji = debt_matrix[j].get(i, Decimal('0'))
                if d_ij >= d_ji:
                    debt_matrix[i][j] = d_ij - d_ji
                    if debt_matrix[i][j] == 0:
                        debt_matrix[i].pop(j, None)
                    debt_matrix[j][i] = Decimal('0')
                    debt_matrix[j].pop(i, None)
                else:
                    debt_matrix[j][i] = d_ji - d_ij
                    if debt_matrix[j][i] == 0:
                        debt_matrix[j].pop(i, None)
                    debt_matrix[i][j] = Decimal('0')
                    debt_matrix[i].pop(j, None)

        # Prepare readable Paid/Borrowed text with amounts for each member (Kittysplit-style)
        id_to_member = {m.id: m for m in group.members.all()}
        paid_borrowed_text = {}
        settlements = {}
        settlement_instructions = []

        for m in group.members.all():
            others = {mid for mid in member_ids if mid != m.id}
            # who this member owes to (creditors)
            owes_to_pairs = [(cred_id, amt) for cred_id, amt in debt_matrix[m.id].items() if amt > 0]
            # who owes this member (debtors)
            owed_by_pairs = []
            for debtor_id in member_ids:
                if debtor_id == m.id:
                    continue
                amt = debt_matrix[debtor_id].get(m.id, Decimal('0'))
                if amt > 0:
                    owed_by_pairs.append((debtor_id, amt))

            total_paid_for = sum((amt for _uid, amt in owed_by_pairs), Decimal('0'))
            total_owes = sum((amt for _uid, amt in owes_to_pairs), Decimal('0'))

            # Build lines similar to Kittysplit:
            # - Gives ₹X to Name(s)
            # - Receives ₹Y from Name(s)
            parts = []
            if owes_to_pairs:
                detail = ', '.join(
                    f"{id_to_member[uid].name} (₹{'{:.2f}'.format(float(amt))})"
                    for uid, amt in sorted(owes_to_pairs, key=lambda x: id_to_member[x[0]].name.lower())
                )
                parts.append(f"Gives ₹{'{:.2f}'.format(float(total_owes))} to {detail}")
            if owed_by_pairs:
                detail = ', '.join(
                    f"{id_to_member[uid].name} (₹{'{:.2f}'.format(float(amt))})"
                    for uid, amt in sorted(owed_by_pairs, key=lambda x: id_to_member[x[0]].name.lower())
                )
                parts.append(f"Receives ₹{'{:.2f}'.format(float(total_paid_for))} from {detail}")

            paid_borrowed_text[m.id] = ' | '.join(parts) if parts else '—'

            settlements[m.id] = {
                'gives_pairs': [(id_to_member[uid].name, float(amt)) for uid, amt in sorted(owes_to_pairs, key=lambda x: id_to_member[x[0]].name.lower())],
                'receives_pairs': [(id_to_member[uid].name, float(amt)) for uid, amt in sorted(owed_by_pairs, key=lambda x: id_to_member[x[0]].name.lower())],
                'total_gives': float(total_owes),
                'total_receives': float(total_paid_for),
            }

        # Generate settlement instructions (like Kittysplit's "How to settle all debts")
        for debtor_id in member_ids:
            for creditor_id in member_ids:
                if debtor_id != creditor_id:
                    amount = debt_matrix[debtor_id].get(creditor_id, Decimal('0'))
                    if amount > 0:
                        settlement_instructions.append({
                            'giver': id_to_member[debtor_id],
                            'receiver': id_to_member[creditor_id],
                            'amount': float(amount),
                            'id': f"{debtor_id}_{creditor_id}"
                        })

        # Sort settlement instructions by amount (largest first)
        settlement_instructions.sort(key=lambda x: x['amount'], reverse=True)

        context = {
            'group': group,
            'member_balances': member_balances,
            'user': user,
            'total_expenses': total_expenses,
            'total_positive': total_positive,
            'total_negative': total_negative,
            'paid_borrowed_text': paid_borrowed_text,
            'settlements': settlements,
            'settlement_instructions': settlement_instructions,
        }
        return render(request, 'groups/group_balances.html', context)
    
    except Group.DoesNotExist:
        return redirect('groups')


@login_required
@ensure_csrf_cookie
def add_group_member(request, group_id):
    user = Registration.objects.get(email=request.session['entry_email'])
    
    try:
        group = Group.objects.get(id=group_id)
        # Check if user is the creator
        if group.created_by != user:
            return redirect('group_detail', group_id=group.id)
        
        if request.method == 'POST':
            member_email = request.POST.get('member_email')
            
            try:
                member = Registration.objects.get(email=member_email)
                # Check if member is already in the group
                if not group.members.filter(id=member.id).exists():
                    GroupMember.objects.create(group=group, member=member, joined_at=datetime.now())
                    return redirect('group_detail', group_id=group.id)
                else:
                    return render(request, 'groups/add_group_member.html', {
                        'group': group,
                        'user': user,
                        'error': 'Member is already in the group'
                    })
            except Registration.DoesNotExist:
                return render(request, 'groups/add_group_member.html', {
                    'group': group,
                    'user': user,
                    'error': 'User with this email does not exist'
                })
        
        context = {
            'group': group,
            'user': user
        }
        return render(request, 'groups/add_group_member.html', context)
    
    except Group.DoesNotExist:
        return redirect('groups')


@login_required
def delete_group(request, group_id):
    user = Registration.objects.get(email=request.session['entry_email'])
    
    try:
        group = Group.objects.get(id=group_id)
        # Check if user is the creator
        if group.created_by != user:
            return redirect('group_detail', group_id=group.id)
        
        group.delete()
        return redirect('groups')
    
    except Group.DoesNotExist:
        return redirect('groups')







