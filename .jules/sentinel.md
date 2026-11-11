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
