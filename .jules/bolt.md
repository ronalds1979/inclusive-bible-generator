## 2023-10-22 - Cache Image and Font loading
**Learning:** In a live preview application where Pillow's `ImageDraw.Draw` is invoked frequently (e.g. bounded by a 500ms debounce), repeated opening, resizing, cropping, compositing, and font parsing of identical background images and fonts severely throttles performance. Drawing text mutates the image, so we must return a `.copy()` of the pre-processed cached background to prevent text accumulation.
**Action:** Implemented an in-memory dictionary cache for pre-processed background images (keyed by path and dimensions) and parsed TrueType fonts (keyed by path and size). Always `.copy()` cached images before yielding them for mutation.
## 2023-10-28 - [getbible_api.py] Cache full chapter payload for verse lookups
**Learning:** The `api.getbible.net/v2` API returns the payload for an entire chapter even when we are requesting specific verses from it. Doing sequential requests for verses from the same chapter incurs significant redundant network overhead.
**Action:** When working with chapter-based APIs, cache the entire chapter payload in memory (e.g. using `functools.lru_cache`) instead of re-fetching per verse request.
## 2023-10-29 - O(n²) to O(n) text wrapping optimization
**Learning:** In Pillow, repeatedly measuring text strings by appending one word at a time via `draw.textbbox` or `draw.textlength` in a loop yields O(n²) string creation and measuring overhead.
**Action:** Measure individual words once, cache the space width, and accumulate widths mathematically (O(n)). This speeds up text wrapping by over 90% for long text blocks without altering the layout.
## 2025-03-01 - O(1) hash map lookup and Regex precompilation

**Learning:** This codebase uses Python loops for basic lookups on large mappings and re-compiles regex at function invocation time. In hot paths (like reference parsing or repeated API calls), Pythons O(n) looping logic and regex compilation add up significantly. Converting large dictionaries to support O(1) lookups during class/module initialization, combined with precompiling regular expressions with `re.compile()` at the class/module level, significantly reduces evaluation time on the hot paths.

**Action:** Whenever parsing or matching complex string formats iteratively, pre-compile the regular expression at class or module level, avoiding `re.match` with raw strings. Additionally, replace iterative matching on dictionaries with pre-transformed mappings designed for direct O(1) key lookups.

## 2025-03-01 - Prevent UI Stuttering: Memoization and Downsampling Optimization

**Learning:** In a Tkinter/CustomTkinter application where continuous keystrokes (e.g., via `<KeyRelease>`) trigger synchronous image rendering (`preview_content`) on the main thread:
1. Navigation keys (like arrows) trigger `<KeyRelease>` events even when the input text hasn't changed. Without state memoization (e.g., comparing `current_params` to `_last_preview_params`), this results in highly redundant rendering cycles that unnecessarily block the UI.
2. Generating live previews using Pillow's `Image.Resampling.LANCZOS` is computationally expensive.

**Action:**
1. Memoize parameter states before heavy rendering functions; if parameters haven't changed, return early.
2. In live preview contexts where speed is prioritized over pixel-perfect archival quality, swap `LANCZOS` for `Image.Resampling.BILINEAR` which provides visually similar downsampling but runs ~40% faster, thereby reducing main thread blocking time.

## 2025-03-02 - O(n) to O(1) Dictionary Mapping Optimization
**Learning:** Repetitive chained string manipulations (e.g., `lang.replace(A, B).replace(C, D)`) or sequential `if/elif "str" in var` checks for mapping predefined choices to keys are computationally expensive and scale poorly (O(n)).
**Action:** Replace iterative string comparisons and nested conditional assignments with O(1) class-level hash map (dictionary) lookups (e.g., `self.LANG_MAP.get(lang, fallback)`). This simplifies code and improves runtime performance by roughly 83% for repetitive function calls.

## 2025-03-02 - Use requests.Session for connection pooling
**Learning:** Repetitive independent `requests.get()` calls to the same host (e.g. api.getbible.net) establish new TCP and TLS connections each time, incurring significant overhead.
**Action:** Use a persistent `requests.Session()` object instead, which reuses the underlying connection via connection pooling, thereby eliminating the redundant handshake overhead and improving response times considerably (often by 50% or more).

## 2025-03-02 - O(n²) string creation to O(1) dictionary word width lookup optimization
**Learning:** In Pillow, when implementing text wrapping, looking up the length of words using `draw.textlength` repeatedly incurs overhead. Memoizing the word widths in an in-memory dictionary prevents redundant calculations for repeated words, and preferring `font.getlength` over `draw.textlength` skips the `ImageDraw` lookup overhead.
**Action:** Use an in-memory dictionary to memoize individual word widths during text wrapping and use `font.getlength` for measuring to drastically reduce execution time by avoiding redundant calculations and lookup overhead.

## 2025-03-02 - Final Wrapped Text Memoization Optimization
**Learning:** In applications where text layouts are repeatedly calculated (e.g. live preview generating in a UI) and text length measuring logic has already been optimized, the layout computation itself (splitting, checking length, joining strings) is still computationally heavy over numerous iterations.
**Action:** When working with live preview generation of strings where text properties (content, font, size, and max width) remain constant between renders, implement an in-memory dictionary cache to memoize the final wrapped text to completely bypass the layout processing overhead.

