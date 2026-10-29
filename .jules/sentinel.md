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
