# Group Split Money Features

This document describes the new group split money functionality added to FinanceFlow, inspired by Splitwise.

## Features Implemented

### 1. Group Management
- **Create Groups**: Users can create new groups for shared expenses
- **Add Members**: Invite users to groups by email address
- **Group Types**: Support for different group types (General, Trip, Roommates, Office, Family, Friends)
- **Group Information**: Track group details, member count, and total expenses

### 2. Expense Management
- **Add Group Expenses**: Create shared expenses within groups
- **Split Types**: Support for equal splits (percentage and custom splits planned)
- **Expense Details**: Track description, amount, category, date, and notes
- **Automatic Calculations**: Per-person amounts calculated automatically

### 3. Balance Tracking
- **Real-time Balances**: Track who owes what in real-time
- **Balance Status**: Shows "owes", "gets back", or "settled up" for each member
- **Detailed Breakdown**: View total paid, total owes, and net balance for each member
- **Settlement Suggestions**: Automatic suggestions for settling debts

### 4. User Interface
- **Modern Design**: Clean, responsive interface with glass morphism effects
- **Splitwise-inspired**: Similar layout and functionality to Splitwise
- **Intuitive Navigation**: Easy-to-use navigation between groups and features
- **Real-time Updates**: Balances update automatically when expenses are added

## Models Added

### Group
- `name`: Group name
- `description`: Optional group description
- `created_by`: User who created the group
- `members`: Many-to-many relationship with users through GroupMember
- `created_at`, `updated_at`: Timestamps

### GroupMember
- `group`: Foreign key to Group
- `user`: Foreign key to Registration
- `role`: Admin or Member role
- `joined_at`: When they joined the group

### GroupExpense
- `group`: Foreign key to Group
- `paid_by`: User who paid for the expense
- `description`: Expense description
- `amount`: Expense amount
- `currency`: Currency used
- `category`: Expense category
- `split_type`: How the expense is split (equal, percentage, custom)
- `expense_date`: Date of the expense
- `notes`: Optional notes

### GroupExpenseSplit
- `expense`: Foreign key to GroupExpense
- `user`: User involved in the split
- `amount`: Amount they owe or get back
- `percentage`: Percentage of the expense (for percentage splits)
- `is_paid`: Whether they've paid their share

## Views Added

### Groups
- `groups()`: Main groups page showing user's groups
- `create_group()`: Create a new group
- `group_detail()`: View group details and expenses
- `add_group_expense()`: Add a new expense to a group
- `group_balances()`: View detailed group balances
- `add_group_member()`: Add a new member to a group

## Templates Added

### Core Templates
- `groups.html`: Main groups listing page
- `create_group.html`: Group creation form
- `group_detail.html`: Group details and expenses view
- `add_group_expense.html`: Add expense form (Splitwise-style)
- `group_balances.html`: Detailed balance view
- `add_group_member.html`: Add member form

## Key Features

### Splitwise-like Functionality
1. **Group Creation**: Similar to Splitwise's "START A NEW GROUP"
2. **Expense Addition**: Modal-style form like Splitwise's "Add an expense"
3. **Balance Display**: Shows balances similar to "Group balances" modal
4. **Member Management**: Add members by email like Splitwise
5. **Split Options**: Equal splits with per-person calculations

### Balance Calculation Logic
- **Positive Balance**: User gets money back (they paid more than their share)
- **Negative Balance**: User owes money (they paid less than their share)
- **Zero Balance**: User is settled up

### Example Scenario
1. User A creates a group "Roommates"
2. User A adds User B to the group
3. User A adds a $100 dinner expense (paid by User A)
4. System automatically calculates:
   - User A: Gets back $50 (paid $100, owes $50)
   - User B: Owes $50 (paid $0, owes $50)
5. Balances show User A gets back $50, User B owes $50

## Navigation Integration
- Added "Groups" link to main navigation
- Integrated with existing dashboard and sidebar
- Consistent styling with existing FinanceFlow design

## Future Enhancements
- Percentage-based splits
- Custom amount splits
- Expense categories and filtering
- Payment tracking
- Export functionality
- Email notifications
- Mobile-responsive improvements

## Usage Instructions

1. **Create a Group**:
   - Navigate to Groups → Create New Group
   - Enter group name and description
   - Click "Create Group"

2. **Add Members**:
   - Go to group details → Add Member
   - Enter member's email address
   - Click "Add Member"

3. **Add Expenses**:
   - Go to group details → Add an expense
   - Fill in expense details
   - Choose split type (currently equal only)
   - Click "Save"

4. **View Balances**:
   - Go to group details → View balances
   - See who owes what and settlement suggestions

## Technical Notes

- Built with Django 3.1.12
- Uses Bootstrap 5 for responsive design
- Glass morphism UI effects
- Real-time balance calculations
- Automatic expense splitting
- Session-based authentication

The group split money functionality provides a complete Splitwise-like experience for managing shared expenses within FinanceFlow.