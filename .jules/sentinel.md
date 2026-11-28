## 2023-10-27 - Missing Timeout on External API Calls
**Vulnerability:** The application was making external network requests using `requests.get()` without specifying a `timeout` parameter.
**Learning:** By default, `requests` does not time out. This means if the external API (getbible.net) hangs or becomes unresponsive, the application's thread will block indefinitely. In a UI application, if this runs on the main thread, it causes the app to freeze. If it runs in a background thread, it leads to thread exhaustion. This represents a localized Denial of Service (DoS) vulnerability.
**Prevention:** Always define a `timeout` parameter explicitly for all external network requests (e.g., `requests.get(url, timeout=10)`).

## Path Traversal Vulnerability
**Vulnerability:** Generating filenames using unsanitized user-controlled input. In `main.py` and `generator.py`, the user-provided `reference` was directly used to generate `safe_ref` (which became the filename). The code stripped spaces and colons but left `/` and `\` intact, allowing for directory traversal when passed into `os.path.join` or used for file paths.
**Learning:** Always sanitize string inputs prior to using them to form file paths to prevent users from writing to arbitrary directories on the local machine. Simply replacing space and colon is not enough. You must account for both Unix (`/`) and Windows (`\`) path separators.
**Prevention:** Thoroughly replace or strip `/` and `\` from strings before using them in file paths (e.g. `replace("/", "_").replace("\\", "_")`), or use `os.path.basename`.

## 2024-05-20 - ReDoS Vulnerability in Reference Parsing
**Vulnerability:** The application parsed user-supplied bible reference strings using unbounded regex patterns containing overlapping quantifier sets (`+?` followed by `\s+`), making it vulnerable to Regular Expression Denial of Service (ReDoS). Extremely long inputs without matches caused catastrophic backtracking and thread starvation.
**Learning:** Even with safe regex structures, complex parses on completely unrestricted user input length can cause severe performance issues or Denial of Service conditions.
**Prevention:** In addition to writing optimal regex, always validate and limit the length of arbitrary user input strings (e.g., `if len(input) > max_allowed_length: return`) before processing them with regular expressions.
## 2025-02-14 - Prevent Path Traversal in Asset Loading
**Vulnerability:** Path traversal possible when dynamically loading background images (`background_filename`) and fonts (`font_type`) due to missing input sanitization before joining with directory paths in `generator.py`.
**Learning:** `os.path.join` does not sanitize inputs natively. If an attacker provides a path like `../../etc/passwd` or an absolute path (e.g. `/etc/passwd`), `os.path.join` could resolve to paths outside the intended directory.
**Prevention:** Always use `os.path.basename()` to strip out any path information when dealing with user-supplied filenames for assets before passing them to `os.path.join()`, ensuring the file is resolved strictly within the designated asset folder.
## 2025-02-14 - Input Validation for UI Thread Safety (DoS Prevention)
**Vulnerability:** The `generate_image` function parsed user-provided hex color strings (`font_color`) directly into integers using `int(..., 16)` without validation. If an invalid string was supplied (e.g. `#ZZZZZZ`), it threw a `ValueError`.
**Learning:** Unhandled exceptions in background threads that serve UI events can crash the thread. If this occurs on a UI-blocking path or breaks the application's expected background loop, it effectively causes a Denial of Service (DoS) for the application's interface.
**Prevention:** Always validate user input strings (e.g., using regex `^#(?:[0-9a-fA-F]{3}){1,2}$` for hex colors) before applying operations like `int(..., 16)` that assume a strict format, and provide a safe fallback for invalid inputs to maintain app stability.

## 2026-10-31 - Prevent UI DoS and Information Leakage
**Vulnerability:** Unbounded user input length could freeze the UI thread during text processing, and unhandled exception traces were exposed directly to the UI.
**Learning:** In desktop applications, large text inputs can cause Denial of Service by consuming excessive CPU/memory on the main thread during tasks like text wrapping. Exposing raw exception strings could also leak local file paths or internal details.
**Prevention:** Always enforce reasonable length boundaries for user inputs, and return generic error messages to the UI without leaking the underlying stack trace or exception object.

## 2025-02-14 - Missing Timeout on Asyncio Network Calls
**Vulnerability:** External TTS API call (`await communicate.save(...)`) lacked a timeout in `generator.py`.
**Learning:** `asyncio` does not enforce default timeouts on underlying socket operations depending on the library. If an external service hangs, any `await` on it will hang indefinitely. When run from background threads serving the UI, this results in thread exhaustion and localized Denial of Service (DoS).
**Prevention:** Always wrap external async calls that depend on network boundaries with `asyncio.wait_for(coroutine, timeout=X)` to ensure failures are quick and the app can recover securely.

