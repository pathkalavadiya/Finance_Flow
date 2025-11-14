import csv
import json
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Sum, Count, Value, CharField
from django.db.models.functions import TruncMonth
from .models import Registration, Expense, Income, Group, GroupMember, GroupExpense, GroupExpenseSplit
from itertools import chain
from operator import attrgetter
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.template.loader import render_to_string
from io import BytesIO
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
@csrf_protect
def register(request):
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone_no = request.POST.get('mob', '').strip()
        password = request.POST.get('password', '')
        # confirm_password and address removed from form; set address to empty
        address = ''
        
        # Basic validation
        if not all([name, email, phone_no, password]):
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "All fields are required"})

        # Email format validation
        import re
        email_regex = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
        if not email_regex.match(email):
            return render(request, 'authentication/register.html',
                        {'register_check_key': "Please enter a valid email address"})

        # Strong password validation: min 8, 1 uppercase, 1 digit, 1 special
        if len(password) < 8:
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "Password must be at least 8 characters long"})
        if not re.search(r'[A-Z]', password):
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "Password must contain at least one uppercase letter"})
        if not re.search(r'\d', password):
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "Password must contain at least one digit"})
        if not re.search(r'[!@#$%^&*()_+\-=[\]{};:\\|,.<>/?]', password):
            return render(request, 'authentication/register.html', 
                        {'register_check_key': "Password must contain at least one special character"})
        
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


@require_http_methods(["GET", "POST"])
def lending(request):
    """Simple lending UI: shows a list and accepts POSTs but doesn't persist.

    This provides a working page so the user can interact with the lending UI.
    """
    message = ''
    # simple in-memory sample lendings for UI
    lendings = [
        { 'name': 'Rohit', 'amount': '1500', 'date': '2025-09-01', 'status': 'Pending' },
        { 'name': 'Anita', 'amount': '2500', 'date': '2025-08-12', 'status': 'Returned' },
    ]

    total_lent = sum(float(l['amount']) for l in lendings)
    outstanding = sum(float(l['amount']) for l in lendings if l['status'] != 'Returned')
    total_received = sum(float(l['amount']) for l in lendings if l['status'] == 'Returned')

    if request.method == 'POST':
        # read fields and show a success message; not persisted
        name = request.POST.get('name', '').strip()
        amount = request.POST.get('amount', '').strip()
        date = request.POST.get('date', '').strip()
        if name and amount and date:
            message = f'Lending saved for {name} (₹{amount}) on {date}'
        else:
            message = 'Please fill all required fields.'

    context = {
        'lendings': lendings,
        'total_lent': int(total_lent),
        'outstanding': int(outstanding),
        'total_received': int(total_received),
        'message': message,
    }
    return render(request, 'lending/lending.html', context)

 
# login
@csrf_protect
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
    
    # Dynamic stats
    user_count = Registration.objects.count()
    total_income_sum = Income.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expense_sum = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
    money_managed = float(total_income_sum) + float(total_expense_sum)
    total_transactions = Income.objects.count() + Expense.objects.count()
    satisfaction_rate = 90  # default static unless you want to compute from feedback later

    context = {
        'user_count': user_count,
        'actual_user_count': user_count,
        'money_managed': int(money_managed),
        'total_transactions': int(total_transactions),
        'satisfaction_rate': int(satisfaction_rate),
    }
    return render(request, 'landing.html', context)


