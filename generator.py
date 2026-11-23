import os
import json
import asyncio
import logging
import stat
import tempfile
import threading
from collections import OrderedDict
import edge_tts
import re
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

Image.MAX_IMAGE_PIXELS = 25_000_000
MAX_IMAGE_PIXELS = 25_000_000
MAX_AUDIO_BYTES = 15 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_LOCALE_FILES = {"en.json", "es.json", "pt-BR.json"}

AUDIO_REF_PATTERN = re.compile(
    r"^((?:\d\s+)?[a-zA-ZáéíóúãõâêîôûçñÁÉÍÓÚÃÕÂÊÎÔÛÇÑ]+(?:\s+[a-zA-ZáéíóúãõâêîôûçñÁÉÍÓÚÃÕÂÊÎÔÛÇÑ]+)*)\s+(\d+)[:\.](\d+)"
)
HEX_COLOR_PATTERN = re.compile(r'^#?(?:[0-9a-fA-F]{3}){1,2}$')
FILENAME_SANITIZE_PATTERN = re.compile(r'[^\w\-]+')
TEMPLATE_TOKEN_PATTERN = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
_WINDOWS_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

class Generator:
    LANG_MAP = {
        "Português (Brasil)": "pt-BR",
        "English (US/UK)": "en",
        "Español (España)": "es",
        "Português": "pt-BR",
        "English": "en",
        "Español": "es"
    }

    SAFE_REF_MAP = str.maketrans(" :/\\", "____")
    SSML_MAP = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})
    # ⚡ Bolt: Precompute translation table to strip angle brackets without per-call regex overhead
    ANGLE_BRACKET_STRIP_MAP = str.maketrans("", "", "<>")

    @staticmethod
    def _is_reparse_point(path):
        is_junction = getattr(os.path, "isjunction", None)
        if os.path.islink(path) or (callable(is_junction) and is_junction(path)):
            return True
        # 🛡️ Sentinel: Fallback for Python <3.12 on Windows where os.path.isjunction is unavailable
        reparse_attr = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if reparse_attr:
            try:
                lst = os.lstat(path)
                return bool(getattr(lst, "st_file_attributes", 0) & reparse_attr)
            except OSError:
                return False
        return False

    @classmethod
    def _has_reparse_in_lineage(cls, path):
        curr = os.path.abspath(path)
        visited = set()
        while curr and curr not in visited:
            visited.add(curr)
            if os.path.lexists(curr) and cls._is_reparse_point(curr):
                return True
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
        return False

    @classmethod
    def _is_safe_regular_file(cls, path, max_bytes=20 * 1024 * 1024):
        if not path or not isinstance(path, str):
            return False
        if path.startswith("\\\\.\\") or path.startswith("\\\\?\\"):
            return False
        base = os.path.splitext(os.path.basename(path))[0].upper()
        if not base or base in _WINDOWS_DEVICE_NAMES:
            return False
        if cls._has_reparse_in_lineage(path):
            return False
        try:
            return os.path.isfile(path) and 0 < os.path.getsize(path) <= max_bytes
        except OSError:
            return False

    @classmethod
    def _open_regular_nofollow(cls, path, mode="rb", max_bytes=20 * 1024 * 1024, encoding=None):
        """Atomically open a verified regular file without following symlinks to prevent TOCTOU."""
        if not cls._is_safe_regular_file(path, max_bytes=max_bytes):
            raise ValueError("Unsafe or invalid regular file")
        lst = os.lstat(path)
        if stat.S_ISLNK(lst.st_mode) or cls._is_reparse_point(path):
            raise ValueError("Refusing to open symlink or reparse point")
        # 🛡️ Sentinel: Open with O_NOFOLLOW where supported and verify inode/lineage identity (guards Windows where O_NOFOLLOW is 0)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or not (0 < st.st_size <= max_bytes):
                raise ValueError("Path is not a regular file within allowed size")
            if st.st_ino and lst.st_ino and (lst.st_dev, lst.st_ino) != (st.st_dev, st.st_ino):
                raise ValueError("File identity changed between lstat and open")
            if cls._has_reparse_in_lineage(path):
                raise ValueError("Reparse point detected in path lineage")
            if "b" in mode:
                return os.fdopen(fd, mode)
            return os.fdopen(fd, mode, encoding=encoding)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise

    @classmethod
    def _is_valid_raster_image(cls, path, max_bytes=20 * 1024 * 1024):
        try:
            with cls._open_regular_nofollow(path, mode="rb", max_bytes=max_bytes) as f:
                header = f.read(8)
        except (OSError, ValueError):
            return False
        is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpeg = header.startswith(b"\xff\xd8\xff")
        return is_png or is_jpeg

    @classmethod
    def _validate_safe_output_path(cls, output_path):
        if not output_path or not isinstance(output_path, str):
            raise ValueError("Invalid output path")
        if output_path.startswith("\\\\.\\") or output_path.startswith("\\\\?\\"):
            raise ValueError("Device paths are not permitted")
        filename = os.path.basename(output_path)
        base = os.path.splitext(filename)[0].upper()
        if not filename or not base or base in _WINDOWS_DEVICE_NAMES:
            raise ValueError("Reserved or invalid output filename")
        if cls._has_reparse_in_lineage(output_path):
            raise ValueError("Refusing to write through symlink or junction")

    @staticmethod
    def sanitize_filename(name):
        """Sanitize a string into a safe single-segment filename."""
        cleaned = FILENAME_SANITIZE_PATTERN.sub('_', (name or "").lower()).strip('_')
        cleaned = os.path.basename(cleaned)[:80]
        return cleaned or "verse"
    # ⚡ Bolt: Precompute 50% darken lookup table and cache custom dimming LUTs
    DARKEN_LUT = [int(i * 127 / 255) for i in range(256)] * 3
    DARKEN_LUTS = {0.5: DARKEN_LUT}

    @classmethod
    def _get_darken_lut(cls, dim_key):
        lut = cls.DARKEN_LUTS.get(dim_key)
        if lut is None:
            if len(cls.DARKEN_LUTS) > 32:
                cls.DARKEN_LUTS.clear()
                cls.DARKEN_LUTS[0.5] = cls.DARKEN_LUT
            dim_factor = 1.0 - dim_key
            lut = [int(i * dim_factor) for i in range(256)] * 3
            cls.DARKEN_LUTS[dim_key] = lut
        return lut

    def __init__(self):
        self.base_dir = BASE_DIR
        self.locales = {}
        self.load_locales()
        self.fonts_dir = os.path.join(self.base_dir, "assets", "fonts")
        self.backgrounds_dir = os.path.join(self.base_dir, "assets", "backgrounds")
        self.output_dir = os.path.join(self.base_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)
        self._cache_lock = threading.Lock()
        self._bg_cache = OrderedDict()
        self._font_cache = OrderedDict()
        self._wrap_cache = OrderedDict()
        self._valid_image_cache = OrderedDict()
        self._text_metrics_cache = OrderedDict()
        self._word_width_cache = OrderedDict()

    def load_locales(self):
        locales_dir = os.path.join(self.base_dir, "locales")
        if not os.path.isdir(locales_dir):
            return
        for filename in sorted(ALLOWED_LOCALE_FILES):
            locale_path = os.path.join(locales_dir, filename)
            lang_code = filename[:-5]
            try:
                with self._open_regular_nofollow(
                    locale_path, mode="r", max_bytes=1024 * 1024, encoding="utf-8"
                ) as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, dict):
                self.locales[lang_code] = {
                    k: v for k, v in data.items()
                    if isinstance(k, str) and isinstance(v, str)
                }

    def get_locale_string(self, lang, key, **kwargs):
        # ⚡ Bolt: Fast-path check if `lang` is already a normalized locale key
        # and skip substitution when no template arguments are provided.
        if not self.locales:
            return ""
        if lang not in self.locales:
            lang = self.LANG_MAP.get(lang, "pt-BR")
            if lang not in self.locales:
                lang = "pt-BR"

        template = self.locales.get(lang, {}).get(key, "")
        if not kwargs:
            return template
        return TEMPLATE_TOKEN_PATTERN.sub(
            lambda m: str(kwargs[m.group(1)]) if m.group(1) in kwargs else m.group(0),
            template,
        )

    def generate_texts(self, lang, verse, reference):
        verse = (verse or "")[:5000]
        reference = (reference or "")[:100]
        description = self.get_locale_string(lang, "default_description")
        alt_text = self.get_locale_string(lang, "alt_text_template", description=description, verse=verse, reference=reference)
        caption = self.get_locale_string(lang, "caption_template", verse=verse, reference=reference)
        return alt_text, caption

    def generate_audio(self, lang, verse, reference, gender="Female", custom_output_path=None):
        verse = (verse or "")[:5000]
        reference = (reference or "")[:100]

        voices = {
            "pt-BR": {"Male": "pt-BR-AntonioNeural", "Female": "pt-BR-FranciscaNeural"},
            "en": {"Male": "en-US-GuyNeural", "Female": "en-US-JennyNeural"},
            "es": {"Male": "es-ES-AlvaroNeural", "Female": "es-ES-ElviraNeural"}
        }

        lang_code = self.LANG_MAP.get(lang, "pt-BR")

        voice = voices[lang_code].get(gender, voices[lang_code]["Female"])

        # Format the reference to avoid reading "3:16" as "3 hours and 16 minutes"
        audio_ref = reference

        match = None
        if reference and len(reference) <= 100:
            match = AUDIO_REF_PATTERN.match(reference.strip())

        if match:
            book = match.group(1).strip()
            chapter = match.group(2)
            v = match.group(3)

            if lang_code == "pt-BR":
                audio_ref = f"{book}, capítulo {chapter}, versículo {v}"
            elif lang_code == "es":
                audio_ref = f"{book}, capítulo {chapter}, versículo {v}"
            else: # en
                audio_ref = f"{book}, chapter {chapter}, verse {v}"

        text_to_read = f"{audio_ref}. \n{verse}"

        if custom_output_path:
            output_path = custom_output_path
        else:
            safe_ref = self.sanitize_filename(reference)
            filename = f"{safe_ref}_{lang_code}.mp3"
            output_path = os.path.join(self.output_dir, filename)

        self._validate_safe_output_path(output_path)
        target_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(target_dir, exist_ok=True)

        async def _stream_to_file(communicate, audio_file):
            total_bytes = 0
            async for message in communicate.stream():
                if message.get("type") == "audio":
                    chunk = message.get("data", b"")
                    total_bytes += len(chunk)
                    if total_bytes > MAX_AUDIO_BYTES:
                        raise ValueError("TTS audio stream exceeds maximum allowed size")
                    audio_file.write(chunk)

        async def _generate():
            temp_fd, temp_path = tempfile.mkstemp(
                dir=target_dir,
                prefix=".tmp_tts_",
                suffix=".mp3",
            )
            try:
                # 🛡️ Sentinel: Strip angle brackets to prevent SSML injection while avoiding double XML-escaping in edge-tts
                safe_text_to_read = text_to_read.translate(self.ANGLE_BRACKET_STRIP_MAP)

                # Adjust the rate to be slightly slower (-15%) for a more natural, documentary-style narration
                communicate = edge_tts.Communicate(safe_text_to_read, voice, rate="-15%")
                # 🛡️ Sentinel: Keep the exclusive mkstemp descriptor open via os.fdopen (no close/reopen TOCTOU),
                # enforce strict timeout/byte cap, and re-validate output_path before atomic replace
                with os.fdopen(temp_fd, "wb") as audio_file:
                    temp_fd = None
                    await asyncio.wait_for(_stream_to_file(communicate, audio_file), timeout=60)
                self._validate_safe_output_path(output_path)
                os.replace(temp_path, output_path)
            except asyncio.TimeoutError as e:
                logger.error("TTS generation timed out.")
                raise Exception("TTS generation timed out.") from e
            finally:
                if temp_fd is not None:
                    try:
                        os.close(temp_fd)
                    except OSError:
                        pass
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

        asyncio.run(_generate())
        return output_path

    @staticmethod
    def _get_font_id(font):
        font_id = (getattr(font, "path", None), getattr(font, "size", 0))
        if font_id[0] is None:
            return id(font)
        return font_id

    def _resolve_valid_image(self, path, max_bytes=20 * 1024 * 1024):
        """Validate raster image path with mtime/size-keyed LRU caching to avoid repeated lineage walks."""
        if not path or not isinstance(path, str):
            return False, 0
        try:
            st = os.stat(path)
        except OSError:
            return False, 0
        if not (0 < st.st_size <= max_bytes):
            return False, 0

        cache_key = (path, st.st_mtime_ns, st.st_size)
        with self._cache_lock:
            if cache_key in self._valid_image_cache:
                self._valid_image_cache.move_to_end(cache_key)
                return True, int(st.st_mtime)

        if not self._is_valid_raster_image(path, max_bytes=max_bytes):
            return False, 0

        with self._cache_lock:
            self._valid_image_cache[cache_key] = True
            self._valid_image_cache.move_to_end(cache_key)
            if len(self._valid_image_cache) > 32:
                self._valid_image_cache.popitem(last=False)
        return True, int(st.st_mtime)

    def _measure_multiline_text(self, draw, text, font):
        """Return (width, height) of wrapped multiline text, cached by (text, font_id)."""
        cache_key = ("multi", text, self._get_font_id(font))
        with self._cache_lock:
            cached = self._text_metrics_cache.get(cache_key)
            if cached is not None:
                self._text_metrics_cache.move_to_end(cache_key)
                return cached

        try:
            bbox = draw.multiline_textbbox((0, 0), text, font=font)
            dims = (bbox[2] - bbox[0], bbox[3] - bbox[1])
        except AttributeError:
            # Fallback for older Pillow
            dims = draw.textsize(text, font=font)

        with self._cache_lock:
            self._text_metrics_cache[cache_key] = dims
            self._text_metrics_cache.move_to_end(cache_key)
            if len(self._text_metrics_cache) > 256:
                self._text_metrics_cache.popitem(last=False)
        return dims

    def _measure_single_text_width(self, draw, text, font):
        """Return width of a single-line string, cached by (text, font_id)."""
        cache_key = ("single", text, self._get_font_id(font))
        with self._cache_lock:
            cached = self._text_metrics_cache.get(cache_key)
            if cached is not None:
                self._text_metrics_cache.move_to_end(cache_key)
                return cached

        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
        except AttributeError:
            width, _ = draw.textsize(text, font=font)

        with self._cache_lock:
            self._text_metrics_cache[cache_key] = width
            self._text_metrics_cache.move_to_end(cache_key)
            if len(self._text_metrics_cache) > 256:
                self._text_metrics_cache.popitem(last=False)
        return width

    def generate_image(self, lang, verse, reference, background_filename="default.png", custom_image_path=None, aspect_ratio="1:1", font_type="Roboto-Regular.ttf", font_color="#FFFFFF", font_size=60, y_offset=0, max_dimension=None, background_dim=0.5):
        verse = (verse or "")[:5000]
        reference = (reference or "")[:100]
        lang_code = self.LANG_MAP.get(lang, "pt-BR")
        if lang_code == "pt-BR":
            lang_code = "pt"

        try:
            safe_dim = max(0.0, min(0.85, float(background_dim)))
        except (ValueError, TypeError):
            safe_dim = 0.5
        dim_key = round(safe_dim, 2)

        target_width = 1080
        target_height = 1080

        if aspect_ratio == "3:4":
            target_width = 1080
            target_height = 1440
        elif aspect_ratio == "4:3":
            target_width = 1440
            target_height = 1080

        # ⚡ Bolt: Render directly at preview scale when max_dimension is provided (skips 1080p copy + thumbnail downscale)
        render_scale = 1.0
        if max_dimension is not None and max_dimension > 0:
            max_side = max(target_width, target_height)
            if max_side > max_dimension:
                render_scale = max_dimension / max_side
                target_width = max(1, int(round(target_width * render_scale)))
                target_height = max(1, int(round(target_height * render_scale)))

        # 🛡️ Sentinel: Enforce regular-file and 20MB file size limit on both custom and built-in images
        # ⚡ Bolt: Use mtime/size-keyed validation cache to avoid repeated lineage walks and header reads
        bg_path = None
        bg_mtime = 0
        if custom_image_path:
            is_valid, mtime = self._resolve_valid_image(custom_image_path)
            if is_valid:
                bg_path = custom_image_path
                bg_mtime = mtime

        if bg_path is None:
            # 🛡️ Sentinel: Prevent path traversal by extracting only the basename
            safe_background_filename = os.path.basename(background_filename or "default.png")
            candidate_path = os.path.join(self.backgrounds_dir, safe_background_filename)
            is_valid, mtime = self._resolve_valid_image(candidate_path)
            if is_valid:
                bg_path = candidate_path
                bg_mtime = mtime
            else:
                bg_path = os.path.join(self.backgrounds_dir, "default.png")
                try:
                    bg_mtime = int(os.path.getmtime(bg_path))
                except OSError:
                    bg_mtime = 0

        # ⚡ Bolt: Cache the un-dimmed resized RGB base background (without dim_key) and derive
        # dimmed variants on demand via point(LUT). Prevents 17-step dim slider LRU thrashing
        # and eliminates disk I/O, decoding, cropping, and resizing on background_dim changes.
        bg_cache_key = (bg_path, bg_mtime, target_width, target_height)
        with self._cache_lock:
            cached_bg = self._bg_cache.get(bg_cache_key)
            if cached_bg is not None:
                self._bg_cache.move_to_end(bg_cache_key)
                img = (
                    cached_bg.point(self._get_darken_lut(dim_key))
                    if dim_key > 0.0
                    else cached_bg.copy()
                )
            else:
                img = None
        if img is None:
            bg_loaded = False
            base_img = None
            try:
                # 🛡️ Sentinel: Open background via _open_regular_nofollow so O_NOFOLLOW, S_ISREG, and 20 MB descriptor size cap are enforced atomically
                with self._open_regular_nofollow(bg_path, mode="rb") as f:
                    with Image.open(f, formats=["PNG", "JPEG"]) as raw_img:
                        if raw_img.width * raw_img.height > MAX_IMAGE_PIXELS:
                            raise ValueError("Image dimensions exceed maximum allowed pixels")

                        # ⚡ Bolt: Use libjpeg DCT downscaling during decompression for large JPEGs
                        if raw_img.format == "JPEG":
                            raw_img.draft("RGB", (target_width, target_height))

                        img_w, img_h = raw_img.size
                        img_ratio = img_w / img_h
                        target_ratio = target_width / target_height

                        if img_ratio > target_ratio:
                            new_w = max(1, int(img_h * target_ratio))
                            left = int((img_w - new_w) / 2)
                            img = raw_img.crop((left, 0, left + new_w, img_h))
                        elif img_ratio < target_ratio:
                            new_h = max(1, int(img_w / target_ratio))
                            top = int((img_h - new_h) / 2)
                            img = raw_img.crop((0, top, img_w, top + new_h))
                        else:
                            img = raw_img

                        # ⚡ Bolt: Use BILINEAR resampling for fast live previews (max_dimension set)
                        if img.size != (target_width, target_height):
                            resample_filter = (
                                Image.Resampling.BILINEAR
                                if max_dimension is not None and max_dimension > 0
                                else Image.Resampling.BICUBIC
                            )
                            img = img.resize((target_width, target_height), resample=resample_filter)
                        if img.mode in ('RGBA', 'LA', 'PA'):
                            base = Image.new('RGB', img.size, (36, 54, 68))
                            rgba = img.convert('RGBA')
                            base.paste(rgba, mask=rgba.getchannel('A'))
                            img = base
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')
                        if img is raw_img:
                            base_img = img.copy()
                        else:
                            img.load()
                            base_img = img
                        img = (
                            base_img.point(self._get_darken_lut(dim_key))
                            if dim_key > 0.0
                            else base_img.copy()
                        )
                        bg_loaded = True
            except Exception:
                img = Image.new('RGB', (target_width, target_height), color=(36, 54, 68))

            # 🛡️ Sentinel: Bound the background cache size with LRU eviction and never cache transient fallback errors
            if bg_loaded and base_img is not None:
                with self._cache_lock:
                    self._bg_cache[bg_cache_key] = base_img
                    self._bg_cache.move_to_end(bg_cache_key)
                    if len(self._bg_cache) > 16:
                        self._bg_cache.popitem(last=False)

        draw = ImageDraw.Draw(img)

        # Convert hex color to RGBA
        if HEX_COLOR_PATTERN.match(font_color):
            fill_color = font_color.lstrip('#')
            try:
                if len(fill_color) == 6:
                    r, g, b = tuple(int(fill_color[i:i+2], 16) for i in (0, 2, 4))
                    rgba_color = (r, g, b, 255)
                elif len(fill_color) == 3:
                    r, g, b = tuple(int(fill_color[i]*2, 16) for i in range(3))
                    rgba_color = (r, g, b, 255)
                else:
                    rgba_color = (255, 255, 255, 255)
            except ValueError:
                rgba_color = (255, 255, 255, 255)
        else:
            rgba_color = (255, 255, 255, 255)

        # Load font
        # 🛡️ Sentinel: Prevent path traversal by extracting only the basename
        safe_font_type = os.path.basename(font_type)
        font_path = os.path.join(self.fonts_dir, safe_font_type)
        try:
            parsed_font_size = int(font_size)
        except (ValueError, TypeError):
            parsed_font_size = 60
        parsed_font_size = max(8, min(300, parsed_font_size))
        safe_font_size = max(8, min(300, int(round(parsed_font_size * render_scale))))

        try:
            parsed_y_offset = int(y_offset)
        except (ValueError, TypeError):
            parsed_y_offset = 0
        parsed_y_offset = max(-1000, min(1000, parsed_y_offset))

        font_cache_key = (font_path, safe_font_size)
        with self._cache_lock:
            cached_fonts = self._font_cache.get(font_cache_key)
            if cached_fonts is not None:
                self._font_cache.move_to_end(font_cache_key)
        if cached_fonts is not None:
            font_large, font_small = cached_fonts
        else:
            try:
                if not self._is_safe_regular_file(font_path):
                    raise OSError("Unsafe or missing font file")
                font_large = ImageFont.truetype(font_path, safe_font_size)
                font_small = ImageFont.truetype(font_path, max(8, int(safe_font_size * 0.66)))
            except (IOError, OSError):
                # Fallback
                default_font_path = os.path.join(self.fonts_dir, "Roboto-Regular.ttf")
                try:
                    if not self._is_safe_regular_file(default_font_path):
                        raise OSError("Unsafe or missing default font file")
                    font_large = ImageFont.truetype(default_font_path, safe_font_size)
                    font_small = ImageFont.truetype(default_font_path, max(8, int(safe_font_size * 0.66)))
                except (IOError, OSError):
                    font_large = ImageFont.load_default()
                    font_small = ImageFont.load_default()
            # 🛡️ Sentinel: Bound the font cache size with LRU eviction to prevent cache thrashing on slider drags
            with self._cache_lock:
                self._font_cache[font_cache_key] = (font_large, font_small)
                self._font_cache.move_to_end(font_cache_key)
                if len(self._font_cache) > 64:
                    self._font_cache.popitem(last=False)

        # Simple text wrapping
        max_width = int(target_width * 0.85) # dynamic max width
        wrapped_verse = self.wrap_text(verse, font_large, max_width, draw)

        # Calculate text position to center it
        verse_width, verse_height = self._measure_multiline_text(draw, wrapped_verse, font_large)

        x_text = (target_width - verse_width) / 2
        # Apply y_offset
        y_text = (target_height - verse_height) / 2 - int(round(50 * render_scale)) + int(round(parsed_y_offset * render_scale))

        # Draw verse
        draw.multiline_text((x_text, y_text), wrapped_verse, font=font_large, fill=rgba_color, align="center")

        # Draw reference
        ref_width = self._measure_single_text_width(draw, reference, font_small)

        x_ref = (target_width - ref_width) / 2
        y_ref = y_text + verse_height + int(safe_font_size * 0.66)

        draw.text((x_ref, y_ref), reference, font=font_small, fill=rgba_color)

        return img

    def save_image_atomic(self, pil_img, output_path, compress_level=1):
        """Validate output_path and atomically write the rendered PNG image."""
        self._validate_safe_output_path(output_path)
        abs_output = os.path.abspath(output_path)
        target_dir = os.path.dirname(abs_output)
        os.makedirs(target_dir, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=target_dir,
            prefix=".tmp_img_",
            suffix=".png",
        )
        os.close(temp_fd)
        try:
            pil_img.save(temp_path, "PNG", compress_level=compress_level)
            os.replace(temp_path, abs_output)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
        return output_path

    def wrap_text(self, text, font, max_width, draw):
        text = (text or "")[:5000]
        # ⚡ Bolt: Key by stable (font.path, font.size) with LRU eviction instead of volatile id(font)
        font_id = self._get_font_id(font)
        cache_key = (text, font_id, max_width)
        with self._cache_lock:
            if cache_key in self._wrap_cache:
                self._wrap_cache.move_to_end(cache_key)
                return self._wrap_cache[cache_key]
            word_widths = self._word_width_cache.get(font_id)
            if word_widths is not None:
                self._word_width_cache.move_to_end(font_id)

        if word_widths is None:
            word_widths = {}
            with self._cache_lock:
                if font_id in self._word_width_cache:
                    word_widths = self._word_width_cache[font_id]
                else:
                    self._word_width_cache[font_id] = word_widths
                    if len(self._word_width_cache) > 32:
                        self._word_width_cache.popitem(last=False)

        # ⚡ Bolt: Measure words individually and accumulate widths
        # to avoid O(n²) string concatenation and re-measuring during wrap.
        # Also memoize individual word widths per font across calls and prefer
        # font.getlength over draw.textlength to avoid ImageDraw lookup overhead.
        lines = []
        words = text.split(' ')
        current_line = []
        current_width = 0

        try:
            measure = font.getlength
        except AttributeError:
            measure = lambda t: font.getsize(t)[0]

        space_width = word_widths.get(" ")
        if space_width is None:
            space_width = measure(" ")
            word_widths[" "] = space_width

        for word in words:
            w = word_widths.get(word)
            if w is None:
                w = measure(word)
                if len(word_widths) < 2048:
                    word_widths[word] = w

            if current_line:
                if current_width + space_width + w > max_width:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_width = w
                else:
                    current_line.append(word)
                    current_width += space_width + w
            else:
                current_line.append(word)
                current_width = w

        if current_line:
            lines.append(' '.join(current_line))

        wrapped = '\n'.join(lines)
        # ⚡ Bolt: Bound the cache size with LRU eviction
        with self._cache_lock:
            self._wrap_cache[cache_key] = wrapped
            self._wrap_cache.move_to_end(cache_key)
            if len(self._wrap_cache) > 256:
                self._wrap_cache.popitem(last=False)
        return wrapped
