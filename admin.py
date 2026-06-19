"""
Admin module for Benjo Moments Photography System.
Handles all admin dashboard functionality.
"""
import os
import re
import uuid
import math
from datetime import datetime
from flask import Blueprint, abort, render_template, request, redirect, session, url_for, flash
from auth import login_required
import database
import config
from extensions import limiter
from uploads import InvalidImageError, save_image, validate_image

admin = Blueprint('admin', __name__, url_prefix='/admin')


@admin.before_request
def require_admin_role():
    if "user_id" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("auth.login"))
    if session.get("user_role") != "admin":
        abort(403)


def parse_positive_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None

def parse_non_negative_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None

def parse_non_negative_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 2_147_483_647 else None

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
    outstanding_expenses = database.get_outstanding_expenses_total()
    net_profit = total_income - total_expenses
    total_pending = database.get_total_pending_balance()
    total_assets = database.get_total_asset_value()
    recent_transactions = database.get_recent_transactions(10)
    
    return render_template('admin/dashboard.html',
                         total_income=total_income,
                         total_expenses=total_expenses,
                         outstanding_expenses=outstanding_expenses,
                         net_profit=net_profit,
                         total_pending=total_pending,
                         total_assets=total_assets,
                         recent_transactions=recent_transactions)


@admin.route('/guide')
@login_required
def manager_guide():
    """General operating guide for the manager portal."""
    from admin_guides import SYSTEM_WORKFLOWS
    return render_template('admin/manager_guide.html', workflows=SYSTEM_WORKFLOWS)

# ============== INCOME ==============
@admin.route('/income')
@login_required
def income():
    """Income management page."""
    records = database.get_all_income()
    total = database.get_total_income()
    return render_template(
        'admin/income.html', records=records, total=total,
        service_catalogue=database.get_service_catalogue(),
    )

@admin.route('/income/add', methods=['POST'])
@login_required
def add_income():
    """Add new income record."""
    date = request.form.get('date')
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()[:100]
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

@admin.route('/income/edit/<int:id>', methods=['POST'])
@login_required
def edit_income(id):
    """Edit income record."""
    date = request.form.get('date')
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()[:100]
    amount = parse_positive_float(request.form.get('amount'))

    if not valid_date(date):
        flash('Please provide a valid date.', 'error')
    elif not all([description, category]):
        flash('Description and category are required.', 'error')
    elif amount is None:
        flash('Amount must be a positive number.', 'error')
    else:
        try:
            database.update_income(id, date, description, category, amount)
            flash('Income record updated successfully.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')

    return redirect(url_for('admin.income'))

@admin.route('/income/delete/<int:id>', methods=['POST'])
@login_required
def delete_income(id):
    """Delete income record."""
    try:
        database.delete_income(id)
        flash('Income record deleted.', 'info')
    except ValueError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('admin.income'))

# ============== EXPENSES ==============
@admin.route('/expenses')
@login_required
def expenses():
    """Expenses management page."""
    records = database.get_all_expenses()
    total = database.get_total_expenses()
    outstanding = database.get_outstanding_expenses_total()
    assets = database.get_all_assets()
    return render_template(
        'admin/expenses.html', records=records, total=total,
        outstanding=outstanding, assets=assets,
    )

