from django.shortcuts import render
from django.shortcuts import redirect
from .models import Registration

# Create your views here.

def register(request):
    if request.method == 'POST':
        store_reg = Registration()
        store_reg.name = request.POST['name']
        store_reg.email = request.POST['email']
        store_reg.add = request.POST['add']
        store_reg.mob = request.POST['mob']
        store_reg.password = request.POST['password']
        try:
            already_registered = Registration.objects.get(email = request.POST['email'])
            if already_registered:
                return render(request,'register.html',{'already_registerd':"This email is already registered.."})
        except:
            store_reg.save()
            return render(request,'register.html',{'stored':"registration sucessfull.."})
    else:
        return render(request,'register.html')
    

def login(request):
    if request.method == 'POST':
        try:
            register_data = Registration.objects.get(email = request.POST['email'])
            if request.POST['password'] == register_data.password:
                request.session['login'] = register_data.email
                return redirect('index')
            else:
                return render(request,'login.html',{'incorrect':"the pasword is incorrect.."})
        except:
            return render(request,'login.html',{'not_registred':"This email is not registerd.."})
    return render(request,'login.html')

