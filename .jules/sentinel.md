## 2024-10-25 - [Missing Timeout in External API Calls]
**Vulnerability:** The application made external network requests using `requests.get()` without specifying a `timeout`.
**Learning:** In a UI application, synchronous or un-timeouted network calls can block threads indefinitely if the remote server is unresponsive, leading to thread exhaustion and a Denial of Service (DoS) condition in the application UI (specifically when called from a background thread to prevent UI freezing, it can exhaust available background threads if many requests are made).
**Prevention:** Always explicitly define a `timeout` parameter for external network requests (e.g., `requests.get(url, timeout=10)`) to ensure the request fails fast and allows the application to recover gracefully.
