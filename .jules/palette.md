## 2023-10-22 - Disable interactive buttons before state allows

**Learning:** When UI elements like "Copy" buttons are present but there's nothing to copy yet, it's better UX to explicitly disable them rather than leaving them active (which could lead to user confusion or silent failures). In Python Desktop apps (customtkinter), using `state="disabled"` is an easy way to signal this.
**Action:** Next time I design or refine a UI, I will ensure actions that depend on a previous action (like generation) are explicitly disabled until the prerequisite action completes.
