## 2023-10-22 - Disable interactive buttons before state allows

**Learning:** When UI elements like "Copy" buttons are present but there's nothing to copy yet, it's better UX to explicitly disable them rather than leaving them active (which could lead to user confusion or silent failures). In Python Desktop apps (customtkinter), using `state="disabled"` is an easy way to signal this.
**Action:** Next time I design or refine a UI, I will ensure actions that depend on a previous action (like generation) are explicitly disabled until the prerequisite action completes.

## 2024-05-18 - Use Inline Component Feedback for Copy Buttons
**Learning:** While global status labels are good for general app state, interactions like "Copy to Clipboard" feel much more responsive when the button itself provides visual feedback (like prepending a '✓ ' temporarily). This localized feedback confirms to the user exactly which button action succeeded.
**Action:** Next time I design or refine a UI, I will implement inline, temporary visual feedback on the specific UI component that was interacted with, rather than relying solely on global success messages.

## 2024-05-18 - Use Inline Component Feedback for Primary Actions
**Learning:** Adding temporary inline feedback (like a checkmark) directly to the main action buttons ("Generate Content", "Fetch Verse") provides a much more satisfying and reassuring UX compared to only updating a secondary global status label.
**Action:** When implementing primary or long-running actions, apply localized temporary visual feedback on the button itself upon success to confirm completion.
## 2024-05-19 - Semantic Status Colors (Cognitive Accessibility)
**Learning:** Initializing generic status labels with a single color (e.g., green) causes cognitive dissonance when error or neutral messages are displayed. In customtkinter, this can be confusing to users relying on visual cues.
**Action:** When updating a shared `CTkLabel` for status messages, always dynamically configure `text_color` (`green` for success, `red` for error, `gray` for loading/neutral) alongside the text update to maintain semantic consistency.

## 2026-10-30 - Dynamic Button States
**Learning:** In customtkinter, binding real-time state updates to interactive elements (disabling buttons when required inputs are empty) prevents silent action failures and gives immediate visual feedback.
**Action:** Always map empty input states to disabled button states for async actions.
## 2026-10-31 - [Empty State UI Prompt]
**Learning:** Hardcoded empty states (like 'No image generated yet') reduce user clarity and fail internationalization.
**Action:** Always map empty state placeholder text to localized keys in JSON and ensure they dynamically reset when input fields are cleared.