@require_http_methods(["POST"])
@csrf_protect
def subscribe_newsletter(request):
    """Subscribe to the newsletter by appending email to a CSV file.
    - If AJAX (fetch/XHR), returns JSON {success, message}
    - Otherwise redirects back to landing with a query param for simple feedback
    This avoids DB migrations while making the feature work immediately.
    """
    email = (request.POST.get('email') or '').strip()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not email:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Please enter an email address.'}, status=400)
        return redirect(f"{request.META.get('HTTP_REFERER', '/') }?newsletter=missing")

    try:
        # Ensure file exists, then append a new line with timestamp
        from pathlib import Path
        import csv
        from datetime import datetime

        base_dir = Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else Path.cwd()
        out_path = base_dir / 'newsletter_subscribers.csv'
        new_file = not out_path.exists()
        with out_path.open('a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(['email', 'subscribed_at', 'ip'])
            writer.writerow([email, datetime.utcnow().isoformat(), request.META.get('REMOTE_ADDR', '')])

        if is_ajax:
            return JsonResponse({'success': True, 'message': 'Subscribed successfully!'}, status=200)
        return redirect(f"{request.META.get('HTTP_REFERER', '/') }?newsletter=success")
    except Exception as e:
        if is_ajax:
            return JsonResponse({'success': False, 'message': f'Failed to subscribe: {str(e)}'}, status=500)
        return redirect(f"{request.META.get('HTTP_REFERER', '/') }?newsletter=error")

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
    insights = []
    
    # Transaction card variables
    today_transactions = 0
    today_income = 0
    today_expense = 0
    weekly_transactions = 0
    weekly_income = 0
    weekly_expense = 0
    monthly_transactions = 0
    monthly_income = 0
    monthly_expense = 0
    recent_transactions = []
    
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
            
            # Savings rate (current month) and change vs previous month (for dashboard cards)
            def _rate(income, expense):
                try:
                    return float(((income or 0) - (expense or 0)) / income * 100) if income and income > 0 else 0.0
                except Exception:
                    return 0.0
            savings_rate = _rate(current_month_income, current_month_expense)
            previous_savings_rate = _rate(previous_income, previous_expenses)
            savings_rate_change = savings_rate - previous_savings_rate

            # Get last update timestamps
            last_income = Income.objects.filter(user=user).order_by('-created_at').first()
            last_expense = Expense.objects.filter(user=user).order_by('-created_at').first()
            
            last_income_update = last_income.created_at if last_income else current_date
            last_expense_update = last_expense.created_at if last_expense else current_date
            
            # Transaction calculations for dashboard cards
            # Today's transactions
            today_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            today_income = Income.objects.filter(
                user=user,
                created_at__gte=today_start,
                created_at__lt=today_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            today_expense = Expense.objects.filter(
                user=user,
                created_at__gte=today_start,
                created_at__lt=today_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            today_transactions = Income.objects.filter(
                user=user,
                created_at__gte=today_start,
                created_at__lt=today_end
            ).count() + Expense.objects.filter(
                user=user,
                created_at__gte=today_start,
                created_at__lt=today_end
            ).count()
            
            # Weekly transactions
            week_start = current_date - timedelta(days=current_date.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            
            weekly_income = Income.objects.filter(
                user=user,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            weekly_expense = Expense.objects.filter(
                user=user,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            weekly_transactions = Income.objects.filter(
                user=user,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).count() + Expense.objects.filter(
                user=user,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).count()
            
            # Monthly transactions
            month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            monthly_income = Income.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_expense = Expense.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_transactions = Income.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count() + Expense.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            
            # Sales Report calculations (keeping existing code)
            # Today's sales (income)
            today_sales = today_income
            
            # This week's sales (income)
            week_sales = weekly_income
            
            # This month's sales (income)
            month_sales = monthly_income
            
            # Planned sales targets (you can make these configurable)
            today_planned_sales = 300
            week_planned_sales = 2100
            month_planned_sales = 9000
            
            # Calculate progress percentages
            today_sales_percentage = min(int((today_sales / today_planned_sales) * 100), 100) if today_planned_sales > 0 else 0
            week_sales_percentage = min(int((week_sales / week_planned_sales) * 100), 100) if week_planned_sales > 0 else 0
            month_sales_percentage = min(int((month_sales / month_planned_sales) * 100), 100) if month_planned_sales > 0 else 0
            
            # Get recent transactions (last 10)
            recent_income = Income.objects.filter(user=user).order_by('-created_at')[:5]
            recent_expense = Expense.objects.filter(user=user).order_by('-created_at')[:5]
            
            # Combine and sort recent transactions
            recent_transactions = []
            
            for income in recent_income:
                recent_transactions.append({
                    'description': income.description,
                    'category': income.category,
                    'amount': income.amount,
                    'date': income.created_at.strftime('%Y-%m-%d'),
                    'type': 'income'
                })
            
            for expense in recent_expense:
                recent_transactions.append({
                    'description': expense.description,
                    'category': expense.category,
                    'amount': expense.amount,
                    'date': expense.created_at.strftime('%Y-%m-%d'),
                    'type': 'expense'
                })
            
            # Sort by date (most recent first) and limit to 10
            recent_transactions = sorted(recent_transactions, key=lambda x: x['date'], reverse=True)[:10]

            # Dynamic Insights
            # 1) Week-over-week spending change
            prev_week_start = week_start - timedelta(days=7)
            prev_week_end = week_start
            prev_week_expense = Expense.objects.filter(
                user=user,
                created_at__gte=prev_week_start,
                created_at__lt=prev_week_end
            ).aggregate(total=Sum('amount'))['total'] or 0

            if prev_week_expense and prev_week_expense > 0:
                wo_w_change_pct = ((weekly_expense - prev_week_expense) / prev_week_expense) * 100
                if wo_w_change_pct > 5:
                    insights.append({
                        'level': 'info',
                        'icon': 'bi-lightbulb',
                        'title': f"This week you spent {wo_w_change_pct:.0f}% more than last week",
                        'subtitle': 'Consider reviewing your expenses'
                    })
                elif wo_w_change_pct < -5:
                    insights.append({
                        'level': 'success',
                        'icon': 'bi-graph-up-arrow',
                        'title': f"Great! You spent {-wo_w_change_pct:.0f}% less than last week",
                        'subtitle': 'Nice savings trend'
                    })
            else:
                if weekly_expense > 0:
                    insights.append({
                        'level': 'info',
                        'icon': 'bi-lightbulb',
                        'title': 'Spending started this week',
                        'subtitle': 'No spend was recorded last week for comparison'
                    })

            # 2) Budget pacing vs month progress
            days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
            day_of_month = current_date.day
            month_progress_pct = (day_of_month / days_in_month) * 100 if days_in_month else 0
            expected_expense_pct = month_progress_pct
            if expense_progress_percentage <= expected_expense_pct + 5:
                insights.append({
                    'level': 'success',
                    'icon': 'bi-check-circle',
                    'title': "You're on track with your budget goals!",
                    'subtitle': 'Keep up the good work'
                })
            else:
                over_pct = max(0, expense_progress_percentage - expected_expense_pct)
                insights.append({
                    'level': 'warning',
                    'icon': 'bi-exclamation-triangle',
                    'title': f'Your spending pace is {over_pct:.0f}% ahead of budget',
                    'subtitle': 'Reduce discretionary expenses to stay on target'
                })

            # 3) Category spike this month vs previous month
            current_cat_totals = Expense.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).values('category').annotate(total=Sum('amount'))

            prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
            prev_month_end = month_start
            prev_cat_totals = Expense.objects.filter(
                user=user,
                created_at__gte=prev_month_start,
                created_at__lt=prev_month_end
            ).values('category').annotate(total=Sum('amount'))

            prev_map = {row['category']: row['total'] for row in prev_cat_totals}
            spike = None
            for row in current_cat_totals:
                cat = row['category'] or 'Other'
                cur = row['total'] or 0
                prev = prev_map.get(cat, 0) or 0
                if prev > 0:
                    change = ((cur - prev) / prev) * 100
                    if change >= 10 and (not spike or change > spike['change']):
                        spike = {'category': cat, 'change': change}
                elif cur > 0 and prev == 0:
                    # Newly appearing category with spend
                    if not spike:
                        spike = {'category': cat, 'change': 100}

            if spike:
                insights.append({
                    'level': 'warning',
                    'icon': 'bi-exclamation-triangle',
                    'title': f"{spike['category']} expenses increased by {spike['change']:.0f}%",
                    'subtitle': 'Review recent purchases in this category'
                })
    
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
        'savings_rate': savings_rate,
        'previous_savings_rate': previous_savings_rate,
        'savings_rate_change': savings_rate_change,
            'balance_change_percent': balance_change_percent,
            # Transaction card data
            'today_transactions': today_transactions,
            'today_income': today_income,
            'today_expense': today_expense,
            'weekly_transactions': weekly_transactions,
            'weekly_income': weekly_income,
            'weekly_expense': weekly_expense,
            'monthly_transactions': monthly_transactions,
            'monthly_income': monthly_income,
            'monthly_expense': monthly_expense,
            'recent_transactions': recent_transactions,
            'insights': insights,
            'notifications_count': len(insights)
        }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
@csrf_protect
def expense(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('date')
        currency = request.POST.get('currency')
        category = request.POST.get('category')
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Save to database with user association
        if user:
            try:
                Expense.objects.create(
                    user=user,
                    amount=amount,
                    description=description,
                    date=date,
                    currency=currency,
                    category=category
                )
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Expense of ₹{amount} added successfully!'
                    })
                else:
                    return render(request, 'transactions/expense.html', {
                        'user': user,
                        'success': True,
                        'amount': amount,
                        'description': description,
                        'currency': currency,
                        'category': category
                    })
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error adding expense: {str(e)}'
                    })
                else:
                    return render(request, 'transactions/expense.html', {
                        'user': user,
                        'error': f'Error adding expense: {str(e)}'
                    })
        else:
            # Handle case where user is not logged in
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            else:
                return redirect('login')
    
    return render(request, 'transactions/expense.html', {'user': user})


@login_required
def transaction_history(request):
    user = None
    transactions = []
    q = (request.GET.get('q') or '').strip()
    
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
        
        if user:
            # Base querysets
            incomes_qs = Income.objects.filter(user=user)
            expenses_qs = Expense.objects.filter(user=user)

            # Apply search filter if provided
            if q:
                incomes_qs = incomes_qs.filter(Q(description__icontains=q) | Q(category__icontains=q))
                expenses_qs = expenses_qs.filter(Q(description__icontains=q) | Q(category__icontains=q))

            # Prepare values for rendering
            incomes = incomes_qs.annotate(
                type=Value('income', output_field=CharField())
            ).values('id', 'amount', 'description', 'date', 'category', 'created_at', 'type', 'user__name')
            
            expenses = expenses_qs.annotate(
                type=Value('expense', output_field=CharField())
            ).values('id', 'amount', 'description', 'date', 'category', 'created_at', 'type', 'user__name')
            
            # Combine and sort by date
            all_transactions = list(chain(incomes, expenses))
            
            # Add author_name field and sort by created_at
            for transaction in all_transactions:
                transaction['author_name'] = transaction.get('user__name', user.name)
            
            transactions = sorted(all_transactions, key=lambda x: x['created_at'], reverse=True)
    
    context = {
        'user': user,
        'transactions': transactions
    }
    
    return render(request, 'transactions/history.html', context)


@login_required
def notifications_data(request):
    """Return dynamic insights as notifications for the current user.
    Shape: { count: int, items: [{level, icon, title, subtitle}] }
    """
    user = None
    items = []
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()

    if not user:
        return JsonResponse({'count': 0, 'items': []})

    # Compute minimal data needed to generate insights
    current_date = datetime.now()

    # Weekly expense vs last week
    week_start = current_date - timedelta(days=current_date.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    weekly_expense = Expense.objects.filter(user=user, created_at__gte=week_start, created_at__lt=week_end).aggregate(total=Sum('amount'))['total'] or 0
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start
    prev_week_expense = Expense.objects.filter(user=user, created_at__gte=prev_week_start, created_at__lt=prev_week_end).aggregate(total=Sum('amount'))['total'] or 0
    if prev_week_expense and prev_week_expense > 0:
        wo_w_change_pct = ((weekly_expense - prev_week_expense) / prev_week_expense) * 100
        if wo_w_change_pct > 5:
            items.append({'level': 'info', 'icon': 'bi-lightbulb', 'title': f"This week you spent {wo_w_change_pct:.0f}% more than last week", 'subtitle': 'Consider reviewing your expenses'})
        elif wo_w_change_pct < -5:
            items.append({'level': 'success', 'icon': 'bi-graph-up-arrow', 'title': f"Great! You spent {-wo_w_change_pct:.0f}% less than last week", 'subtitle': 'Nice savings trend'})
    elif weekly_expense > 0:
        items.append({'level': 'info', 'icon': 'bi-lightbulb', 'title': 'Spending started this week', 'subtitle': 'No spend was recorded last week for comparison'})

    # Budget pacing vs month progress
    # Monthly totals and simple budget constants (keep in sync with dashboard)
    month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if current_date.month == 12:
        month_end = month_start.replace(year=current_date.year + 1, month=1)
    else:
        month_end = month_start.replace(month=current_date.month + 1)
    current_month_expense = Expense.objects.filter(user=user, created_at__gte=month_start, created_at__lt=month_end).aggregate(total=Sum('amount'))['total'] or 0
    expense_budget = 2500  # same as dashboard
    expense_progress_percentage = min(int(((current_month_expense or 0) / expense_budget) * 100), 100) if expense_budget > 0 else 0
    days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
    day_of_month = current_date.day
    month_progress_pct = (day_of_month / days_in_month) * 100 if days_in_month else 0
    expected_expense_pct = month_progress_pct
    if expense_progress_percentage <= expected_expense_pct + 5:
        items.append({'level': 'success', 'icon': 'bi-check-circle', 'title': "You're on track with your budget goals!", 'subtitle': 'Keep up the good work'})
    else:
        over_pct = max(0, expense_progress_percentage - expected_expense_pct)
        items.append({'level': 'warning', 'icon': 'bi-exclamation-triangle', 'title': f'Your spending pace is {over_pct:.0f}% ahead of budget', 'subtitle': 'Reduce discretionary expenses to stay on target'})

    # Category spike vs previous month
    current_cat_totals = Expense.objects.filter(user=user, created_at__gte=month_start, created_at__lt=month_end).values('category').annotate(total=Sum('amount'))
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
    prev_month_end = month_start
    prev_cat_totals = Expense.objects.filter(user=user, created_at__gte=prev_month_start, created_at__lt=prev_month_end).values('category').annotate(total=Sum('amount'))
    prev_map = {row['category']: row['total'] for row in prev_cat_totals}
    spike = None
    for row in current_cat_totals:
        cat = row['category'] or 'Other'
        cur = row['total'] or 0
        prev = prev_map.get(cat, 0) or 0
        if prev > 0:
            change = ((cur - prev) / prev) * 100
            if change >= 10 and (not spike or change > spike['change']):
                spike = {'category': cat, 'change': change}
        elif cur > 0 and prev == 0 and not spike:
            spike = {'category': cat, 'change': 100}
    if spike:
        items.append({'level': 'warning', 'icon': 'bi-exclamation-triangle', 'title': f"{spike['category']} expenses increased by {spike['change']:.0f}%", 'subtitle': 'Review recent purchases in this category'})

    return JsonResponse({'count': len(items), 'items': items})


@login_required
def export_profile_data(request):
    """Export the current user's incomes and expenses as a CSV file."""
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    if not user:
        return redirect('login')

    # Prepare CSV response
    from io import StringIO
    buffer = StringIO()
    writer = csv.writer(buffer)

    # Basic user info
    writer.writerow(['FinanceFlow Export'])
    writer.writerow(['Name', user.name])
    writer.writerow(['Email', user.email])
    writer.writerow([])

    # Incomes
    writer.writerow(['Incomes'])
    writer.writerow(['Date', 'Amount', 'Currency', 'Category', 'Description'])
    for inc in Income.objects.filter(user=user).order_by('-created_at'):
        writer.writerow([getattr(inc, 'date', getattr(inc, 'created_at', '')),
                         inc.amount, getattr(inc, 'currency', ''), inc.category, inc.description])
    writer.writerow([])

    # Expenses
    writer.writerow(['Expenses'])
    writer.writerow(['Date', 'Amount', 'Currency', 'Category', 'Description'])
    for exp in Expense.objects.filter(user=user).order_by('-created_at'):
        writer.writerow([getattr(exp, 'date', getattr(exp, 'created_at', '')),
                         exp.amount, getattr(exp, 'currency', ''), exp.category, exp.description])

    content = buffer.getvalue()
    buffer.close()

    from django.http import HttpResponse
    resp = HttpResponse(content, content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="financeflow_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return resp


@login_required
@require_http_methods(["POST"]) 
def delete_account(request):
    """Delete the current user's account and related data."""
    # Detect AJAX vs normal form
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    if not user:
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        return redirect('login')

    try:
        # Delete user-related data
        Income.objects.filter(user=user).delete()
        Expense.objects.filter(user=user).delete()
        # Finally delete Registration record
        user.delete()
        # Clear session
        if 'entry_email' in request.session:
            del request.session['entry_email']

        if is_ajax:
            return JsonResponse({'success': True, 'message': 'Account deleted successfully.'})
        return redirect('landing')
    except Exception as e:
        if is_ajax:
            return JsonResponse({'success': False, 'message': f'Failed to delete account: {str(e)}'}, status=500)
        return redirect('profile')


@login_required
@csrf_protect
def income(request):
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('date')
        currency = request.POST.get('currency')
        category = request.POST.get('category')
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Save to database with user association
        if user:
            try:
                Income.objects.create(
                    user=user,
                    amount=amount,
                    description=description,
                    date=date,
                    currency=currency,
                    category=category
                )
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Income of ₹{amount} added successfully!'
                    })
                else:
                    return render(request, 'transactions/income.html', {
                        'user': user,
                        'success': True,
                        'amount': amount,
                        'description': description,
                        'currency': currency,
                        'category': category
                    })
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error adding income: {str(e)}'
                    })
                else:
                    return render(request, 'transactions/income.html', {
                        'user': user,
                        'error': f'Error adding income: {str(e)}'
                    })
        else:
            # Handle case where user is not logged in
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            else:
                return redirect('login')
    
    return render(request, 'transactions/income.html', {'user': user})