@admin.route('/expenses/add', methods=['POST'])
@login_required
def add_expense():
    """Add new expense record."""
    date = request.form.get('date')
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()[:100]
    amount = parse_positive_float(request.form.get('amount'))
    asset_id = request.form.get('asset_id', type=int)
    payment_status = request.form.get('payment_status', 'paid')
    payee = request.form.get('payee', '').strip()[:255]
    due_date = request.form.get('due_date') or None
    paid_date = request.form.get('paid_date') or None
    
    if not valid_date(date):
        flash('Please provide a valid date.', 'error')
    elif not all([description, category]):
        flash('Description and category are required.', 'error')
    elif amount is None:
        flash('Amount must be a positive number.', 'error')
    else:
        try:
            database.add_expense(
                date, description, category, amount, asset_id, payment_status,
                payee, due_date, paid_date,
            )
            flash('Expense record added successfully.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
    
    return redirect(url_for('admin.expenses'))

@admin.route('/expenses/edit/<int:id>', methods=['POST'])
@login_required
def edit_expense(id):
    """Edit expense record."""
    date = request.form.get('date')
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()[:100]
    amount = parse_positive_float(request.form.get('amount'))
    asset_id = request.form.get('asset_id', type=int)
    payment_status = request.form.get('payment_status', 'paid')
    payee = request.form.get('payee', '').strip()[:255]
    due_date = request.form.get('due_date') or None
    paid_date = request.form.get('paid_date') or None

    if not valid_date(date):
        flash('Please provide a valid date.', 'error')
    elif not all([description, category]):
        flash('Description and category are required.', 'error')
    elif amount is None:
        flash('Amount must be a positive number.', 'error')
    else:
        try:
            database.update_expense(
                id, date, description, category, amount, asset_id,
                payment_status, payee, due_date, paid_date,
            )
            flash('Expense record updated successfully.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')

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
    return render_template(
        'admin/customers.html', records=records, total_pending=total_pending,
        service_catalogue=database.get_service_catalogue(),
    )

@admin.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    """Add new customer."""
    name = request.form.get('name', '').strip()[:255]
    service = request.form.get('service', '').strip()[:255]
    amount_paid = parse_non_negative_float(request.form.get('amount_paid', 0))
    total_amount = parse_positive_float(request.form.get('total_amount'))
    contact = request.form.get('contact', '').strip()[:255]
    location = request.form.get('location', '').strip()[:500]
    
    if not all([name, service]):
        flash('Name and service are required.', 'error')
    elif total_amount is None:
        flash('Total amount must be a positive number.', 'error')
    elif amount_paid is None:
        flash('Amount paid cannot be negative.', 'error')
    elif amount_paid > total_amount:
        flash('Amount paid cannot exceed total amount.', 'error')
    else:
        database.add_customer(name, service, amount_paid, total_amount, contact, location)
        flash('Customer added successfully.', 'success')
    
    return redirect(url_for('admin.customers'))

@admin.route('/customers/edit/<int:id>', methods=['POST'])
@login_required
def edit_customer(id):
    """Edit customer."""
    name = request.form.get('name', '').strip()[:255]
    service = request.form.get('service', '').strip()[:255]
    amount_paid = parse_non_negative_float(request.form.get('amount_paid', 0))
    total_amount = parse_positive_float(request.form.get('total_amount'))
    contact = request.form.get('contact', '').strip()[:255]
    location = request.form.get('location', '').strip()[:500]

    if not all([name, service]):
        flash('Name and service are required.', 'error')
    elif total_amount is None:
        flash('Total amount must be a positive number.', 'error')
    elif amount_paid is None:
        flash('Amount paid cannot be negative.', 'error')
    elif amount_paid > total_amount:
        flash('Amount paid cannot exceed total amount.', 'error')
    else:
        try:
            database.update_customer(id, name, service, amount_paid, total_amount, contact, location)
            flash('Customer updated successfully.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')

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
    elif len(invoice_number) > 50:
        flash('Invoice number must be 50 characters or fewer.', 'error')
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
    try:
        settled = database.mark_invoice_paid(id)
        if settled:
            flash('Invoice marked as paid and recorded as income.', 'success')
        else:
            flash('Invoice was already paid.', 'info')
    except ValueError as exc:
        flash(str(exc), 'error')
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
    name = request.form.get('name', '').strip()[:255]
    category = request.form.get('category', '').strip()[:100]
    value = parse_positive_float(request.form.get('value'))
    supplier = request.form.get('supplier', '').strip()[:255]
    
    if not all([name, category]):
        flash('Name and category are required.', 'error')
    elif value is None:
        flash('Value must be a positive number.', 'error')
    else:
        database.add_asset(name, category, value, supplier)
        flash('Asset added successfully.', 'success')
    
    return redirect(url_for('admin.assets'))

@admin.route('/assets/edit/<int:id>', methods=['POST'])
@login_required
def edit_asset(id):
    """Edit asset."""
    name = request.form.get('name', '').strip()[:255]
    category = request.form.get('category', '').strip()[:100]
    value = parse_positive_float(request.form.get('value'))
    supplier = request.form.get('supplier', '').strip()[:255]

    if not all([name, category]):
        flash('Name and category are required.', 'error')
    elif value is None:
        flash('Value must be a positive number.', 'error')
    else:
        database.update_asset(id, name, category, value, supplier)
        flash('Asset updated successfully.', 'success')

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
    """Upload one or more images to gallery (batch upload up to 10)."""
    files = request.files.getlist('image')
    album = request.form.get('album', 'other')
    caption = request.form.get('caption', '').strip()[:1000]

    if not files or all(f.filename == '' for f in files):
        flash('No image files selected.', 'error')
        return redirect(url_for('admin.gallery_manager'))

    if album not in config.ALBUM_FOLDERS:
        flash('Invalid album selected.', 'error')
        return redirect(url_for('admin.gallery_manager'))

    album_folder = config.ALBUM_FOLDERS.get(album, 'other')
    upload_path = os.path.join(config.UPLOAD_FOLDER, album_folder)
    os.makedirs(upload_path, exist_ok=True)

    uploaded = 0
    errors = []
    if len(files) > 10:
        errors.append("Only the first 10 files were processed.")

    for file in files[:10]:  # Hard limit: max 10 per request
        if file.filename == '':
            continue
        try:
            extension = validate_image(file)
            filename = f"{uuid.uuid4().hex}.{extension}"
            save_image(file, upload_path, filename)
            try:
                database.add_gallery_image(filename, album, caption)
            except Exception:
                os.remove(os.path.join(upload_path, filename))
                raise
            uploaded += 1
        except InvalidImageError as exc:
            errors.append(f"{file.filename}: {exc}")

    if uploaded:
        flash(f'{uploaded} image{"s" if uploaded > 1 else ""} uploaded successfully.', 'success')
    for error in errors:
        flash(error, 'warning')

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
    """Delete an image record and its file."""
    image = database.delete_gallery_image(id)
    if image:
        file_path = os.path.join(
            config.UPLOAD_FOLDER,
            config.ALBUM_FOLDERS[image['album']],
            image['filename'],
        )
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            flash('Image record deleted, but the file could not be removed.', 'warning')
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
    site_name = request.form.get('site_name', '').strip()[:255]
    hero_text = request.form.get('hero_text', '').strip()
    hero_subtext = request.form.get('hero_subtext', '').strip()
    about_text = request.form.get('about_text', '').strip()
    contact_phone = request.form.get('contact_phone', '').strip()[:100]
    contact_email = request.form.get('contact_email', '').strip().lower()[:255]
    address = request.form.get('address', '').strip()
    facebook_url = request.form.get('facebook_url', '').strip()
    instagram_url = request.form.get('instagram_url', '').strip()
    youtube_url = request.form.get('youtube_url', '').strip()
    tiktok_url = request.form.get('tiktok_url', '').strip()
    whatsapp_number = re.sub(r'\D', '', request.form.get('whatsapp_number', ''))

    if not site_name:
        flash('Site name is required.', 'error')
        return redirect(url_for('admin.website_settings'))

    if contact_email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', contact_email):
        flash('Please provide a valid contact email address.', 'error')
        return redirect(url_for('admin.website_settings'))

    social_urls = [facebook_url, instagram_url, youtube_url, tiktok_url]
    if any(value and not value.startswith('https://') for value in social_urls):
        flash('Social media links must start with https://.', 'error')
        return redirect(url_for('admin.website_settings'))
    if whatsapp_number and not 8 <= len(whatsapp_number) <= 15:
        flash('WhatsApp number must contain 8 to 15 digits, including country code.', 'error')
        return redirect(url_for('admin.website_settings'))

    database.update_website_settings(
        site_name,
        hero_text,
        hero_subtext,
        about_text,
        contact_phone,
        contact_email,
        address,
        facebook_url,
        instagram_url,
        youtube_url,
        tiktok_url,
        whatsapp_number,
    )
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
    display_order = parse_non_negative_int(request.form.get('display_order', 0))
    if display_order is None:
        flash('Display order must be a non-negative whole number.', 'error')
        return redirect(url_for('admin.website_settings'))

    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin.website_settings'))

    try:
        extension = validate_image(file)
        filename = f"{uuid.uuid4().hex}.{extension}"

        hero_folder = os.path.join(config.UPLOAD_FOLDER, 'hero')
        save_image(file, hero_folder, filename)
        try:
            database.add_hero_image(filename, display_order)
        except Exception:
            os.remove(os.path.join(hero_folder, filename))
            raise
        flash('Hero image uploaded successfully.', 'success')
    except InvalidImageError as exc:
        flash(str(exc), 'error')

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
        name = request.form.get('name', '').strip()[:255]
        description = request.form.get('description', '').strip()
        price = parse_positive_float(request.form.get('price'))
        price_label = request.form.get('price_label', '/session').strip()[:50]
        icon = request.form.get('icon', 'fa-camera').strip()[:100]
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
        name = request.form.get('name', '').strip()[:255]
        description = request.form.get('description', '').strip()
        price = parse_positive_float(request.form.get('price'))
        price_label = request.form.get('price_label', '/session').strip()[:50]
        icon = request.form.get('icon', 'fa-camera').strip()[:100]
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