## 2023-11-20 - Prevent SSRF and Path Traversal in URL Interpolation
**Vulnerability:** The application constructed external API URLs by directly interpolating unvalidated user inputs (e.g., `bible_id`, `book_nr`, `chapter`) into a format string (`f".../{bible_id}/{book_nr}/{chapter}.json"`).
**Learning:** Constructing URLs without encoding variables allows an attacker to inject characters like `..`, `/`, or `?` which can alter the path structure or inject query parameters, potentially causing Server-Side Request Forgery (SSRF) or API path traversal.
**Prevention:** Always URL-encode dynamic segments of a URL path or query string using `urllib.parse.quote(str(var), safe="")` to safely escape slashes and control characters before constructing the URL string.

## 2025-05-18 - Prevent SSML Injection in Text-to-Speech
**Vulnerability:** The application passed user-supplied bible reference and verse texts directly into `edge_tts.Communicate` without escaping HTML/XML elements like `<` and `>`.
**Learning:** `edge_tts` generates speech from text using SSML (Speech Synthesis Markup Language). Allowing raw `<` and `>` characters permits a malicious user to perform SSML injection (e.g., inputting `<break time='10s'/>` to cause unbounded delays), which leads to backend abuse or DoS.
**Prevention:** Always sanitize input intended for TTS or SSML engines by escaping characters (`<` to `&lt;`, `>` to `&gt;`, `&` to `&amp;`) to prevent SSML injection vulnerabilities before processing.

## 2025-02-14 - Prevent Memory Exhaustion (DoS) in Cache Collections
**Vulnerability:** The application stored image and font objects indefinitely in memory cache dictionaries (`_bg_cache`, `_font_cache`) without any size limits or eviction policy.
**Learning:** In long-running applications (such as desktop applications), continuously adding heavy objects like PIL Images to an unbounded cache dictionary eventually leads to Memory Exhaustion and crash (Denial of Service).
**Prevention:** Always set a bounds check (e.g. `if len(cache) > MAX_SIZE: cache.clear()`) before inserting new items into in-memory dictionaries that cache heavy objects.


## 2026-11-17 - Comprehensive Security Hardening (Sentinel Audit Remediation)
**Vulnerabilities Remediated:**
- Anchored `locales`, `assets/fonts`, `assets/backgrounds`, and `output` to `BASE_DIR` in `generator.py`, added locale filename allowlisting (`ALLOWED_LOCALE_FILES`) + schema validation, and replaced `str.format(**kwargs)` with safe literal token replacement to eliminate untrusted search path & format-string traversal attacks.
- Synchronized `GetBibleAPI._session` with a `threading.Lock()`, disabled automatic redirects (`allow_redirects=False`), enforced a 15-second total stream deadline, validated JSON schema, and returned immutable verse tuples from `_fetch_chapter`.
- Added in-flight guards (`_fetching_verse`, `_is_generating`) in `main.py` to prevent `<Return>` thread flooding and `trigger_preview()` re-enabling `generate_btn` mid-generation.
- Added atomic temporary file writes with a 15 MB audio byte cap in `generate_audio()`, removed double XML escaping (`edge-tts` handles XML escaping internally; `<` and `>` are stripped directly), fixed `AUDIO_REF_PATTERN` overlapping quantifiers, enforced `_is_safe_regular_file` checks on custom and built-in images, clamped crop/font/offset bounds, and excluded `*.*` from save dialogs.
- Removed unused `api_key_label` from locale files, pinned `requests==2.34.2`, and expanded `.gitignore`.

## 2026-11-17 - Follow-up Audit Hardening
**Vulnerabilities Remediated:**
- Replaced the overlapping quantifier in `GetBibleAPI.REFERENCE_PATTERN` (`getbible_api.py`) to prevent ReDoS and added circumflex vowels (`âêîôûÂÊÎÔÛ`) so Portuguese/Spanish book names such as `Gênesis` and `Êxodo` parse properly.
- Enhanced `Generator._is_safe_regular_file` and added `_validate_safe_output_path` / `save_image_atomic` (`generator.py`) to reject symlinks/junctions across the path lineage, block Windows reserved device names on exports, validate font files before loading, and bound `DARKEN_LUTS`.
- Sanitized quick-reference chapter/verse inputs in `main.py`, routed custom image validation through `_is_safe_regular_file`, used `save_image_atomic` for PNG exports, and added `test_security.py`.

