"""Administrative workflows for users, services, and private client delivery."""

import os
import re
import secrets
import shutil
import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

import config
import database
from auth import login_required
from extensions import limiter
from uploads import InvalidImageError, save_image, validate_image


admin_extended = Blueprint("admin_extended", __name__, url_prefix="/admin")


@admin_extended.before_request
@login_required
def require_admin():
    if session.get("user_role") != "admin":
        abort(403)


def _boolean_field(name: str) -> bool:
    return request.form.get(name) == "on"


def _non_negative_int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _new_pin() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


@admin_extended.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        try:
            database.create_user(
                request.form.get("name", ""),
                request.form.get("email", ""),
                request.form.get("password", ""),
            )
            flash("Administrator account created.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin_extended.users"))
    return render_template("admin/users.html", users=database.get_all_users())


@admin_extended.route("/users/<int:user_id>/update", methods=["POST"])
def update_user(user_id):
    try:
        database.update_user(
            user_id,
            request.form.get("name", ""),
            request.form.get("email", ""),
            _boolean_field("is_active"),
            request.form.get("password", ""),
        )
        flash("Administrator account updated.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.users"))


@admin_extended.route("/services")
def services():
    return render_template(
        "admin/services.html",
        service_catalogue=database.get_service_catalogue(active_only=False),
    )


@admin_extended.route("/services/categories/add", methods=["POST"])
def add_service_category():
    try:
        database.add_service_category(
            request.form.get("name", ""),
            request.form.get("description", ""),
            request.form.get("icon", ""),
            request.form.get("image_url", ""),
            _non_negative_int(request.form.get("display_order")),
        )
        flash("Service category added.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.services"))


@admin_extended.route("/services/categories/<int:category_id>/update", methods=["POST"])
def update_service_category(category_id):
    try:
        database.update_service_category(
            category_id,
            request.form.get("name", ""),
            request.form.get("description", ""),
            request.form.get("icon", ""),
            request.form.get("image_url", ""),
            _non_negative_int(request.form.get("display_order")),
            _boolean_field("is_active"),
        )
        flash("Service category updated.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.services"))


@admin_extended.route("/services/categories/<int:category_id>/delete", methods=["POST"])
def delete_service_category(category_id):
    database.delete_service_category(category_id)
    flash("Service category and its services deleted.", "info")
    return redirect(url_for("admin_extended.services"))


@admin_extended.route("/services/items/add", methods=["POST"])
def add_service_item():
    try:
        database.add_professional_service(
            request.form.get("category_id", type=int),
            request.form.get("name", ""),
            request.form.get("description", ""),
            request.form.get("icon", ""),
            _non_negative_int(request.form.get("display_order")),
        )
        flash("Professional service added.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.services"))


@admin_extended.route("/services/items/<int:service_id>/update", methods=["POST"])
def update_service_item(service_id):
    try:
        database.update_professional_service(
            service_id,
            request.form.get("category_id", type=int),
            request.form.get("name", ""),
            request.form.get("description", ""),
            request.form.get("icon", ""),
            _non_negative_int(request.form.get("display_order")),
            _boolean_field("is_active"),
        )
        flash("Professional service updated.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.services"))


@admin_extended.route("/services/items/<int:service_id>/delete", methods=["POST"])
def delete_service_item(service_id):
    database.delete_professional_service(service_id)
    flash("Professional service deleted.", "info")
    return redirect(url_for("admin_extended.services"))


@admin_extended.route("/client-collections", methods=["GET", "POST"])
def client_collections():
    if request.method == "POST":
        pin = request.form.get("pin", "").strip() or _new_pin()
        code = request.form.get("collection_code", "").strip().upper()
        if code and not re.fullmatch(r"[A-Z0-9-]{3,80}", code):
            flash("Collection code may only contain letters, numbers, and dashes.", "error")
            return redirect(url_for("admin_extended.client_collections"))
        try:
            collection = database.add_client_collection(
                request.form.get("title", ""),
                request.form.get("client_name", ""),
                request.form.get("client_email", ""),
                request.form.get("description", ""),
                request.form.get("location", ""),
                request.form.get("event_date") or None,
                request.form.get("expires_at") or None,
                pin,
                code or None,
                session.get("user_id"),
            )
            flash(
                f"Collection created. Code: {collection['collection_code']} | PIN: {pin}. "
                "Copy this PIN now; it is stored securely and cannot be displayed again.",
                "success",
            )
            return redirect(url_for("admin_extended.client_collection_detail", collection_id=collection["id"]))
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin_extended.client_collections"))
    search = request.args.get("q", "").strip()[:100]
    status = request.args.get("status", "all")
    if status not in {"all", "active", "locked", "expired"}:
        status = "all"
    return render_template(
        "admin/client_collections.html",
        collections=database.get_all_client_collections(search=search, status=status),
        search=search,
        status=status,
    )


