import os
import json
import asyncio
import edge_tts
import re
from PIL import Image, ImageDraw, ImageFont

AUDIO_REF_PATTERN = re.compile(r"^([^\d]+|\d?\s*[a-zA-ZáéíóúãõâêîôûçñÁÉÍÓÚÃÕÂÊÎÔÛÇÑ]+)\s+(\d+)[:\.](\d+)")
HEX_COLOR_PATTERN = re.compile(r'^#?(?:[0-9a-fA-F]{3}){1,2}$')

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

    def __init__(self):
        self.locales = {}
        self.load_locales()
        self.fonts_dir = os.path.join("assets", "fonts")
        self.backgrounds_dir = os.path.join("assets", "backgrounds")
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)
        self._bg_cache = {}
        self._font_cache = {}
        self._wrap_cache = {}

    def load_locales(self):
        locales_dir = "locales"
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]
                with open(os.path.join(locales_dir, filename), "r", encoding="utf-8") as f:
                    self.locales[lang_code] = json.load(f)

    def get_locale_string(self, lang, key, **kwargs):
        # ⚡ Bolt: Fast-path check if `lang` is already a normalized locale key
        # and skip `.format(**kwargs)` when no template arguments are provided.
        if lang not in self.locales:
            lang = self.LANG_MAP.get(lang, "pt-BR")
            if lang not in self.locales:
                lang = "pt-BR"

        template = self.locales[lang].get(key, "")
        if not kwargs:
            return template
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def generate_texts(self, lang, verse, reference):
        description = self.get_locale_string(lang, "default_description")
        alt_text = self.get_locale_string(lang, "alt_text_template", description=description, verse=verse, reference=reference)
        caption = self.get_locale_string(lang, "caption_template", verse=verse, reference=reference)
        return alt_text, caption

    def generate_audio(self, lang, verse, reference, gender="Female", custom_output_path=None):
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
            safe_ref = reference.lower().translate(self.SAFE_REF_MAP)
            filename = f"{safe_ref}_{lang_code}.mp3"
            output_path = os.path.join(self.output_dir, filename)

        async def _generate():
            try:
                # 🛡️ Sentinel: Sanitize text to prevent SSML injection
                safe_text_to_read = text_to_read.translate(self.SSML_MAP)

                # Adjust the rate to be slightly slower (-15%) for a more natural, documentary-style narration
                communicate = edge_tts.Communicate(safe_text_to_read, voice, rate="-15%")
                # 🛡️ Sentinel: Enforce strict timeout on external TTS service to prevent DoS/thread hanging. Timeout scaled to allow for longer generations safely.
                await asyncio.wait_for(communicate.save(output_path), timeout=60)
            except asyncio.TimeoutError as e:
                print("Error: TTS generation timed out.")
                raise Exception("TTS generation timed out.") from e

        asyncio.run(_generate())
        return output_path

    def generate_image(self, lang, verse, reference, background_filename="default.png", custom_image_path=None, aspect_ratio="1:1", font_type="Roboto-Regular.ttf", font_color="#FFFFFF", font_size=60, y_offset=0):
        lang_code = self.LANG_MAP.get(lang, "pt-BR")
        if lang_code == "pt-BR":
            lang_code = "pt"

        target_width = 1080
        target_height = 1080

        if aspect_ratio == "3:4":
            target_width = 1080
            target_height = 1440
        elif aspect_ratio == "4:3":
            target_width = 1440
            target_height = 1080

        # 🛡️ Sentinel: Enforce 20MB file size limit on custom images to prevent memory exhaustion DoS
        if (
            custom_image_path
            and os.path.exists(custom_image_path)
            and os.path.getsize(custom_image_path) <= 20 * 1024 * 1024
        ):
            bg_path = custom_image_path
        else:
            # 🛡️ Sentinel: Prevent path traversal by extracting only the basename
            safe_background_filename = os.path.basename(background_filename)
            bg_path = os.path.join(self.backgrounds_dir, safe_background_filename)
            if not os.path.exists(bg_path):
                bg_path = os.path.join(self.backgrounds_dir, "default.png")

        bg_cache_key = (bg_path, target_width, target_height)
        if bg_cache_key in self._bg_cache:
            img = self._bg_cache[bg_cache_key].copy()
        else:
            try:
                img = Image.open(bg_path).convert("RGBA")
            except Exception:
                img = Image.new('RGBA', (target_width, target_height), color=(73, 109, 137, 255))

            # Center crop and resize
            img_w, img_h = img.size
            img_ratio = img_w / img_h
            target_ratio = target_width / target_height

            if img_ratio > target_ratio:
                # Image is wider than target ratio
                new_w = int(img_h * target_ratio)
                left = int((img_w - new_w) / 2)
                right = left + new_w
                img = img.crop((left, 0, right, img_h))
            elif img_ratio < target_ratio:
                # Image is taller than target ratio
                new_h = int(img_w / target_ratio)
                top = int((img_h - new_h) / 2)
                bottom = top + new_h
                img = img.crop((0, top, img_w, bottom))

            img = img.resize((target_width, target_height))

            # Add dark overlay
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 128))
            img = Image.alpha_composite(img, overlay)
            # 🛡️ Sentinel: Bound the background cache size to prevent memory exhaustion (DoS)
            if len(self._bg_cache) > 16:
                self._bg_cache.clear()
            self._bg_cache[bg_cache_key] = img.copy()

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

        font_cache_key = (font_path, font_size)
        if font_cache_key in self._font_cache:
            font_large, font_small = self._font_cache[font_cache_key]
        else:
            try:
                font_large = ImageFont.truetype(font_path, int(font_size))
                font_small = ImageFont.truetype(font_path, int(font_size * 0.66))
            except IOError:
                # Fallback
                default_font_path = os.path.join(self.fonts_dir, "Roboto-Regular.ttf")
                try:
                    font_large = ImageFont.truetype(default_font_path, int(font_size))
                    font_small = ImageFont.truetype(default_font_path, int(font_size * 0.66))
                except IOError:
                    font_large = ImageFont.load_default()
                    font_small = ImageFont.load_default()
            # 🛡️ Sentinel: Bound the font cache size to prevent memory exhaustion (DoS)
            if len(self._font_cache) > 32:
                self._font_cache.clear()
            self._font_cache[font_cache_key] = (font_large, font_small)

        # Simple text wrapping
        max_width = int(target_width * 0.85) # dynamic max width
        wrapped_verse = self.wrap_text(verse, font_large, max_width, draw)

        # Calculate text position to center it
        try:
            bbox = draw.multiline_textbbox((0, 0), wrapped_verse, font=font_large)
            verse_width = bbox[2] - bbox[0]
            verse_height = bbox[3] - bbox[1]
        except AttributeError:
             # Fallback for older Pillow
             verse_width, verse_height = draw.textsize(wrapped_verse, font=font_large)

        x_text = (target_width - verse_width) / 2
        # Apply y_offset
        y_text = (target_height - verse_height) / 2 - 50 + int(y_offset)

        # Draw verse
        draw.multiline_text((x_text, y_text), wrapped_verse, font=font_large, fill=rgba_color, align="center")

        # Draw reference
        try:
            bbox_ref = draw.textbbox((0, 0), reference, font=font_small)
            ref_width = bbox_ref[2] - bbox_ref[0]
        except AttributeError:
             ref_width, ref_height = draw.textsize(reference, font=font_small)

        x_ref = (target_width - ref_width) / 2
        y_ref = y_text + verse_height + int(font_size * 0.66)

        draw.text((x_ref, y_ref), reference, font=font_small, fill=rgba_color)

        return img

    def wrap_text(self, text, font, max_width, draw):
        # ⚡ Bolt: Check if wrapped text is already cached for these parameters
        # to completely bypass layout process when inputs haven't changed.
        # Use id(font) to avoid font.getname() exceptions and ensure uniqueness.
        cache_key = (text, id(font), max_width)
        if cache_key in self._wrap_cache:
            return self._wrap_cache[cache_key]

        # ⚡ Bolt: Measure words individually and accumulate widths
        # to avoid O(n²) string concatenation and re-measuring during wrap.
        # Also memoize individual word widths in a dictionary and prefer
        # font.getlength over draw.textlength to avoid ImageDraw lookup overhead.
        lines = []
        words = text.split(' ')
        current_line = []
        current_width = 0

        try:
            space_width = font.getlength(" ")
            measure = font.getlength
        except AttributeError:
            space_width = font.getsize(" ")[0]
            measure = lambda t: font.getsize(t)[0]

        word_widths = {}
        for word in words:
            if word not in word_widths:
                word_widths[word] = measure(word)
            w = word_widths[word]

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
        # ⚡ Bolt: Bound the cache size to prevent memory leaks
        if len(self._wrap_cache) > 256:
            self._wrap_cache.clear()
        self._wrap_cache[cache_key] = wrapped
        return wrapped