## 2026-11-17 - Single-Pass Localization, Raster Magic-Byte & Bible Query Hardening
**Vulnerabilities Remediated:**
- Replaced sequential `str.replace` loops in `Generator.get_locale_string` (`generator.py`) with single-pass `TEMPLATE_TOKEN_PATTERN.sub(...)` replacement so substituted values cannot inject `{key}` placeholders.
- Added `_is_safe_regular_file` checks when loading locale JSON files in `load_locales()` and scanning assets in `main.py`, plus PNG/JPEG magic-byte validation (`_is_valid_raster_image`) for custom and built-in background images.
- Enforced `verse[:5000]` and `reference[:100]` caps in `generate_texts()`, `generate_image()`, and `wrap_text()`.
- Added `BIBLE_ID_PATTERN` validation and numeric bounds (`1 <= chapter <= 150`, `1 <= verse <= 200`) in `GetBibleAPI` (`getbible_api.py`), and checked `_has_reparse_in_lineage` in `open_output_folder()` (`main.py`).

## 2026-11-23 - Windows O_NOFOLLOW No-Op & Python <3.12 Junction Detection
**Vulnerability:** `Generator._open_regular_nofollow` relied on `getattr(os, "O_NOFOLLOW", 0)` (which evaluates to `0` on Windows) without verifying `(st_dev, st_ino)` identity or re-checking lineage after opening, and `_is_reparse_point` relied on `os.path.isjunction` (unavailable on Python 3.10–3.11).
**Learning:** On Windows, `os.O_NOFOLLOW` is undefined, so `os.open(..., os.O_RDONLY | 0)` silently follows symlinks/junctions if a path is swapped after pre-checks, and `os.path.isjunction` fallback lambdas silently return `False` on Python <3.12.
**Prevention:** Always combine `os.lstat` pre-checks with `os.fstat(fd)` `(st_dev, st_ino)` identity and lineage checks after `os.open`, and check `stat.FILE_ATTRIBUTE_REPARSE_POINT` via `os.lstat` when `os.path.isjunction` is unavailable.

## 2026-11-26 - requests.raise_for_status() Allows 3xx Redirect Responses
**Vulnerability:** `GetBibleAPI._fetch_chapter` (`getbible_api.py`) set `allow_redirects=False` and relied solely on `response.raise_for_status()`, which only raises on 4xx/5xx status codes and would still read/parse a 3xx redirect body.
**Learning:** In Python `requests`, disabling redirects (`allow_redirects=False`) leaves 3xx responses unraised by `raise_for_status()`.
**Prevention:** Explicitly require `response.status_code == 200` alongside `raise_for_status()` whenever `allow_redirects=False` is used.

## 2026-11-27 - UNC SMB Net-NTLMv2 Leak & Pre-Validation os.stat()
**Vulnerability:** `Generator._has_unsafe_path_syntax` (`generator.py`) blocked `\\.\`, `\\?\`, and `\??\` device prefixes but allowed UNC network paths (`\\host\share`, `//host/share`), and `_resolve_valid_image()` called `os.stat(path)` before path syntax or reparse validation.
**Learning:** On Windows, calling `os.stat()`, `os.lstat()`, or `os.path.lexists()` on a UNC path triggers an outbound SMB connection that leaks the user's Net-NTLMv2 hash even if subsequent checks reject the file.
**Prevention:** Reject all `\\` (UNC/device) and `\??\` prefixes in `_has_unsafe_path_syntax()` and always run syntax and reparse checks before `os.lstat()` (never calling `os.stat()` on unvalidated paths).


## 2026-11-28 - Control & Bidi Character Sanitization Gap on User-Supplied Text
**Vulnerability:** `GetBibleAPI` stripped C0/C1 control characters and Unicode Bidi overrides/isolates from upstream API verse text, but `Generator` (`generate_texts`, `generate_audio`, `generate_image`, `wrap_text`) accepted unsanitized user/pasted inputs, and `generate_image` called `os.path.getmtime()` on the fallback `default.png` path before `_resolve_valid_image()`.
**Learning:** Sanitizing only remote API payloads leaves pasted/manual UI inputs vulnerable to Bidi text spoofing in generated cards/captions and illegal XML 1.0 control characters in `edge-tts` SSML synthesis.
**Prevention:** Enforce `Generator.sanitize_text()` at the `Generator` entrypoints (`generate_texts`, `generate_audio`, `generate_image`, `wrap_text`) and validate fallback asset paths through `_resolve_valid_image()`.
