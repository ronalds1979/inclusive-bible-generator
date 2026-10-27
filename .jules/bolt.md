## 2023-10-22 - Cache Image and Font loading
**Learning:** In a live preview application where Pillow's `ImageDraw.Draw` is invoked frequently (e.g. bounded by a 500ms debounce), repeated opening, resizing, cropping, compositing, and font parsing of identical background images and fonts severely throttles performance. Drawing text mutates the image, so we must return a `.copy()` of the pre-processed cached background to prevent text accumulation.
**Action:** Implemented an in-memory dictionary cache for pre-processed background images (keyed by path and dimensions) and parsed TrueType fonts (keyed by path and size). Always `.copy()` cached images before yielding them for mutation.

## 2024-11-20 - API Chapter Caching
**Learning:** The `api.getbible.net/v2` API fetches verses by returning the *entire* chapter payload. Redundant network calls for the same chapter (e.g., when a user browses sequential verses) cause unnecessary latency.
**Action:** Implemented an in-memory LRU cache (`@functools.lru_cache`) on the private `_fetch_chapter_json` method to prevent redundant downloads, dropping response times for cached chapters from ~800ms to ~0ms.
