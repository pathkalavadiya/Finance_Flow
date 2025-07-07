from django.shortcuts import render
from .models import Registration


# Create your views here.
<<<<<<< HEAD
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
=======
def index(request):
    return render(request, 'index.html')

def add_expense(request):
    return render(request, 'expenses/add_expense.html')
>>>>>>> c62aaeeeba9b988c71292dc8499b3f225fdc63fc
