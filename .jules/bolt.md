
## 2024-05-14 - Optimize repetitive PIL operations in CustomTkinter preview
**Learning:** CustomTkinter's live preview mode triggers redundant disk I/O and PIL image processing (resizing, cropping, dark overlay) on every keystroke, which blocks the UI thread and causes noticeable lag.
**Action:** Use `@functools.lru_cache` to cache static background operations and font loading. Since `PIL.Image` objects are mutable, ALWAYS use `.copy()` when fetching from the cache to prevent UI-driven modifications from corrupting the cached original image.
