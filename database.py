"""
Database module for Benjo Moments Photography System.
Handles database initialization, schema creation, and CRUD operations.
"""
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash
import config

def get_db_connection():
    """Create a database connection with row factory."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with all required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Income table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Customers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service TEXT NOT NULL,
            amount_paid REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Invoices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            date DATE NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Assets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            value REAL NOT NULL,
            supplier TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Gallery table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            album TEXT NOT NULL,
            caption TEXT,
            published INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Website settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS website_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT DEFAULT 'Benjo Moments',
            hero_text TEXT DEFAULT 'Capturing Your Precious Moments',
            hero_subtext TEXT DEFAULT 'Professional Photography Services',
            about_text TEXT DEFAULT 'We are a professional photography studio specializing in weddings, portraits, and special events.',
            contact_phone TEXT DEFAULT '+256 700 000 000',
            contact_email TEXT DEFAULT 'info@benjomoments.com',
            address TEXT DEFAULT 'Kampala, Uganda',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Contact messages table - stores client inquiries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            service TEXT,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Pricing packages table - editable from admin
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pricing_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            price_label TEXT DEFAULT '/session',
            icon TEXT DEFAULT 'fa-camera',
            features TEXT,
            is_featured INTEGER DEFAULT 0,
            display_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def create_default_admin():
    """Create default admin user if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute('SELECT id FROM users WHERE email = ?', (config.DEFAULT_ADMIN_EMAIL,))
    if not cursor.fetchone():
        password_hash = generate_password_hash(config.DEFAULT_ADMIN_PASSWORD)
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, 'admin')
        ''', (config.DEFAULT_ADMIN_NAME, config.DEFAULT_ADMIN_EMAIL, password_hash))
        conn.commit()
    
    conn.close()

def init_default_settings():
    """Initialize default website settings if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM website_settings LIMIT 1')
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO website_settings (site_name, hero_text, hero_subtext, about_text, contact_phone, contact_email, address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Benjo Moments',
            'Capturing Your Precious Moments',
            'Professional Photography for Weddings, Events & Portraits',
            'Benjo Moments is a professional photography studio dedicated to capturing life\'s most precious moments. With years of experience in wedding, portrait, and event photography, we bring creativity and passion to every shoot.',
            '+256 700 000 000',
            'info@benjomoments.com',
            'Kampala, Uganda'
        ))
        conn.commit()
    
    conn.close()

# ============== CRUD OPERATIONS ==============

# --- Income ---
def get_all_income():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM income ORDER BY date DESC').fetchall()
    conn.close()
    return rows

def add_income(date, description, category, amount):
    conn = get_db_connection()
    conn.execute('INSERT INTO income (date, description, category, amount) VALUES (?, ?, ?, ?)',
                 (date, description, category, amount))
    conn.commit()
    conn.close()

def delete_income(income_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM income WHERE id = ?', (income_id,))
    conn.commit()
    conn.close()

def get_total_income():
    conn = get_db_connection()
    result = conn.execute('SELECT COALESCE(SUM(amount), 0) as total FROM income').fetchone()
    conn.close()
    return result['total']

# --- Expenses ---
def get_all_expenses():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM expenses ORDER BY date DESC').fetchall()
    conn.close()
    return rows

def add_expense(date, description, category, amount):
    conn = get_db_connection()
    conn.execute('INSERT INTO expenses (date, description, category, amount) VALUES (?, ?, ?, ?)',
                 (date, description, category, amount))
    conn.commit()
    conn.close()

def delete_expense(expense_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()

def get_total_expenses():
    conn = get_db_connection()
    result = conn.execute('SELECT COALESCE(SUM(amount), 0) as total FROM expenses').fetchone()
    conn.close()
    return result['total']

# --- Customers ---
def get_all_customers():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM customers ORDER BY created_at DESC').fetchall()
    conn.close()
    return rows

def get_customer(customer_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()
    return row

def add_customer(name, service, amount_paid, total_amount, contact):
    conn = get_db_connection()
    conn.execute('INSERT INTO customers (name, service, amount_paid, total_amount, contact) VALUES (?, ?, ?, ?, ?)',
                 (name, service, amount_paid, total_amount, contact))
    conn.commit()
    conn.close()

def update_customer_payment(customer_id, amount_paid):
    conn = get_db_connection()
    conn.execute('UPDATE customers SET amount_paid = ? WHERE id = ?', (amount_paid, customer_id))
    conn.commit()
    conn.close()

def delete_customer(customer_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()

def get_total_pending_balance():
    conn = get_db_connection()
    result = conn.execute('SELECT COALESCE(SUM(total_amount - amount_paid), 0) as total FROM customers').fetchone()
    conn.close()
    return result['total']

# --- Invoices ---
def get_all_invoices():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT i.*, c.name as customer_name 
        FROM invoices i 
        JOIN customers c ON i.customer_id = c.id 
        ORDER BY i.date DESC
    ''').fetchall()
    conn.close()
    return rows

