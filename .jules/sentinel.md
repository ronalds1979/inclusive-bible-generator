## 2024-05-18 - [Missing Timeout in External Requests]
**Vulnerability:** The application was making external API requests using `requests.get()` without specifying a `timeout` parameter.
**Learning:** Default behavior of many Python HTTP libraries (like `requests`) is to wait indefinitely for a response if no timeout is specified. This could lead to a Denial of Service (DoS) vulnerability via thread exhaustion if the external API hangs or becomes unresponsive.
**Prevention:** Always enforce a timeout parameter (e.g., `requests.get(url, timeout=10)`) on all external network requests to fail fast and securely.
