## 2024-05-24 - Caching PIL Images in UI-Driven Applications
**Learning:** When using `@functools.lru_cache` to cache `PIL.Image` objects in a live-preview UI (like customtkinter), modifying the image directly (e.g., cropping, resizing, or drawing) alters the original cached instance. Subsequent render cycles will reuse this corrupted state, leading to cumulative distortions and visual bugs.
**Action:** Always duplicate mutable cached objects retrieved from `@functools.lru_cache` using `.copy()` (e.g., `img = _get_cached_image(path).copy()`) before applying any modifications.
