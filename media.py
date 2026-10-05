"""Bounded Reddit image downloads and Instagram-compatible JPEG conversion."""
from urllib.parse import urlsplit
import requests
from PIL import Image, ImageOps

MAX_BYTES = 20 * 1024 * 1024


def is_reddit_image(url):
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == 'https' and parsed.hostname in ('i.redd.it', 'preview.redd.it')
                and parsed.port in (None, 443) and not parsed.username and not parsed.password
                and parsed.path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
    except ValueError:
        return False


def prepare_image(url, destination):
    if not is_reddit_image(url):
        raise ValueError('Only direct HTTPS Reddit images are supported')
    with requests.get(url, timeout=(5, 30), stream=True, allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError('Image redirects are not supported')
        total = 0
        with open(destination, 'wb') as stream:
            for chunk in response.iter_content(64 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError('Image exceeds the 20 MB limit')
                stream.write(chunk)
    with Image.open(destination) as original:
        if original.width * original.height > 40_000_000:
            raise ValueError('Image exceeds the 40 megapixel limit')
        image = ImageOps.exif_transpose(original).convert('RGB')
        image.thumbnail((1080, 1350), Image.Resampling.LANCZOS)
        width, height = image.size
        canvas_width = max(width, (height * 4 + 4) // 5)
        canvas_height = max(height, (width * 100 + 190) // 191)
        canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
        canvas.paste(image, ((canvas_width - width) // 2, (canvas_height - height) // 2))
        target_height = max(566, min(1350, round(canvas.height * 1080 / canvas.width)))
        canvas = canvas.resize((1080, target_height), Image.Resampling.LANCZOS)
        canvas.save(destination, 'JPEG', quality=95)
    return destination
