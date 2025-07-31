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

# Group Split Money Models
class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(Registration, through='GroupMember', related_name='joined_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_total_expenses(self):
        """Get total expenses for this group"""
        return self.groupexpense_set.aggregate(total=models.Sum('amount'))['total'] or 0

    def get_member_count(self):
        """Get number of members in the group"""
        return self.members.count()

class GroupMember(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(Registration, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user.name} - {self.group.name}"

class GroupExpense(models.Model):
    SPLIT_TYPE_CHOICES = [
        ('equal', 'Equal'),
        ('percentage', 'Percentage'),
        ('custom', 'Custom'),
    ]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    paid_by = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='paid_expenses')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    category = models.CharField(max_length=50, blank=True, null=True)
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPE_CHOICES, default='equal')
    expense_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - {self.amount} {self.currency}"

    def get_per_person_amount(self):
        """Calculate amount per person for equal split"""
        member_count = self.group.members.count()
        if member_count > 0:
            return self.amount / member_count
        return 0

class GroupExpenseSplit(models.Model):
    expense = models.ForeignKey(GroupExpense, on_delete=models.CASCADE)
    user = models.ForeignKey(Registration, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('expense', 'user')

    def __str__(self):
        return f"{self.user.name} - {self.amount} {self.expense.currency}"

    def get_balance_status(self):
        """Get balance status for this user in this expense"""
        if self.amount > 0:
            return f"owes ${self.amount}"
        elif self.amount < 0:
            return f"gets back ${abs(self.amount)}"
        else:
            return "settled up" 
    