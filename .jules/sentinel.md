## 2023-10-27 - Missing Timeout on External API Calls
**Vulnerability:** The application was making external network requests using `requests.get()` without specifying a `timeout` parameter.
**Learning:** By default, `requests` does not time out. This means if the external API (getbible.net) hangs or becomes unresponsive, the application's thread will block indefinitely. In a UI application, if this runs on the main thread, it causes the app to freeze. If it runs in a background thread, it leads to thread exhaustion. This represents a localized Denial of Service (DoS) vulnerability.
**Prevention:** Always define a `timeout` parameter explicitly for all external network requests (e.g., `requests.get(url, timeout=10)`).

## Path Traversal Vulnerability
**Vulnerability:** Generating filenames using unsanitized user-controlled input. In `main.py` and `generator.py`, the user-provided `reference` was directly used to generate `safe_ref` (which became the filename). The code stripped spaces and colons but left `/` and `\` intact, allowing for directory traversal when passed into `os.path.join` or used for file paths.
**Learning:** Always sanitize string inputs prior to using them to form file paths to prevent users from writing to arbitrary directories on the local machine. Simply replacing space and colon is not enough. You must account for both Unix (`/`) and Windows (`\`) path separators.
**Prevention:** Thoroughly replace or strip `/` and `\` from strings before using them in file paths (e.g. `replace("/", "_").replace("\\", "_")`), or use `os.path.basename`.
