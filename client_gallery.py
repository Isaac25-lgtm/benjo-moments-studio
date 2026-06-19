"""Protected client collection viewing and downloads."""

import os
import tempfile
import zipfile
from datetime import datetime

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, send_file,
    send_from_directory, session, url_for,
)
from werkzeug.utils import secure_filename

import config
import database
from extensions import limiter


client_gallery = Blueprint("client_gallery", __name__)


def _access_key(collection_id: int) -> str:
    return f"client_collection_{collection_id}"


def _authorized_collection(code: str):
    collection = database.get_client_collection_by_code(code, active_only=True)
    if not collection:
        abort(404)
    if collection.get("expires_at") and collection["expires_at"] < datetime.utcnow():
        abort(410)
    visitor_id = session.get(_access_key(collection["id"]))
    if not visitor_id:
        return collection, None
    return collection, int(visitor_id)


@client_gallery.route("/client-gallery")
def collection_search():
    settings = database.get_website_settings()
    code = request.args.get("code", "").strip().upper()[:80]
    if code:
        collection = database.get_client_collection_by_code(code, active_only=True)
        if collection:
            return redirect(url_for("client_gallery.collection_unlock", code=collection["collection_code"]))
        flash("No active collection matches that code.", "error")
    search = request.args.get("q", "").strip()[:100]
    return render_template(
        "public/client_gallery_search.html",
        settings=settings,
        code=code,
        search=search,
        collections=database.get_public_client_collections(search),
    )


@client_gallery.route("/client-gallery/<code>/cover")
def collection_cover(code):
    is_admin = session.get("user_role") == "admin" and session.get("user_id")
    collection = database.get_client_collection_by_code(code, active_only=not is_admin)
    if not collection:
        abort(404)
    if not is_admin and collection.get("expires_at") and collection["expires_at"] < datetime.utcnow():
        abort(404)
    image = database.get_collection_cover_image(collection["id"])
    if not image:
        abort(404)
    directory = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection["id"]))
    response = send_from_directory(directory, image["filename"], conditional=True, max_age=3600)
    response.headers["Cache-Control"] = "private, max-age=3600" if is_admin else "public, max-age=3600"
    return response


@client_gallery.route("/client-gallery/<code>", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def collection_unlock(code):
    settings = database.get_website_settings()
    collection = database.get_client_collection_by_code(code, active_only=True)
    if not collection:
        abort(404)
    if collection.get("expires_at") and collection["expires_at"] < datetime.utcnow():
        return render_template(
            "public/client_gallery_unlock.html",
            settings=settings,
            collection=collection,
            expired=True,
        ), 410
    if session.get(_access_key(collection["id"])):
        return redirect(url_for("client_gallery.collection_view", code=collection["collection_code"]))
    if request.method == "POST":
        try:
            unlocked = database.unlock_client_collection(
                collection["collection_code"],
                request.form.get("email", ""),
                request.form.get("name", ""),
                request.form.get("pin", ""),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            unlocked = None
        if unlocked:
            session[_access_key(collection["id"])] = unlocked["visitor_id"]
            session.permanent = True
            return redirect(url_for("client_gallery.collection_view", code=collection["collection_code"]))
        flash("The email or collection PIN was not accepted.", "error")
    return render_template(
        "public/client_gallery_unlock.html",
        settings=settings,
        collection=collection,
        expired=False,
    )


@client_gallery.route("/client-gallery/<code>/photos")
def collection_view(code):
    collection, visitor_id = _authorized_collection(code)
    if not visitor_id:
        return redirect(url_for("client_gallery.collection_unlock", code=collection["collection_code"]))
    search = request.args.get("q", "").strip()[:100]
    images = database.get_collection_images_for_visitor(collection["id"], search)
    comments = database.get_gallery_comments(collection["id"])
    comments_by_image = {}
    for comment in comments:
        comments_by_image.setdefault(comment["image_id"], []).append(comment)
    return render_template(
        "public/client_collection.html",
        settings=database.get_website_settings(),
        collection=collection,
        images=images,
        search=search,
        comments_by_image=comments_by_image,
    )


@client_gallery.route("/client-gallery/<code>/photo/<int:image_id>")
def collection_photo(code, image_id):
    if session.get("user_role") == "admin" and session.get("user_id"):
        collection = database.get_client_collection_by_code(code)
        if not collection:
            abort(404)
    else:
        collection, visitor_id = _authorized_collection(code)
        if not visitor_id:
            abort(403)
    image = database.get_client_collection_image(image_id)
    if not image or image["collection_id"] != collection["id"]:
        abort(404)
    directory = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection["id"]))
    response = send_from_directory(directory, image["filename"], conditional=True, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"
    return response


@client_gallery.route("/client-gallery/<code>/download/<int:image_id>")
def download_photo(code, image_id):
    collection, visitor_id = _authorized_collection(code)
    if not visitor_id:
        abort(403)
    image = database.get_client_collection_image(image_id)
    if not image or image["collection_id"] != collection["id"]:
        abort(404)
    database.add_gallery_download(collection["id"], visitor_id, image_id, "image")
    directory = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection["id"]))
    response = send_from_directory(
        directory,
        image["filename"],
        as_attachment=True,
        download_name=image["original_name"],
        conditional=True,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Vary"] = "Cookie"
    return response


@client_gallery.route("/client-gallery/<code>/download-all")
@limiter.limit("5 per hour")
def download_all(code):
    collection, visitor_id = _authorized_collection(code)
    if not visitor_id:
        abort(403)
    images = database.get_collection_images_for_visitor(collection["id"])
    if not images:
        abort(404)
    source = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection["id"]))
    temporary = tempfile.NamedTemporaryFile(prefix="benjo-gallery-", suffix=".zip", delete=False)
    temporary.close()
    try:
        with zipfile.ZipFile(temporary.name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            used_names = set()
            for index, image in enumerate(images, 1):
                path = os.path.join(source, image["filename"])
                if not os.path.isfile(path):
                    continue
                archive_name = secure_filename(image["original_name"]) or f"photo-{index}.jpg"
                if archive_name in used_names:
                    stem, extension = os.path.splitext(archive_name)
                    archive_name = f"{stem}-{index}{extension}"
                used_names.add(archive_name)
                archive.write(path, archive_name)
        database.add_gallery_download(collection["id"], visitor_id, None, "all")
        response = send_file(
            temporary.name,
            as_attachment=True,
            download_name=f"{collection['collection_code']}-photos.zip",
            mimetype="application/zip",
        )
        response.call_on_close(lambda: os.path.exists(temporary.name) and os.remove(temporary.name))
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Vary"] = "Cookie"
        return response
    except Exception:
        if os.path.exists(temporary.name):
            os.remove(temporary.name)
        raise


@client_gallery.route("/client-gallery/<code>/photo/<int:image_id>/comment", methods=["POST"])
@limiter.limit("20 per hour")
def comment_on_photo(code, image_id):
    collection, visitor_id = _authorized_collection(code)
    if not visitor_id:
        abort(403)
    try:
        database.add_gallery_comment(image_id, visitor_id, request.form.get("comment", ""))
        flash("Your comment was added.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("client_gallery.collection_view", code=collection["collection_code"]) + f"#photo-{image_id}")


@client_gallery.route("/client-gallery/<code>/lock", methods=["POST"])
def lock_collection(code):
    collection = database.get_client_collection_by_code(code)
    if collection:
        session.pop(_access_key(collection["id"]), None)
    return redirect(url_for("client_gallery.collection_unlock", code=code))
