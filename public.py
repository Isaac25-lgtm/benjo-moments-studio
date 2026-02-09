"""
Public website module for Benjo Moments Photography System.
Handles all public-facing pages.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
import database

public = Blueprint('public', __name__)

@public.route('/')
def index():
    """Homepage."""
    settings = database.get_website_settings()
    # Get all published gallery images for Featured Work section
    gallery_images = database.get_published_gallery_images()
    # Get active pricing packages
    pricing_packages = database.get_active_pricing_packages()
    return render_template('public/index.html', settings=settings, gallery_images=gallery_images, pricing_packages=pricing_packages)

@public.route('/gallery')
def gallery():
    """Gallery page with album filtering."""
    album = request.args.get('album', None)
    settings = database.get_website_settings()
    
    if album:
        images = database.get_published_gallery_images(album)
    else:
        images = database.get_published_gallery_images()
    
    albums = ['weddings', 'kukyala', 'birthdays', 'baby', 'other']
    return render_template('public/gallery.html', settings=settings, images=images, albums=albums, current_album=album)

@public.route('/services')
def services():
    """Services page."""
    settings = database.get_website_settings()
    return render_template('public/services.html', settings=settings)

@public.route('/about')
def about():
    """About page."""
    settings = database.get_website_settings()
    return render_template('public/about.html', settings=settings)

@public.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page with form."""
    settings = database.get_website_settings()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        service = request.form.get('service', '').strip()
        message = request.form.get('message', '').strip()
        
        if all([name, email, message]):
            # Save message to database for manager to see
            database.add_contact_message(name, email, phone, service, message)
            flash('Thank you for your message! We will get back to you soon.', 'success')
        else:
            flash('Please fill in all required fields.', 'error')
    
    return render_template('public/contact.html', settings=settings)

@public.route('/submit-contact', methods=['POST'])
def submit_contact():
    """Handle contact form submission from homepage."""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    service = request.form.get('service', '').strip()
    message = request.form.get('message', '').strip()
    
    if all([name, email, message]):
        # Save message to database for manager to see
        database.add_contact_message(name, email, phone, service, message)
        flash('Thank you for your message! We will get back to you soon.', 'success')
    else:
        flash('Please fill in all required fields.', 'error')
    
    return redirect(url_for('public.index') + '#contact')

