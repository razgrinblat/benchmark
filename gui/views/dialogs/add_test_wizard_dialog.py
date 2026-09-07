from typing import Callable
import customtkinter as ctk


class AddTestWizardDialog(ctk.CTkToplevel):
    """
    Step-by-step modal wizard for configuring and adding a new test suite.
    Step 1: Name the test
    Step 2: Number of sessions & session names
    Step 3: Processing mode (sequential / parallel) per session
    Step 4: File payload (count, size, scale) per session
    Step 5: FEC percentage & chunk size per session
    Step 6: Review summary & create
    """

    STEP_TITLES = [
        "1. Test Name",
        "2. Sessions",
        "3. Processing Mode",
        "4. File Payload",
        "5. FEC & Chunk Size",
        "6. Review & Create"
    ]

    def __init__(self, parent, config_data: dict, on_success: Callable[[dict, dict], None], **kwargs):
        super().__init__(parent, **kwargs)
        self.config_data = config_data
        self.on_success = on_success

        self.title("🧙 Add Test Suite - Guided Step Wizard")
        self.geometry("740x660")
        self.minsize(700, 600)
        self.transient(parent)

        try:
            self.grab_set()
        except Exception:
            pass

        # Wizard State
        existing_tests = self.config_data.get("tests", [])
        self.test_name = f"Test-{len(existing_tests) + 1}"
        self.session_count = 1
        self.session_names = [f"{self.test_name}_Session_1"]
        self.session_modes = {self.session_names[0]: "parallel"}
        self.session_payloads = {self.session_names[0]: {"count": 10, "size": 1, "scale": "MB"}}
        self.session_fec_chunks = {self.session_names[0]: {"fec": 0, "chunk": 65000}}

        self.current_step = 1

        # Layout containers
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_top_tracker()
        self._build_content_area()
        self._build_bottom_controls()

        self._show_current_step()

    def _build_top_tracker(self):
        tracker_card = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "#1e293b"), height=70)
        tracker_card.grid(row=0, column=0, sticky="ew")
        tracker_card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(tracker_card, fg_color="transparent")
        inner.pack(padx=16, pady=12, fill="x")

        self.step_heading_lbl = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#38bdf8"
        )
        self.step_heading_lbl.pack(anchor="w")

        # Step pills row
        self.pills_row = ctk.CTkFrame(inner, fg_color="transparent")
        self.pills_row.pack(fill="x", pady=(6, 0))

        self.pill_labels = []
        for idx, title in enumerate(self.STEP_TITLES, start=1):
            pill = ctk.CTkLabel(
                self.pills_row,
                text=title,
                corner_radius=6,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=("gray50", "#94a3b8"),
                fg_color="transparent",
                padx=8,
                pady=2
            )
            pill.pack(side="left", padx=2)
            self.pill_labels.append(pill)

            if idx < len(self.STEP_TITLES):
                arr = ctk.CTkLabel(self.pills_row, text="›", font=ctk.CTkFont(size=11), text_color=("gray50", "#64748b"))
                arr.pack(side="left", padx=1)

    def _build_content_area(self):
        self.content_scroll = ctk.CTkScrollableFrame(self, corner_radius=10, fg_color=("gray95", "#0f172a"))
        self.content_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        self.content_scroll.grid_columnconfigure(0, weight=1)

    def _build_bottom_controls(self):
        bottom_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "#1e293b"), height=60)
        bottom_bar.grid(row=2, column=0, sticky="ew")

        inner = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        self.btn_cancel = ctk.CTkButton(
            inner,
            text="Cancel",
            width=90,
            height=34,
            corner_radius=8,
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self.destroy
        )
        self.btn_cancel.pack(side="left")

        self.error_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#ef4444"
        )
        self.error_label.pack(side="left", padx=16)

        self.btn_next = ctk.CTkButton(
            inner,
            text="Next ➔",
            width=140,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._on_next_click
        )
        self.btn_next.pack(side="right", padx=(6, 0))

        self.btn_back = ctk.CTkButton(
            inner,
            text="⮜ Back",
            width=90,
            height=34,
            corner_radius=8,
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self._on_back_click
        )
        self.btn_back.pack(side="right")

    def _update_tracker(self):
        self.step_heading_lbl.configure(
            text=f"Step {self.current_step} of {len(self.STEP_TITLES)}: {self.STEP_TITLES[self.current_step-1]}"
        )
        for idx, pill in enumerate(self.pill_labels, start=1):
            if idx == self.current_step:
                pill.configure(
                    fg_color=("#2563eb", "#1d4ed8"),
                    text_color="#ffffff",
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
                )
            elif idx < self.current_step:
                pill.configure(
                    fg_color=("gray80", "#334155"),
                    text_color=("#10b981", "#34d399"),
                    font=ctk.CTkFont(family="Segoe UI", size=11)
                )
            else:
                pill.configure(
                    fg_color="transparent",
                    text_color=("gray50", "#94a3b8"),
                    font=ctk.CTkFont(family="Segoe UI", size=11)
                )

        self.btn_back.configure(state="normal" if self.current_step > 1 else "disabled")
        if self.current_step == len(self.STEP_TITLES):
            self.btn_next.configure(text="🎉 Create Suite", fg_color="#10b981", hover_color="#059669")
        else:
            self.btn_next.configure(text="Next ➔", fg_color="#2563eb", hover_color="#1d4ed8")

        self.error_label.configure(text="")

    def _clear_content(self):
        for widget in self.content_scroll.winfo_children():
            widget.destroy()

    def _show_current_step(self):
        self._update_tracker()
        self._clear_content()

        if self.current_step == 1:
            self._render_step_1()
        elif self.current_step == 2:
            self._render_step_2()
        elif self.current_step == 3:
            self._render_step_3()
        elif self.current_step == 4:
            self._render_step_4()
        elif self.current_step == 5:
            self._render_step_5()
        elif self.current_step == 6:
            self._render_step_6()

    # --- STEP 1: TEST NAME ---
    def _render_step_1(self):
        card = ctk.CTkFrame(self.content_scroll, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card.pack(fill="x", padx=12, pady=16)

        title = ctk.CTkLabel(
            card,
            text="🏷️ Name Your Benchmark Test Suite",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w", padx=16, pady=(16, 6))

        desc = ctk.CTkLabel(
            card,
            text="Provide a unique descriptive identifier for this test suite (e.g. StressTest-LargeFiles, Throughput-Parallel).",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8"),
            wraplength=620,
            justify="left"
        )
        desc.pack(anchor="w", padx=16, pady=(0, 16))

        lbl_entry = ctk.CTkLabel(card, text="Test Suite Name:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_entry.pack(anchor="w", padx=16, pady=(0, 4))

        self.entry_suite_name = ctk.CTkEntry(card, height=36, corner_radius=8, font=ctk.CTkFont(size=13))
        self.entry_suite_name.pack(fill="x", padx=16, pady=(0, 20))
        self.entry_suite_name.insert(0, self.test_name)
        self.entry_suite_name.focus()

    def _validate_step_1(self) -> bool:
        name = self.entry_suite_name.get().strip()
        if not name:
            self.error_label.configure(text="Test suite name cannot be empty.")
            return False

        existing_names = [t.get("name") for t in self.config_data.get("tests", [])]
        if name in existing_names:
            self.error_label.configure(text=f"Test suite '{name}' already exists.")
            return False

        self.test_name = name
        return True

    # --- STEP 2: NUMBER OF SESSIONS & SESSION NAMES ---
    def _render_step_2(self):
        card = ctk.CTkFrame(self.content_scroll, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card.pack(fill="x", padx=12, pady=16)

        title = ctk.CTkLabel(
            card,
            text="🔢 Session Count & Session Identifiers",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w", padx=16, pady=(16, 6))

        desc = ctk.CTkLabel(
            card,
            text="Choose how many sessions will run in parallel during this test suite, and assign a unique name to each session.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8"),
            wraplength=620,
            justify="left"
        )
        desc.pack(anchor="w", padx=16, pady=(0, 14))

        # Stepper row
        stepper_frame = ctk.CTkFrame(card, fg_color="transparent")
        stepper_frame.pack(anchor="w", padx=16, pady=(0, 14))

        lbl_s_cnt = ctk.CTkLabel(stepper_frame, text="Total Sessions:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_s_cnt.pack(side="left", padx=(0, 10))

        btn_dec = ctk.CTkButton(
            stepper_frame,
            text="➖",
            width=36,
            height=32,
            corner_radius=6,
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=lambda: self._adjust_session_count(-1)
        )
        btn_dec.pack(side="left", padx=2)

        self.lbl_count_val = ctk.CTkLabel(
            stepper_frame,
            text=str(self.session_count),
            width=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_count_val.pack(side="left", padx=6)

        btn_inc = ctk.CTkButton(
            stepper_frame,
            text="➕",
            width=36,
            height=32,
            corner_radius=6,
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=lambda: self._adjust_session_count(1)
        )
        btn_inc.pack(side="left", padx=2)

        # Dynamic container for session name entries
        self.sessions_input_container = ctk.CTkFrame(card, fg_color="transparent")
        self.sessions_input_container.pack(fill="x", padx=16, pady=(0, 16))

        self._render_session_name_entries()

    def _adjust_session_count(self, delta: int):
        new_cnt = max(1, min(16, self.session_count + delta))
        if new_cnt == self.session_count:
            return

        self._save_session_names_from_entries()
        self.session_count = new_cnt
        self.lbl_count_val.configure(text=str(self.session_count))

        while len(self.session_names) < self.session_count:
            idx = len(self.session_names) + 1
            default_name = f"{self.test_name}_Session_{idx}"
            self.session_names.append(default_name)
            self.session_modes[default_name] = "parallel"
            self.session_payloads[default_name] = {"count": 10, "size": 1, "scale": "MB"}
            self.session_fec_chunks[default_name] = {"fec": 0, "chunk": 65000}

        while len(self.session_names) > self.session_count:
            popped = self.session_names.pop()
            self.session_modes.pop(popped, None)
            self.session_payloads.pop(popped, None)
            self.session_fec_chunks.pop(popped, None)

        self._render_session_name_entries()

    def _render_session_name_entries(self):
        for widget in self.sessions_input_container.winfo_children():
            widget.destroy()

        self.session_name_entry_widgets = []
        for i in range(self.session_count):
            row = ctk.CTkFrame(self.sessions_input_container, fg_color="transparent")
            row.pack(fill="x", pady=4)

            lbl = ctk.CTkLabel(row, text=f"Session #{i+1} Name:", width=130, anchor="w", font=ctk.CTkFont(size=12))
            lbl.pack(side="left")

            entry = ctk.CTkEntry(row, height=32, corner_radius=6)
            entry.pack(side="left", fill="x", expand=True)

            val = self.session_names[i] if i < len(self.session_names) else f"{self.test_name}_Session_{i+1}"
            entry.insert(0, val)
            self.session_name_entry_widgets.append(entry)

    def _save_session_names_from_entries(self):
        updated_names = []
        for i, entry in enumerate(self.session_name_entry_widgets):
            val = entry.get().strip() or f"{self.test_name}_Session_{i+1}"
            old_name = self.session_names[i] if i < len(self.session_names) else val
            if old_name != val:
                # Migrate dictionary keys
                if old_name in self.session_modes:
                    self.session_modes[val] = self.session_modes.pop(old_name)
                if old_name in self.session_payloads:
                    self.session_payloads[val] = self.session_payloads.pop(old_name)
                if old_name in self.session_fec_chunks:
                    self.session_fec_chunks[val] = self.session_fec_chunks.pop(old_name)
            updated_names.append(val)
        self.session_names = updated_names

    def _validate_step_2(self) -> bool:
        self._save_session_names_from_entries()
        for i, s_name in enumerate(self.session_names):
            if not s_name:
                self.error_label.configure(text=f"Session #{i+1} cannot have an empty name.")
                return False

        if len(self.session_names) != len(set(self.session_names)):
            self.error_label.configure(text="All session names in this suite must be unique.")
            return False

        # Ensure all sessions have initialized properties
        for s_name in self.session_names:
            if s_name not in self.session_modes:
                self.session_modes[s_name] = "parallel"
            if s_name not in self.session_payloads:
                self.session_payloads[s_name] = {"count": 10, "size": 1, "scale": "MB"}
            if s_name not in self.session_fec_chunks:
                self.session_fec_chunks[s_name] = {"fec": 0, "chunk": 65000}

        return True

    # --- STEP 3: PROCESSING MODE (SEQUENTIAL / PARALLEL) ---
    def _render_step_3(self):
        header_card = ctk.CTkFrame(self.content_scroll, corner_radius=10, fg_color=("gray90", "#1e293b"))
        header_card.pack(fill="x", padx=12, pady=(16, 8))

        title = ctk.CTkLabel(
            header_card,
            text="⚡ File Processing Mode per Session",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w", padx=16, pady=(16, 4))

        desc = ctk.CTkLabel(
            header_card,
            text="For each session, specify whether files are generated and transferred in Sequential or Parallel mode.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8"),
            wraplength=620,
            justify="left"
        )
        desc.pack(anchor="w", padx=16, pady=(0, 16))

        self.step3_mode_widgets = {}

        for s_name in self.session_names:
            s_card = ctk.CTkFrame(self.content_scroll, corner_radius=8, fg_color=("gray85", "#1e293b"))
            s_card.pack(fill="x", padx=12, pady=6)

            h_row = ctk.CTkFrame(s_card, fg_color="transparent")
            h_row.pack(fill="x", padx=16, pady=12)

            lbl = ctk.CTkLabel(h_row, text=f"📦 Session: {s_name}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8")
            lbl.pack(side="left")

            current_mode = self.session_modes.get(s_name, "parallel")
            seg = ctk.CTkSegmentedButton(
                h_row,
                values=["sequential", "parallel"],
                corner_radius=6,
                selected_color="#2563eb",
                selected_hover_color="#1d4ed8"
            )
            seg.set(current_mode)
            seg.pack(side="right")

            self.step3_mode_widgets[s_name] = seg

    def _validate_step_3(self) -> bool:
        for s_name, seg in self.step3_mode_widgets.items():
            self.session_modes[s_name] = seg.get()
        return True

    # --- STEP 4: FILE PAYLOAD SETTINGS ---
    def _render_step_4(self):
        header_card = ctk.CTkFrame(self.content_scroll, corner_radius=10, fg_color=("gray90", "#1e293b"))
        header_card.pack(fill="x", padx=12, pady=(16, 8))

        title = ctk.CTkLabel(
            header_card,
            text="📁 File Payload Settings per Session",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w", padx=16, pady=(16, 4))

        desc = ctk.CTkLabel(
            header_card,
            text="Configure how many files to generate, the file size, and the scale unit (KB, MB, GB) for each session.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8"),
            wraplength=620,
            justify="left"
        )
        desc.pack(anchor="w", padx=16, pady=(0, 16))

        self.step4_payload_widgets = {}

        for s_name in self.session_names:
            s_card = ctk.CTkFrame(self.content_scroll, corner_radius=8, fg_color=("gray85", "#1e293b"))
            s_card.pack(fill="x", padx=12, pady=6)

            lbl_title = ctk.CTkLabel(s_card, text=f"📦 Session: {s_name}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8")
            lbl_title.pack(anchor="w", padx=16, pady=(12, 6))

            grid = ctk.CTkFrame(s_card, fg_color="transparent")
            grid.pack(fill="x", padx=16, pady=(0, 12))
            grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

            p_data = self.session_payloads.get(s_name, {"count": 10, "size": 1, "scale": "MB"})

            # File count
            c_lbl = ctk.CTkLabel(grid, text="File Count:", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
            c_lbl.grid(row=0, column=0, sticky="w", padx=4)
            c_entry = ctk.CTkEntry(grid, height=32, corner_radius=6)
            c_entry.grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 0))
            c_entry.insert(0, str(p_data["count"]))

            # File size
            s_lbl = ctk.CTkLabel(grid, text="File Size:", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
            s_lbl.grid(row=0, column=1, sticky="w", padx=4)
            s_entry = ctk.CTkEntry(grid, height=32, corner_radius=6)
            s_entry.grid(row=1, column=1, sticky="ew", padx=4, pady=(2, 0))
            s_entry.insert(0, str(p_data["size"]))

            # File scale
            sc_lbl = ctk.CTkLabel(grid, text="Scale Unit:", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
            sc_lbl.grid(row=0, column=2, sticky="w", padx=4)
            sc_menu = ctk.CTkOptionMenu(grid, values=["KB", "MB", "GB"], height=32, corner_radius=6)
            sc_menu.grid(row=1, column=2, sticky="ew", padx=4, pady=(2, 0))
            sc_menu.set(p_data["scale"])

            # Total badge
            tot_lbl = ctk.CTkLabel(grid, text="Total Payload:", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
            tot_lbl.grid(row=0, column=3, sticky="w", padx=4)
            tot_val = ctk.CTkLabel(
                grid,
                text=f"{p_data['count'] * p_data['size']} {p_data['scale']}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#10b981",
                height=32
            )
            tot_val.grid(row=1, column=3, sticky="w", padx=4, pady=(2, 0))

            def update_total(e=None, cnt_e=c_entry, sz_e=s_entry, sc_m=sc_menu, tv=tot_val):
                try:
                    c = int(cnt_e.get().strip() or 0)
                    s = int(sz_e.get().strip() or 0)
                    sc = sc_m.get()
                    tv.configure(text=f"{c * s} {sc}")
                except Exception:
                    tv.configure(text="--")

            c_entry.bind("<KeyRelease>", update_total)
            s_entry.bind("<KeyRelease>", update_total)
            sc_menu.configure(command=lambda _: update_total())

            self.step4_payload_widgets[s_name] = {
                "count": c_entry,
                "size": s_entry,
                "scale": sc_menu
            }

    def _validate_step_4(self) -> bool:
        for s_name, w in self.step4_payload_widgets.items():
            try:
                cnt = int(w["count"].get().strip())
                sz = int(w["size"].get().strip())
                scale = w["scale"].get().strip()
                if cnt <= 0 or sz <= 0:
                    self.error_label.configure(text=f"Session '{s_name}': Count and Size must be greater than 0.")
                    return False
                self.session_payloads[s_name] = {
                    "count": cnt,
                    "size": sz,
                    "scale": scale
                }
            except ValueError:
                self.error_label.configure(text=f"Session '{s_name}': File Count and Size must be valid integers.")
                return False
        return True

    # --- STEP 5: FEC & CHUNK SIZE CONFIGURATION ---
    def _render_step_5(self):
        header_card = ctk.CTkFrame(self.content_scroll, corner_radius=10, fg_color=("gray90", "#1e293b"))
        header_card.pack(fill="x", padx=12, pady=(16, 8))

        title = ctk.CTkLabel(
            header_card,
            text="🎛️ FEC Percentage & Chunk Size per Session",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w", padx=16, pady=(16, 4))

        desc = ctk.CTkLabel(
            header_card,
            text="Configure Forward Error Correction (FEC) packet loss tolerance (%) and transfer chunk size (bytes) for each session.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8"),
            wraplength=620,
            justify="left"
        )
        desc.pack(anchor="w", padx=16, pady=(0, 16))

        self.step5_fec_widgets = {}

        for s_name in self.session_names:
            s_card = ctk.CTkFrame(self.content_scroll, corner_radius=8, fg_color=("gray85", "#1e293b"))
            s_card.pack(fill="x", padx=12, pady=6)

            lbl_title = ctk.CTkLabel(s_card, text=f"📦 Session: {s_name}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8")
            lbl_title.pack(anchor="w", padx=16, pady=(12, 6))

            grid = ctk.CTkFrame(s_card, fg_color="transparent")
            grid.pack(fill="x", padx=16, pady=(0, 14))
            grid.grid_columnconfigure((0, 1), weight=1)

            fc_data = self.session_fec_chunks.get(s_name, {"fec": 0, "chunk": 65000})

            # FEC Col
            fec_box = ctk.CTkFrame(grid, fg_color="transparent")
            fec_box.grid(row=0, column=0, sticky="nsew", padx=6)

            fec_lbl = ctk.CTkLabel(fec_box, text="FEC Percentage (%):", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
            fec_lbl.pack(anchor="w")

            fec_entry = ctk.CTkEntry(fec_box, height=32, corner_radius=6)
            fec_entry.pack(fill="x", pady=(2, 6))
            fec_entry.insert(0, str(fc_data["fec"]))

            # FEC Preset buttons
            fec_presets = ctk.CTkFrame(fec_box, fg_color="transparent")
            fec_presets.pack(fill="x")
            for p_lbl, p_val in [("0% None", 0), ("10% Low", 10), ("66% High", 66)]:
                btn_p = ctk.CTkButton(
                    fec_presets,
                    text=p_lbl,
                    height=22,
                    font=ctk.CTkFont(size=10),
                    corner_radius=4,
                    fg_color=("gray80", "#334155"),
                    hover_color=("gray70", "#475569"),
                    command=lambda v=p_val, e=fec_entry: self._set_entry(e, str(v))
                )
                btn_p.pack(side="left", padx=2)

            # Chunk Col
            chk_box = ctk.CTkFrame(grid, fg_color="transparent")
            chk_box.grid(row=0, column=1, sticky="nsew", padx=6)

            chk_lbl = ctk.CTkLabel(chk_box, text="Chunk Size (Bytes):", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
            chk_lbl.pack(anchor="w")

            chk_entry = ctk.CTkEntry(chk_box, height=32, corner_radius=6)
            chk_entry.pack(fill="x", pady=(2, 6))
            chk_entry.insert(0, str(fc_data["chunk"]))

            # Chunk Presets
            chk_presets = ctk.CTkFrame(chk_box, fg_color="transparent")
            chk_presets.pack(fill="x")
            for p_lbl, p_val in [("18KB", 18000), ("65KB", 65000), ("80KB", 80000)]:
                btn_p = ctk.CTkButton(
                    chk_presets,
                    text=p_lbl,
                    height=22,
                    font=ctk.CTkFont(size=10),
                    corner_radius=4,
                    fg_color=("gray80", "#334155"),
                    hover_color=("gray70", "#475569"),
                    command=lambda v=p_val, e=chk_entry: self._set_entry(e, str(v))
                )
                btn_p.pack(side="left", padx=2)

            self.step5_fec_widgets[s_name] = {
                "fec": fec_entry,
                "chunk": chk_entry
            }

    def _set_entry(self, entry: ctk.CTkEntry, val: str):
        entry.delete(0, "end")
        entry.insert(0, val)

    def _validate_step_5(self) -> bool:
        for s_name, w in self.step5_fec_widgets.items():
            try:
                fec = int(w["fec"].get().strip())
                chunk = int(w["chunk"].get().strip())
                if not (0 <= fec <= 100):
                    self.error_label.configure(text=f"Session '{s_name}': FEC percentage must be between 0 and 100.")
                    return False
                if chunk <= 0:
                    self.error_label.configure(text=f"Session '{s_name}': Chunk size must be greater than 0.")
                    return False
                self.session_fec_chunks[s_name] = {
                    "fec": fec,
                    "chunk": chunk
                }
            except ValueError:
                self.error_label.configure(text=f"Session '{s_name}': FEC and Chunk Size must be valid integers.")
                return False
        return True

    # --- STEP 6: SUMMARY & REVIEW ---
    def _render_step_6(self):
        card = ctk.CTkFrame(self.content_scroll, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card.pack(fill="x", padx=12, pady=16)

        title = ctk.CTkLabel(
            card,
            text="📋 Review Test Suite Configuration",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#10b981"
        )
        title.pack(anchor="w", padx=16, pady=(16, 4))

        desc = ctk.CTkLabel(
            card,
            text="Review the details below. Click 'Create Suite' to save this new test configuration.",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8")
        )
        desc.pack(anchor="w", padx=16, pady=(0, 16))

        # Overview banner
        banner = ctk.CTkFrame(card, corner_radius=8, fg_color=("gray80", "#0f172a"))
        banner.pack(fill="x", padx=16, pady=(0, 16))

        lbl_sname = ctk.CTkLabel(
            banner,
            text=f"🧪 Suite Name: {self.test_name}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_sname.pack(side="left", padx=14, pady=10)

        lbl_scnt = ctk.CTkLabel(
            banner,
            text=f"Parallel Sessions: {len(self.session_names)}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a855f7"
        )
        lbl_scnt.pack(side="right", padx=14, pady=10)

        # Per-session breakdown
        for s_name in self.session_names:
            s_row = ctk.CTkFrame(card, corner_radius=6, fg_color=("gray85", "#334155"))
            s_row.pack(fill="x", padx=16, pady=4)

            top_r = ctk.CTkFrame(s_row, fg_color="transparent")
            top_r.pack(fill="x", padx=12, pady=(8, 4))

            lbl_sn = ctk.CTkLabel(top_r, text=f"📦 {s_name}", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
            lbl_sn.pack(side="left")

            mode = self.session_modes.get(s_name, "sequential")
            m_badge = ctk.CTkLabel(
                top_r,
                text=f"⚡ {mode.upper()}",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#38bdf8" if mode == "parallel" else "#fbbf24"
            )
            m_badge.pack(side="right")

            bot_r = ctk.CTkFrame(s_row, fg_color="transparent")
            bot_r.pack(fill="x", padx=12, pady=(0, 8))

            p = self.session_payloads.get(s_name, {"count": 1, "size": 1, "scale": "MB"})
            fc = self.session_fec_chunks.get(s_name, {"fec": 0, "chunk": 65000})

            param_text = (
                f"Files: {p['count']} × {p['size']}{p['scale']} (Total: {p['count']*p['size']} {p['scale']})  |  "
                f"FEC: {fc['fec']}%  |  Chunk: {fc['chunk']:,} Bytes"
            )
            lbl_p = ctk.CTkLabel(bot_r, text=param_text, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=("gray40", "#cbd5e1"))
            lbl_p.pack(anchor="w")

    def _on_next_click(self):
        # Validate current step before advancing
        if self.current_step == 1 and not self._validate_step_1():
            return
        elif self.current_step == 2 and not self._validate_step_2():
            return
        elif self.current_step == 3 and not self._validate_step_3():
            return
        elif self.current_step == 4 and not self._validate_step_4():
            return
        elif self.current_step == 5 and not self._validate_step_5():
            return
        elif self.current_step == 6:
            # Finalize creation
            self._finalize_creation()
            return

        self.current_step += 1
        self._show_current_step()

    def _on_back_click(self):
        if self.current_step > 1:
            self.current_step -= 1
            self._show_current_step()

    def _finalize_creation(self):
        new_test_def = {
            "name": self.test_name,
            "sessions": list(self.session_names)
        }

        new_session_defs = {}
        for s_name in self.session_names:
            p = self.session_payloads[s_name]
            fc = self.session_fec_chunks[s_name]
            new_session_defs[s_name] = {
                "mode": self.session_modes[s_name],
                "file_count": p["count"],
                "file_size": p["size"],
                "file_scale": p["scale"],
                "fec_value": fc["fec"],
                "chunk_value": fc["chunk"]
            }

        self.destroy()
        self.on_success(new_test_def, new_session_defs)
