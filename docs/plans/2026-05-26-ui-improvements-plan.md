# UI Color and Theme Improvements Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Improve the Gate Automation Monitor UI style, colors, and layout to match the company identity (blue and yellow) and present a clean, modern, and lightweight design.

**Architecture:** Refactor the styling logic in `views/main_window.py` using `ttk.Style` config/map commands over the `clam` theme base. No backend changes or database modifications.

**Tech Stack:** Python 3, Tkinter/ttk

---

### Task 1: UI Stylesheet Refactoring and Accent Styles

**Files:**
- Modify: `views/main_window.py`

**Step 1: Implement the color variables and styles**
We will replace lines 19 to 44 of `views/main_window.py` with custom colors:
```python
        BG_APP = "#f1f5f9"
        BG_CARD = "#ffffff"
        COLOR_PRIMARY = "#1e3a8a"
        COLOR_ACCENT = "#eab308"
        COLOR_ACCENT_HOVER = "#ca8a04"
        COLOR_TEXT_MAIN = "#0f172a"
        COLOR_TEXT_MUTED = "#64748b"
        BORDER_COLOR = "#cbd5e1"

        self.configure(bg=BG_APP)
        
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 10), background=BG_APP, foreground=COLOR_TEXT_MAIN)
        style.configure("TNotebook", background=COLOR_PRIMARY, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[15, 6], background=COLOR_PRIMARY, foreground="white", borderwidth=0)
        style.map("TNotebook.Tab", 
                  background=[("selected", BG_APP), ("active", "#1e40af")], 
                  foreground=[("selected", COLOR_PRIMARY), ("active", COLOR_ACCENT)])
        
        style.configure("Card.TFrame", background=BG_CARD, borderwidth=1, relief="solid", bordercolor=BORDER_COLOR)
        
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=COLOR_PRIMARY, foreground="white", padding=6)
        style.map("Primary.TButton", background=[("active", "#1e40af")])
        
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background=COLOR_ACCENT, foreground=COLOR_PRIMARY, padding=6)
        style.map("Accent.TButton", background=[("active", COLOR_ACCENT_HOVER)])
        
        style.configure("Success.TLabel", font=("Segoe UI", 14, "bold"), foreground="#10b981", background=BG_CARD)
        style.configure("Danger.TLabel", font=("Segoe UI", 14, "bold"), foreground="#ef4444", background=BG_CARD)
        style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"), foreground=COLOR_PRIMARY, background=BG_CARD)

        style.configure("Treeview", font=("Segoe UI", 10), rowheight=26, borderwidth=0, background=BG_CARD, fieldbackground=BG_CARD, foreground=COLOR_TEXT_MAIN)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=COLOR_PRIMARY, foreground="white", relief="flat")
        style.map("Treeview.Heading", background=[("active", "#1e40af")], foreground=[("active", "white")])
        style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", COLOR_PRIMARY)])
```

**Step 2: Run verification to check python compilation/syntax**
Run: `python3 -m py_compile views/main_window.py`
Expected: Exits with 0 (no output, syntax is correct).

**Step 3: Commit**
```bash
git add views/main_window.py
git commit -m "style: define main colors and stylesheet variables in main_window"
```

---

### Task 2: Apply Accent Styles and Cleanup Inline Backgrounds

**Files:**
- Modify: `views/main_window.py`

**Step 1: Replace hardcoded colors and apply styles on buttons & labels**
- Apply `Accent.TButton` to `btn_sync` in `_build_monitor_tab`:
  ```python
  btn_sync = ttk.Button(inner_top, text="⟳ Sincronizar Agora", style="Accent.TButton", command=self.on_sync)
  ```
- Update mock simulator labels/buttons in `_build_monitor_tab`:
  ```python
  ttk.Label(inner_mock, text="Simulador (ex: IN:0100...):", font=("Segoe UI", 9, "bold"), background="#ffffff", foreground="#64748b").pack(side='left', padx=(0, 10))
  ```
  And the simulated button:
  ```python
  ttk.Button(inner_mock, text="Ler Tag", style="Accent.TButton", command=self._handle_mock).pack(side='right', padx=5)
  ```
- In `_build_readers_tab`, update configurations title and labels to use `#ffffff` (BG_CARD) background and `COLOR_PRIMARY` foreground:
  ```python
  ttk.Label(inner_config, text="Configuração das Portas Seriais", font=("Segoe UI", 14, "bold"), background="#ffffff", foreground="#1e3a8a").grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 15))
  ...
  ttk.Label(inner_config, text="Leitor Entrada (IN):", background="#ffffff", font=("Segoe UI", 10, "bold"), foreground="#64748b").grid(row=1, column=0, sticky='w', pady=10)
  ...
  ttk.Label(inner_config, text="Leitor Saída (OUT):", background="#ffffff", font=("Segoe UI", 10, "bold"), foreground="#64748b").grid(row=2, column=0, sticky='w', pady=10)
  ```
- Apply `Primary.TButton` style to `btn_refresh` in both `_build_vehicles_tab` and `_build_tags_tab`:
  ```python
  btn_refresh = ttk.Button(tab, text="⟳ Atualizar Lista", style="Primary.TButton", command=self.refresh_vehicles)
  ...
  btn_refresh = ttk.Button(tab, text="⟳ Atualizar Lista", style="Primary.TButton", command=self.refresh_tags)
  ```

**Step 2: Run verification to check python compilation/syntax**
Run: `python3 -m py_compile views/main_window.py`
Expected: Exits with 0.

**Step 3: Commit**
```bash
git add views/main_window.py
git commit -m "style: apply button styles and fix inline label backgrounds"
```

---

### Task 3: Verify Entire Application Launch and Functionality

**Files:**
- Test: Launching the app locally to verify.

**Step 1: Run the main app or its tests**
Run: `pytest`
Expected: All existing tests pass.

**Step 2: Run verification to launch GUI**
Run: launch the application and visually inspect the tabs, alignment, and functionality.

**Step 3: Commit and finish**
Update `docs/plans/task.md` to complete all UI improvements tasks.
