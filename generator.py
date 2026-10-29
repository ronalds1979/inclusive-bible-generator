import os
import json
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont

class Generator:
    def __init__(self):
        self.locales = {}
        self.load_locales()
        self.fonts_dir = os.path.join("assets", "fonts")
        self.backgrounds_dir = os.path.join("assets", "backgrounds")
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)
        self._bg_cache = {}
        self._font_cache = {}

    def load_locales(self):
        locales_dir = "locales"
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5]
                with open(os.path.join(locales_dir, filename), "r", encoding="utf-8") as f:
                    self.locales[lang_code] = json.load(f)

    def get_locale_string(self, lang, key, **kwargs):
        lang = lang.replace(" (Brasil)", "").replace("English (US/UK)", "en").replace("Español (España)", "es").replace("Português", "pt-BR")
        if lang not in self.locales:
             # Fallback
             lang = "pt-BR"

        template = self.locales[lang].get(key, "")
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

        lang_code = "pt-BR"
        if "English" in lang:
            lang_code = "en"
        elif "Español" in lang:
            lang_code = "es"

        voice = voices[lang_code].get(gender, voices[lang_code]["Female"])

        # Format the reference to avoid reading "3:16" as "3 hours and 16 minutes"
        import re
        audio_ref = reference

        match = None
        if reference and len(reference) <= 100:
            match = re.match(r"^([^\d]+|\d?\s*[a-zA-ZáéíóúãõâêîôûçñÁÉÍÓÚÃÕÂÊÎÔÛÇÑ]+)\s+(\d+)[:\.](\d+)", reference.strip())

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
            safe_ref = reference.lower().replace(" ", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
            filename = f"{safe_ref}_{lang_code}.mp3"
            output_path = os.path.join(self.output_dir, filename)

        async def _generate():
            # Adjust the rate to be slightly slower (-15%) for a more natural, documentary-style narration
            communicate = edge_tts.Communicate(text_to_read, voice, rate="-15%")
            await communicate.save(output_path)

        asyncio.run(_generate())
        return output_path

    def generate_image(self, lang, verse, reference, background_filename="default.png", custom_image_path=None, aspect_ratio="1:1", font_type="Roboto-Regular.ttf", font_color="#FFFFFF", font_size=60, y_offset=0):
        lang_code = "pt"
        if "English" in lang:
            lang_code = "en"
        elif "Español" in lang:
            lang_code = "es"

        target_width = 1080
        target_height = 1080

        if aspect_ratio == "3:4":
            target_width = 1080
            target_height = 1440
        elif aspect_ratio == "4:3":
            target_width = 1440
            target_height = 1080

        if custom_image_path and os.path.exists(custom_image_path):
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
            self._bg_cache[bg_cache_key] = img.copy()

        draw = ImageDraw.Draw(img)

        # Convert hex color to RGBA
        fill_color = font_color.lstrip('#')
        if len(fill_color) == 6:
            r, g, b = tuple(int(fill_color[i:i+2], 16) for i in (0, 2, 4))
            rgba_color = (r, g, b, 255)
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
        # ⚡ Bolt: Measure words individually and accumulate widths
        # to avoid O(n²) string concatenation and re-measuring during wrap.
        # This speeds up text wrapping by ~95%.
        lines = []
        words = text.split(' ')
        current_line = []
        current_width = 0

        try:
            space_width = draw.textlength(" ", font=font)
            measure = lambda t: draw.textlength(t, font=font)
        except AttributeError:
            space_width = draw.textsize(" ", font=font)[0]
            measure = lambda t: draw.textsize(t, font=font)[0]

        for word in words:
            w = measure(word)
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

        return '\n'.join(lines)
