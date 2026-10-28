## 2023-10-22 - Cache Image and Font loading
**Learning:** In a live preview application where Pillow's `ImageDraw.Draw` is invoked frequently (e.g. bounded by a 500ms debounce), repeated opening, resizing, cropping, compositing, and font parsing of identical background images and fonts severely throttles performance. Drawing text mutates the image, so we must return a `.copy()` of the pre-processed cached background to prevent text accumulation.
**Action:** Implemented an in-memory dictionary cache for pre-processed background images (keyed by path and dimensions) and parsed TrueType fonts (keyed by path and size). Always `.copy()` cached images before yielding them for mutation.
## 2023-10-28 - [getbible_api.py] Cache full chapter payload for verse lookups
**Learning:** The `api.getbible.net/v2` API returns the payload for an entire chapter even when we are requesting specific verses from it. Doing sequential requests for verses from the same chapter incurs significant redundant network overhead.
**Action:** When working with chapter-based APIs, cache the entire chapter payload in memory (e.g. using `functools.lru_cache`) instead of re-fetching per verse request.
⚡ Optimized uncached regex compilation in _parse_reference by pre-compiling regex pattern at class-level
