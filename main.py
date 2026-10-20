import customtkinter as ctk
from generator import Generator
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
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Language Selector
        self.lang_var = ctk.StringVar(value="Português (Brasil)")
        self.lang_dropdown = ctk.CTkOptionMenu(
            self,
            values=["Português (Brasil)", "English (US/UK)", "Español (España)"],
            variable=self.lang_var,
            command=self.change_language
        )
        self.lang_dropdown.grid(row=0, column=0, columnspan=2, pady=10, padx=20, sticky="ew")

        # Verse Input
        self.verse_label = ctk.CTkLabel(self, text="Versículo Bíblico:")
        self.verse_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")

        self.verse_input = ctk.CTkTextbox(self, height=80)
        self.verse_input.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        # Reference Input
        self.reference_label = ctk.CTkLabel(self, text="Referência (ex: Salmos 119:105):")
        self.reference_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")

        self.reference_input = ctk.CTkEntry(self)
        self.reference_input.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        # Aspect Ratio Selector
        self.aspect_ratio_label = ctk.CTkLabel(self, text="Proporção da Imagem:")
        self.aspect_ratio_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")

        self.aspect_ratio_var = ctk.StringVar(value="1:1")
        self.aspect_ratio_dropdown = ctk.CTkOptionMenu(
            self,
            values=["1:1", "3:4", "4:3"],
            variable=self.aspect_ratio_var
        )
        self.aspect_ratio_dropdown.grid(row=6, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        # Background Selector
        self.background_label = ctk.CTkLabel(self, text="Imagem de Fundo:")
        self.background_label.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="w")

        self.bg_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bg_frame.grid(row=8, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")
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

        # Generate Button
        self.generate_btn = ctk.CTkButton(self, text="Gerar Conteúdo", command=self.generate_content)
        self.generate_btn.grid(row=9, column=0, columnspan=2, pady=20)

        # Output Textbox (Alt-Text & Caption)
        self.output_textbox = ctk.CTkTextbox(self, height=150)
        self.output_textbox.grid(row=10, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        # Copy/Save Buttons Frame
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.grid(row=11, column=0, columnspan=2, pady=10)

        self.copy_alt_btn = ctk.CTkButton(self.buttons_frame, text="Copiar Alt-Text", command=self.copy_alt)
        self.copy_alt_btn.grid(row=0, column=0, padx=10)

        self.copy_caption_btn = ctk.CTkButton(self.buttons_frame, text="Copiar Legenda", command=self.copy_caption)
        self.copy_caption_btn.grid(row=0, column=1, padx=10)

        self.save_btn = ctk.CTkButton(self.buttons_frame, text="Salvar Imagem", command=self.save_image)
        self.save_btn.grid(row=0, column=2, padx=10)

        self.status_label = ctk.CTkLabel(self, text="", text_color="green")
        self.status_label.grid(row=12, column=0, columnspan=2, pady=10)

        self.alt_text = ""
        self.caption = ""
        self.last_generated_image_path = None

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

    def update_ui_texts(self):
        lang = self.get_lang_key()

        self.title(self.generator.get_locale_string(lang, "title"))
        self.verse_label.configure(text=self.generator.get_locale_string(lang, "verse_label"))
        self.reference_label.configure(text=self.generator.get_locale_string(lang, "reference_label"))

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

        self.generate_btn.configure(text=self.generator.get_locale_string(lang, "generate_btn"))
        self.copy_alt_btn.configure(text=self.generator.get_locale_string(lang, "copy_alt_text_btn"))
        self.copy_caption_btn.configure(text=self.generator.get_locale_string(lang, "copy_caption_btn"))
        self.save_btn.configure(text=self.generator.get_locale_string(lang, "save_btn"))
        self.status_label.configure(text="")

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

    def generate_content(self):
        verse = self.verse_input.get("1.0", "end-1c").strip()
        reference = self.reference_input.get().strip()
        background = self.bg_var.get()

        # Determine raw ratio from selection
        ratio_selection = self.aspect_ratio_var.get()
        if "3:4" in ratio_selection:
            aspect_ratio = "3:4"
        elif "4:3" in ratio_selection:
            aspect_ratio = "4:3"
        else:
            aspect_ratio = "1:1"

        if not verse or not reference:
            return

        lang = self.get_lang_key()

        # 1. Generate Image
        img_path = self.generator.generate_image(
            self.current_lang,
            verse,
            reference,
            background_filename=background,
            custom_image_path=self.custom_image_path,
            aspect_ratio=aspect_ratio
        )
        self.last_generated_image_path = img_path

        # 2 & 3. Generate Texts
        self.alt_text, self.caption = self.generator.generate_texts(lang, verse, reference)

        # Display Texts
        self.output_textbox.delete("1.0", "end")

        alt_label = self.generator.get_locale_string(lang, "alt_text_label")
        cap_label = self.generator.get_locale_string(lang, "caption_label")

        display_text = f"--- {alt_label} ---\n{self.alt_text}\n\n--- {cap_label} ---\n{self.caption}"
        self.output_textbox.insert("1.0", display_text)

        msg = self.generator.get_locale_string(lang, "success_msg")
        self.status_label.configure(text=msg)

    def save_image(self):
        if self.last_generated_image_path:
            lang = self.get_lang_key()
            import shutil
            from tkinter import filedialog

            # Extract filename
            filename = os.path.basename(self.last_generated_image_path)

            # Prompt user for save location
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=filename,
                title=self.generator.get_locale_string(lang, "save_btn"),
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )

            if save_path:
                shutil.copy2(self.last_generated_image_path, save_path)
                self.status_label.configure(text=self.generator.get_locale_string(lang, "save_success_msg", path=save_path))

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
