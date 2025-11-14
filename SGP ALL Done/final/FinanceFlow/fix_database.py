#!/usr/bin/env python3
"""
Simple script to fix the database schema by adding updated_at columns
"""
import sqlite3
import os
from datetime import datetime

def fix_database():
    db_path = 'db.sqlite3'
    
    if not os.path.exists(db_path):
        print("Database file not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if updated_at column exists in Income table
        cursor.execute("PRAGMA table_info(project_app_income)")
        income_columns = [column[1] for column in cursor.fetchall()]
        
        if 'updated_at' not in income_columns:
            print("Adding updated_at column to Income table...")
            cursor.execute("""
                ALTER TABLE project_app_income 
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            
            # Update existing records
            cursor.execute("""
                UPDATE project_app_income 
                SET updated_at = created_at 
                WHERE updated_at IS NULL
            """)
        
        # Check if updated_at column exists in Expense table
        cursor.execute("PRAGMA table_info(project_app_expense)")
        expense_columns = [column[1] for column in cursor.fetchall()]
        
        if 'updated_at' not in expense_columns:
            print("Adding updated_at column to Expense table...")
            cursor.execute("""
                ALTER TABLE project_app_expense 
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)
            
            # Update existing records
            cursor.execute("""
                UPDATE project_app_expense 
                SET updated_at = created_at 
                WHERE updated_at IS NULL
            """)
        
        conn.commit()
        print("Database schema fixed successfully!")
        
    except Exception as e:
        print(f"Error fixing database: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()