@login_required
def profile(request):
    user = None
    total_income = 0
    total_expenses = 0
    net_balance = 0
    
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
        
        if user:
            # Calculate total income
            income_sum = Income.objects.filter(user=user).aggregate(total=Sum('amount'))
            total_income = income_sum['total'] or 0
            
            # Calculate total expenses
            expense_sum = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))
            total_expenses = expense_sum['total'] or 0
            
            # Calculate net balance
            net_balance = total_income - total_expenses
    
            # Build dynamic recent reports list (virtual entries)
            def _size_estimate(count):
                # Rough estimate: 60 bytes per row -> convert to MB
                mb = (count * 60) / (1024*1024)
                return f"{mb:.1f} MB"

            recent_reports = []
            # Define reporting window
            end_date = timezone.now()
            current_start = end_date - timedelta(days=30)
            # Income Report (last 30 days)
            inc_count = Income.objects.filter(user=user, created_at__range=[current_start, end_date]).count()
            if inc_count:
                recent_reports.append({
                    'name': f"Income Report - {end_date.strftime('%b %Y')}",
                    'desc': 'Monthly income summary',
                    'type': 'Income',
                    'badge': 'success',
                    'generated': end_date.strftime('%b %d, %Y'),
                    'size': _size_estimate(inc_count),
                    'view_url': reverse('analytics'),
                    'download_url': reverse('generate_report') + f"?report_type=Income+Report&date_range=Last+30+days&format=CSV"
                })

            # Expense Report (last 30 days)
            exp_count = Expense.objects.filter(user=user, created_at__range=[current_start, end_date]).count()
            if exp_count:
                recent_reports.append({
                    'name': f"Expense Report - {end_date.strftime('%b %Y')}",
                    'desc': 'Monthly expense breakdown',
                    'type': 'Expense',
                    'badge': 'warning',
                    'generated': end_date.strftime('%b %d, %Y'),
                    'size': _size_estimate(exp_count),
                    'view_url': reverse('analytics'),
                    'download_url': reverse('generate_report') + f"?report_type=Expense+Report&date_range=Last+30+days&format=CSV"
                })

            # Balance Report (last 30 days)
            if inc_count or exp_count:
                recent_reports.append({
                    'name': f"Balance Report - {end_date.strftime('%b %Y')}",
                    'desc': 'Monthly balance summary',
                    'type': 'Balance',
                    'badge': 'primary',
                    'generated': end_date.strftime('%b %d, %Y'),
                    'size': _size_estimate(inc_count + exp_count),
                    'view_url': reverse('analytics'),
                    'download_url': reverse('generate_report') + f"?report_type=Balance+Report&date_range=Last+30+days&format=CSV"
                })

            # Custom Report example if Food category exists
            if Expense.objects.filter(user=user, category__iexact='Food').exists() or Expense.objects.filter(user=user, category__iexact='Groceries').exists():
                recent_reports.append({
                    'name': 'Custom Report - Food Expenses',
                    'desc': 'Food category analysis',
                    'type': 'Custom',
                    'badge': 'info',
                    'generated': end_date.strftime('%b %d, %Y'),
                    'size': _size_estimate(exp_count),
                    'view_url': reverse('analytics'),
                    'download_url': reverse('generate_report') + f"?report_type=Expense+Report&date_range=Last+30+days&format=CSV"
                })

    context = {
        'user': user,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_balance': net_balance
    }
    
    return render(request, 'user/profile.html', context)



