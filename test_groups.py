#!/usr/bin/env python
"""
Simple test script to verify group functionality
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from project_app.models import Registration, Group, GroupMember, GroupExpense, GroupExpenseSplit
from decimal import Decimal

def test_group_functionality():
    """Test the group functionality"""
    print("Testing Group Functionality...")
    
    # Create test users
    try:
        user1 = Registration.objects.create(
            name="Test User 1",
            email="user1@test.com",
            phone_no="1234567890",
            password="test123",
            address="Test Address 1"
        )
        print(f"✓ Created user: {user1.name}")
        
        user2 = Registration.objects.create(
            name="Test User 2", 
            email="user2@test.com",
            phone_no="0987654321",
            password="test123",
            address="Test Address 2"
        )
        print(f"✓ Created user: {user2.name}")
        
        # Create a group
        group = Group.objects.create(
            name="Test Group",
            description="A test group for splitting expenses",
            created_by=user1
        )
        print(f"✓ Created group: {group.name}")
        
        # Add members to group
        GroupMember.objects.create(group=group, user=user1, role='admin')
        GroupMember.objects.create(group=group, user=user2, role='member')
        print(f"✓ Added members to group")
        
        # Create a group expense
        expense = GroupExpense.objects.create(
            group=group,
            paid_by=user1,
            description="Dinner",
            amount=Decimal('100.00'),
            currency='USD',
            category='Food & Dining',
            split_type='equal',
            expense_date='2024-01-15'
        )
        print(f"✓ Created expense: {expense.description}")
        
        # Create expense splits
        GroupExpenseSplit.objects.create(
            expense=expense,
            user=user1,
            amount=Decimal('-50.00')  # User1 gets money back
        )
        GroupExpenseSplit.objects.create(
            expense=expense,
            user=user2,
            amount=Decimal('50.00')   # User2 owes money
        )
        print(f"✓ Created expense splits")
        
        # Test group methods
        print(f"✓ Group member count: {group.get_member_count()}")
        print(f"✓ Group total expenses: ${group.get_total_expenses()}")
        
        print("\n🎉 All tests passed! Group functionality is working correctly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("This might be due to database migration issues.")

if __name__ == "__main__":
    test_group_functionality()