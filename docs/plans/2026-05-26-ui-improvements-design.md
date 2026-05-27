# Design Document: UI Color and Theme Improvements

## Goal
Improve the user interface of the Gate Automation Monitor to use the company's brand colors (corporate navy blue and golden yellow) and provide a clean, modern, and light interface without introducing heavy dependencies or performance bottlenecks. All modifications must be restricted entirely to UI styling in `views/main_window.py`.

## Proposed Theme Design (Hybrid Modern Theme)

### Color Palette
- **Primary (Deep Blue)**: `#1e3a8a` (Deep Blue/Indigo) - Used for tab header backgrounds, main buttons, and primary headers.
- **Accent (Golden Yellow)**: `#eab308` (Warm golden-yellow) - Used for quick actions, highlights, and subtle borders on active components.
- **Accent Hover (Darker Yellow)**: `#ca8a04` - Hover state for yellow buttons.
- **Main Background**: `#f1f5f9` (Light gray-blue) - A modern, soft background replacing the stark white window background.
- **Card Background**: `#ffffff` (Pure white) - Container cards for UI sections.
- **Border Color**: `#cbd5e1` (Light gray border) - Replaces dark borders for a cleaner look.
- **Status Safe/Success**: `#10b981` (Emerald green) - For "ONLINE" and "PORTÃO ABERTO" states.
- **Status Danger/Error**: `#ef4444` (Soft red) - For "OFFLINE" and error states.
- **Text Main**: `#0f172a` (Very dark slate) - High contrast text.
- **Text Muted**: `#64748b` (Medium slate) - Less important text labels.

### Component Styling
1. **Window Background**:
   - The main window background is styled with `bg="#f1f5f9"`.

2. **Notebook and Tabs**:
   - **TNotebook**: Background styled with `#1e3a8a` to create a prominent, integrated dark blue header.
   - **TNotebook.Tab**: Background set to `#1e3a8a` (inactive) and `#f1f5f9` (active), with active text in `#1e3a8a` and inactive text in `#ffffff`. A golden accent strip is configured dynamically.

3. **Card Panels (Card.TFrame)**:
   - Fills background with `#ffffff`.
   - Subtle border styled with `#cbd5e1`.

4. **Treeview Tables**:
   - Clean column headers using Deep Blue `#1e3a8a` background and white text.
   - Soft selection styling utilizing `#dbeafe` background and `#1e3a8a` foreground.
   - Restricting updates to colors only, ensuring no change to backend logic or data structures.

5. **Buttons**:
   - Primary buttons (like save/configure): navy blue with white text.
   - Action/Simulation buttons (like Sync and Read Tag): yellow with dark blue text.

## Verification Plan
1. **Visual Checks**: Launch `main.py` and manually verify the alignment, font scaling, tab transitions, hover states, and color contrast.
2. **Behavioral Checks**: Confirm all tabs, sync actions, mock simulator, and settings functions continue to work exactly as they did before styling changes.
