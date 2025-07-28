from django.shortcuts import render, redirect, redirect
from django.db.models import Sum
from .models import Registration, Expense, Income
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

