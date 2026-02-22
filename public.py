"""
Public website module for Benjo Moments Photography System.
Handles all public-facing pages.
"""
import os
import re
from flask import Blueprint, abort, render_template, request, flash, redirect, send_from_directory, url_for
from werkzeug.utils import secure_filename
import config
import database
from extensions import limiter

public = Blueprint('public', __name__)

def valid_email(value):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value))

@public.route('/')
def index():
    """Homepage."""
    settings = database.get_website_settings()
    # Get all published gallery images for Featured Work section
    gallery_images = database.get_published_gallery_images()
    # Get active pricing packages
    pricing_packages = database.get_active_pricing_packages()
    hero_images = database.get_all_hero_images()
    return render_template('public/index.html', settings=settings, gallery_images=gallery_images, pricing_packages=pricing_packages, hero_images=hero_images)

@public.route('/gallery')
def gallery():
    """Gallery page with album filtering."""
    album = request.args.get('album', None)
    settings = database.get_website_settings()
    albums = list(config.ALBUM_FOLDERS.keys())
    
    if album and album not in albums:
        abort(404)

    if album:
        images = database.get_published_gallery_images(album)
    else:
        images = database.get_published_gallery_images()
    
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
    gallery_images = database.get_published_gallery_images()
    return render_template('public/about.html', settings=settings, gallery_images=gallery_images)

@public.route('/contact', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def contact():
    """Contact page with form."""
    settings = database.get_website_settings()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        service = request.form.get('service', '').strip()
        message = request.form.get('message', '').strip()
        
        if not all([name, email, message]):
            flash('Please fill in all required fields.', 'error')
        elif not valid_email(email):
            flash('Please provide a valid email address.', 'error')
        else:
            # Save message to database for manager to see
            database.add_contact_message(name, email, phone, service, message)
            flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('public.contact'))
    
    return render_template('public/contact.html', settings=settings)

@public.route('/submit-contact', methods=['POST'])
@limiter.limit("5 per minute")
def submit_contact():
    """Handle contact form submission from homepage."""
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    service = request.form.get('service', '').strip()
    message = request.form.get('message', '').strip()
    
    if not all([name, email, message]):
        flash('Please fill in all required fields.', 'error')
    elif not valid_email(email):
        flash('Please provide a valid email address.', 'error')
    else:
        # Save message to database for manager to see
        database.add_contact_message(name, email, phone, service, message)
        flash('Thank you for your message! We will get back to you soon.', 'success')
    
    return redirect(url_for('public.index') + '#contact')

@public.route('/uploads/<album>/<path:filename>')
def uploaded_file(album, filename):
    """Serve uploaded files from configured storage path."""
    if album not in config.ALBUM_FOLDERS:
        abort(404)

    safe_name = secure_filename(filename)
    if safe_name != filename:
        abort(404)

    album_folder = config.ALBUM_FOLDERS[album]
    target_dir = os.path.join(config.UPLOAD_FOLDER, album_folder)
    return send_from_directory(target_dir, safe_name)

@public.route('/uploads/hero/<path:filename>')
def hero_image_file(filename):
    """Serve hero slider images."""
    safe_name = secure_filename(filename)
    if safe_name != filename:
        abort(404)
    target_dir = os.path.join(config.UPLOAD_FOLDER, 'hero')
    return send_from_directory(target_dir, safe_name)

