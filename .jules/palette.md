## 2024-05-24 - Interactive State Feedback
**Learning:** For desktop applications generated via customtkinter, disabling buttons (like copy buttons or action buttons) during empty states or asynchronous operations provides immediate, intuitive feedback to users, preventing confusion and duplicate actions.
**Action:** Always initialize context-dependent actions (like "Copy") as disabled until content is available, and disable main action buttons during async tasks, restoring their state when the task completes. Include inline visual feedback on successful actions where possible.
