import time
import queue
import logging
import threading
from pathlib import Path
import customtkinter as ctk

from core import BenchmarkController
from config import dut_settings

CONFIG_JSON_PATH = Path("config.json")
DUT_INI_PATH = Path("dut_settings.ini")


class ExecutionView(ctk.CTkFrame):
    """
    Live Execution & Monitor Tab.
    Provides test selection, benchmark triggers, progress bars, live ETA, and console logs.
    """

    def __init__(self, parent, app_controller, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app_controller

        self.is_running = False
        self.benchmark_thread = None
        self.start_time = None
        self.total_tests_to_run = 0
        self.completed_tests = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_ui()
        self.update_live_timer()

    def _build_ui(self):
        # Header Title
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        title = ctk.CTkLabel(
            header_frame,
            text="🚀 Benchmark Execution & Live Monitor",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_frame,
            text="Orchestrate file generation, throughput benchmarking, and live telemetry across DUTs.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=("gray40", "#94a3b8")
        )
        subtitle.pack(anchor="w")

        # KPI Metrics Cards (4-column row)
        kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        kpi_container.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        for col in range(4):
            kpi_container.grid_columnconfigure(col, weight=1, uniform="kpi")

        self.kpi_card_suite = self._create_kpi_card(kpi_container, 0, "🎯 Target Suite", "All Tests")
        self.kpi_card_elapsed = self._create_kpi_card(kpi_container, 1, "⏱️ Elapsed Time", "00:00:00")
        self.kpi_card_eta = self._create_kpi_card(kpi_container, 2, "⏳ Estimated Time", "--:--")
        self.kpi_card_status = self._create_kpi_card(kpi_container, 3, "🚦 State", "Ready", value_color="#10b981")

        # Controls & Action Panel Card
        control_card = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray90", "#1e293b"))
        control_card.grid(row=2, column=0, sticky="ew", pady=(0, 16), padx=2)
        control_card.grid_columnconfigure(1, weight=1)

        # Suite Selector
        selector_label = ctk.CTkLabel(control_card, text="Select Test Suite:", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
        selector_label.grid(row=0, column=0, padx=(18, 10), pady=16, sticky="w")

        self.suite_option_var = ctk.StringVar(value="All Tests")
        self.suite_option_menu = ctk.CTkOptionMenu(
            control_card,
            variable=self.suite_option_var,
            values=["All Tests"],
            width=220,
            corner_radius=8,
            command=lambda v: self.kpi_card_suite.configure(text=v)
        )
        self.suite_option_menu.grid(row=0, column=1, padx=10, pady=16, sticky="w")

        # Flags Checkboxes
        self.mount_var = ctk.BooleanVar(value=True)
        self.mount_checkbox = ctk.CTkCheckBox(
            control_card, 
            text="Auto-mount DUTs (-m)", 
            variable=self.mount_var,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.mount_checkbox.grid(row=0, column=2, padx=15, pady=16)

        self.verbose_var = ctk.BooleanVar(value=False)
        self.verbose_checkbox = ctk.CTkCheckBox(
            control_card, 
            text="Verbose Debug (-v)", 
            variable=self.verbose_var,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.verbose_checkbox.grid(row=0, column=3, padx=15, pady=16)

        # Run Button
        btn_frame = ctk.CTkFrame(control_card, fg_color="transparent")
        btn_frame.grid(row=0, column=4, padx=(15, 18), pady=16, sticky="e")

        self.btn_run = ctk.CTkButton(
            btn_frame,
            text="▶  START BENCHMARK",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            corner_radius=8,
            command=self.start_benchmark_run
        )
        self.btn_run.pack(side="left", padx=5)

        # Live Progress & Step Indicator Frame
        progress_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray90", "#1e293b"))
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 16), padx=2)
        progress_frame.grid_columnconfigure(0, weight=1)

        prog_header = ctk.CTkFrame(progress_frame, fg_color="transparent")
        prog_header.pack(fill="x", padx=18, pady=(12, 6))

        self.progress_status_label = ctk.CTkLabel(
            prog_header, 
            text="Waiting to launch benchmark...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("gray30", "#cbd5e1")
        )
        self.progress_status_label.pack(side="left")

        self.progress_pct_label = ctk.CTkLabel(
            prog_header, 
            text="0%", 
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("gray30", "#38bdf8")
        )
        self.progress_pct_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(progress_frame, corner_radius=6, height=10)
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 14))
        self.progress_bar.set(0.0)

        # Terminal & Log Console Card
        console_card = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray90", "#1e293b"))
        console_card.grid(row=4, column=0, sticky="nsew", padx=2)
        console_card.grid_columnconfigure(0, weight=1)
        console_card.grid_rowconfigure(1, weight=1)

        console_toolbar = ctk.CTkFrame(console_card, fg_color="transparent")
        console_toolbar.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 8))

        console_title = ctk.CTkLabel(
            console_toolbar,
            text="💻 Orchestrator Live Console",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("gray20", "#e2e8f0")
        )
        console_title.pack(side="left")

        btn_copy_logs = ctk.CTkButton(
            console_toolbar,
            text="📋 Copy Logs",
            width=90,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self.copy_console_logs
        )
        btn_copy_logs.pack(side="right", padx=5)

        btn_clear_console = ctk.CTkButton(
            console_toolbar,
            text="🧹 Clear",
            width=70,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self.clear_console
        )
        btn_clear_console.pack(side="right", padx=5)

        self.console_textbox = ctk.CTkTextbox(
            console_card,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("white", "#0b1120"),
            text_color=("black", "#e2e8f0"),
            corner_radius=8
        )
        self.console_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.console_textbox.configure(state="disabled")

    def _create_kpi_card(self, parent, col, title, initial_value, value_color=None):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card.grid(row=0, column=col, padx=5, sticky="ew")
        
        lbl_title = ctk.CTkLabel(
            card, 
            text=title, 
            font=ctk.CTkFont(family="Segoe UI", size=11), 
            text_color=("gray40", "#94a3b8")
        )
        lbl_title.pack(anchor="w", padx=14, pady=(10, 2))

        lbl_val = ctk.CTkLabel(
            card,
            text=initial_value,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=value_color if value_color else ("gray10", "#f8fafc")
        )
        lbl_val.pack(anchor="w", padx=14, pady=(0, 10))
        return lbl_val

    def update_suite_options(self, suite_names: list):
        values = ["All Tests"] + suite_names
        self.suite_option_menu.configure(values=values)
        if self.suite_option_var.get() not in values:
            self.suite_option_var.set("All Tests")
        self.kpi_card_suite.configure(text=self.suite_option_var.get())

    def start_benchmark_run(self):
        if self.is_running:
            return

        test_choice = self.suite_option_var.get()
        target_test = None if test_choice == "All Tests" else test_choice

        all_tests = self.app.get_configured_tests()
        if target_test:
            self.total_tests_to_run = 1
        else:
            self.total_tests_to_run = max(len(all_tests), 1)

        self.completed_tests = 0
        self.start_time = time.time()
        self.is_running = True

        self.btn_run.configure(state="disabled", fg_color="gray")
        self.kpi_card_status.configure(text="Running", text_color="#38bdf8")
        self.app.set_sidebar_status("Benchmark Running", "#38bdf8")
        self.progress_bar.set(0.0)
        self.progress_pct_label.configure(text="0%")
        self.progress_status_label.configure(text=f"Launching benchmark suite '{test_choice}'...")

        self.benchmark_thread = threading.Thread(
            target=self._benchmark_worker,
            args=(target_test, self.mount_var.get(), self.verbose_var.get()),
            daemon=True
        )
        self.benchmark_thread.start()

    def _benchmark_worker(self, target_test: str, auto_mount: bool, verbose: bool):
        class BenchmarkArgs:
            config = str(CONFIG_JSON_PATH)
            dut_settings = str(DUT_INI_PATH)
            mount = auto_mount
            test = target_test
            verbose = verbose

        args = BenchmarkArgs()
        dut_settings._DEFAULT_INI_PATH = Path(args.dut_settings)

        try:
            logging.info("Initializing BenchmarkController...")
            controller = BenchmarkController(args)
            controller.start_benchmark()
            logging.info("BenchmarkController completed all test suites successfully.")
            self.app.log_queue.put((logging.INFO, "BENCHMARK_STATUS:COMPLETE_SUCCESS"))
        except Exception as exc:
            logging.exception(f"Benchmark execution error: {exc}")
            self.app.log_queue.put((logging.ERROR, f"BENCHMARK_STATUS:COMPLETE_FAILED:{exc}"))
        finally:
            self.after(0, self._on_benchmark_completed)

    def _on_benchmark_completed(self):
        self.is_running = False
        self.btn_run.configure(state="normal", fg_color="#10b981")
        self.kpi_card_status.configure(text="Finished", text_color="#10b981")
        self.app.set_sidebar_status("System Idle", "#10b981")
        self.progress_bar.set(1.0)
        self.progress_pct_label.configure(text="100%")
        self.progress_status_label.configure(text="Benchmark completed.")
        self.kpi_card_eta.configure(text="00:00")
        self.app.on_benchmark_finished()

    def handle_log_message(self, msg: str):
        self.append_console_log(msg)

        if "=== Finished Test:" in msg:
            self.completed_tests += 1
            pct = min(self.completed_tests / max(self.total_tests_to_run, 1), 1.0)
            self.progress_bar.set(pct)
            self.progress_pct_label.configure(text=f"{int(pct * 100)}%")
            self.progress_status_label.configure(text=f"Completed {self.completed_tests} of {self.total_tests_to_run} test suite(s)...")

        elif "=== Starting Test:" in msg:
            suite_name = msg.split("'")[1] if "'" in msg else "Suite"
            self.progress_status_label.configure(text=f"Running {suite_name} ({self.completed_tests+1}/{self.total_tests_to_run})...")

    def update_live_timer(self):
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            self.kpi_card_elapsed.configure(text=f"{h:02d}:{m:02d}:{s:02d}")

            if self.completed_tests > 0 and self.total_tests_to_run > self.completed_tests:
                avg_time_per_test = elapsed / self.completed_tests
                remaining_tests = self.total_tests_to_run - self.completed_tests
                eta_secs = int(avg_time_per_test * remaining_tests)
                em, es = divmod(eta_secs, 60)
                eh, em = divmod(em, 60)
                self.kpi_card_eta.configure(text=f"{eh:02d}:{em:02d}:{es:02d}" if eh > 0 else f"{em:02d}:{es:02d}")
            elif self.total_tests_to_run <= self.completed_tests:
                self.kpi_card_eta.configure(text="00:00")
            else:
                self.kpi_card_eta.configure(text="Calculating...")
        elif not self.is_running:
            self.kpi_card_eta.configure(text="--:--")

        self.after(1000, self.update_live_timer)

    def append_console_log(self, msg: str):
        self.console_textbox.configure(state="normal")
        self.console_textbox.insert("end", msg + "\n")
        self.console_textbox.see("end")
        self.console_textbox.configure(state="disabled")

    def clear_console(self):
        self.console_textbox.configure(state="normal")
        self.console_textbox.delete("1.0", "end")
        self.console_textbox.configure(state="disabled")

    def copy_console_logs(self):
        content = self.console_textbox.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)
