from django.db import models
from datetime import datetime
from decimal import Decimal

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
    date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=10)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    # created_by = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='created_expenses', null=True, blank=True)

    def __str__(self):
        return f"{self.amount} {self.currency} - {self.category}"

    @property
    def author_name(self):
        return self.user.name if self.user else "Unknown"

class Income(models.Model):
    user = models.ForeignKey(Registration, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=10)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    # created_by = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='created_incomes', null=True, blank=True)

    def __str__(self):
        return f"{self.amount} {self.currency} - {self.category}"
    
    @property
    def author_name(self):
        return self.user.name if self.user else "Unknown"


# Group Split Money Models
class Group(models.Model):
    GROUP_TYPE_CHOICES = [
        ('trip', 'Trip'),
        ('home', 'Home'),
        ('friends', 'Friends'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, default='other')
    created_by = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(Registration, through='GroupMember', related_name='joined_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_member_balance(self, member):
        """Calculate the balance for a specific member in this group"""
        # Get all expenses where this member was involved
        member_expenses = GroupExpense.objects.filter(
            group=self,
            included_members=member
        )
        
        # Calculate total amount this member owes (their share of expenses)
        total_owed = sum(
            expense.amount / expense.included_members.count()
            for expense in member_expenses
        )
        
        # Get all expenses paid by this member
        paid_expenses = GroupExpense.objects.filter(
            group=self,
            paid_by=member
        )
        
        # Calculate total amount this member paid
        total_paid = sum(expense.amount for expense in paid_expenses)
        
        # Balance = amount paid - amount owed
        return total_paid - total_owed


class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    member = models.ForeignKey(Registration, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'member')

    def __str__(self):
        return f"{self.member.name} in {self.group.name}"


class GroupExpense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    paid_by = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='paid_expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    included_members = models.ManyToManyField(Registration, related_name='included_expenses')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"


class GroupExpenseSplit(models.Model):
    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE)
    member = models.ForeignKey(Registration, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('expense', 'member')

    def __str__(self):
        return f"{self.member.name} owes {self.amount} for {self.expense.description}"



 
    