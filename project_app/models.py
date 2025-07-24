from django.db import models

# Create your models here.
# Registration model
class Registration(models.Model):
    name=models.CharField(max_length=50)
    email=models.EmailField()
    phone_no=models.CharField(max_length=10)
    password=models.CharField(max_length=8)
    address=models.TextField()

    def __str__(self):
        return self.email

class Expense(models.Model):
    user = models.ForeignKey(Registration, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    currency = models.CharField(max_length=10)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} {self.currency} - {self.category}" 
    