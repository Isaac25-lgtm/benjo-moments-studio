"""
Admin module for Benjo Moments Photography System.
Handles all admin dashboard functionality.
"""
import os
import re
import uuid
from datetime import datetime
from flask import Blueprint, abort, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from auth import login_required
import database
import config
from extensions import limiter

admin = Blueprint('admin', __name__, url_prefix='/admin')

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def parse_positive_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None

def parse_non_negative_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None

def parse_non_negative_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None

def valid_date(date_string):
    if not date_string:
        return False
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# ============== DASHBOARD ==============
@admin.route('/')
@login_required
def dashboard():
    """Admin dashboard with summary statistics."""
    total_income = database.get_total_income()
    total_expenses = database.get_total_expenses()
    net_profit = total_income - total_expenses
    total_pending = database.get_total_pending_balance()
    total_assets = database.get_total_asset_value()
    recent_transactions = database.get_recent_transactions(10)
    
    return render_template('admin/dashboard.html',
                         total_income=total_income,
                         total_expenses=total_expenses,
                         net_profit=net_profit,
                         total_pending=total_pending,
                         total_assets=total_assets,
                         recent_transactions=recent_transactions)

# ============== INCOME ==============
@admin.route('/income')
@login_required
def income():
    """Income management page."""
    records = database.get_all_income()
    total = database.get_total_income()
    return render_template('admin/income.html', records=records, total=total)

@admin.route('/income/add', methods=['POST'])
@login_required
def add_income():
    """Add new income record."""
    date = request.form.get('date')
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    amount = parse_positive_float(request.form.get('amount'))
    
    if not valid_date(date):
        flash('Please provide a valid date.', 'error')
    elif not all([description, category]):
        flash('Description and category are required.', 'error')
    elif amount is None:
        flash('Amount must be a positive number.', 'error')
    else:
        database.add_income(date, description, category, amount)
        flash('Income record added successfully.', 'success')
    
    return redirect(url_for('admin.income'))

@admin.route('/income/delete/<int:id>', methods=['POST'])
@login_required
def delete_income(id):
    """Delete income record."""
    database.delete_income(id)
    flash('Income record deleted.', 'info')
    return redirect(url_for('admin.income'))

# ============== EXPENSES ==============
@admin.route('/expenses')
@login_required
def expenses():
    """Expenses management page."""
    records = database.get_all_expenses()
    total = database.get_total_expenses()
    return render_template('admin/expenses.html', records=records, total=total)

@admin.route('/expenses/add', methods=['POST'])
@login_required
def add_expense():
    """Add new expense record."""
    date = request.form.get('date')
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    amount = parse_positive_float(request.form.get('amount'))
    
    if not valid_date(date):
        flash('Please provide a valid date.', 'error')
    elif not all([description, category]):
        flash('Description and category are required.', 'error')
    elif amount is None:
        flash('Amount must be a positive number.', 'error')
    else:
        database.add_expense(date, description, category, amount)
        flash('Expense record added successfully.', 'success')
    
    return redirect(url_for('admin.expenses'))