@login_required
def reports(request):
    user = None
    expenses = []
    incomes = []
    total_income = 0
    total_expense = 0
    net_balance = 0
    message = None
    message_type = None
    
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
            
            # Calculate current and previous 30-day periods for dynamic KPIs
            end_date = timezone.now()
            current_start = end_date - timedelta(days=30)
            prev_start = end_date - timedelta(days=60)
            prev_end = current_start - timedelta(seconds=1)

            # Current period sums (last 30 days)
            current_income_sum = Income.objects.filter(
                user=user,
                created_at__range=[current_start, end_date]
            ).aggregate(total=Sum('amount'))['total'] or 0
            current_expense_sum = Expense.objects.filter(
                user=user,
                created_at__range=[current_start, end_date]
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Previous period sums (30-60 days ago)
            previous_income = Income.objects.filter(
                user=user,
                created_at__range=[prev_start, prev_end]
            ).aggregate(total=Sum('amount'))['total'] or 0
            previous_expenses = Expense.objects.filter(
                user=user,
                created_at__range=[prev_start, prev_end]
            ).aggregate(total=Sum('amount'))['total'] or 0

            # Dynamic KPIs
            def _rate(income, expense):
                try:
                    return float(((income or 0) - (expense or 0)) / income * 100) if income and income > 0 else 0.0
                except Exception:
                    return 0.0

            savings_rate_report = _rate(current_income_sum, current_expense_sum)
            previous_savings_rate_report = _rate(previous_income, previous_expenses)
            savings_rate_change_report = savings_rate_report - previous_savings_rate_report

            # Net savings change percent
            current_balance_period = float(current_income_sum) - float(current_expense_sum)
            previous_balance_period = float(previous_income) - float(previous_expenses)
            if previous_balance_period:
                balance_change_percent_report = ((current_balance_period - previous_balance_period) / abs(previous_balance_period)) * 100.0
            else:
                balance_change_percent_report = 0.0

            # Overall balance (all-time) remains for other cards
            balance = net_balance
            # Calculate previous period data for comparison
            end_date = timezone.now()
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

            # Build dynamic recent reports with computed sizes (CSV simulation)
            import io as _io

            def _format_size(n_bytes: int) -> str:
                try:
                    if n_bytes >= 1024 * 1024:
                        return f"{n_bytes / (1024*1024):.1f} MB"
                    if n_bytes >= 1024:
                        return f"{n_bytes / 1024:.1f} KB"
                    return f"{n_bytes} B"
                except Exception:
                    return "-"

            def _csv_size_for(queryset, kind: str) -> int:
                # Build a CSV in-memory similar to generate_report()
                header = ['Type', 'Amount', 'Category', 'Description', 'Currency', 'Date']
                buf = _io.StringIO()
                w = csv.writer(buf)
                w.writerow(header)
                for obj in queryset:
                    w.writerow([
                        kind,
                        float(obj.amount),
                        obj.category,
                        obj.description,
                        obj.currency,
                        obj.created_at.strftime('%Y-%m-%d %H:%M')
                    ])
                return len(buf.getvalue().encode('utf-8'))

            # time windows for these sample recent reports
            gen_dt = timezone.now()
            last30_start = gen_dt - timedelta(days=30)
            last30_incomes = Income.objects.filter(user=user, created_at__range=[last30_start, gen_dt]).order_by('-created_at')
            last30_expenses = Expense.objects.filter(user=user, created_at__range=[last30_start, gen_dt]).order_by('-created_at')

            income_csv_bytes = _csv_size_for(last30_incomes, 'Income')
            expense_csv_bytes = _csv_size_for(last30_expenses, 'Expense')

            # Balance report uses both incomes and expenses
            buf_bal = _io.StringIO()
            w_bal = csv.writer(buf_bal)
            w_bal.writerow(['Type', 'Amount', 'Category', 'Description', 'Currency', 'Date'])
            for obj in last30_incomes:
                w_bal.writerow(['Income', float(obj.amount), obj.category, obj.description, obj.currency, obj.created_at.strftime('%Y-%m-%d %H:%M')])
            for obj in last30_expenses:
                w_bal.writerow(['Expense', float(obj.amount), obj.category, obj.description, obj.currency, obj.created_at.strftime('%Y-%m-%d %H:%M')])
            balance_csv_bytes = len(buf_bal.getvalue().encode('utf-8'))

            # Custom report example: top expense category in last 30 days
            top_cat_row = last30_expenses.values('category').annotate(total=Sum('amount')).order_by('-total').first()
            top_cat = (top_cat_row or {}).get('category', 'All')
            custom_qs = last30_expenses if top_cat == 'All' else last30_expenses.filter(category=top_cat)
            custom_csv_bytes = _csv_size_for(custom_qs, 'Expense')

            recent_reports = [
                {
                    'name': f"Income Report - {gen_dt.strftime('%b %Y')}",
                    'type': 'Income',
                    'generated': gen_dt.strftime('%b %d, %Y'),
                    'size_display': _format_size(income_csv_bytes),
                },
                {
                    'name': f"Expense Report - {gen_dt.strftime('%b %Y')}",
                    'type': 'Expense',
                    'generated': (gen_dt - timedelta(days=1)).strftime('%b %d, %Y'),
                    'size_display': _format_size(expense_csv_bytes),
                },
                {
                    'name': f"Balance Report - { (gen_dt - timedelta(days=gen_dt.day)).strftime('%b %Y') }",
                    'type': 'Balance',
                    'generated': (gen_dt - timedelta(days=gen_dt.day)).strftime('%b %d, %Y'),
                    'size_display': _format_size(balance_csv_bytes),
                },
                {
                    'name': f"Custom Report - {top_cat if top_cat else 'All'}",
                    'type': 'Custom',
                    'generated': (gen_dt - timedelta(days=16)).strftime('%b %d, %Y'),
                    'size_display': _format_size(custom_csv_bytes),
                },
            ]
    
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
        'message': message,
        'message_type': message_type,
        'recent_reports': recent_reports if 'recent_reports' in locals() else [],
        # Dynamic KPIs for Reports page
        'savings_rate_report': savings_rate_report if 'savings_rate_report' in locals() else 0,
        'savings_rate_change_report': savings_rate_change_report if 'savings_rate_change_report' in locals() else 0,
        'balance_change_percent_report': balance_change_percent_report if 'balance_change_percent_report' in locals() else 0,
    }
    return render(request, 'reports/reports.html', context)


