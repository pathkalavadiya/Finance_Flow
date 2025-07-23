from django.shortcuts import render, redirect, redirect
from .models import Registration, Expense

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
                return redirect('index')
            else:
                return render(request, 'login.html', {'login_key_incorrect': "Email or password is wrong"})
        else:
            return render(request, 'login.html', {'not_register': "This email is not registered"})
    return render(request, 'login.html')


def dashboard(request):
    return render(request, 'dashboard.html')


def expense(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        currency = request.POST.get('currency')
        category = request.POST.get('category')
        # Save to database
        Expense.objects.create(
            amount=amount,
            description=description,
            currency=currency,
            category=category
        )
        return render(request, 'expense.html', {
            'success': True,
            'amount': amount,
            'description': description,
            'currency': currency,
            'category': category
        })
    return render(request, 'expense.html')

