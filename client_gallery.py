"""Protected client collection viewing and downloads."""

import os
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, send_file,
    send_from_directory, session, url_for,
)
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps

import config
import database
from extensions import limiter


client_gallery = Blueprint("client_gallery", __name__)

DOWNLOAD_QUALITIES = {
    "original": {"label": "Original", "max_edge": None, "jpeg_quality": None},
    "high": {"label": "High Resolution", "max_edge": 3000, "jpeg_quality": 92},
    "web": {"label": "Web / Social", "max_edge": 1600, "jpeg_quality": 84},
}


def _access_key(collection_id: int) -> str:
    return f"client_collection_{collection_id}"


def _is_admin_session() -> bool:
    user_id = session.get("user_id")
    if not user_id or session.get("user_role") != "admin":
        return False
    if config.TEST_AUTH_MODE:
        return True
    user = database.get_user_by_id(user_id)
    return bool(
        user
        and user.get("is_active")
        and user.get("role") == "admin"
        and session.get("auth_version") == user.get("auth_version")
    )


def _is_manager_client_test() -> bool:
    return request.args.get("client_view") == "1" and _is_admin_session()


def _requested_quality() -> str:
    quality = request.args.get("quality", "original").strip().lower()
    if quality not in DOWNLOAD_QUALITIES:
        abort(400, description="Unsupported download quality.")
    return quality


def _resized_jpeg(path: str, original_name: str, quality: str):
    options = DOWNLOAD_QUALITIES[quality]
    with Image.open(path) as stored:
        image = ImageOps.exif_transpose(stored)
        image.thumbnail(
            (options["max_edge"], options["max_edge"]),
            Image.Resampling.LANCZOS,
        )
        if image.mode in ("RGBA", "LA"):
            background = Image.new("RGB", image.size, "white")
            alpha = image.getchannel("A")
            background.paste(image.convert("RGB"), mask=alpha)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        output = BytesIO()
        image.save(
            output,
            format="JPEG",
            quality=options["jpeg_quality"],
            optimize=True,
        )
    output.seek(0)
    stem = os.path.splitext(secure_filename(original_name))[0] or "photo"
    return output, f"{stem}-{quality}.jpg"


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
    is_admin = _is_admin_session()
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
    is_admin = _is_admin_session()
    client_test_mode = is_admin and request.args.get("client_view") == "1"
    collection = database.get_client_collection_by_code(
        code, active_only=(not is_admin or client_test_mode)
    )
    if not collection:
        abort(404)
    if is_admin and not client_test_mode:
        return redirect(url_for("client_gallery.collection_view", code=collection["collection_code"]))
    if collection.get("expires_at") and collection["expires_at"] < datetime.utcnow():
        return render_template(
            "public/client_gallery_unlock.html",
            settings=settings,
            collection=collection,
            expired=True,
        ), 410
    if session.get(_access_key(collection["id"])):
        return redirect(url_for(
            "client_gallery.collection_view",
            code=collection["collection_code"],
            client_view=1 if client_test_mode else None,
        ))
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
            return redirect(url_for(
                "client_gallery.collection_view",
                code=collection["collection_code"],
                client_view=1 if client_test_mode else None,
            ))
        flash("That collection PIN was not accepted. Check the PIN supplied by Benjo Moments and try again.", "error")
    return render_template(
        "public/client_gallery_unlock.html",
        settings=settings,
        collection=collection,
        expired=False,
        manager_client_test=client_test_mode,
    )


@client_gallery.route("/client-gallery/<code>/photos")
def collection_view(code):
    client_test_mode = _is_manager_client_test()
    preview_mode = _is_admin_session() and not client_test_mode
    if preview_mode:
        collection = database.get_client_collection_by_code(code)
        if not collection:
            abort(404)
    else:
        collection, visitor_id = _authorized_collection(code)
        if not visitor_id:
            return redirect(url_for(
                "client_gallery.collection_unlock",
                code=collection["collection_code"],
                client_view=1 if client_test_mode else None,
            ))
    search = request.args.get("q", "").strip()[:100]
    images = database.get_collection_images_for_visitor(collection["id"], search)
    comments = database.get_gallery_comments(collection["id"])
    comments_by_image = {}
    for comment in comments:
        comments_by_image.setdefault(comment["image_id"], []).append(comment)
    like_summary = database.get_gallery_like_summary(
        collection["id"],
        None if preview_mode else visitor_id,
    )
    return render_template(
        "public/client_collection.html",
        settings=database.get_website_settings(),
        collection=collection,
        images=images,
        search=search,
        comments_by_image=comments_by_image,
        preview_mode=preview_mode,
        client_test_mode=client_test_mode,
        like_counts=like_summary["counts"],
        liked_image_ids=like_summary["liked_image_ids"],
        download_qualities=DOWNLOAD_QUALITIES,
    )


@client_gallery.route("/client-gallery/<code>/photo/<int:image_id>")
def collection_photo(code, image_id):
    if _is_admin_session():
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
    directory = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection["id"]))
    path = os.path.join(directory, image["filename"])
    if not os.path.isfile(path):
        abort(404)
    quality = _requested_quality()
    if quality == "original":
        response = send_from_directory(
            directory,
            image["filename"],
            as_attachment=True,
            download_name=image["original_name"],
            conditional=True,
        )
    else:
        output, download_name = _resized_jpeg(path, image["original_name"], quality)
        response = send_file(
            output,
            as_attachment=True,
            download_name=download_name,
            mimetype="image/jpeg",
        )
    database.add_gallery_download(
        collection["id"], visitor_id, image_id, f"image_{quality}"
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
    quality = _requested_quality()
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
                if quality == "original":
                    archive_name = secure_filename(image["original_name"]) or f"photo-{index}.jpg"
                    payload = None
                else:
                    payload, archive_name = _resized_jpeg(path, image["original_name"], quality)
                if archive_name in used_names:
                    stem, extension = os.path.splitext(archive_name)
                    archive_name = f"{stem}-{index}{extension}"
                used_names.add(archive_name)
                if payload is None:
                    archive.write(path, archive_name)
                else:
                    archive.writestr(archive_name, payload.getvalue())
        database.add_gallery_download(
            collection["id"], visitor_id, None, f"all_{quality}"
        )
        response = send_file(
            temporary.name,
            as_attachment=True,
            download_name=f"{collection['collection_code']}-{quality}-photos.zip",
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


@client_gallery.route("/client-gallery/<code>/photo/<int:image_id>/like", methods=["POST"])
@limiter.limit("60 per hour")
def like_photo(code, image_id):
    collection, visitor_id = _authorized_collection(code)
    if not visitor_id:
        abort(403)
    try:
        liked = database.toggle_gallery_like(image_id, visitor_id)
        flash("Photo liked." if liked else "Photo removed from your likes.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for(
        "client_gallery.collection_view",
        code=collection["collection_code"],
        client_view=1 if _is_manager_client_test() else None,
    ) + f"#photo-{image_id}")


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
    return redirect(url_for(
        "client_gallery.collection_view",
        code=collection["collection_code"],
        client_view=1 if _is_manager_client_test() else None,
    ) + f"#photo-{image_id}")


@client_gallery.route("/client-gallery/<code>/lock", methods=["POST"])
def lock_collection(code):
    collection = database.get_client_collection_by_code(code)
    if collection:
        session.pop(_access_key(collection["id"]), None)
    return redirect(url_for(
        "client_gallery.collection_unlock",
        code=code,
        client_view=1 if request.form.get("client_view") == "1" and _is_admin_session() else None,
    ))
