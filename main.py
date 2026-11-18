import datetime
import os
import random
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, colorchooser
from PIL import Image

import customtkinter as ctk
from book_mapping import BOOK_MAPPING
from generator import Generator
from getbible_api import GetBibleAPI
import pyperclip

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    LANG_MAP = {
        "Português (Brasil)": "pt-BR",
        "English (US/UK)": "en",
        "Español (España)": "es"
    }

    CURATED_VOTD_REFS = [
        (19, 119, "105"),
        (43, 3, "16"),
        (19, 23, "1"),
        (50, 4, "13"),
        (20, 3, "5-6"),
        (23, 41, "10"),
        (45, 8, "28"),
        (62, 4, "8"),
    ]

    def __init__(self):
        super().__init__()

        self.generator = Generator()
        self.current_lang = "Português (Brasil)"
        self.api_loading = True
        self._fetching_verse = False
        self._is_generating = False
        self._votd_offset = 0

        self.title("inclusive-bible-generator")
        self.geometry("1100x750")

        self.grid_columnconfigure(0, weight=1) # Left side controls
        self.grid_columnconfigure(1, weight=1) # Right side preview
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0) # Fixed bottom status bar

        # Main Containers
        self.left_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(1, weight=1)

        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=(0, 20), pady=(20, 8), sticky="nsew")
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
        self.instructions_label = ctk.CTkLabel(self.left_frame, text="", text_color="gray", justify="left", wraplength=460)
        self.instructions_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Bible API Fetch
        self.api_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.api_frame.grid(row=2, column=0, columnspan=2, pady=(10, 10), sticky="ew")
        self.api_frame.grid_columnconfigure((0, 1), weight=1)

        self.bible_version_label = ctk.CTkLabel(self.api_frame, text="Versão:")
        self.bible_version_label.grid(row=0, column=0, pady=(0, 5), padx=(0, 5), sticky="w")

        self.bible_version_var = ctk.StringVar()
        self.bible_version_dropdown = ctk.CTkOptionMenu(
            self.api_frame, values=["-"], variable=self.bible_version_var, state="disabled"
        )
        self.bible_version_dropdown.grid(row=1, column=0, padx=(0, 5), sticky="ew")
        self.bible_versions_map = {}

        self.fetch_btn = ctk.CTkButton(self.api_frame, text="Buscar Versículo", command=self.fetch_verse, state="disabled")
        self.fetch_btn.grid(row=1, column=1, padx=(5, 0), sticky="ew")

        # Quick Book / Chapter / Verse selector + Verse of the Day
        self.quick_ref_frame = ctk.CTkFrame(self.api_frame, fg_color="transparent")
        self.quick_ref_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        self.quick_ref_frame.grid_columnconfigure(0, weight=2)
        self.quick_ref_frame.grid_columnconfigure(1, weight=0)
        self.quick_ref_frame.grid_columnconfigure(2, weight=0)
        self.quick_ref_frame.grid_columnconfigure(3, weight=1)

        self.book_label = ctk.CTkLabel(self.quick_ref_frame, text="Livro:")
        self.book_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.chapter_label = ctk.CTkLabel(self.quick_ref_frame, text="Cap.:")
        self.chapter_label.grid(row=0, column=1, padx=4, sticky="w")
        self.verse_num_label = ctk.CTkLabel(self.quick_ref_frame, text="Verso:")
        self.verse_num_label.grid(row=0, column=2, padx=4, sticky="w")

        canonical_books = self._get_canonical_books("pt")
        default_book = canonical_books[18] if len(canonical_books) > 18 else canonical_books[0]
        self.book_var = ctk.StringVar(value=default_book)
        self.book_dropdown = ctk.CTkOptionMenu(
            self.quick_ref_frame,
            values=canonical_books,
            variable=self.book_var,
            command=lambda _choice: self.apply_quick_reference(fetch=True),
        )
        self.book_dropdown.grid(row=1, column=0, padx=(0, 5), sticky="ew")

        self.chapter_var = ctk.StringVar(value="119")
        self.chapter_entry = ctk.CTkEntry(self.quick_ref_frame, textvariable=self.chapter_var, width=54)
        self.chapter_entry.grid(row=1, column=1, padx=4)
        self.chapter_entry.bind("<Return>", lambda _e: self.apply_quick_reference(fetch=True))
        self.chapter_entry.bind("<FocusOut>", lambda _e: self.apply_quick_reference(fetch=False))

        self.verse_num_var = ctk.StringVar(value="105")
        self.verse_num_entry = ctk.CTkEntry(self.quick_ref_frame, textvariable=self.verse_num_var, width=54)
        self.verse_num_entry.grid(row=1, column=2, padx=4)
        self.verse_num_entry.bind("<Return>", lambda _e: self.apply_quick_reference(fetch=True))
        self.verse_num_entry.bind("<FocusOut>", lambda _e: self.apply_quick_reference(fetch=False))

        self.votd_btn = ctk.CTkButton(
            self.quick_ref_frame,
            text="☀️ Versículo do Dia",
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray15", "gray90"),
            command=self.load_verse_of_the_day,
        )
        self.votd_btn.grid(row=1, column=3, padx=(5, 0), sticky="ew")

        # Reference Input
        self.reference_label = ctk.CTkLabel(self.left_frame, text="Referência (ex: Salmos 119:105):")
        self.reference_label.grid(row=3, column=0, pady=(0, 0), sticky="w")

        self.reference_input = ctk.CTkEntry(self.left_frame)
        self.reference_input.grid(row=4, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Verse Input
        self.verse_header = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.verse_header.grid(row=5, column=0, columnspan=2, pady=(0, 2), sticky="ew")
        self.verse_header.grid_columnconfigure(0, weight=1)

        self.verse_label = ctk.CTkLabel(self.verse_header, text="Versículo Bíblico:")
        self.verse_label.grid(row=0, column=0, sticky="w")

        self.clear_inputs_btn = ctk.CTkButton(
            self.verse_header,
            text="✕",
            width=28,
            height=22,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray20", "gray85"),
            command=self.clear_verse_inputs,
        )
        self.clear_inputs_btn.grid(row=0, column=1, sticky="e")
        self._bind_hint(self.clear_inputs_btn, "clear_inputs_tooltip")

        self.verse_input = ctk.CTkTextbox(self.left_frame, height=80)
        self.verse_input.grid(row=6, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        self.verse_input.bind("<Tab>", self._focus_next_widget)
        self.verse_input.bind("<Shift-Tab>", self._focus_prev_widget)
        self.verse_input.bind("<ISO_Left_Tab>", self._focus_prev_widget)

        # Background Selector
        self.background_label = ctk.CTkLabel(self.left_frame, text="Imagem de Fundo:")
        self.background_label.grid(row=7, column=0, pady=(10, 0), sticky="w")

        self.bg_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.bg_frame.grid(row=8, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        self.bg_frame.grid_columnconfigure(0, weight=1)
        self.bg_frame.grid_columnconfigure(1, weight=1)

        self.bg_var = ctk.StringVar(value="default.png")
        try:
            bg_files = [
                f for f in os.listdir(self.generator.backgrounds_dir)
                if (f.endswith('.png') or f.endswith('.jpg'))
                and self.generator._is_safe_regular_file(os.path.join(self.generator.backgrounds_dir, f))
            ]
        except OSError:
            bg_files = []
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

        self.clear_custom_img_btn = ctk.CTkButton(
            self.bg_frame,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray20", "gray85"),
            command=lambda: self.clear_custom_image(self._default_bg_file),
        )
        self.clear_custom_img_btn.grid(row=0, column=2, padx=(4, 0))
        self._bind_hint(self.clear_custom_img_btn, "clear_custom_image_tooltip")
        self.clear_custom_img_btn.grid_remove()
        self._default_bg_file = bg_files[0]

        self.bg_dim_label = ctk.CTkLabel(self.bg_frame, text="Escurecer Fundo: 50%")
        self.bg_dim_label.grid(row=1, column=0, columnspan=2, pady=(8, 2), sticky="w")

        self.bg_dim_var = ctk.IntVar(value=50)
        self.bg_dim_slider = ctk.CTkSlider(
            self.bg_frame,
            from_=0,
            to=85,
            number_of_steps=17,
            variable=self.bg_dim_var,
            command=self._on_bg_dim_changed,
        )
        self.bg_dim_slider.grid(row=2, column=0, columnspan=3, sticky="ew")
        self._bind_slider_keys(self.bg_dim_slider, self.bg_dim_var, 5, 0, 85, self._on_bg_dim_changed)

        self.contrast_warning_frame = ctk.CTkFrame(
            self.bg_frame,
            fg_color=("#FFF3CD", "#3B2F14"),
            corner_radius=6,
        )
        self.contrast_warning_frame.grid(row=3, column=0, columnspan=2, pady=(8, 0), sticky="ew")
        self.contrast_warning_frame.grid_columnconfigure(0, weight=1)
        self.contrast_warning_label = ctk.CTkLabel(
            self.contrast_warning_frame,
            text="",
            text_color=("#664D03", "#FFECB5"),
            justify="left",
            wraplength=320,
        )
        self.contrast_warning_label.grid(row=0, column=0, padx=(10, 6), pady=6, sticky="w")
        self.contrast_fix_btn = ctk.CTkButton(
            self.contrast_warning_frame,
            text="",
            width=110,
            height=26,
            command=self.auto_fix_contrast,
        )
        self.contrast_fix_btn.grid(row=0, column=1, padx=(0, 8), pady=6, sticky="e")
        self.contrast_warning_frame.grid_remove()

        # Font customization block
        self.font_config_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.font_config_frame.grid(row=9, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        self.font_config_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.font_type_label = ctk.CTkLabel(self.font_config_frame, text="Tipo de Fonte:")
        self.font_type_label.grid(row=0, column=0, pady=(0, 5), padx=(0, 5), sticky="w")

        self.font_var = ctk.StringVar(value="Roboto-Regular.ttf")
        try:
            font_files = [
                f for f in os.listdir(self.generator.fonts_dir)
                if f.endswith('.ttf')
                and self.generator._is_safe_regular_file(os.path.join(self.generator.fonts_dir, f))
            ]
        except OSError:
            font_files = []
        if not font_files:
            font_files = ["Roboto-Regular.ttf"]
        self.font_dropdown = ctk.CTkOptionMenu(
            self.font_config_frame, values=font_files, variable=self.font_var, command=self.trigger_preview
        )
        self.font_dropdown.grid(row=1, column=0, padx=(0, 5), sticky="ew")

        self.font_color_label = ctk.CTkLabel(self.font_config_frame, text="Cor do Texto:")
        self.font_color_label.grid(row=0, column=1, pady=(0, 5), padx=5, sticky="w")

        self.font_color_var = ctk.StringVar(value="#FFFFFF")

        # Color selector UI with option for Custom
        self.color_selector_frame = ctk.CTkFrame(self.font_config_frame, fg_color="transparent")
        self.color_selector_frame.grid(row=1, column=1, padx=5, sticky="ew")
        self.color_selector_frame.grid_columnconfigure((0, 1), weight=1)
        self.color_selector_frame.grid_columnconfigure(2, weight=0)

        self.font_color_dropdown = ctk.CTkOptionMenu(
            self.color_selector_frame,
            values=["Branco", "Preto", "Dourado", "Vermelho", "Personalizado..."],
            command=self.on_color_selected
        )
        self.font_color_dropdown.grid(row=0, column=0, sticky="ew")

        self.font_color_entry = ctk.CTkEntry(self.color_selector_frame, textvariable=self.font_color_var, width=80)
        self.font_color_entry.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        self.font_color_entry.bind("<KeyRelease>", self._on_custom_color_typed)

        self.color_picker_btn = ctk.CTkButton(
            self.color_selector_frame,
            text="🎨",
            width=32,
            border_width=1,
            border_color=("gray60", "gray40"),
            command=self.pick_custom_color
        )
        self.color_picker_btn.grid(row=0, column=2, padx=(4, 0))
        self._bind_hint(self.color_picker_btn, "color_picker_title")
        self._sync_color_swatch()

        # Initially hide the custom entry box and picker, only show when Custom... is selected
        self.font_color_entry.grid_remove()
        self.color_picker_btn.grid_remove()

        self.font_size_header = ctk.CTkFrame(self.font_config_frame, fg_color="transparent")
        self.font_size_header.grid(row=0, column=2, pady=(0, 5), padx=(5, 0), sticky="ew")
        self.font_size_header.grid_columnconfigure(0, weight=1)

        self.font_size_label = ctk.CTkLabel(self.font_size_header, text="Tamanho da Fonte: 60")
        self.font_size_label.grid(row=0, column=0, sticky="w")

        self.reset_font_size_btn = ctk.CTkButton(
            self.font_size_header,
            text="↺ 60",
            width=48,
            height=22,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray20", "gray85"),
            command=self.reset_font_size,
        )
        self.reset_font_size_btn.grid(row=0, column=1, sticky="e")
        self._bind_hint(self.reset_font_size_btn, "reset_font_size_tooltip")

        self.font_size_var = ctk.IntVar(value=60)
        self.font_size_slider = ctk.CTkSlider(self.font_config_frame, from_=20, to=120, variable=self.font_size_var, command=self._on_font_size_changed)
        self.font_size_slider.grid(row=1, column=2, padx=(5, 0), sticky="ew")
        self._bind_slider_keys(self.font_size_slider, self.font_size_var, 2, 20, 120, self._on_font_size_changed)

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

        self.y_offset_header = ctk.CTkFrame(self.bottom_config_frame, fg_color="transparent")
        self.y_offset_header.grid(row=0, column=1, pady=(0, 5), padx=5, sticky="ew")
        self.y_offset_header.grid_columnconfigure(0, weight=1)

        self.y_offset_label = ctk.CTkLabel(self.y_offset_header, text="Posição Vertical (Y): 0")
        self.y_offset_label.grid(row=0, column=0, sticky="w")

        self.reset_y_btn = ctk.CTkButton(
            self.y_offset_header,
            text="↺ 0",
            width=44,
            height=22,
            fg_color="transparent",
            border_width=1,
            border_color=("gray60", "gray40"),
            text_color=("gray20", "gray85"),
            command=self.reset_y_offset
        )
        self.reset_y_btn.grid(row=0, column=1, sticky="e")
        self._bind_hint(self.reset_y_btn, "reset_y_tooltip")

        self.y_offset_var = ctk.IntVar(value=0)
        self.y_offset_slider = ctk.CTkSlider(self.bottom_config_frame, from_=-400, to=400, variable=self.y_offset_var, command=self._on_y_offset_changed)
        self.y_offset_slider.grid(row=1, column=1, padx=5, sticky="ew")
        self._bind_slider_keys(self.y_offset_slider, self.y_offset_var, 10, -400, 400, self._on_y_offset_changed)

        # Audio Configuration block
        self.audio_config_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.audio_config_frame.grid(row=11, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        self.audio_config_frame.grid_columnconfigure((0, 1), weight=1)

        self.audio_generate_var = ctk.BooleanVar(value=False)
        self.audio_generate_checkbox = ctk.CTkCheckBox(self.audio_config_frame, text="Gerar Áudio (TTS)?", variable=self.audio_generate_var, command=self.toggle_audio_options)
        self.audio_generate_checkbox.grid(row=0, column=0, pady=(0, 5), padx=(0, 5), sticky="w")

        self.gender_label = ctk.CTkLabel(self.audio_config_frame, text="Voz:")
        self.gender_label.grid(row=0, column=1, pady=(0, 5), padx=5, sticky="w")

        self.gender_var = ctk.StringVar(value="Female")
        self.gender_dropdown = ctk.CTkOptionMenu(
            self.audio_config_frame,
            values=["Female", "Male"],
            variable=self.gender_var,
            state="disabled"
        )
        self.gender_dropdown.grid(row=1, column=1, padx=(5, 0), sticky="ew")

        # Bind text inputs to preview
        self.verse_input.bind("<KeyRelease>", self.trigger_preview)
        self.reference_input.bind("<KeyRelease>", self.trigger_preview)

        # Bind enter key for quick fetch
        self.reference_input.bind("<Return>", lambda event: self.fetch_verse())

        # Desktop keyboard shortcuts
        self.bind("<Control-g>", lambda _e: self.generate_content())
        self.bind("<Control-G>", lambda _e: self.generate_content())
        self.bind("<Control-f>", lambda _e: self.fetch_verse())
        self.bind("<Control-F>", lambda _e: self.fetch_verse())
        self.bind("<Control-d>", lambda _e: self.load_verse_of_the_day())
        self.bind("<Control-D>", lambda _e: self.load_verse_of_the_day())
        self.bind("<Control-Shift-C>", lambda _e: self.copy_alt())
        self.bind("<Control-Shift-c>", lambda _e: self.copy_alt())
        self.bind("<Control-Shift-L>", lambda _e: self.copy_caption())
        self.bind("<Control-Shift-l>", lambda _e: self.copy_caption())
        self.bind("<Control-o>", lambda _e: self.open_output_folder())
        self.bind("<Control-O>", lambda _e: self.open_output_folder())
        self.bind("<Control-Shift-X>", lambda _e: self.clear_verse_inputs())
        self.bind("<Control-Shift-x>", lambda _e: self.clear_verse_inputs())

        # Output Textbox (Alt-Text & Caption)
        self.output_textbox = ctk.CTkTextbox(self.left_frame, height=150, state="disabled")
        self.output_textbox.grid(row=12, column=0, columnspan=2, pady=10, sticky="ew")
        self.output_textbox.bind("<Tab>", self._focus_next_widget)
        self.output_textbox.bind("<Shift-Tab>", self._focus_prev_widget)
        self.output_textbox.bind("<ISO_Left_Tab>", self._focus_prev_widget)

        # Generate Button
        self.generate_btn = ctk.CTkButton(self.left_frame, text="Gerar Conteúdo", command=self.generate_content)
        self.generate_btn.grid(row=13, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        self._bind_hint(self.generate_btn, "generate_btn", "Ctrl+G")

        # Copy/Save Buttons Frame
        self.buttons_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.buttons_frame.grid(row=14, column=0, columnspan=2, pady=10, sticky="ew")
        self.buttons_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.copy_alt_btn = ctk.CTkButton(self.buttons_frame, text="Copiar Alt-Text", command=self.copy_alt, state="disabled")
        self.copy_alt_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        self._bind_hint(self.copy_alt_btn, "copy_alt_text_btn", "Ctrl+Shift+C")

        self.copy_caption_btn = ctk.CTkButton(self.buttons_frame, text="Copiar Legenda", command=self.copy_caption, state="disabled")
        self.copy_caption_btn.grid(row=0, column=1, padx=4, sticky="ew")
        self._bind_hint(self.copy_caption_btn, "copy_caption_btn", "Ctrl+Shift+L")

        self.open_output_btn = ctk.CTkButton(self.buttons_frame, text="📂 Abrir Pasta", command=self.open_output_folder, state="disabled")
        self.open_output_btn.grid(row=0, column=2, padx=(4, 0), sticky="ew")
        self._bind_hint(self.open_output_btn, "open_output_btn", "Ctrl+O")

        self._bind_hint(self.fetch_btn, "fetch_verse_btn", "Ctrl+F")
        self._bind_hint(self.votd_btn, "votd_btn", "Ctrl+D")

        # Fixed bottom status bar (always visible regardless of scroll position)
        self.status_bar = ctk.CTkFrame(self, corner_radius=6, fg_color=("gray92", "gray17"))
        self.status_bar.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.status_bar, text="", text_color="gray", anchor="w", wraplength=1040)
        self.status_label.grid(row=0, column=0, padx=12, pady=6, sticky="ew")

        self.alt_text = ""
        self.caption = ""
        self.last_generated_image_path = None

        self._last_preview_params = None
        self._btn_reset_timers = {}

        # Start initial preview
        self.trigger_preview()

        # Image Preview
        self.preview_label = ctk.CTkLabel(
            self.right_frame,
            text=self.generator.get_locale_string(self.get_lang_key(), "preview_empty_state"),
            text_color="gray",
            cursor="sb_v_double_arrow",
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        self.preview_label.bind("<ButtonPress-1>", self._start_preview_drag)
        self.preview_label.bind("<B1-Motion>", self._on_preview_drag)
        self.preview_label.bind("<Double-Button-1>", lambda _e: self.reset_y_offset())
        self.preview_label.bind("<Enter>", lambda _e: self._show_hover_hint("drag_preview_hint"))
        self.preview_label.bind("<Leave>", lambda _e: self._clear_hover_hint())

        # Initial UI Update
        self.update_ui_texts()
        self.load_bible_versions()

    _CANONICAL_BOOKS_CACHE = {}

    def _get_canonical_books(self, lang_prefix):
        cached = self._CANONICAL_BOOKS_CACHE.get(lang_prefix)
        if cached is not None:
            return cached
        mapping = BOOK_MAPPING.get(lang_prefix, BOOK_MAPPING["en"])
        seen_nrs = set()
        books = []
        for name, nr in mapping.items():
            if nr not in seen_nrs:
                seen_nrs.add(nr)
                books.append(name)
        self._CANONICAL_BOOKS_CACHE[lang_prefix] = books
        return books

    def _get_lang_prefix(self):
        return self.get_lang_key()[:2]

    def apply_quick_reference(self, fetch=True):
        book = self.book_var.get().strip()
        chapter = re.sub(r"\D", "", self.chapter_var.get())[:3] or "1"
        raw_verse = re.sub(r"[^\d\-]", "", self.verse_num_var.get().strip())[:10].strip("-")
        if "-" in raw_verse:
            parts = [p for p in raw_verse.split("-") if p]
            verse = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else (parts[0] if parts else "")
        else:
            verse = raw_verse
        ref = f"{book} {chapter}:{verse}" if verse else f"{book} {chapter}"
        self.reference_input.delete(0, "end")
        self.reference_input.insert(0, ref)
        self.trigger_preview()
        if fetch and not getattr(self, "api_loading", False):
            self.fetch_verse()

    def _bind_hint(self, widget, hint_key, shortcut=None):
        """Show status-bar hint on both pointer hover and keyboard focus."""
        show = (
            (lambda _e: self._show_shortcut_hint(hint_key, shortcut))
            if shortcut
            else (lambda _e: self._show_hover_hint(hint_key))
        )
        clear = lambda _e: self._clear_hover_hint()
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", clear)
        widget.bind("<FocusIn>", show)
        widget.bind("<FocusOut>", clear)

    def _bind_slider_keys(self, slider, var, step, min_val, max_val, on_change):
        """Allow keyboard arrow keys to adjust CTkSlider values."""
        def adjust(delta):
            nxt = max(min_val, min(max_val, int(var.get()) + delta))
            var.set(nxt)
            on_change(nxt)
            return "break"

        slider.bind("<Left>", lambda _e: adjust(-step))
        slider.bind("<Right>", lambda _e: adjust(step))
        slider.bind("<Shift-Left>", lambda _e: adjust(-step * 2))
        slider.bind("<Shift-Right>", lambda _e: adjust(step * 2))

    def _focus_next_widget(self, event):
        event.widget.tk_focusNext().focus_set()
        return "break"

    def _focus_prev_widget(self, event):
        event.widget.tk_focusPrev().focus_set()
        return "break"

    def load_verse_of_the_day(self):
        if getattr(self, "_fetching_verse", False) or getattr(self, "api_loading", False):
            return
        idx = (datetime.date.today().toordinal() + self._votd_offset) % len(self.CURATED_VOTD_REFS)
        self._votd_offset += 1
        book_nr, chapter, verse = self.CURATED_VOTD_REFS[idx]
        lang_prefix = self._get_lang_prefix()
        books = self._get_canonical_books(lang_prefix)
        book_name = books[book_nr - 1] if 1 <= book_nr <= len(books) else books[0]
        self.book_var.set(book_name)
        self.chapter_var.set(str(chapter))
        self.verse_num_var.set(verse)
        self.apply_quick_reference(fetch=True)

    def _on_bg_dim_changed(self, value):
        self.trigger_preview()

    def _on_font_size_changed(self, value):
        self.trigger_preview()

    def _on_y_offset_changed(self, value):
        self.trigger_preview()

    def reset_font_size(self):
        self.font_size_var.set(60)
        self._on_font_size_changed(60)

    def clear_verse_inputs(self):
        self.reference_input.delete(0, "end")
        self.verse_input.delete("1.0", "end")
        self._last_preview_params = None
        self.trigger_preview()
        self.preview_content()
        self.reference_input.focus_set()

    def reset_y_offset(self):
        self.y_offset_var.set(0)
        self._on_y_offset_changed(0)

    def toggle_audio_options(self):
        if self.audio_generate_var.get():
            self.gender_dropdown.configure(state="normal")
            self.gender_label.configure(text_color=("gray10", "gray90"))
        else:
            self.gender_dropdown.configure(state="disabled")
            self.gender_label.configure(text_color=("gray55", "gray50"))

    def get_lang_key(self):
        return self.LANG_MAP.get(self.current_lang, "pt-BR")

    def change_language(self, choice):
        self.current_lang = choice
        had_ref = bool(self.reference_input.get().strip())
        self.update_ui_texts()
        if had_ref:
            self.apply_quick_reference(fetch=False)
        self.load_bible_versions()

    def update_ui_texts(self):
        lang = self.get_lang_key()

        self.title(self.generator.get_locale_string(lang, "title"))
        self.instructions_label.configure(text=self.generator.get_locale_string(lang, "instructions"))
        self._last_verse_label_text = None
        self.verse_label.configure(text=self.generator.get_locale_string(lang, "verse_label"))
        self.reference_label.configure(text=self.generator.get_locale_string(lang, "reference_label"))
        self.bible_version_label.configure(text=self.generator.get_locale_string(lang, "bible_version_label"))
        self.fetch_btn.configure(text=self.generator.get_locale_string(lang, "fetch_verse_btn"))
        self.book_label.configure(text=self.generator.get_locale_string(lang, "book_label"))
        self.chapter_label.configure(text=self.generator.get_locale_string(lang, "chapter_label"))
        self.verse_num_label.configure(text=self.generator.get_locale_string(lang, "verse_num_label"))
        self.votd_btn.configure(text=self.generator.get_locale_string(lang, "votd_btn"))

        lang_prefix = self._get_lang_prefix()
        books = self._get_canonical_books(lang_prefix)
        current_book = self.book_var.get()
        book_nr = None
        for prefix in ("pt", "en", "es"):
            if current_book in BOOK_MAPPING.get(prefix, {}):
                book_nr = BOOK_MAPPING[prefix][current_book]
                break
        self.book_dropdown.configure(values=books)
        if book_nr is not None and 1 <= book_nr <= len(books):
            self.book_var.set(books[book_nr - 1])
        elif books and current_book not in books:
            self.book_var.set(books[0])

        self.generate_btn.configure(text=self.generator.get_locale_string(lang, "generate_btn"))


        ratio_square = self.generator.get_locale_string(lang, "ratio_square")
        ratio_portrait = self.generator.get_locale_string(lang, "ratio_portrait")
        ratio_landscape = self.generator.get_locale_string(lang, "ratio_landscape")

        self.aspect_ratio_label.configure(text=self.generator.get_locale_string(lang, "aspect_ratio_label"))
        self.aspect_ratio_dropdown.configure(values=[
            ratio_square,
            ratio_portrait,
            ratio_landscape,
        ])

        # Keep selected option in sync
        current_ratio = self.aspect_ratio_var.get()
        if "1:1" in current_ratio or "Square" in current_ratio or "Quadrado" in current_ratio or "Cuadrado" in current_ratio:
            self.aspect_ratio_var.set(ratio_square)
        elif "3:4" in current_ratio or "Portrait" in current_ratio or "Retrato" in current_ratio:
            self.aspect_ratio_var.set(ratio_portrait)
        elif "4:3" in current_ratio or "Landscape" in current_ratio or "Paisagem" in current_ratio or "Paisaje" in current_ratio:
            self.aspect_ratio_var.set(ratio_landscape)

        self.background_label.configure(text=self.generator.get_locale_string(lang, "background_label"))
        self.custom_image_btn.configure(text=self.generator.get_locale_string(lang, "custom_image_btn"))
        self.bg_dim_label.configure(text=f"{self.generator.get_locale_string(lang, 'background_dim_label')}: {int(self.bg_dim_var.get())}%")

        self.font_type_label.configure(text=self.generator.get_locale_string(lang, "font_type_label"))

        color_white = self.generator.get_locale_string(lang, "color_white")
        color_black = self.generator.get_locale_string(lang, "color_black")
        color_gold = self.generator.get_locale_string(lang, "color_gold")
        color_red = self.generator.get_locale_string(lang, "color_red")
        color_custom = self.generator.get_locale_string(lang, "color_custom")

        self.font_color_dropdown.configure(values=[
            color_white,
            color_black,
            color_gold,
            color_red,
            color_custom,
        ])

        # Keep selected color in sync with new language
        current_color = self.font_color_var.get()
        preset_map = {
            "#FFFFFF": color_white,
            "#000000": color_black,
            "#FFD700": color_gold,
            "#FF0000": color_red,
        }
        if current_color in preset_map:
            self.font_color_dropdown.set(preset_map[current_color])
            self.font_color_entry.grid_remove()
            self.color_picker_btn.grid_remove()
        else:
            self.font_color_dropdown.set(color_custom)
            self.font_color_entry.grid()
            self.color_picker_btn.grid()
        self.font_color_label.configure(text=self.generator.get_locale_string(lang, "font_color_label"))
        self.font_size_label.configure(text=f"{self.generator.get_locale_string(lang, 'font_size_label')}: {int(self.font_size_var.get())}")
        self.y_offset_label.configure(text=f"{self.generator.get_locale_string(lang, 'y_offset_label')}: {int(self.y_offset_var.get())}")

        self.audio_generate_checkbox.configure(text=self.generator.get_locale_string(lang, "audio_label"))
        self.gender_label.configure(text=self.generator.get_locale_string(lang, "gender_label"))

        gender_female = self.generator.get_locale_string(lang, "gender_female")
        gender_male = self.generator.get_locale_string(lang, "gender_male")

        self.gender_dropdown.configure(values=[
            gender_female,
            gender_male,
        ])

        current_gender = self.gender_var.get()
        if "Female" in current_gender or "Feminina" in current_gender or "Femenina" in current_gender:
            self.gender_var.set(gender_female)
        else:
            self.gender_var.set(gender_male)

        self.copy_alt_btn.configure(text=self.generator.get_locale_string(lang, "copy_alt_text_btn"))
        self.copy_caption_btn.configure(text=self.generator.get_locale_string(lang, "copy_caption_btn"))
        self.open_output_btn.configure(text=self.generator.get_locale_string(lang, "open_output_btn"))
        self.contrast_warning_label.configure(text=self.generator.get_locale_string(lang, "contrast_warning_msg"))
        self.contrast_fix_btn.configure(text=self.generator.get_locale_string(lang, "contrast_fix_btn"))
        self._showing_hover_hint = False
        self.status_label.configure(text="", text_color="gray")
        self._update_contrast_warning()
        if not getattr(self.preview_label, "image", None):
            self.preview_label.configure(text=self.generator.get_locale_string(lang, "preview_empty_state"))

    def load_bible_versions(self, event=None):
        # ⚡ Bolt: GetBibleAPI.get_versions() is an in-memory lookup; avoid spawning a thread & flickering UI
        lang = self.get_lang_key()
        lang_code = "pt-BR"
        if "en" in lang:
            lang_code = "en"
        elif "es" in lang:
            lang_code = "es"

        versions = GetBibleAPI.get_versions(lang=lang_code)
        if versions:
            self.bible_versions_map = {v["name"]: v["id"] for v in versions}
            self._update_version_dropdown(list(self.bible_versions_map.keys()))
        else:
            self._update_version_dropdown_error()

    def _update_version_dropdown(self, version_names):
        self.api_loading = False
        self.bible_version_dropdown.configure(values=version_names, state="normal")
        self.bible_version_var.set(version_names[0])
        self.status_label.configure(text="")
        self.trigger_preview()
        if not getattr(self, "_initial_verse_loaded", False):
            self._initial_verse_loaded = True
            if not self.reference_input.get().strip() and not self.verse_input.get("1.0", "end-1c").strip():
                self.apply_quick_reference(fetch=True)

    def _update_version_dropdown_error(self):
        self.api_loading = False
        self.bible_version_dropdown.configure(values=["-"])
        self.bible_version_var.set("-")
        lang = self.get_lang_key()
        self.status_label.configure(text=self.generator.get_locale_string(lang, "error_loading_versions_msg"), text_color="red")

    def fetch_verse(self):
        if getattr(self, "_fetching_verse", False) or getattr(self, "api_loading", False):
            return

        version_name = self.bible_version_var.get()
        reference = self.reference_input.get().strip()
        lang = self.get_lang_key()

        if version_name == "-" or not reference:
            self.status_label.configure(text=self.generator.get_locale_string(lang, "missing_version_ref_msg"), text_color="red")
            if not reference:
                self.reference_input.focus_set()
            return

        bible_id = self.bible_versions_map.get(version_name)
        if not bible_id:
            return

        self._fetching_verse = True
        self._last_fetch_state = "disabled"
        original_text = self.generator.get_locale_string(lang, "fetch_verse_btn")
        self.fetch_btn.configure(state="disabled", text="⏳ " + original_text)
        self.votd_btn.configure(state="disabled")
        self.book_dropdown.configure(state="disabled")

        def _fetch():
            fetching_msg = self.generator.get_locale_string(lang, "fetching_verse_msg")
            self.after(0, lambda: self.status_label.configure(text=fetching_msg, text_color="gray"))

            try:
                content = GetBibleAPI.get_passage(bible_id, reference, lang)
            except Exception:
                content = None
            self.after(0, lambda: self._update_verse_ui(content))

        threading.Thread(target=_fetch, daemon=True).start()

    def _schedule_button_reset(self, button, locale_key):
        timer_id = self._btn_reset_timers.pop(button, None)
        if timer_id is not None:
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass

        def _reset():
            self._btn_reset_timers.pop(button, None)
            text = self.generator.get_locale_string(self.get_lang_key(), locale_key)
            button.configure(text=text)

        self._btn_reset_timers[button] = self.after(2000, _reset)

    def _update_verse_ui(self, content):
        self._fetching_verse = False
        self._last_fetch_state = "normal"
        self.fetch_btn.configure(state="normal")
        self.votd_btn.configure(state="normal")
        self.book_dropdown.configure(state="normal")
        lang = self.get_lang_key()
        original_text = self.generator.get_locale_string(lang, "fetch_verse_btn")
        if content:
            self.verse_input.delete("1.0", "end")
            self.verse_input.insert("1.0", content[:5000])
            self.status_label.configure(text=self.generator.get_locale_string(lang, "verse_fetched_msg"), text_color="green")

            self.fetch_btn.configure(text="✓ " + original_text)
            self._schedule_button_reset(self.fetch_btn, "fetch_verse_btn")

            self.trigger_preview()
        else:
            self.fetch_btn.configure(text=original_text)
            self.status_label.configure(text=self.generator.get_locale_string(lang, "error_fetching_verse_msg"), text_color="red")

    def _show_shortcut_hint(self, locale_key, shortcut):
        label = self.generator.get_locale_string(self.get_lang_key(), locale_key)
        self._set_hover_hint_text(f"{label} ({shortcut})")

    def _show_hover_hint(self, locale_key):
        hint_text = self.generator.get_locale_string(self.get_lang_key(), locale_key)
        self._set_hover_hint_text(hint_text)

    def _set_hover_hint_text(self, hint_text):
        if not getattr(self, "_showing_hover_hint", False):
            self._saved_status = (
                self.status_label.cget("text"),
                self.status_label.cget("text_color"),
            )
        self._showing_hover_hint = True
        self._active_hint_text = hint_text
        self.status_label.configure(text=hint_text, text_color="gray")

    def _clear_hover_hint(self):
        if getattr(self, "_showing_hover_hint", False):
            self._showing_hover_hint = False
            current_text = self.status_label.cget("text")
            if current_text == getattr(self, "_active_hint_text", None):
                saved_text, saved_color = getattr(self, "_saved_status", ("", "gray"))
                self.status_label.configure(text=saved_text, text_color=saved_color)

    def _start_preview_drag(self, event):
        self._drag_start_y = event.y_root
        self._drag_start_offset = self.y_offset_var.get()

    def _on_preview_drag(self, event):
        if not hasattr(self, "_drag_start_y"):
            return
        delta = (event.y_root - self._drag_start_y) * 2
        updated = max(-400, min(400, int(round(self._drag_start_offset + delta))))
        if updated != self.y_offset_var.get():
            self.y_offset_var.set(updated)
            self.trigger_preview()

    def _update_contrast_warning(self):
        if not hasattr(self, "contrast_warning_frame"):
            return
        if self._is_low_contrast():
            lang = self.get_lang_key()
            self.contrast_warning_label.configure(
                text=self.generator.get_locale_string(lang, "contrast_warning_msg")
            )
            self.contrast_fix_btn.configure(
                text=self.generator.get_locale_string(lang, "contrast_fix_btn")
            )
            self.contrast_warning_frame.grid()
        else:
            self.contrast_warning_frame.grid_remove()

    def _get_background_luminance(self):
        bg_path = self.custom_image_path or os.path.join(self.generator.backgrounds_dir, self.bg_var.get())
        cache = getattr(self, "_bg_luminance_cache", None)
        if cache is None:
            cache = {}
            self._bg_luminance_cache = cache
        if bg_path in cache:
            return cache[bg_path]
        lum = 0.35
        try:
            if os.path.isfile(bg_path) and self.generator._is_safe_regular_file(bg_path):
                with Image.open(bg_path) as img:
                    thumb = img.convert("RGB").resize((16, 16))
                    pixels = list(thumb.getdata())
                    if pixels:
                        lum = sum((0.299 * r + 0.587 * g + 0.114 * b) / 255 for r, g, b in pixels) / len(pixels)
        except Exception:
            pass
        cache[bg_path] = lum
        return lum

    def _is_low_contrast(self):
        color = self.font_color_var.get().strip()
        lum = self._color_luminance(color)
        if lum is None:
            return False
        bg_dim = max(0, min(100, int(self.bg_dim_var.get())))
        effective_bg_lum = self._get_background_luminance() * (1.0 - (bg_dim / 100.0))
        lighter = max(lum, effective_bg_lum)
        darker = min(lum, effective_bg_lum)
        contrast_ratio = (lighter + 0.05) / (darker + 0.05)
        return contrast_ratio < 4.5

    def auto_fix_contrast(self):
        lum = self._color_luminance(self.font_color_var.get().strip())
        if lum is None:
            return
        if lum > 0.5:
            # Darken background until contrast ratio reaches >= 4.5 (or max 85% dim)
            base_bg_lum = self._get_background_luminance()
            if base_bg_lum > 0:
                target_bg_lum = max(0.0, ((lum + 0.05) / 4.5) - 0.05)
                needed_dim = int(min(85, max(45, round((1.0 - (target_bg_lum / base_bg_lum)) * 100))))
            else:
                needed_dim = 45
            self.bg_dim_var.set(needed_dim)
        else:
            self.bg_dim_var.set(0)

        if self._is_low_contrast():
            # Medium/dark text (e.g., #FF0000) still fails 4.5:1 even at 0% dim; switch to white + darkened bg
            self.font_color_var.set("#FFFFFF")
            lang = self.get_lang_key()
            self.font_color_dropdown.set(self.generator.get_locale_string(lang, "color_white"))
            self.font_color_entry.grid_remove()
            self.color_picker_btn.grid_remove()
            base_bg_lum = self._get_background_luminance()
            if base_bg_lum > 0:
                target_bg_lum = max(0.0, ((1.0 + 0.05) / 4.5) - 0.05)
                needed_dim = int(min(85, max(45, round((1.0 - (target_bg_lum / base_bg_lum)) * 100))))
            else:
                needed_dim = 45
            self.bg_dim_var.set(needed_dim)
        self.trigger_preview()

    def trigger_preview(self, *args):
        # ⚡ Bolt: Skip redundant CustomTkinter .configure() redraws when slider values or button states are unchanged
        lang = self.get_lang_key()
        font_size = int(self.font_size_var.get())
        y_offset = int(self.y_offset_var.get())
        bg_dim = int(self.bg_dim_var.get())

        if getattr(self, "_last_label_state", None) != (lang, font_size, y_offset, bg_dim):
            self._last_label_state = (lang, font_size, y_offset, bg_dim)
            self.font_size_label.configure(text=f"{self.generator.get_locale_string(lang, 'font_size_label')}: {font_size}")
            self.y_offset_label.configure(text=f"{self.generator.get_locale_string(lang, 'y_offset_label')}: {y_offset}")
            self.bg_dim_label.configure(text=f"{self.generator.get_locale_string(lang, 'background_dim_label')}: {bg_dim}%")

        reset_font_state = "normal" if font_size != 60 else "disabled"
        if getattr(self, "_last_reset_font_state", None) != reset_font_state:
            self._last_reset_font_state = reset_font_state
            self.reset_font_size_btn.configure(state=reset_font_state)

        reset_y_state = "normal" if y_offset != 0 else "disabled"
        if getattr(self, "_last_reset_y_state", None) != reset_y_state:
            self._last_reset_y_state = reset_y_state
            self.reset_y_btn.configure(state=reset_y_state)

        self._update_contrast_warning()

        verse = self.verse_input.get("1.0", "end-1c").strip()
        reference = self.reference_input.get().strip()

        verse_base_label = self.generator.get_locale_string(lang, "verse_label")
        verse_label_text = f"{verse_base_label} ({len(verse)}/5000)" if verse else verse_base_label
        verse_label_color = "red" if len(verse) > 5000 else ("gray10", "gray90")
        if getattr(self, "_last_verse_label_state", None) != (verse_label_text, verse_label_color):
            self._last_verse_label_state = (verse_label_text, verse_label_color)
            self.verse_label.configure(text=verse_label_text, text_color=verse_label_color)

        clear_state = "normal" if (verse or reference) else "disabled"
        if getattr(self, "_last_clear_state", None) != clear_state:
            self._last_clear_state = clear_state
            self.clear_inputs_btn.configure(state=clear_state)

        fetch_state = (
            "normal"
            if reference and not getattr(self, "api_loading", False) and not getattr(self, "_fetching_verse", False)
            else "disabled"
        )
        if getattr(self, "_last_fetch_state", None) != fetch_state:
            self._last_fetch_state = fetch_state
            self.fetch_btn.configure(state=fetch_state)

        generate_state = (
            "normal"
            if verse and reference and not getattr(self, "_is_generating", False)
            else "disabled"
        )
        if getattr(self, "_last_generate_state", None) != generate_state:
            self._last_generate_state = generate_state
            self.generate_btn.configure(state=generate_state)

        if hasattr(self, '_preview_after_id'):
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(500, self.preview_content)

    HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

    @classmethod
    def _color_luminance(cls, hex_color):
        if not cls.HEX_COLOR_RE.match(hex_color):
            return None
        hex_val = hex_color.lstrip("#")
        if len(hex_val) == 3:
            hex_val = "".join(c * 2 for c in hex_val)
        r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255

    @classmethod
    def _contrast_text_color(cls, hex_color):
        luminance = cls._color_luminance(hex_color)
        if luminance is None:
            return "#FFFFFF"
        return "#000000" if luminance > 0.5 else "#FFFFFF"

    def _sync_color_swatch(self):
        color = self.font_color_var.get().strip()
        if self.HEX_COLOR_RE.match(color):
            self.font_color_entry.configure(border_color=("gray60", "gray40"))
            self.color_picker_btn.configure(
                fg_color=color,
                hover_color=color,
                text_color=self._contrast_text_color(color)
            )
        else:
            self.font_color_entry.configure(border_color="red")

    def _on_custom_color_typed(self, *args):
        self._sync_color_swatch()
        self.trigger_preview()

    def pick_custom_color(self):
        lang = self.get_lang_key()
        current = self.font_color_var.get().strip()
        initial = current if self.HEX_COLOR_RE.match(current) else "#FFFFFF"
        _, hex_color = colorchooser.askcolor(
            initialcolor=initial,
            title=self.generator.get_locale_string(lang, "color_picker_title")
        )
        if hex_color:
            self.font_color_var.set(hex_color.upper())
            self._sync_color_swatch()
            self.trigger_preview()

    def on_color_selected(self, choice):
        lang = self.get_lang_key()
        custom_label = self.generator.get_locale_string(lang, "color_custom")

        if choice == custom_label:
            self.font_color_entry.grid()
            self.color_picker_btn.grid()
            self._sync_color_swatch()
        else:
            color_map = {
                self.generator.get_locale_string(lang, "color_white"): "#FFFFFF",
                self.generator.get_locale_string(lang, "color_black"): "#000000",
                self.generator.get_locale_string(lang, "color_gold"): "#FFD700",
                self.generator.get_locale_string(lang, "color_red"): "#FF0000"
            }
            hex_color = color_map.get(choice, "#FFFFFF")
            self.font_color_var.set(hex_color)
            self.font_color_entry.grid_remove()
            self.color_picker_btn.grid_remove()
            self.trigger_preview()

    def clear_custom_image(self, choice):
        self.custom_image_path = None
        if choice and choice != self.bg_var.get():
            self.bg_var.set(choice)
        self.clear_custom_img_btn.grid_remove()
        self.trigger_preview()

    def select_custom_image(self):
        file_path = filedialog.askopenfilename(
            title=self.generator.get_locale_string(self.get_lang_key(), "custom_image_btn"),
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )
        if file_path:
            # 🛡️ Sentinel: Reject non-regular files, symlinks/junctions, device names, non-raster files, and oversized files (> 20MB)
            if not self.generator._is_valid_raster_image(file_path):
                self.status_label.configure(
                    text=self.generator.get_locale_string(self.get_lang_key(), "image_size_limit_error"),
                    text_color="red",
                )
                return
            self.custom_image_path = file_path
            self.bg_var.set(f"Custom: {os.path.basename(file_path)}")
            self.clear_custom_img_btn.grid()
            self.trigger_preview()

    def get_current_params(self):
        verse = self.verse_input.get("1.0", "end-1c").strip()
        # 🛡️ Sentinel: Enforce length limits to prevent DoS (e.g. from extreme wrapping)
        if len(verse) > 5000:
            verse = verse[:5000]

        reference = self.reference_input.get().strip()
        if len(reference) > 100:
            reference = reference[:100]

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

        background_dim = round(self.bg_dim_var.get() / 100.0, 2)

        return verse, reference, background, font_type, font_color, font_size, y_offset, aspect_ratio, self.custom_image_path, background_dim

    def _sync_live_output_texts(self, lang, verse, reference):
        texts_key = (lang, verse, reference)
        if getattr(self, "_last_live_texts_key", None) == texts_key:
            return
        self._last_live_texts_key = texts_key
        if verse and reference:
            alt_text, caption = self.generator.generate_texts(lang, verse, reference)
            self.alt_text = alt_text
            self.caption = caption
            alt_label = self.generator.get_locale_string(lang, "alt_text_label")
            cap_label = self.generator.get_locale_string(lang, "caption_label")
            display_text = f"--- {alt_label} ---\n{self.alt_text}\n\n--- {cap_label} ---\n{self.caption}"
            self.output_textbox.configure(state="normal")
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", display_text)
            self.output_textbox.configure(state="disabled")
            self.copy_alt_btn.configure(state="normal")
            self.copy_caption_btn.configure(state="normal")
        else:
            self.alt_text = ""
            self.caption = ""
            self.output_textbox.configure(state="normal")
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.configure(state="disabled")
            self.copy_alt_btn.configure(state="disabled")
            self.copy_caption_btn.configure(state="disabled")

    def preview_content(self):
        current_params = self.get_current_params()
        verse, reference, background, font_type, font_color, font_size, y_offset, aspect_ratio, custom_image_path, background_dim = current_params
        lang = self.get_lang_key()
        self._sync_live_output_texts(lang, verse, reference)

        if not verse or not reference:
            self._preview_request_id = getattr(self, "_preview_request_id", 0) + 1
            self.preview_label.configure(image="", text=self.generator.get_locale_string(lang, "preview_empty_state"))
            self.preview_label.image = None
            return

        # ⚡ Bolt: Prevent redundant preview rendering if params haven't changed.
        # This occurs frequently when navigation keys trigger `<KeyRelease>` without altering the text.
        if current_params == self._last_preview_params:
            return

        self._last_preview_params = current_params
        request_id = getattr(self, "_preview_request_id", 0) + 1
        self._preview_request_id = request_id
        current_lang = self.current_lang

        def _render_preview():
            # ⚡ Bolt: Skip stale queued requests before allocating/rendering
            if request_id != getattr(self, "_preview_request_id", 0):
                return
            try:
                pil_img = self.generator.generate_image(
                    current_lang, verse, reference, background_filename=background,
                    custom_image_path=custom_image_path, aspect_ratio=aspect_ratio,
                    font_type=font_type, font_color=font_color, font_size=font_size, y_offset=y_offset,
                    max_dimension=500, background_dim=background_dim
                )
                if request_id != getattr(self, "_preview_request_id", 0):
                    return
                self.after(0, self._apply_preview_result, request_id, pil_img, False)
            except Exception:
                self.after(0, self._apply_preview_result, request_id, None, True)

        # ⚡ Bolt: Reuse a single-worker ThreadPoolExecutor to avoid OS thread spawn overhead and GIL thrashing
        if not hasattr(self, "_preview_executor"):
            self._preview_executor = ThreadPoolExecutor(max_workers=1)
        self._preview_executor.submit(_render_preview)

    def _apply_preview_result(self, request_id, pil_img, had_error):
        if request_id != getattr(self, "_preview_request_id", 0):
            return
        if had_error or pil_img is None:
            # 🛡️ Sentinel: Fail securely - don't expose sensitive stack traces to UI
            lang = self.get_lang_key()
            self.preview_label.configure(image="", text=self.generator.get_locale_string(lang, "error_preview_msg"))
            return
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        self.preview_label.configure(image=ctk_img, text="")
        self.preview_label.image = ctk_img

    def generate_content(self):
        if getattr(self, "_is_generating", False):
            return

        verse, reference, background, font_type, font_color, font_size, y_offset, aspect_ratio, custom_image_path, background_dim = self.get_current_params()
        if not verse or not reference:
            return

        lang = self.get_lang_key()
        lang_code = "pt" if lang == "pt-BR" else lang

        safe_ref = self.generator.sanitize_filename(reference)
        default_image_filename = f"{safe_ref}_{lang_code}.png"
        default_audio_filename = f"{safe_ref}_{lang_code}.mp3"

        # Prompt user for image save location before processing
        image_save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_image_filename,
            title=f"{self.generator.get_locale_string(lang, 'save_btn')} - {self.generator.get_locale_string(lang, 'save_image_suffix')}",
            filetypes=[("PNG files", "*.png")]
        )
        if not image_save_path:
            return
        if not image_save_path.lower().endswith(".png"):
            image_save_path += ".png"

        audio_save_path = None
        if self.audio_generate_var.get():
            # Prompt user for audio save location before processing
            audio_save_path = filedialog.asksaveasfilename(
                defaultextension=".mp3",
                initialfile=default_audio_filename,
                title=f"{self.generator.get_locale_string(lang, 'save_btn')} - {self.generator.get_locale_string(lang, 'save_audio_suffix')}",
                filetypes=[("MP3 files", "*.mp3")]
            )
            if not audio_save_path:
                return
            if not audio_save_path.lower().endswith(".mp3"):
                audio_save_path += ".mp3"

        self._is_generating = True
        self._last_generate_state = "disabled"
        self.status_label.configure(text=self.generator.get_locale_string(lang, "generating_files_msg"), text_color="gray")
        original_generate_text = self.generator.get_locale_string(lang, "generate_btn")
        self.generate_btn.configure(state="disabled", text="⏳ " + original_generate_text)
        self.update()

        def _process():
            try:
                # ⚡ Bolt: Run network-bound TTS audio generation concurrently with CPU-bound image rendering/PNG save
                audio_future = None
                if self.audio_generate_var.get() and audio_save_path:
                    gender_selection = self.gender_var.get()
                    gender_key = "Male" if "Male" in gender_selection or "Masculin" in gender_selection else "Female"
                    if not hasattr(self, "_audio_executor"):
                        self._audio_executor = ThreadPoolExecutor(max_workers=1)
                    audio_future = self._audio_executor.submit(
                        self.generator.generate_audio,
                        self.current_lang,
                        verse,
                        reference,
                        gender=gender_key,
                        custom_output_path=audio_save_path,
                    )

                # Generate Image to Disk
                pil_img = self.generator.generate_image(
                    self.current_lang, verse, reference, background_filename=background,
                    custom_image_path=custom_image_path, aspect_ratio=aspect_ratio,
                    font_type=font_type, font_color=font_color, font_size=font_size, y_offset=y_offset,
                    background_dim=background_dim
                )
                # ⚡ Bolt: Use fast zlib compression level 1 when exporting final PNGs atomically
                self.generator.save_image_atomic(pil_img, image_save_path, compress_level=1)

                # Generate Texts
                alt_text, caption = self.generator.generate_texts(lang, verse, reference)

                # Collect Audio result
                audio_msg = ""
                if audio_future is not None:
                    try:
                        audio_path = audio_future.result()
                        audio_msg = self.generator.get_locale_string(
                            lang, "audio_saved_msg", path=os.path.abspath(audio_path)
                        )
                    except Exception:
                        # 🛡️ Sentinel: Do not leak exception strings
                        audio_msg = self.generator.get_locale_string(lang, "audio_error_msg")

                self.after(0, self._on_generate_complete, lang, audio_msg, image_save_path, alt_text, caption)
            except Exception:
                # 🛡️ Sentinel: Catch unhandled thread exceptions and update UI generically
                err_msg = self.generator.get_locale_string(lang, "generate_error_msg")
                self.after(0, self._on_generate_error, err_msg, original_generate_text)

        threading.Thread(target=_process, daemon=True).start()

    def _on_generate_error(self, err_msg, original_generate_text):
        self._is_generating = False
        self._last_generate_state = "normal"
        self.status_label.configure(text=err_msg, text_color="red")
        self.generate_btn.configure(state="normal", text=original_generate_text)

    def _on_generate_complete(self, lang, audio_msg, image_save_path, alt_text, caption):
        self._is_generating = False
        self._last_generate_state = "normal"
        self.last_generated_image_path = image_save_path
        self.alt_text = alt_text
        self.caption = caption

        self.generate_btn.configure(state="normal")
        # Update Textbox
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("1.0", "end")
        alt_label = self.generator.get_locale_string(lang, "alt_text_label")
        cap_label = self.generator.get_locale_string(lang, "caption_label")
        display_text = f"--- {alt_label} ---\n{self.alt_text}\n\n--- {cap_label} ---\n{self.caption}"
        self.output_textbox.insert("1.0", display_text)
        self.output_textbox.configure(state="disabled")

        # Enable copy/open buttons
        self.copy_alt_btn.configure(state="normal")
        self.copy_caption_btn.configure(state="normal")
        self.open_output_btn.configure(state="normal")

        # Status Label
        msg = self.generator.get_locale_string(lang, "success_msg")
        self.status_label.configure(text=msg + audio_msg, text_color="green")

        original_text = self.generator.get_locale_string(lang, "generate_btn")
        self.generate_btn.configure(text="✓ " + original_text)
        self._schedule_button_reset(self.generate_btn, "generate_btn")

    def open_output_folder(self):
        if not self.last_generated_image_path:
            return
        lang = self.get_lang_key()
        folder = os.path.dirname(os.path.abspath(self.last_generated_image_path))
        if not os.path.isdir(folder) or self.generator._has_reparse_in_lineage(folder):
            self.status_label.configure(text=self.generator.get_locale_string(lang, "folder_unavailable_error"), text_color="red")
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except OSError:
            self.status_label.configure(text=self.generator.get_locale_string(lang, "open_folder_error"), text_color="red")

    def copy_alt(self):
        if self.alt_text:
            lang = self.get_lang_key()
            try:
                pyperclip.copy(self.alt_text)
            except Exception:
                self.status_label.configure(text=self.generator.get_locale_string(lang, "clipboard_error"), text_color="red")
                return
            self.status_label.configure(text=self.generator.get_locale_string(lang, "copy_success_msg"), text_color="green")
            original_text = self.generator.get_locale_string(lang, "copy_alt_text_btn")
            self.copy_alt_btn.configure(text="✓ " + original_text)
            self._schedule_button_reset(self.copy_alt_btn, "copy_alt_text_btn")

    def copy_caption(self):
        if self.caption:
            lang = self.get_lang_key()
            try:
                pyperclip.copy(self.caption)
            except Exception:
                self.status_label.configure(text=self.generator.get_locale_string(lang, "clipboard_error"), text_color="red")
                return
            self.status_label.configure(text=self.generator.get_locale_string(lang, "copy_success_msg"), text_color="green")
            original_text = self.generator.get_locale_string(lang, "copy_caption_btn")
            self.copy_caption_btn.configure(text="✓ " + original_text)
            self._schedule_button_reset(self.copy_caption_btn, "copy_caption_btn")

if __name__ == "__main__":
    app = App()
    app.mainloop()
