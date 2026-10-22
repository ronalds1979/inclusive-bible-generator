import customtkinter as ctk
from generator import Generator
from youversion_api import YouVersionAPI
import pyperclip
import os

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.generator = Generator()
        self.current_lang = "Português (Brasil)"

        self.title("inclusive-bible-generator")
        self.geometry("1100x750")

        self.grid_columnconfigure(0, weight=1) # Left side controls
        self.grid_columnconfigure(1, weight=1) # Right side preview
        self.grid_rowconfigure(0, weight=1)

        # Main Containers
        self.left_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(1, weight=1)

        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)

        # Language Selector
        self.lang_var = ctk.StringVar(value="Português (Brasil)")
        self.lang_dropdown = ctk.CTkOptionMenu(
            self.left_frame,
            values=["Português (Brasil)", "English (US/UK)", "Español (España)"],
            variable=self.lang_var,
            command=self.change_language
        )
        self.lang_dropdown.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Instructions
        self.instructions_label = ctk.CTkLabel(self.left_frame, text="", text_color="gray", justify="left")
        self.instructions_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Bible API Fetch
        self.api_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.api_frame.grid(row=2, column=0, columnspan=2, pady=(10, 10), sticky="ew")
        self.api_frame.grid_columnconfigure((0, 1), weight=1)

        self.bible_version_label = ctk.CTkLabel(self.api_frame, text="Versão:")
        self.bible_version_label.grid(row=0, column=0, pady=(0, 5), padx=(0, 5), sticky="w")

        self.bible_version_var = ctk.StringVar()
        self.bible_version_dropdown = ctk.CTkOptionMenu(
            self.api_frame, values=["-"], variable=self.bible_version_var
        )
        self.bible_version_dropdown.grid(row=1, column=0, padx=(0, 5), sticky="ew")
        self.bible_versions_map = {}

        self.fetch_btn = ctk.CTkButton(self.api_frame, text="Buscar Versículo", command=self.fetch_verse)
        self.fetch_btn.grid(row=1, column=1, padx=(5, 0), sticky="ew")

        # Reference Input
        self.reference_label = ctk.CTkLabel(self.left_frame, text="Referência (ex: Salmos 119:105):")
        self.reference_label.grid(row=3, column=0, pady=(0, 0), sticky="w")

        self.reference_input = ctk.CTkEntry(self.left_frame)
        self.reference_input.grid(row=4, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Verse Input
        self.verse_label = ctk.CTkLabel(self.left_frame, text="Versículo Bíblico:")
        self.verse_label.grid(row=5, column=0, pady=(0, 0), sticky="w")

        self.verse_input = ctk.CTkTextbox(self.left_frame, height=80)
        self.verse_input.grid(row=6, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Background Selector
        self.background_label = ctk.CTkLabel(self.left_frame, text="Imagem de Fundo:")
        self.background_label.grid(row=7, column=0, pady=(10, 0), sticky="w")

        self.bg_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.bg_frame.grid(row=8, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        self.bg_frame.grid_columnconfigure(0, weight=1)
        self.bg_frame.grid_columnconfigure(1, weight=1)

        self.bg_var = ctk.StringVar(value="default.png")
        bg_files = [f for f in os.listdir(self.generator.backgrounds_dir) if f.endswith('.png') or f.endswith('.jpg')]
        if not bg_files:
            bg_files = ["default.png"]

        self.bg_dropdown = ctk.CTkOptionMenu(
            self.bg_frame,
            values=bg_files,
            variable=self.bg_var,
            command=self.clear_custom_image
        )
        self.bg_dropdown.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.custom_image_path = None
        self.custom_image_btn = ctk.CTkButton(self.bg_frame, text="Selecionar Imagem Personalizada", command=self.select_custom_image)
        self.custom_image_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # Font customization block
        self.font_config_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.font_config_frame.grid(row=9, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        self.font_config_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.font_type_label = ctk.CTkLabel(self.font_config_frame, text="Tipo de Fonte:")
        self.font_type_label.grid(row=0, column=0, pady=(0, 5), padx=(0, 5), sticky="w")

        self.font_var = ctk.StringVar(value="Roboto-Regular.ttf")
        font_files = [f for f in os.listdir(self.generator.fonts_dir) if f.endswith('.ttf')]
        self.font_dropdown = ctk.CTkOptionMenu(
            self.font_config_frame, values=font_files, variable=self.font_var, command=self.trigger_preview
        )
        self.font_dropdown.grid(row=1, column=0, padx=(0, 5), sticky="ew")

        self.font_color_label = ctk.CTkLabel(self.font_config_frame, text="Cor do Texto:")
        self.font_color_label.grid(row=0, column=1, pady=(0, 5), padx=5, sticky="w")

        self.font_color_var = ctk.StringVar(value="#FFFFFF")
        self.font_color_entry = ctk.CTkEntry(self.font_config_frame, textvariable=self.font_color_var)
        self.font_color_entry.grid(row=1, column=1, padx=5, sticky="ew")
        self.font_color_entry.bind("<KeyRelease>", self.trigger_preview)

        self.font_size_label = ctk.CTkLabel(self.font_config_frame, text="Tamanho da Fonte:")
        self.font_size_label.grid(row=0, column=2, pady=(0, 5), padx=(5, 0), sticky="w")

        self.font_size_var = ctk.IntVar(value=60)
        self.font_size_slider = ctk.CTkSlider(self.font_config_frame, from_=20, to=120, variable=self.font_size_var, command=self.trigger_preview)
        self.font_size_slider.grid(row=1, column=2, padx=(5, 0), sticky="ew")

        # Bottom customization block
        self.bottom_config_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.bottom_config_frame.grid(row=10, column=0, columnspan=2, pady=(10, 20), sticky="ew")
        self.bottom_config_frame.grid_columnconfigure((0, 1), weight=1)

        self.aspect_ratio_label = ctk.CTkLabel(self.bottom_config_frame, text="Proporção da Imagem:")
        self.aspect_ratio_label.grid(row=0, column=0, pady=(0, 5), sticky="w")

        self.aspect_ratio_var = ctk.StringVar(value="1:1")
        self.aspect_ratio_dropdown = ctk.CTkOptionMenu(
            self.bottom_config_frame,
            values=["1:1", "3:4", "4:3"],
            variable=self.aspect_ratio_var,
            command=self.trigger_preview
        )
        self.aspect_ratio_dropdown.grid(row=1, column=0, padx=(0, 5), sticky="ew")

        self.y_offset_label = ctk.CTkLabel(self.bottom_config_frame, text="Posição Vertical (Y):")
        self.y_offset_label.grid(row=0, column=1, pady=(0, 5), padx=5, sticky="w")

        self.y_offset_var = ctk.IntVar(value=0)
        self.y_offset_slider = ctk.CTkSlider(self.bottom_config_frame, from_=-400, to=400, variable=self.y_offset_var, command=self.trigger_preview)
        self.y_offset_slider.grid(row=1, column=1, padx=5, sticky="ew")

        # Audio Configuration block
        self.audio_config_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.audio_config_frame.grid(row=11, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        self.audio_config_frame.grid_columnconfigure((0, 1), weight=1)

        self.audio_generate_var = ctk.BooleanVar(value=False)
        self.audio_generate_checkbox = ctk.CTkCheckBox(self.audio_config_frame, text="Gerar Áudio (TTS)?", variable=self.audio_generate_var)
        self.audio_generate_checkbox.grid(row=0, column=0, pady=(0, 5), padx=(0, 5), sticky="w")

        self.gender_label = ctk.CTkLabel(self.audio_config_frame, text="Voz:")
        self.gender_label.grid(row=0, column=1, pady=(0, 5), padx=5, sticky="w")

        self.gender_var = ctk.StringVar(value="Female")
        self.gender_dropdown = ctk.CTkOptionMenu(
            self.audio_config_frame,
            values=["Female", "Male"],
            variable=self.gender_var
        )
        self.gender_dropdown.grid(row=1, column=1, padx=(5, 0), sticky="ew")

        # Bind text inputs to preview
        self.verse_input.bind("<KeyRelease>", self.trigger_preview)
        self.reference_input.bind("<KeyRelease>", self.trigger_preview)

        # Output Textbox (Alt-Text & Caption)
        self.output_textbox = ctk.CTkTextbox(self.left_frame, height=150)
        self.output_textbox.grid(row=12, column=0, columnspan=2, pady=10, sticky="ew")

        # Generate Button
        self.generate_btn = ctk.CTkButton(self.left_frame, text="Gerar Conteúdo", command=self.generate_content)
        self.generate_btn.grid(row=13, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        # Copy/Save Buttons Frame
        self.buttons_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.buttons_frame.grid(row=14, column=0, columnspan=2, pady=10)

        self.copy_alt_btn = ctk.CTkButton(self.buttons_frame, text="Copiar Alt-Text", command=self.copy_alt)
        self.copy_alt_btn.grid(row=0, column=0, padx=10)

        self.copy_caption_btn = ctk.CTkButton(self.buttons_frame, text="Copiar Legenda", command=self.copy_caption)
        self.copy_caption_btn.grid(row=0, column=1, padx=10)

        self.status_label = ctk.CTkLabel(self.left_frame, text="", text_color="green")
        self.status_label.grid(row=15, column=0, columnspan=2, pady=10)

        self.alt_text = ""
        self.caption = ""
        self.last_generated_image_path = None

        # Start initial preview
        self.trigger_preview()

        # Image Preview
        self.preview_label = ctk.CTkLabel(self.right_frame, text="Nenhuma imagem gerada ainda.", text_color="gray")
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        # Initial UI Update
        self.update_ui_texts()

    def get_lang_key(self):
        lang = self.current_lang
        if "English" in lang: return "en"
        if "Español" in lang: return "es"
        return "pt-BR"

    def change_language(self, choice):
        self.current_lang = choice
        self.update_ui_texts()
        self.load_bible_versions()

    def update_ui_texts(self):
        lang = self.get_lang_key()

        self.title(self.generator.get_locale_string(lang, "title"))
        self.instructions_label.configure(text=self.generator.get_locale_string(lang, "instructions"))
        self.verse_label.configure(text=self.generator.get_locale_string(lang, "verse_label"))
        self.reference_label.configure(text=self.generator.get_locale_string(lang, "reference_label"))
        self.bible_version_label.configure(text=self.generator.get_locale_string(lang, "bible_version_label"))
        self.fetch_btn.configure(text=self.generator.get_locale_string(lang, "fetch_verse_btn"))
        self.generate_btn.configure(text=self.generator.get_locale_string(lang, "generate_btn"))

        self.aspect_ratio_label.configure(text=self.generator.get_locale_string(lang, "aspect_ratio_label"))
        self.aspect_ratio_dropdown.configure(values=[
            self.generator.get_locale_string(lang, "ratio_square"),
            self.generator.get_locale_string(lang, "ratio_portrait"),
            self.generator.get_locale_string(lang, "ratio_landscape")
        ])

        # Keep selected option in sync
        current_ratio = self.aspect_ratio_var.get()
        if "1:1" in current_ratio or "Square" in current_ratio or "Quadrado" in current_ratio or "Cuadrado" in current_ratio:
            self.aspect_ratio_var.set(self.generator.get_locale_string(lang, "ratio_square"))
        elif "3:4" in current_ratio or "Portrait" in current_ratio or "Retrato" in current_ratio:
            self.aspect_ratio_var.set(self.generator.get_locale_string(lang, "ratio_portrait"))
        elif "4:3" in current_ratio or "Landscape" in current_ratio or "Paisagem" in current_ratio or "Paisaje" in current_ratio:
            self.aspect_ratio_var.set(self.generator.get_locale_string(lang, "ratio_landscape"))

        self.background_label.configure(text=self.generator.get_locale_string(lang, "background_label"))
        self.custom_image_btn.configure(text=self.generator.get_locale_string(lang, "custom_image_btn"))

        self.font_type_label.configure(text=self.generator.get_locale_string(lang, "font_type_label"))
        self.font_color_label.configure(text=self.generator.get_locale_string(lang, "font_color_label"))
        self.font_size_label.configure(text=self.generator.get_locale_string(lang, "font_size_label"))
        self.y_offset_label.configure(text=self.generator.get_locale_string(lang, "y_offset_label"))

        self.audio_generate_checkbox.configure(text=self.generator.get_locale_string(lang, "audio_label"))
        self.gender_label.configure(text=self.generator.get_locale_string(lang, "gender_label"))

        self.gender_dropdown.configure(values=[
            self.generator.get_locale_string(lang, "gender_female"),
            self.generator.get_locale_string(lang, "gender_male")
        ])

        current_gender = self.gender_var.get()
        if "Female" in current_gender or "Feminina" in current_gender or "Femenina" in current_gender:
            self.gender_var.set(self.generator.get_locale_string(lang, "gender_female"))
        else:
            self.gender_var.set(self.generator.get_locale_string(lang, "gender_male"))

        self.copy_alt_btn.configure(text=self.generator.get_locale_string(lang, "copy_alt_text_btn"))
        self.copy_caption_btn.configure(text=self.generator.get_locale_string(lang, "copy_caption_btn"))
        self.status_label.configure(text="")

    def load_bible_versions(self, event=None):
        import threading

        def _fetch():
            self.after(0, lambda: self.status_label.configure(text="Loading Bible versions..."))

            lang_code = "pt-BR"
            if "en" in self.get_lang_key(): lang_code = "en"
            elif "es" in self.get_lang_key(): lang_code = "es"

            # App key is ignored now as we use bible-api.com
            versions = YouVersionAPI.get_versions(lang=lang_code)

            if versions:
                self.bible_versions_map = {v["name"]: v["id"] for v in versions}
                version_names = list(self.bible_versions_map.keys())
                self.after(0, lambda: self._update_version_dropdown(version_names))
            else:
                self.after(0, lambda: self._update_version_dropdown_error())

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_version_dropdown(self, version_names):
        self.bible_version_dropdown.configure(values=version_names)
        self.bible_version_var.set(version_names[0])
        self.status_label.configure(text="")

    def _update_version_dropdown_error(self):
        self.bible_version_dropdown.configure(values=["-"])
        self.bible_version_var.set("-")
        self.status_label.configure(text="Error loading versions or invalid API key.")

    def fetch_verse(self):
        version_name = self.bible_version_var.get()
        reference = self.reference_input.get().strip()

        if version_name == "-" or not reference:
            self.status_label.configure(text="Please provide Version, and Reference.")
            return

        bible_id = self.bible_versions_map.get(version_name)
        if not bible_id:
            return

        import threading

        def _fetch():
            self.after(0, lambda: self.status_label.configure(text="Fetching verse..."))

            content = YouVersionAPI.get_passage(None, bible_id, reference)
            self.after(0, lambda: self._update_verse_ui(content))

        threading.Thread(target=_fetch, daemon=True).start()

    def _update_verse_ui(self, content):
        if content:
            self.verse_input.delete("1.0", "end")
            self.verse_input.insert("1.0", content)
            self.status_label.configure(text="Verse fetched successfully.")
            self.trigger_preview()
        else:
            self.status_label.configure(text="Error fetching verse. Check reference format (e.g., JHN.3.16).")

    def trigger_preview(self, *args):
        if hasattr(self, '_preview_after_id'):
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(500, self.preview_content)

    def clear_custom_image(self, _choice):
        self.custom_image_path = None

    def select_custom_image(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title=self.generator.get_locale_string(self.get_lang_key(), "custom_image_btn"),
            filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if file_path:
            self.custom_image_path = file_path
            self.bg_var.set(os.path.basename(file_path))
            self.trigger_preview()

    def get_current_params(self):
        verse = self.verse_input.get("1.0", "end-1c").strip()
        reference = self.reference_input.get().strip()
        background = self.bg_var.get()
        font_type = self.font_var.get()
        font_color = self.font_color_var.get().strip()
        font_size = self.font_size_var.get()
        y_offset = self.y_offset_var.get()

        ratio_selection = self.aspect_ratio_var.get()
        if "3:4" in ratio_selection:
            aspect_ratio = "3:4"
        elif "4:3" in ratio_selection:
            aspect_ratio = "4:3"
        else:
            aspect_ratio = "1:1"

        return verse, reference, background, font_type, font_color, font_size, y_offset, aspect_ratio

    def preview_content(self):
        verse, reference, background, font_type, font_color, font_size, y_offset, aspect_ratio = self.get_current_params()
        if not verse or not reference:
            return

        try:
            pil_img = self.generator.generate_image(
                self.current_lang, verse, reference, background_filename=background,
                custom_image_path=self.custom_image_path, aspect_ratio=aspect_ratio,
                font_type=font_type, font_color=font_color, font_size=font_size, y_offset=y_offset
            )

            preview_max_size = (500, 500)
            from PIL import Image
            pil_img.thumbnail(preview_max_size, Image.Resampling.LANCZOS)

            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            self.preview_label.configure(image=ctk_img, text="")
            self.preview_label.image = ctk_img
        except Exception as e:
            self.preview_label.configure(image="", text=f"Error rendering preview:\n{str(e)}")

    def generate_content(self):
        verse, reference, background, font_type, font_color, font_size, y_offset, aspect_ratio = self.get_current_params()
        if not verse or not reference:
            return

        lang = self.get_lang_key()
        lang_code = "pt"
        if "en" in lang: lang_code = "en"
        elif "es" in lang: lang_code = "es"

        from tkinter import filedialog
        safe_ref = reference.lower().replace(" ", "_").replace(":", "_")
        default_image_filename = f"{safe_ref}_{lang_code}.png"
        default_audio_filename = f"{safe_ref}_{lang_code}.mp3"

        # Prompt user for image save location before processing
        image_save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_image_filename,
            title=self.generator.get_locale_string(lang, "save_btn") + " - Imagem",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if not image_save_path:
            return

        audio_save_path = None
        if self.audio_generate_var.get():
            # Prompt user for audio save location before processing
            audio_save_path = filedialog.asksaveasfilename(
                defaultextension=".mp3",
                initialfile=default_audio_filename,
                title=self.generator.get_locale_string(lang, "save_btn") + " - Áudio",
                filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")]
            )
            if not audio_save_path:
                return

        self.status_label.configure(text="Gerando arquivos...")
        self.update()

        import threading

        def _process():
            # Generate Image to Disk
            pil_img = self.generator.generate_image(
                self.current_lang, verse, reference, background_filename=background,
                custom_image_path=self.custom_image_path, aspect_ratio=aspect_ratio,
                font_type=font_type, font_color=font_color, font_size=font_size, y_offset=y_offset
            )
            pil_img.save(image_save_path, "PNG")
            self.last_generated_image_path = image_save_path

            # Generate Texts
            self.alt_text, self.caption = self.generator.generate_texts(lang, verse, reference)

            # Generate Audio
            audio_msg = ""
            if self.audio_generate_var.get() and audio_save_path:
                gender_selection = self.gender_var.get()
                gender_key = "Male" if "Male" in gender_selection or "Masculin" in gender_selection else "Female"
                try:
                    audio_path = self.generator.generate_audio(self.current_lang, verse, reference, gender=gender_key, custom_output_path=audio_save_path)
                    audio_msg = f"\nÁudio salvo em: {os.path.abspath(audio_path)}"
                except Exception as e:
                    audio_msg = f"\nErro ao gerar áudio: {e}"

            self.after(0, self._on_generate_complete, lang, audio_msg)

        threading.Thread(target=_process, daemon=True).start()

    def _on_generate_complete(self, lang, audio_msg):
        # Update Textbox
        self.output_textbox.delete("1.0", "end")
        alt_label = self.generator.get_locale_string(lang, "alt_text_label")
        cap_label = self.generator.get_locale_string(lang, "caption_label")
        display_text = f"--- {alt_label} ---\n{self.alt_text}\n\n--- {cap_label} ---\n{self.caption}"
        self.output_textbox.insert("1.0", display_text)

        # Status Label
        msg = self.generator.get_locale_string(lang, "success_msg")
        self.status_label.configure(text=msg + audio_msg)

    def copy_alt(self):
        if self.alt_text:
            pyperclip.copy(self.alt_text)
            lang = self.get_lang_key()
            self.status_label.configure(text=self.generator.get_locale_string(lang, "copy_success_msg"))

    def copy_caption(self):
        if self.caption:
            pyperclip.copy(self.caption)
            lang = self.get_lang_key()
            self.status_label.configure(text=self.generator.get_locale_string(lang, "copy_success_msg"))

if __name__ == "__main__":
    app = App()
    app.mainloop()
