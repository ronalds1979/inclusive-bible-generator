## 2024-05-24 - Missing Timeout on External API Calls
**Vulnerability:** External API requests in `getbible_api.py` were lacking a timeout configuration (`requests.get(url)`).
**Learning:** By default, the `requests` library will wait indefinitely for a response if no timeout is specified. In the context of a GUI application, an unresponsive external API can cause background threads to hang indefinitely, potentially leading to thread exhaustion and a Denial of Service (DoS).
**Prevention:** Always explicitly define a `timeout` parameter for external network requests (e.g., `requests.get(url, timeout=10)`) to ensure the application fails securely and gracefully when dealing with uncooperative external services.
