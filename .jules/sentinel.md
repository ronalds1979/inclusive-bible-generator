## 2025-02-14 - Fix Path Traversal and SSRF Vulnerabilities

**Vulnerability:** Path Traversal via string replacement in file generation (`main.py` and `generator.py`), and URL Injection/SSRF in API request generation (`youversion_api.py`).

**Learning:** Replacing only spaces and colons with underscores in a user-provided string (like a Bible reference) is insufficient to prevent directory traversal sequences (like `../`), potentially allowing file writes outside the intended output directory. Constructing URLs via simple string interpolation without URL encoding user input allows URL injection/SSRF.

**Prevention:** Use a regex (like `re.sub(r'[^\w\-]', '_', text)`) to strictly sanitize user inputs intended for filenames, allowing only safe characters. Use URL encoding (e.g., `urllib.parse.quote()`) to sanitize user inputs appended to URLs.