@admin_extended.route("/client-collections/<int:collection_id>")
def client_collection_detail(collection_id):
    collection = database.get_client_collection(collection_id)
    if not collection:
        abort(404)
    return render_template(
        "admin/client_collection_detail.html",
        collection=collection,
        activity=database.get_collection_activity(collection_id),
    )


@admin_extended.route("/client-collections/<int:collection_id>/update", methods=["POST"])
def update_client_collection(collection_id):
    try:
        database.update_client_collection(
            collection_id,
            request.form.get("title", ""),
            request.form.get("client_name", ""),
            request.form.get("client_email", ""),
            request.form.get("description", ""),
            request.form.get("location", ""),
            request.form.get("event_date") or None,
            request.form.get("expires_at") or None,
            _boolean_field("is_active"),
        )
        flash("Client collection updated.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.client_collection_detail", collection_id=collection_id))


@admin_extended.route("/client-collections/<int:collection_id>/reset-pin", methods=["POST"])
def reset_collection_pin(collection_id):
    pin = request.form.get("pin", "").strip() or _new_pin()
    try:
        database.reset_client_collection_pin(collection_id, pin)
        flash(f"PIN reset to {pin}. Copy it now; it cannot be displayed again.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.client_collection_detail", collection_id=collection_id))


@admin_extended.route("/client-collections/<int:collection_id>/upload", methods=["POST"])
@limiter.limit("10 per minute")
def upload_collection_images(collection_id):
    collection = database.get_client_collection(collection_id)
    if not collection:
        abort(404)
    files = request.files.getlist("images")
    if not files or all(not file.filename for file in files):
        flash("Select at least one image.", "error")
        return redirect(url_for("admin_extended.client_collection_detail", collection_id=collection_id))
    destination = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection_id))
    caption = request.form.get("caption", "").strip()[:1000]
    uploaded = 0
    if len(files) > 25:
        flash("Only the first 25 photos were processed. Upload the rest in another batch.", "warning")
    for file in files[:25]:
        if not file.filename:
            continue
        try:
            extension = validate_image(file)
            filename = f"{uuid.uuid4().hex}.{extension}"
            save_image(file, destination, filename)
            try:
                database.add_client_collection_image(
                    collection_id, filename, secure_filename(file.filename) or filename, caption, uploaded
                )
            except Exception:
                os.remove(os.path.join(destination, filename))
                raise
            uploaded += 1
        except InvalidImageError as exc:
            flash(f"{file.filename}: {exc}", "warning")
    flash(f"{uploaded} client photo{'s' if uploaded != 1 else ''} uploaded.", "success")
    return redirect(url_for("admin_extended.client_collection_detail", collection_id=collection_id))


@admin_extended.route(
    "/client-collections/<int:collection_id>/images/<int:image_id>/cover",
    methods=["POST"],
)
def set_collection_cover(collection_id, image_id):
    try:
        database.set_client_collection_cover(collection_id, image_id)
        flash("Collection cover updated.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin_extended.client_collection_detail", collection_id=collection_id))


@admin_extended.route("/client-collections/<int:collection_id>/images/<int:image_id>/delete", methods=["POST"])
def delete_collection_image(collection_id, image_id):
    existing = database.get_client_collection_image(image_id)
    if not existing or existing["collection_id"] != collection_id:
        abort(404)
    image = database.delete_client_collection_image(image_id)
    if image:
        path = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection_id), image["filename"])
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            flash("Photo record deleted, but its file could not be removed.", "warning")
    flash("Client photo deleted.", "info")
    return redirect(url_for("admin_extended.client_collection_detail", collection_id=collection_id))


@admin_extended.route("/client-collections/<int:collection_id>/delete", methods=["POST"])
def delete_collection(collection_id):
    collection = database.delete_client_collection(collection_id)
    if collection:
        directory = os.path.abspath(
            os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection_id))
        )
        root = os.path.abspath(os.path.join(config.UPLOAD_FOLDER, "client_collections"))
        if os.path.commonpath([root, directory]) == root:
            shutil.rmtree(directory, ignore_errors=True)
    flash("Client collection deleted.", "info")
    return redirect(url_for("admin_extended.client_collections"))