@login_required
def generate_report(request):
    """Generate and download financial reports"""
    if request.method not in ('POST', 'GET'):
        return redirect('reports')
    
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if not user:
        return HttpResponse('Unauthorized', status=401)
    
    data = request.POST if request.method == 'POST' else request.GET
    report_type = data.get('report_type', 'Income Report')
    date_range = data.get('date_range', 'Last 7 days')
    format_type = data.get('format', 'PDF')
    
    # Calculate date range based on selection
    end_date = timezone.now()
    if date_range == 'Last 7 days':
        start_date = end_date - timedelta(days=7)
    elif date_range == 'Last 30 days':
        start_date = end_date - timedelta(days=30)
    elif date_range == 'Last 3 months':
        start_date = end_date - timedelta(days=90)
    elif date_range == 'Last 6 months':
        start_date = end_date - timedelta(days=180)
    elif date_range == 'Last year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=7)  # Default to last 7 days
    
    # Filter data based on date range
    incomes = Income.objects.filter(
        user=user,
        created_at__range=[start_date, end_date]
    ).order_by('-created_at')
    
    expenses = Expense.objects.filter(
        user=user,
        created_at__range=[start_date, end_date]
    ).order_by('-created_at')
    
    # Build rows once, reuse for CSV/Excel/JSON
    rows = []
    header = ['Type', 'Amount', 'Category', 'Description', 'Currency', 'Date']
    if report_type == 'Income Report':
        for income in incomes:
            rows.append([
                'Income',
                float(income.amount),
                income.category,
                income.description,
                income.currency,
                income.created_at.strftime('%Y-%m-%d %H:%M')
            ])
    elif report_type == 'Expense Report':
        for expense in expenses:
            rows.append([
                'Expense',
                float(expense.amount),
                expense.category,
                expense.description,
                expense.currency,
                expense.created_at.strftime('%Y-%m-%d %H:%M')
            ])
    else:  # Balance Report
        for income in incomes:
            rows.append([
                'Income',
                float(income.amount),
                income.category,
                income.description,
                income.currency,
                income.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        for expense in expenses:
            rows.append([
                'Expense',
                float(expense.amount),
                expense.category,
                expense.description,
                expense.currency,
                expense.created_at.strftime('%Y-%m-%d %H:%M')
            ])

    if format_type == 'CSV':
        # Generate CSV report
        response = HttpResponse(content_type='text/csv')
        filename = f"{report_type.replace(' ', '_')}_{date_range.replace(' ', '_')}_{end_date.strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Report Type', report_type])
        writer.writerow(['Date Range', date_range])
        writer.writerow(['Generated On', end_date.strftime('%Y-%m-%d %H:%M')])
        writer.writerow([])
        writer.writerow(header)
        writer.writerows(rows)
        return response

    elif format_type == 'Excel':
        # Return Excel-friendly CSV (Excel opens CSV natively)
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = f"{report_type.replace(' ', '_')}_{date_range.replace(' ', '_')}_{end_date.strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(header)
        writer.writerows(rows)
        return response

    elif format_type == 'JSON':
        payload = {
            'report_type': report_type,
            'date_range': date_range,
            'generated_on': end_date.strftime('%Y-%m-%d %H:%M'),
            'columns': header,
            'rows': rows,
        }
        data = json.dumps(payload, indent=2)
        response = HttpResponse(data, content_type='application/json')
        filename = f"{report_type.replace(' ', '_')}_{date_range.replace(' ', '_')}_{end_date.strftime('%Y%m%d')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


    
    elif format_type == 'PDF':
        # Attempt to generate a real PDF using xhtml2pdf (pisa)
        try:
            from xhtml2pdf import pisa
        except Exception:
            html = render_to_string('reports/pdf_report.html', {
                'user': user,
                'report_type': report_type,
                'date_range': date_range,
                'generated_on': end_date,
                'header': ['Type', 'Amount', 'Category', 'Description', 'Currency', 'Date'],
                'rows': rows,
                'pdf_notice': 'xhtml2pdf is not installed. Please install it to enable direct PDF download.'
            })
            return HttpResponse(html)

        html = render_to_string('reports/pdf_report.html', {
            'user': user,
            'report_type': report_type,
            'date_range': date_range,
            'generated_on': end_date,
            'header': ['Type', 'Amount', 'Category', 'Description', 'Currency', 'Date'],
            'rows': rows,
            'pdf_notice': ''
        })
        result = BytesIO()
        pdf = pisa.CreatePDF(src=html, dest=result)
        if pdf.err:
            return HttpResponse('Failed to generate PDF.', content_type='text/plain', status=500)
        filename = f"{report_type.replace(' ', '_')}_{date_range.replace(' ', '_')}_{end_date.strftime('%Y%m%d')}.pdf"
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    else:
        # PDF or other non-implemented formats
        return HttpResponse('PDF generation is not yet implemented. Please choose CSV, Excel or JSON.', content_type='text/plain')


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

    # Savings rate (current month) and change vs previous month
    def _rate(income, expense):
        try:
            return float(((income or 0) - (expense or 0)) / income * 100) if income and income > 0 else 0.0
        except Exception:
            return 0.0
    savings_rate = _rate(current_income, current_expenses)
    previous_savings_rate = _rate(previous_income, previous_expenses)
    savings_rate_change = savings_rate - previous_savings_rate
    
    # Average monthly income and expense
    avg_monthly_income = total_income / 12 if total_income > 0 else 0
    avg_monthly_expense = total_expense / 12 if total_expense > 0 else 0

    # Build dynamic Expense Analysis & Saving Tips using current vs previous month
    # Current month category totals
    current_cats = Expense.objects.filter(
        user=user,
        created_at__gte=current_month_start,
        created_at__lt=end_date
    ).values('category').annotate(total=Sum('amount')).order_by('-total')

    # Previous month category totals
    prev_cats = Expense.objects.filter(
        user=user,
        created_at__gte=previous_month_start,
        created_at__lt=previous_month
    ).values('category').annotate(total=Sum('amount')).order_by('-total')

    prev_map = {row['category'] or 'Other': float(row['total'] or 0) for row in prev_cats}
    cur_map = {row['category'] or 'Other': float(row['total'] or 0) for row in current_cats}

    total_cur_exp = sum(cur_map.values()) or 0.0
    saving_tips = []

    # 1) Top category optimization (e.g., Housing if dominant)
    if current_cats:
        top_cat = (current_cats[0]['category'] or 'Other')
        top_pct = (float(current_cats[0]['total'])/total_cur_exp*100.0) if total_cur_exp > 0 else 0.0
        if top_pct >= 25.0:
            saving_tips.append({
                'level': 'info',
                'title': f"{top_cat.title()} Optimization",
                'summary': f"Your {top_cat.lower()} costs are {top_pct:.0f}% of total expenses. Consider:",
                'lines': [
                    'Negotiating contract/plan',
                    'Switching to economical alternatives',
                    'Setting a monthly cap for this category',
                ]
            })

    # 2) Food spending alert if increased > 10%
    cur_food = cur_map.get('Food', 0.0) + cur_map.get('Groceries', 0.0)
    prev_food = prev_map.get('Food', 0.0) + prev_map.get('Groceries', 0.0)
    if prev_food > 0 and cur_food > prev_food * 1.10:
        rise = ((cur_food - prev_food)/prev_food*100.0)
        saving_tips.append({
            'level': 'warning',
            'title': 'Food Spending Alert',
            'summary': f"Food expenses increased by {rise:.0f}% this month:",
            'lines': ['Plan meals in advance', 'Use grocery lists', 'Limit dining out']
        })

    # 3) Transport savings if decreased > 10%
    cur_trans = cur_map.get('Transport', 0.0) + cur_map.get('Transportation', 0.0)
    prev_trans = prev_map.get('Transport', 0.0) + prev_map.get('Transportation', 0.0)
    if prev_trans > 0 and cur_trans < prev_trans * 0.90:
        saving_tips.append({
            'level': 'success',
            'title': 'Transportation Savings',
            'summary': 'Great job on transport costs:',
            'lines': ['Consider carpooling', 'Public transport options', 'Regular maintenance']
        })

    # 4) Income growth tip if current income > previous by > 10%
    if previous_income and current_income and previous_income > 0:
        inc_growth = ((float(current_income) - float(previous_income))/float(previous_income))*100.0
        if inc_growth >= 10.0:
            saving_tips.append({
                'level': 'primary',
                'title': 'Income Growth',
                'summary': f"Your income grew by {inc_growth:.1f}%:",
                'lines': ['Freelance opportunities', 'Skill development', 'Investment income']
            })

    # Daily data (last 7 days)
    today = datetime.now().date()
    daily_income = []
    daily_expense = []
    
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_income = Income.objects.filter(
            user=user,
            created_at__date=day
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        day_expense = Expense.objects.filter(
            user=user,
            created_at__date=day
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        daily_income.append(float(day_income))
        daily_expense.append(float(day_expense))
    
    # Weekly data (last 4 weeks)
    weekly_income = []
    weekly_expense = []
    
    for i in range(4):
        week_end = today - timedelta(days=7*i)
        week_start = week_end - timedelta(days=6)
        
        week_income = Income.objects.filter(
            user=user,
            created_at__date__range=[week_start, week_end]
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        week_expense = Expense.objects.filter(
            user=user,
            created_at__date__range=[week_start, week_end]
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        weekly_income.insert(0, float(week_income))
        weekly_expense.insert(0, float(week_expense))

    # Simple ML-like predictions based on recent monthly trends
    # Build last 6 month expense totals (floats)
    recent_months = []
    recent_expenses_list = []
    for i in range(1, 7):
        m_end = end_date.replace(day=1) - timedelta(days=30*(i-1))
        m_start = (m_end - timedelta(days=1)).replace(day=1)
        total_m_exp = Expense.objects.filter(user=user, created_at__gte=m_start, created_at__lt=m_end).aggregate(total=Sum('amount'))['total'] or 0
        recent_months.append(m_start.strftime('%b %Y'))
        recent_expenses_list.append(float(total_m_exp))

    # Prediction = average of last 3 months (fallback to 0)
    last3 = recent_expenses_list[:3] if recent_expenses_list else []
    predicted_expenses = float(sum(last3)/len(last3)) if last3 and len(last3) > 0 else 0.0

    # Confidence from variance: lower variance -> higher confidence
    import statistics
    try:
        stddev = statistics.pstdev(last3) if last3 and len(last3) > 1 else 0
        mean = (sum(last3)/len(last3)) if last3 and len(last3) > 0 else 0
        variability = (stddev/mean) if mean > 0 else 0
        prediction_confidence = max(0, min(1.0, 1.0 - variability)) * 100.0
    except Exception:
        prediction_confidence = 60.0

    # Potential savings suggestion (10% of predicted)
    potential_savings = max(0.0, predicted_expenses * 0.10)

    # Goal achievement likelihood vs a default savings goal for the month
    savings_goal_amount = 30000.0
    current_month_savings = float(max(0.0, (current_income or 0) - (current_expenses or 0)))
    goal_achievement_pct = max(0.0, min(100.0, (current_month_savings / savings_goal_amount * 100.0) if savings_goal_amount > 0 else 0.0))

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
    
    # Debug: Add fallback data if no transactions exist
    if not expense_categories_for_json:
        expense_categories_for_json = [
            {'category': 'No Data', 'total': 0}
        ]
    
    if not income_categories_for_json:
        income_categories_for_json = [
            {'category': 'No Data', 'total': 0}
        ]
    
    context = {
        'user': user,
        'monthly_income': list(monthly_income),
        'monthly_expense': list(monthly_expense),
        'daily_income': daily_income,
        'daily_expense': daily_expense,
        'weekly_income': weekly_income,
        'weekly_expense': weekly_expense,
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
        'daily_income_json': json.dumps(daily_income),
        'daily_expense_json': json.dumps(daily_expense),
        'weekly_income_json': json.dumps(weekly_income),
        'weekly_expense_json': json.dumps(weekly_expense),
        # Predictions (ML Insights)
        'predicted_expenses': predicted_expenses,
        'prediction_confidence': prediction_confidence,
        'potential_savings': potential_savings,
        'savings_goal_amount': savings_goal_amount,
        'goal_achievement_pct': goal_achievement_pct,
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
    
    elif chart_type == 'category' or chart_type == 'categories':
        # Category breakdown data
        income_categories = Income.objects.filter(user=user).values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        expense_categories = Expense.objects.filter(user=user).values('category').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        # Return data in the format expected by the dashboard chart
        if expense_categories:
            return JsonResponse({
                'labels': [item['category'] for item in expense_categories],
                'datasets': [{
                    'data': [float(item['total']) for item in expense_categories]
                }]
            })
        else:
            # Return empty data if no expenses found
            return JsonResponse({
                'labels': ['No Data'],
                'datasets': [{
                    'data': [0]
                }]
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
    
    elif chart_type == 'balance':
        # Balance trend data - calculate monthly balance (income - expenses)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Get monthly data for the last 12 months
        monthly_data = []
        labels = []
        
        for i in range(12):
            month_start = (end_date.replace(day=1) - timedelta(days=30*i)).replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            # Calculate income for this month
            monthly_income = Income.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate expenses for this month
            monthly_expense = Expense.objects.filter(
                user=user,
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate balance
            balance = float(monthly_income) - float(monthly_expense)
            monthly_data.insert(0, balance)
            labels.insert(0, month_start.strftime('%b %Y'))
        
        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'label': 'Balance',
                'data': monthly_data,
                'borderColor': '#3B82F6',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'tension': 0.4,
                'fill': True
            }]
        })
    
    elif chart_type == 'filtered':
        # Handle filtered dashboard data
        date_range = request.GET.get('date_range', 'all')
        category = request.GET.get('category', 'all')
        amount_range = request.GET.get('amount_range', 'all')
        
        # Build filters
        income_filters = {'user': user}
        expense_filters = {'user': user}
        
        # Apply date range filter
        current_date = datetime.now()
        if date_range == 'today':
            start_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            income_filters['created_at__gte'] = start_date
            income_filters['created_at__lt'] = end_date
            expense_filters['created_at__gte'] = start_date
            expense_filters['created_at__lt'] = end_date
        elif date_range == 'this_week':
            start_date = current_date - timedelta(days=current_date.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
            income_filters['created_at__gte'] = start_date
            income_filters['created_at__lt'] = end_date
            expense_filters['created_at__gte'] = start_date
            expense_filters['created_at__lt'] = end_date
        elif date_range == 'this_month':
            start_date = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if current_date.month == 12:
                end_date = start_date.replace(year=current_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=current_date.month + 1)
            income_filters['created_at__gte'] = start_date
            income_filters['created_at__lt'] = end_date
            expense_filters['created_at__gte'] = start_date
            expense_filters['created_at__lt'] = end_date
        elif date_range == 'last_3_months':
            end_date = current_date
            start_date = current_date - timedelta(days=90)
            income_filters['created_at__gte'] = start_date
            income_filters['created_at__lte'] = end_date
            expense_filters['created_at__gte'] = start_date
            expense_filters['created_at__lte'] = end_date
        
        # Apply category filter
        if category != 'all':
            income_filters['category'] = category
            expense_filters['category'] = category
        
        # Get filtered data
        filtered_income = Income.objects.filter(**income_filters)
        filtered_expense = Expense.objects.filter(**expense_filters)
        
        # Apply amount range filter
        if amount_range != 'all':
            if amount_range == '0-1000':
                filtered_income = filtered_income.filter(amount__gte=0, amount__lte=1000)
                filtered_expense = filtered_expense.filter(amount__gte=0, amount__lte=1000)
            elif amount_range == '1000-5000':
                filtered_income = filtered_income.filter(amount__gt=1000, amount__lte=5000)
                filtered_expense = filtered_expense.filter(amount__gt=1000, amount__lte=5000)
            elif amount_range == '5000-10000':
                filtered_income = filtered_income.filter(amount__gt=5000, amount__lte=10000)
                filtered_expense = filtered_expense.filter(amount__gt=5000, amount__lte=10000)
            elif amount_range == '10000+':
                filtered_income = filtered_income.filter(amount__gt=10000)
                filtered_expense = filtered_expense.filter(amount__gt=10000)
        
        # Calculate transaction counts
        today_income_count = filtered_income.filter(created_at__date=current_date.date()).count()
        today_expense_count = filtered_expense.filter(created_at__date=current_date.date()).count()
        today_income_sum = filtered_income.filter(created_at__date=current_date.date()).aggregate(total=Sum('amount'))['total'] or 0
        today_expense_sum = filtered_expense.filter(created_at__date=current_date.date()).aggregate(total=Sum('amount'))['total'] or 0
        
        # Weekly data
        week_start = current_date - timedelta(days=current_date.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        
        weekly_income_count = filtered_income.filter(created_at__gte=week_start, created_at__lt=week_end).count()
        weekly_expense_count = filtered_expense.filter(created_at__gte=week_start, created_at__lt=week_end).count()
        weekly_income_sum = filtered_income.filter(created_at__gte=week_start, created_at__lt=week_end).aggregate(total=Sum('amount'))['total'] or 0
        weekly_expense_sum = filtered_expense.filter(created_at__gte=week_start, created_at__lt=week_end).aggregate(total=Sum('amount'))['total'] or 0
        
        # Monthly data
        month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if current_date.month == 12:
            month_end = month_start.replace(year=current_date.year + 1, month=1)
        else:
            month_end = month_start.replace(month=current_date.month + 1)
            
        monthly_income_count = filtered_income.filter(created_at__gte=month_start, created_at__lt=month_end).count()
        monthly_expense_count = filtered_expense.filter(created_at__gte=month_start, created_at__lt=month_end).count()
        monthly_income_sum = filtered_income.filter(created_at__gte=month_start, created_at__lt=month_end).aggregate(total=Sum('amount'))['total'] or 0
        monthly_expense_sum = filtered_expense.filter(created_at__gte=month_start, created_at__lt=month_end).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get recent transactions
        recent_income = filtered_income.order_by('-created_at')[:5]
        recent_expense = filtered_expense.order_by('-created_at')[:5]
        
        recent_transactions = []
        for income in recent_income:
            recent_transactions.append({
                'description': income.description,
                'category': income.category,
                'amount': float(income.amount),
                'date': income.created_at.strftime('%Y-%m-%d'),
                'type': 'income'
            })
        
        for expense in recent_expense:
            recent_transactions.append({
                'description': expense.description,
                'category': expense.category,
                'amount': float(expense.amount),
                'date': expense.created_at.strftime('%Y-%m-%d'),
                'type': 'expense'
            })
        
        # Sort by date (most recent first) and limit to 10
        recent_transactions = sorted(recent_transactions, key=lambda x: x['date'], reverse=True)[:10]
        
        return JsonResponse({
            'transaction_counts': {
                'today': {
                    'total': today_income_count + today_expense_count,
                    'income': float(today_income_sum),
                    'expense': float(today_expense_sum)
                },
                'weekly': {
                    'total': weekly_income_count + weekly_expense_count,
                    'income': float(weekly_income_sum),
                    'expense': float(weekly_expense_sum)
                },
                'monthly': {
                    'total': monthly_income_count + monthly_expense_count,
                    'income': float(monthly_income_sum),
                    'expense': float(monthly_expense_sum)
                }
            },
            'recent_transactions': recent_transactions
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
    
    # Calculate statistics with default values of 0
    total_groups = len(unique_groups)
    
    # Calculate total members across all groups
    total_members = 0
    for group in unique_groups:
        total_members += group.members.count()
    
    # Calculate total group expenses (all time) and individual group expenses
    total_group_expenses = 0
    group_expenses_dict = {}
    
    for group in unique_groups:
        group_expenses = GroupExpense.objects.filter(group=group).aggregate(total=Sum('amount'))['total'] or 0
        total_group_expenses += group_expenses
        group_expenses_dict[group.id] = group_expenses
    
    # Calculate pending settlements (simplified calculation)
    pending_settlements = 0
    for group in unique_groups:
        # Get all expenses for this group
        group_expenses = GroupExpense.objects.filter(group=group)
        for expense in group_expenses:
            # Calculate what each member owes
            included_count = expense.included_members.count()
            if included_count > 0:
                per_person_amount = expense.amount / included_count
                # If someone other than the payer is included, they owe money
                if expense.paid_by not in expense.included_members.all():
                    pending_settlements += per_person_amount
    
    context = {
        'groups': unique_groups,
        'user': user,
        'total_groups': total_groups,
        'total_members': total_members,
        'total_group_expenses': total_group_expenses,
        'pending_settlements': pending_settlements,
        'group_expenses_dict': group_expenses_dict
    }
    return render(request, 'groups/groups.html', context)


@login_required
@ensure_csrf_cookie
def create_group(request):
    user = Registration.objects.get(email=request.session['entry_email'])
    
    if request.method == 'POST':
        group_name = request.POST.get('name')  # Changed from 'group_name' to 'name'
        description = request.POST.get('description', '')
        group_type = request.POST.get('group_type', 'other')
        
        # Validate that group name is provided
        if not group_name or not group_name.strip():
            return render(request, 'groups/create_group.html', {
                'user': user,
                'error': 'Group name is required'
            })
        
        # Create the group
        group = Group.objects.create(
            name=group_name.strip(),
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


@login_required
def generate_custom_report(request):
    """Generate custom reports based on user filters"""
    if request.method == 'POST':
        user = None
        if 'entry_email' in request.session:
            user = Registration.objects.filter(email=request.session['entry_email']).first()
        
        if not user:
            return redirect('login')
        
        # Get form data
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        category = request.POST.get('category', 'All')
        transaction_type = request.POST.get('type', 'All')
        amount_range = request.POST.get('amount_range', 'All')
        sort_by = request.POST.get('sort_by', 'date_desc')
        group_by = request.POST.get('group_by', 'None')
        export_format = request.POST.get('export_format', 'PDF')
        
        # Build query filters
        income_filters = {'user': user}
        expense_filters = {'user': user}
        
        if start_date:
            income_filters['created_at__gte'] = start_date
            expense_filters['created_at__gte'] = start_date
        
        if end_date:
            income_filters['created_at__lte'] = end_date
            expense_filters['created_at__lte'] = end_date
        
        if category != 'All':
            income_filters['category'] = category
            expense_filters['category'] = category
        
        # Get transactions based on type
        transactions = []
        
        if transaction_type in ['All', 'Income']:
            income_data = Income.objects.filter(**income_filters).values(
                'amount', 'category', 'description', 'created_at'
            ).annotate(type=Value('Income', output_field=CharField()))
            transactions.extend(list(income_data))
        
        if transaction_type in ['All', 'Expense']:
            expense_data = Expense.objects.filter(**expense_filters).values(
                'amount', 'category', 'description', 'created_at'
            ).annotate(type=Value('Expense', output_field=CharField()))
            transactions.extend(list(expense_data))
        
        # Apply amount range filter
        if amount_range != 'All':
            if amount_range == '0-1000':
                transactions = [t for t in transactions if 0 <= float(t['amount']) <= 1000]
            elif amount_range == '1000-5000':
                transactions = [t for t in transactions if 1000 < float(t['amount']) <= 5000]
            elif amount_range == '5000-10000':
                transactions = [t for t in transactions if 5000 < float(t['amount']) <= 10000]
            elif amount_range == '10000+':
                transactions = [t for t in transactions if float(t['amount']) > 10000]
        
        # Sort transactions
        if sort_by == 'date_desc':
            transactions.sort(key=lambda x: x['created_at'], reverse=True)
        elif sort_by == 'date_asc':
            transactions.sort(key=lambda x: x['created_at'])
        elif sort_by == 'amount_desc':
            transactions.sort(key=lambda x: float(x['amount']), reverse=True)
        elif sort_by == 'amount_asc':
            transactions.sort(key=lambda x: float(x['amount']))
        elif sort_by == 'category':
            transactions.sort(key=lambda x: x['category'])
        
        # Generate report based on format
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Custom_Report_{timestamp}"

        if export_format == 'CSV':
            return generate_csv_report(transactions, filename)
        elif export_format == 'JSON':
            return generate_json_report(transactions, filename)
        elif export_format == 'Excel':
            # Excel-friendly CSV content type
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Type', 'Amount', 'Category', 'Description', 'Date'])
            for t in transactions:
                writer.writerow([
                    t['type'],
                    float(t['amount']),
                    t['category'],
                    t['description'],
                    t['created_at'].strftime('%Y-%m-%d %H:%M')
                ])
            return response
        elif export_format == 'PDF':
            # Build rows for PDF
            header = ['Type', 'Amount', 'Category', 'Description', 'Date']
            rows = []
            for t in transactions:
                rows.append([
                    t['type'],
                    float(t['amount']),
                    t['category'],
                    t['description'],
                    t['created_at'].strftime('%Y-%m-%d %H:%M')
                ])

            try:
                from xhtml2pdf import pisa
            except Exception:
                # Fallback to HTML preview if xhtml2pdf is not installed
                html = render_to_string('reports/pdf_report.html', {
                    'user': user,
                    'report_type': 'Custom Report',
                    'date_range': f"{start_date or ''} to {end_date or ''}".strip(),
                    'generated_on': timezone.now(),
                    'header': header,
                    'rows': rows,
                    'pdf_notice': 'xhtml2pdf is not installed. Please install it to enable direct PDF download.'
                })
                return HttpResponse(html)

            html = render_to_string('reports/pdf_report.html', {
                'user': user,
                'report_type': 'Custom Report',
                'date_range': f"{start_date or ''} to {end_date or ''}".strip(),
                'generated_on': timezone.now(),
                'header': header,
                'rows': rows,
                'pdf_notice': ''
            })
            result = BytesIO()
            pdf = pisa.CreatePDF(src=html, dest=result)
            if pdf.err:
                return HttpResponse('Failed to generate PDF.', content_type='text/plain', status=500)
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
            return response
        else:
            # Default to CSV if format is unrecognized
            return generate_csv_report(transactions, filename)
    
    return redirect('reports')


def generate_csv_report(transactions, filename):
    """Generate CSV report from transactions data"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Description', 'Amount'])
    
    for transaction in transactions:
        writer.writerow([
            transaction['created_at'].strftime('%Y-%m-%d %H:%M'),
            transaction['type'],
            transaction['category'],
            transaction['description'],
            f"₹{transaction['amount']}"
        ])
    
    return response




def generate_json_report(transactions, filename):
    """Generate JSON report from transactions data"""
    # Convert datetime objects to strings for JSON serialization
    for transaction in transactions:
        transaction['created_at'] = transaction['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        transaction['amount'] = str(transaction['amount'])
    
    response = HttpResponse(
        json.dumps(transactions, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
    
    return response


# Edit and Delete Transaction Views
@login_required
def edit_income(request, income_id):
    """Edit an existing income transaction"""
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if not user:
        return redirect('login')
    
    income = get_object_or_404(Income, id=income_id, user=user)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('date')
        currency = request.POST.get('currency')
        category = request.POST.get('category')
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            income.amount = amount
            income.description = description
            income.date = date
            income.currency = currency
            income.category = category
            income.save()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Income of ₹{amount} updated successfully!'
                })
            else:
                messages.success(request, f'Income of ₹{amount} updated successfully!')
                return redirect('transaction_history')
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'Error updating income: {str(e)}'
                })
            else:
                messages.error(request, f'Error updating income: {str(e)}')
    
    context = {
        'user': user,
        'income': income,
        'edit_mode': True
    }
    return render(request, 'transactions/edit_income.html', context)


@login_required
def edit_expense(request, expense_id):
    """Edit an existing expense transaction"""
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if not user:
        return redirect('login')
    
    expense = get_object_or_404(Expense, id=expense_id, user=user)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date = request.POST.get('date')
        currency = request.POST.get('currency')
        category = request.POST.get('category')
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            expense.amount = amount
            expense.description = description
            expense.date = date
            expense.currency = currency
            expense.category = category
            expense.save()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Expense of ₹{amount} updated successfully!'
                })
            else:
                messages.success(request, f'Expense of ₹{amount} updated successfully!')
                return redirect('transaction_history')
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'Error updating expense: {str(e)}'
                })
            else:
                messages.error(request, f'Error updating expense: {str(e)}')
    
    context = {
        'user': user,
        'expense': expense,
        'edit_mode': True
    }
    return render(request, 'transactions/edit_expense.html', context)


@login_required
def delete_income(request, income_id):
    """Delete an income transaction"""
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if not user:
        return redirect('login')
    
    income = get_object_or_404(Income, id=income_id, user=user)
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            amount = income.amount
            income.delete()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Income of ₹{amount} deleted successfully!'
                })
            else:
                messages.success(request, f'Income of ₹{amount} deleted successfully!')
                return redirect('transaction_history')
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'Error deleting income: {str(e)}'
                })
            else:
                messages.error(request, f'Error deleting income: {str(e)}')
    
    context = {
        'user': user,
        'income': income,
        'delete_mode': True
    }
    return render(request, 'transactions/delete_income.html', context)


@login_required
def delete_expense(request, expense_id):
    """Delete an expense transaction"""
    user = None
    if 'entry_email' in request.session:
        user = Registration.objects.filter(email=request.session['entry_email']).first()
    
    if not user:
        return redirect('login')
    
    expense = get_object_or_404(Expense, id=expense_id, user=user)
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            amount = expense.amount
            expense.delete()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f'Expense of ₹{amount} deleted successfully!'
                })
            else:
                messages.success(request, f'Expense of ₹{amount} deleted successfully!')
                return redirect('transaction_history')
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'Error deleting expense: {str(e)}'
                })
            else:
                messages.error(request, f'Error deleting expense: {str(e)}')
    
    context = {
        'user': user,
        'expense': expense,
        'delete_mode': True
    }
    return render(request, 'transactions/delete_expense.html', context)