@admin.route('/expenses/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    """Delete expense record."""
    database.delete_expense(id)
    flash('Expense record deleted.', 'info')
    return redirect(url_for('admin.expenses'))

# ============== CUSTOMERS ==============
@admin.route('/customers')
@login_required
def customers():
    """Customers management page."""
    records = database.get_all_customers()
    total_pending = database.get_total_pending_balance()
    return render_template('admin/customers.html', records=records, total_pending=total_pending)

@admin.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    """Add new customer."""
    name = request.form.get('name', '').strip()
    service = request.form.get('service', '').strip()
    amount_paid = parse_non_negative_float(request.form.get('amount_paid', 0))
    total_amount = parse_positive_float(request.form.get('total_amount'))
    contact = request.form.get('contact', '').strip()
    
    if not all([name, service]):
        flash('Name and service are required.', 'error')
    elif total_amount is None:
        flash('Total amount must be a positive number.', 'error')
    elif amount_paid is None:
        flash('Amount paid cannot be negative.', 'error')
    elif amount_paid > total_amount:
        flash('Amount paid cannot exceed total amount.', 'error')
    else:
        database.add_customer(name, service, amount_paid, total_amount, contact)
        flash('Customer added successfully.', 'success')
    
    return redirect(url_for('admin.customers'))

@admin.route('/customers/delete/<int:id>', methods=['POST'])
@login_required
def delete_customer(id):
    """Delete customer."""
    database.delete_customer(id)
    flash('Customer deleted.', 'info')
    return redirect(url_for('admin.customers'))

# ============== INVOICES ==============
@admin.route('/invoices')
@login_required
def invoices():
    """Invoices management page."""
    records = database.get_all_invoices()
    customers_list = database.get_all_customers()
    next_invoice_number = database.generate_invoice_number()
    return render_template('admin/invoices.html', records=records, customers=customers_list, next_invoice_number=next_invoice_number)

@admin.route('/invoices/add', methods=['POST'])
@login_required
def add_invoice():
    """Create new invoice."""
    invoice_number = request.form.get('invoice_number', '').strip()
    customer_id = request.form.get('customer_id', type=int)
    date = request.form.get('date')
    amount = parse_positive_float(request.form.get('amount'))
    
    if not customer_id:
        flash('Please select a customer.', 'error')
    elif not database.get_customer(customer_id):
        flash('Selected customer does not exist.', 'error')
    elif not valid_date(date):
        flash('Please provide a valid invoice date.', 'error')
    elif amount is None:
        flash('Amount must be a positive number.', 'error')
    elif invoice_number and not re.match(r'^[A-Za-z0-9\-]+$', invoice_number):
        flash('Invoice number can only contain letters, numbers, and dashes.', 'error')
    else:
        try:
            database.add_invoice(invoice_number, customer_id, date, amount)
            flash('Invoice created successfully.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
        except RuntimeError:
            flash('Failed to generate a unique invoice number. Please try again.', 'error')
    
    return redirect(url_for('admin.invoices'))

@admin.route('/invoices/mark-paid/<int:id>', methods=['POST'])
@login_required
def mark_invoice_paid(id):
    """Mark invoice as paid."""
    database.update_invoice_status(id, 'paid')  # lowercase canonical status
    flash('Invoice marked as paid.', 'success')
    return redirect(url_for('admin.invoices'))

@admin.route('/invoices/delete/<int:id>', methods=['POST'])
@login_required
def delete_invoice(id):
    """Delete invoice."""
    database.delete_invoice(id)
    flash('Invoice deleted.', 'info')
    return redirect(url_for('admin.invoices'))

@admin.route('/assets')
@login_required
def assets():
    """Assets management page."""
    records = database.get_all_assets()
    total = database.get_total_asset_value()
    return render_template('admin/assets.html', records=records, total=total)

@admin.route('/assets/add', methods=['POST'])
@login_required
def add_asset():
    """Add new asset."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    value = parse_positive_float(request.form.get('value'))
    supplier = request.form.get('supplier', '').strip()
    
    if not all([name, category]):
        flash('Name and category are required.', 'error')
    elif value is None:
        flash('Value must be a positive number.', 'error')
    else:
        database.add_asset(name, category, value, supplier)
        flash('Asset added successfully.', 'success')
    
    return redirect(url_for('admin.assets'))

@admin.route('/assets/delete/<int:id>', methods=['POST'])
@login_required
def delete_asset(id):
    """Delete asset."""
    database.delete_asset(id)
    flash('Asset deleted.', 'info')
    return redirect(url_for('admin.assets'))

# ============== REPORTS ==============
@admin.route('/reports')
@login_required
def reports():
    """Reports page with date filtering."""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    if start_date and end_date:
        if not valid_date(start_date) or not valid_date(end_date):
            flash('Please provide valid start and end dates.', 'error')
            income_records = []
            expense_records = []
            total_income = 0
            total_expenses = 0
        elif start_date > end_date:
            flash('Start date cannot be after end date.', 'error')
            income_records = []
            expense_records = []
            total_income = 0
            total_expenses = 0
        else:
            income_records = database.get_income_by_date_range(start_date, end_date)
            expense_records = database.get_expenses_by_date_range(start_date, end_date)
            total_income = sum(r['amount'] for r in income_records)
            total_expenses = sum(r['amount'] for r in expense_records)
    else:
        income_records = []
        expense_records = []
        total_income = 0
        total_expenses = 0
    
    net_profit = total_income - total_expenses
    
    return render_template('admin/reports.html',
                         income_records=income_records,
                         expense_records=expense_records,
                         total_income=total_income,
                         total_expenses=total_expenses,
                         net_profit=net_profit,
                         start_date=start_date,
                         end_date=end_date)

# ============== GALLERY MANAGER ==============
@admin.route('/gallery')
@login_required
def gallery_manager():
    """Gallery management page."""
    images = database.get_all_gallery_images()
    albums = list(config.ALBUM_FOLDERS.keys())
    return render_template('admin/gallery_manager.html', images=images, albums=albums)

@admin.route('/gallery/upload', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def upload_image():
    """Upload new image to gallery."""
    if 'image' not in request.files:
        flash('No image file provided.', 'error')
        return redirect(url_for('admin.gallery_manager'))
    
    file = request.files['image']
    album = request.form.get('album', 'other')
    caption = request.form.get('caption', '').strip()
    
    if album not in config.ALBUM_FOLDERS:
        flash('Invalid album selected.', 'error')
        return redirect(url_for('admin.gallery_manager'))

    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin.gallery_manager'))
    
    if file and allowed_file(file.filename):
        original_name = secure_filename(file.filename)
        extension = original_name.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{extension}"
        
        album_folder = config.ALBUM_FOLDERS.get(album, 'other')
        upload_path = os.path.join(config.UPLOAD_FOLDER, album_folder)
        
        # Ensure directory exists
        os.makedirs(upload_path, exist_ok=True)
        
        file.save(os.path.join(upload_path, filename))
        database.add_gallery_image(filename, album, caption)
        flash('Image uploaded successfully.', 'success')
    else:
        flash('Invalid file type. Allowed: png, jpg, jpeg, gif, webp', 'error')
    
    return redirect(url_for('admin.gallery_manager'))

@admin.route('/gallery/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_image(id):
    """Toggle image publish status."""
    database.toggle_gallery_publish(id)
    flash('Image status updated.', 'success')
    return redirect(url_for('admin.gallery_manager'))

@admin.route('/gallery/delete/<int:id>', methods=['POST'])
@login_required
def delete_image(id):
    """Soft-delete image from gallery (DB only — file kept for restore)."""
    database.delete_gallery_image(id)
    # File is intentionally NOT removed from disk so that restore_gallery_image()
    # can bring the record back and the file is still accessible.
    flash('Image deleted.', 'info')
    return redirect(url_for('admin.gallery_manager'))

# ============== WEBSITE SETTINGS ==============
@admin.route('/settings')
@login_required
def website_settings():
    """Website settings page."""
    settings = database.get_website_settings()
    hero_images = database.get_all_hero_images()
    return render_template('admin/website_settings.html', settings=settings, hero_images=hero_images)

@admin.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update website settings."""
    site_name = request.form.get('site_name', '').strip()
    hero_text = request.form.get('hero_text', '').strip()
    hero_subtext = request.form.get('hero_subtext', '').strip()
    about_text = request.form.get('about_text', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()
    contact_email = request.form.get('contact_email', '').strip()
    address = request.form.get('address', '').strip()

    if not site_name:
        flash('Site name is required.', 'error')
        return redirect(url_for('admin.website_settings'))

    if contact_email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', contact_email):
        flash('Please provide a valid contact email address.', 'error')
        return redirect(url_for('admin.website_settings'))

    database.update_website_settings(site_name, hero_text, hero_subtext, about_text, contact_phone, contact_email, address)
    flash('Website settings updated successfully.', 'success')
    
    return redirect(url_for('admin.website_settings'))

@admin.route('/settings/hero-image/upload', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def upload_hero_image():
    """Upload a new hero slider image."""
    if 'hero_image' not in request.files:
        flash('No image file provided.', 'error')
        return redirect(url_for('admin.website_settings'))

    file = request.files['hero_image']
    display_order = parse_non_negative_int(request.form.get('display_order', 0)) or 0

    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin.website_settings'))

    if file and allowed_file(file.filename):
        original_name = secure_filename(file.filename)
        extension = original_name.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{extension}"

        hero_folder = os.path.join(config.UPLOAD_FOLDER, 'hero')
        os.makedirs(hero_folder, exist_ok=True)

        file.save(os.path.join(hero_folder, filename))
        database.add_hero_image(filename, display_order)
        flash('Hero image uploaded successfully.', 'success')
    else:
        flash('Invalid file type. Allowed: png, jpg, jpeg, gif, webp', 'error')

    return redirect(url_for('admin.website_settings'))

@admin.route('/settings/hero-image/delete/<int:id>', methods=['POST'])
@login_required
def delete_hero_image(id):
    """Delete a hero slider image."""
    image = database.delete_hero_image(id)
    if image:
        file_path = os.path.join(config.UPLOAD_FOLDER, 'hero', image['filename'])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                flash('Image record deleted, but file could not be removed from disk.', 'warning')
    flash('Hero image deleted.', 'info')
    return redirect(url_for('admin.website_settings'))

# ============== CLIENT MESSAGES ==============
@admin.route('/messages')
@login_required
def messages():
    """View all client messages/inquiries."""
    all_messages = database.get_all_messages()
    unread_count = database.get_unread_messages_count()
    return render_template('admin/messages.html', messages=all_messages, unread_count=unread_count)

@admin.route('/messages/read/<int:id>', methods=['POST'])
@login_required
def mark_message_read(id):
    """Mark a message as read."""
    database.mark_message_read(id)
    flash('Message marked as read.', 'success')
    return redirect(url_for('admin.messages'))

@admin.route('/messages/delete/<int:id>', methods=['POST'])
@login_required
def delete_message(id):
    """Delete a message."""
    database.delete_message(id)
    flash('Message deleted.', 'info')
    return redirect(url_for('admin.messages'))


# ============== PRICING PACKAGES ==============
@admin.route('/pricing')
@login_required
def pricing():
    """Manage pricing packages."""
    packages = database.get_all_pricing_packages()
    return render_template('admin/pricing.html', packages=packages)

@admin.route('/pricing/add', methods=['GET', 'POST'])
@login_required
def add_pricing():
    """Add a new pricing package."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = parse_positive_float(request.form.get('price'))
        price_label = request.form.get('price_label', '/session')
        icon = request.form.get('icon', 'fa-camera')
        features = request.form.get('features', '')
        is_featured = 1 if request.form.get('is_featured') else 0
        display_order = parse_non_negative_int(request.form.get('display_order', 0))

        if not name:
            flash('Package name is required.', 'error')
        elif price is None:
            flash('Price must be a positive number.', 'error')
        elif display_order is None:
            flash('Display order must be a non-negative number.', 'error')
        elif not re.match(r'^fa-[a-z0-9-]+$', icon):
            flash('Icon must be a valid Font Awesome class (example: fa-camera).', 'error')
        else:
            cleaned_features = [item.strip() for item in features.split('|') if item.strip()]
            database.add_pricing_package(
                name,
                description,
                int(price),
                price_label,
                icon,
                '|'.join(cleaned_features),
                is_featured,
                display_order
            )
            flash('Pricing package added successfully!', 'success')
            return redirect(url_for('admin.pricing'))
    
    return render_template('admin/pricing_form.html', package=None)

@admin.route('/pricing/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_pricing(id):
    """Edit an existing pricing package."""
    package = database.get_pricing_package(id)
    if not package:
        abort(404)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = parse_positive_float(request.form.get('price'))
        price_label = request.form.get('price_label', '/session')
        icon = request.form.get('icon', 'fa-camera')
        features = request.form.get('features', '')
        is_featured = 1 if request.form.get('is_featured') else 0
        display_order = parse_non_negative_int(request.form.get('display_order', 0))

        if not name:
            flash('Package name is required.', 'error')
        elif price is None:
            flash('Price must be a positive number.', 'error')
        elif display_order is None:
            flash('Display order must be a non-negative number.', 'error')
        elif not re.match(r'^fa-[a-z0-9-]+$', icon):
            flash('Icon must be a valid Font Awesome class (example: fa-camera).', 'error')
        else:
            cleaned_features = [item.strip() for item in features.split('|') if item.strip()]
            database.update_pricing_package(
                id,
                name,
                description,
                int(price),
                price_label,
                icon,
                '|'.join(cleaned_features),
                is_featured,
                display_order
            )
            flash('Pricing package updated successfully!', 'success')
            return redirect(url_for('admin.pricing'))
    
    return render_template('admin/pricing_form.html', package=package)

@admin.route('/pricing/delete/<int:id>', methods=['POST'])
@login_required
def delete_pricing(id):
    """Delete a pricing package."""
    database.delete_pricing_package(id)
    flash('Pricing package deleted.', 'info')
    return redirect(url_for('admin.pricing'))

@admin.route('/pricing/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_pricing(id):
    """Toggle active status of a pricing package."""
    database.toggle_pricing_package(id)
    flash('Package status updated.', 'success')
    return redirect(url_for('admin.pricing'))