def add_invoice(invoice_number, customer_id, date, amount):
    conn = get_db_connection()
    conn.execute('INSERT INTO invoices (invoice_number, customer_id, date, amount) VALUES (?, ?, ?, ?)',
                 (invoice_number, customer_id, date, amount))
    conn.commit()
    conn.close()

def update_invoice_status(invoice_id, status):
    conn = get_db_connection()
    conn.execute('UPDATE invoices SET status = ? WHERE id = ?', (status, invoice_id))
    conn.commit()
    conn.close()

def delete_invoice(invoice_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))
    conn.commit()
    conn.close()

def generate_invoice_number():
    conn = get_db_connection()
    result = conn.execute('SELECT COUNT(*) as count FROM invoices').fetchone()
    conn.close()
    return f"INV-{result['count'] + 1:04d}"

# --- Assets ---
def get_all_assets():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM assets ORDER BY created_at DESC').fetchall()
    conn.close()
    return rows

def add_asset(name, category, value, supplier):
    conn = get_db_connection()
    conn.execute('INSERT INTO assets (name, category, value, supplier) VALUES (?, ?, ?, ?)',
                 (name, category, value, supplier))
    conn.commit()
    conn.close()

def delete_asset(asset_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
    conn.commit()
    conn.close()

def get_total_asset_value():
    conn = get_db_connection()
    result = conn.execute('SELECT COALESCE(SUM(value), 0) as total FROM assets').fetchone()
    conn.close()
    return result['total']

# --- Gallery ---
def get_all_gallery_images():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM gallery ORDER BY uploaded_at DESC').fetchall()
    conn.close()
    return rows

def get_published_gallery_images(album=None):
    conn = get_db_connection()
    if album:
        rows = conn.execute('SELECT * FROM gallery WHERE published = 1 AND album = ? ORDER BY uploaded_at DESC', (album,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM gallery WHERE published = 1 ORDER BY uploaded_at DESC').fetchall()
    conn.close()
    return rows

def add_gallery_image(filename, album, caption):
    conn = get_db_connection()
    conn.execute('INSERT INTO gallery (filename, album, caption, published) VALUES (?, ?, ?, 1)',
                 (filename, album, caption))
    conn.commit()
    conn.close()

def toggle_gallery_publish(image_id):
    conn = get_db_connection()
    conn.execute('UPDATE gallery SET published = NOT published WHERE id = ?', (image_id,))
    conn.commit()
    conn.close()

def delete_gallery_image(image_id):
    conn = get_db_connection()
    row = conn.execute('SELECT filename, album FROM gallery WHERE id = ?', (image_id,)).fetchone()
    conn.execute('DELETE FROM gallery WHERE id = ?', (image_id,))
    conn.commit()
    conn.close()
    return row

# --- Website Settings ---
def get_website_settings():
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM website_settings LIMIT 1').fetchone()
    conn.close()
    return row

def update_website_settings(site_name, hero_text, hero_subtext, about_text, contact_phone, contact_email, address):
    conn = get_db_connection()
    conn.execute('''
        UPDATE website_settings 
        SET site_name = ?, hero_text = ?, hero_subtext = ?, about_text = ?, 
            contact_phone = ?, contact_email = ?, address = ?, updated_at = ?
        WHERE id = 1
    ''', (site_name, hero_text, hero_subtext, about_text, contact_phone, contact_email, address, datetime.now()))
    conn.commit()
    conn.close()

# --- Reports ---
def get_income_by_date_range(start_date, end_date):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM income WHERE date BETWEEN ? AND ? ORDER BY date DESC', (start_date, end_date)).fetchall()
    conn.close()
    return rows

def get_expenses_by_date_range(start_date, end_date):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC', (start_date, end_date)).fetchall()
    conn.close()
    return rows

def get_recent_transactions(limit=10):
    """Get recent income and expenses combined."""
    conn = get_db_connection()
    income = conn.execute('SELECT id, date, description, category, amount, "income" as type FROM income ORDER BY date DESC LIMIT ?', (limit,)).fetchall()
    expenses = conn.execute('SELECT id, date, description, category, amount, "expense" as type FROM expenses ORDER BY date DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    
    # Combine and sort
    transactions = list(income) + list(expenses)
    transactions.sort(key=lambda x: x['date'], reverse=True)
    return transactions[:limit]

# --- User Authentication ---
def get_user_by_email(email):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return row

def get_user_by_id(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return row

# --- Contact Messages ---
def get_all_messages():
    """Get all contact messages, newest first."""
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM contact_messages ORDER BY created_at DESC').fetchall()
    conn.close()
    return rows

def get_unread_messages_count():
    """Get count of unread messages."""
    conn = get_db_connection()
    result = conn.execute('SELECT COUNT(*) as count FROM contact_messages WHERE is_read = 0').fetchone()
    conn.close()
    return result['count']

def add_contact_message(name, email, phone, service, message):
    """Add a new contact message from a client."""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO contact_messages (name, email, phone, service, message) 
        VALUES (?, ?, ?, ?, ?)
    ''', (name, email, phone, service, message))
    conn.commit()
    conn.close()

def mark_message_read(message_id):
    """Mark a message as read."""
    conn = get_db_connection()
    conn.execute('UPDATE contact_messages SET is_read = 1 WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()

def delete_message(message_id):
    """Delete a contact message."""
    conn = get_db_connection()
    conn.execute('DELETE FROM contact_messages WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()


# ===== PRICING PACKAGES =====

def get_all_pricing_packages():
    """Get all pricing packages ordered by display_order."""
    conn = get_db_connection()
    packages = conn.execute('''
        SELECT * FROM pricing_packages 
        ORDER BY display_order ASC, id ASC
    ''').fetchall()
    conn.close()
    return packages

def get_active_pricing_packages():
    """Get only active pricing packages for public display."""
    conn = get_db_connection()
    packages = conn.execute('''
        SELECT * FROM pricing_packages 
        WHERE is_active = 1
        ORDER BY display_order ASC, id ASC
    ''').fetchall()
    conn.close()
    return packages

def get_pricing_package(package_id):
    """Get a single pricing package by ID."""
    conn = get_db_connection()
    package = conn.execute('SELECT * FROM pricing_packages WHERE id = ?', (package_id,)).fetchone()
    conn.close()
    return package

def add_pricing_package(name, description, price, price_label, icon, features, is_featured, display_order):
    """Add a new pricing package."""
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO pricing_packages (name, description, price, price_label, icon, features, is_featured, display_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, price, price_label, icon, features, is_featured, display_order))
    conn.commit()
    conn.close()

def update_pricing_package(package_id, name, description, price, price_label, icon, features, is_featured, display_order):
    """Update an existing pricing package."""
    conn = get_db_connection()
    conn.execute('''
        UPDATE pricing_packages 
        SET name = ?, description = ?, price = ?, price_label = ?, icon = ?, features = ?, is_featured = ?, display_order = ?
        WHERE id = ?
    ''', (name, description, price, price_label, icon, features, is_featured, display_order, package_id))
    conn.commit()
    conn.close()

def delete_pricing_package(package_id):
    """Delete a pricing package."""
    conn = get_db_connection()
    conn.execute('DELETE FROM pricing_packages WHERE id = ?', (package_id,))
    conn.commit()
    conn.close()

def toggle_pricing_package(package_id):
    """Toggle the active status of a pricing package."""
    conn = get_db_connection()
    conn.execute('UPDATE pricing_packages SET is_active = NOT is_active WHERE id = ?', (package_id,))
    conn.commit()
    conn.close()

def create_default_pricing_packages():
    """Create default pricing packages if none exist."""
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM pricing_packages').fetchone()[0]
    
    if count == 0:
        # Insert default packages
        packages = [
            ('Basic', 'Perfect for portraits & small events', 300000, '/session', 'fa-camera', 
             '2 Hours Coverage|50+ Edited Photos|Digital Download|1 Location|Basic Retouching', 0, 1),
            ('Premium', 'Best for weddings & kukyala', 1500000, '/event', 'fa-heart',
             'Full Day Coverage|300+ Edited Photos|Photo Album Included|Multiple Locations|2 Photographers|Premium Retouching', 1, 2),
            ('Full Package', 'Photo + Video combo deal', 2500000, '/event', 'fa-video',
             'Photography + Videography|500+ Photos & Full Video|Highlight Reel|Premium Album + USB|Same Day Edit Preview|Drone Coverage', 0, 3)
        ]
        
        for pkg in packages:
            conn.execute('''
                INSERT INTO pricing_packages (name, description, price, price_label, icon, features, is_featured, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', pkg)
        
        conn.commit()
    
    conn.close()
