## 2023-10-27 - Missing Timeout on External API Calls
**Vulnerability:** The application was making external network requests using `requests.get()` without specifying a `timeout` parameter.
**Learning:** By default, `requests` does not time out. This means if the external API (getbible.net) hangs or becomes unresponsive, the application's thread will block indefinitely. In a UI application, if this runs on the main thread, it causes the app to freeze. If it runs in a background thread, it leads to thread exhaustion. This represents a localized Denial of Service (DoS) vulnerability.
**Prevention:** Always define a `timeout` parameter explicitly for all external network requests (e.g., `requests.get(url, timeout=10)`).
