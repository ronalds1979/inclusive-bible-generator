
## 2023-10-23 - Image Preview Rendering Loop Optimization
**Learning:** In desktop UI applications built with `customtkinter` and `Pillow`, rendering live previews on keystrokes (`trigger_preview` fired on every `<KeyRelease>`) causes redundant disk I/O when processing the base background template and fonts. `Pillow` lacks native rendering memoization out-of-the-box.
**Action:** Extract static/base layers (e.g. background processing, overlay adding) and static fonts from the text-rendering function. Wrap them with `@functools.lru_cache` and ensure mutable objects like `PIL.Image` are `.copy()`'d before further UI-driven text manipulation. This eliminates redundant disk I/O and PIL manipulation when adjusting purely UI text on top.
