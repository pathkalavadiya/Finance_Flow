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
    user = models.ForeignKey(Registration, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    currency = models.CharField(max_length=10)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} {self.currency} - {self.category}"

class Income(models.Model):
    user = models.ForeignKey(Registration, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    currency = models.CharField(max_length=10)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} {self.currency} - {self.category}"

class Lending(models.Model):
    LOAN_STATUS_CHOICES = [
        ('active', 'Active'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(Registration, on_delete=models.CASCADE, null=True, blank=True)
    borrower_name = models.CharField(max_length=100)
    borrower_phone = models.CharField(max_length=15)
    borrower_email = models.EmailField(blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    description = models.TextField(blank=True, null=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    loan_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=LOAN_STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.borrower_name} - {self.amount} {self.currency}"

    def get_total_amount(self):
        """Calculate total amount including interest"""
        interest_amount = (self.amount * self.interest_rate) / 100
        return self.amount + interest_amount 
    