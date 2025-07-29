-- Create the lending table manually
CREATE TABLE IF NOT EXISTS project_app_lending (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    borrower_name VARCHAR(100) NOT NULL,
    borrower_phone VARCHAR(15) NOT NULL,
    borrower_email VARCHAR(254) NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    description TEXT NULL,
    interest_rate DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    loan_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NULL,
    FOREIGN KEY (user_id) REFERENCES project_app_registration(id)
); 