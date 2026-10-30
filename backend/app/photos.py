import io

from PIL import Image

MAX_SIZE = 512
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
JPEG_QUALITY = 85


def prepare_photo(raw: bytes) -> bytes:
    if not raw:
        raise ValueError("Пустой файл")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Файл больше 5 МБ")
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw))
    except Exception:
        raise ValueError("Это не изображение")

    img = img.convert("RGB")
    if max(img.size) > MAX_SIZE:
        img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()