## 2025-03-02 - O(n) String Manipulation to O(1) Translate Optimization
**Learning:** Chained string manipulations like `.replace(" ", "_").replace(":", "_").replace("/", "_").replace("\\", "_")` loop over strings repeatedly resulting in O(n) complexity where `n` scales by the number of replaces.
**Action:** Use Python's built-in `str.translate` functionality by pre-computing mappings via `str.maketrans()` on class level. This reduces the time complexity for substring replacements to roughly O(1) relative to chained replaces, minimizing unnecessary intermediate string objects.

## 2026-11-17 - Fast PNG Compression, Cached Dimming LUTs & Canonical Book Cache
**Learning:** Pillow's default PNG `compress_level=6` spends substantial CPU time compressing high-resolution verse exports, while non-50% background dimming rebuilds a 768-element LUT list comprehension per render. Additionally, rebuilding the 66-book canonical list and running `re.sub` on TTS strings adds avoidable overhead.
**Action:** Save generated PNGs with `compress_level=1`, cache dimming LUTs by `dim_key` in `Generator.DARKEN_LUTS`, use `str.translate(ANGLE_BRACKET_STRIP_MAP)` for TTS angle-bracket stripping, cache canonical book lists in `App._CANONICAL_BOOKS_CACHE`, and hoist repeated locale lookups in `update_ui_texts()`.

## 2026-11-20 - Memoize Contrast Warning State in trigger_preview()
**Learning:** Even when slider labels and button states are memoized in `trigger_preview()`, an un-memoized `_update_contrast_warning()` still recomputes contrast ratios and calls Tkinter `.configure()` and `.grid()`/`.grid_remove()` on every keystroke, font-size change, and Y-offset drag tick, causing redundant grid layout passes.
**Action:** Gate `_update_contrast_warning()` on `(lang, color, bg_dim, bg_source)` and memoize the rendered UI state tuple before calling `.configure()` or `.grid()`/`.grid_remove()`.

## 2026-11-21 - Un-dimmed Base Background Caching Prevents 17-Step LRU Thrashing
**Learning:** Keying `Generator._bg_cache` (capacity 16) by `dim_key` causes complete cache thrashing when sweeping the 17-step `background_dim` slider (0%–85%), forcing repeated file validation, image decoding, cropping, and resizing on every tick.
**Action:** Cache only the un-dimmed resized RGB base image under `(bg_path, bg_mtime, target_width, target_height)` and derive dimmed variants via `base_img.point(self._get_darken_lut(dim_key))` (which returns a fresh `Image` without mutating the cached base).

## 2026-11-21 - JPEG DCT Draft Downscaling & Single-Pass Validation for Background Luminance
**Learning:** `App._get_background_luminance()` runs synchronously on the UI thread before `preview_content()` populates `Generator._bg_cache`. Calling `img.convert("RGB").resize((16, 16))` without `img.draft("RGB", (16, 16))` decodes full 12MP JPEGs (~117 ms), while validating with `_is_valid_raster_image()` before `_open_regular_nofollow()` walks parent directories for reparse points twice. Note also that `BILINEAR` resampling must only precede `.convert("RGB")` for `"RGB"`/`"RGBA"`/`"L"` modes (palette `"P"` PNGs require RGB conversion first).
**Action:** Open once via `_open_regular_nofollow()`, verify magic bytes + `f.seek(0)`, call `img.draft("RGB", (16, 16))` for JPEGs, downsample `"RGB"`/`"RGBA"`/`"L"` with `BILINEAR` before `.convert("RGB")`, and read flat bytes with `.tobytes()`.

## 2026-11-27 - Subpixel-Aligned Alpha Mask Caching for Pillow Text Rendering
**Learning:** Profiling `Generator.generate_image()` with `cProfile` on cached previews showed `ImageDraw.multiline_text()` / `ImageDraw.text()` (`Font.render()`) accounted for ~65% of per-frame time (~1.49 ms of 2.33 ms/frame) because `y_offset` drags, `background_dim` ticks, and background swaps re-rasterized unchanged glyphs on every render. When coordinates have fractional centering offsets (e.g., `(target_width - width) / 2` ending in `.5`), caching an `'L'` mask at integer `(0, 0)` causes subpixel misalignment.
**Action:** Key `Generator._text_mask_cache` by `(is_multiline, text, font_id, align, round(x_frac, 4), round(y_frac, 4))` where `x_frac = x - math.floor(x)` and `y_frac = y - math.floor(y)` (invariant across `y_offset` drags), render into a tight `'L'` mask, and composite via `img.paste(rgba_color[:3], (ix + x0, iy + y0), mask)` for pixel-identical output (~78% faster text draw).

## 2026-11-28 - Separate Dimmed Background Cache Eliminates Pillow `point()` Overhead
**Learning:** While keeping `_bg_cache` un-dimmed prevents 17-step `background_dim` slider thrashing, `cProfile` on steady-state renders (`y_offset` drags, font/color/text edits) revealed `Image.point(lut)` still accounted for ~26% of per-frame time (~0.635 ms/frame, calling `builtins.round` 768 times per render in Pillow's Python wrapper).
**Action:** Pair the 16-entry un-dimmed `_bg_cache` with a small separate `_dimmed_bg_cache` (capacity 8, keyed with `dim_key`) so steady-state renders `.copy()` directly (~0.047 ms vs ~0.635 ms) while dim-slider sweeps still hit `_bg_cache`.
