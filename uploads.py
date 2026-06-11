"""Validation and storage helpers for user-uploaded images."""

from pathlib import Path
import warnings

from PIL import Image, UnidentifiedImageError

import config


class InvalidImageError(ValueError):
    pass


_FORMAT_EXTENSIONS = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
}


def validate_image(file_storage) -> str:
    """Validate size and image bytes, then return a canonical extension."""
    if not file_storage or not file_storage.filename:
        raise InvalidImageError("No image file was selected.")

    stream = file_storage.stream
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)

    if size <= 0:
        raise InvalidImageError("The selected image is empty.")
    if size > config.MAX_IMAGE_FILE_SIZE:
        raise InvalidImageError("Each image must be 10 MB or smaller.")

    Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(stream) as image:
                image_format = image.format
                image.verify()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise InvalidImageError("The selected file is not a valid supported image.") from exc
    finally:
        stream.seek(0)

    extension = _FORMAT_EXTENSIONS.get(image_format)
    if not extension:
        raise InvalidImageError("Only JPEG, PNG, and WebP images are supported.")
    return extension


def save_image(file_storage, destination: str, filename: str) -> None:
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    file_storage.save(target / filename)
