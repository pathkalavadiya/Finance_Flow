# Generated manually for Lending model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('project_app', '0006_expense_user_income'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lending',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('borrower_name', models.CharField(max_length=100)),
                ('borrower_phone', models.CharField(max_length=15)),
                ('borrower_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(default='USD', max_length=10)),
                ('description', models.TextField(blank=True, null=True)),
                ('interest_rate', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('loan_date', models.DateField()),
                ('due_date', models.DateField()),
                ('status', models.CharField(choices=[('active', 'Active'), ('paid', 'Paid'), ('overdue', 'Overdue'), ('cancelled', 'Cancelled')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project_app.registration')),
            ],
        ),
    ] 