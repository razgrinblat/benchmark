import queue
import logging
import customtkinter as ctk

from gui.logger_handler import GUILogHandler
from gui.views.execution_view import ExecutionView
from gui.views.config_view import ConfigView
from gui.views.history_view import HistoryView

# Configure theme and appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """
    Main Application Window coordinating sidebar navigation, views, and live log polling.
    """

    def __init__(self):
        super().__init__()

        self.title("SmartChannel Benchmark Studio")
        self.geometry("1200x820")
        self.minsize(1050, 700)

        # Layout grid: sidebar (col 0) and content container (col 1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Thread-safe logging queue and handler
        self.log_queue = queue.Queue()
        self.gui_log_handler = GUILogHandler(self.log_queue)
        self.gui_log_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)-7s] %(message)s', datefmt='%H:%M:%S'))
        root_logger = logging.getLogger()
        root_logger.addHandler(self.gui_log_handler)
        root_logger.setLevel(logging.INFO)

        # Build Sidebar
        self._build_sidebar()

        # Content container
        self.content_container = ctk.CTkFrame(self, fg_color=("gray95", "#0f172a"), corner_radius=0)
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        # Instantiate Views
        self.execution_view = ExecutionView(self.content_container, app_controller=self)
        self.config_view = ConfigView(self.content_container, app_controller=self)
        self.history_view = HistoryView(self.content_container, app_controller=self)

        self.views = {
            "execution": self.execution_view,
            "config": self.config_view,
            "history": self.history_view,
        }

        # Show initial tab
        self.show_tab("execution")

        # Start periodic log polling
        self.poll_log_queue()

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray90", "#1e293b"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # Brand header
        brand_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=20, pady=(25, 20), sticky="ew")

        logo_title = ctk.CTkLabel(
            brand_frame,
            text="⚡ SmartChannel",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=("gray10", "#38bdf8")
        )
        logo_title.pack(anchor="w")

        sub_title = ctk.CTkLabel(
            brand_frame,
            text="BENCHMARK STUDIO",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=("gray50", "#94a3b8")
        )
        sub_title.pack(anchor="w")

        # Navigation items
        self.nav_buttons = {}
        nav_items = [
            ("execution", "🚀  Live Execution"),
            ("config", "⚙️  Configuration"),
            ("history", "📊  History & Results"),
        ]

        for idx, (tab_key, tab_label) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=tab_label,
                anchor="w",
                height=42,
                corner_radius=8,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color="transparent",
                text_color=("gray20", "#cbd5e1"),
                hover_color=("gray80", "#334155"),
                command=lambda k=tab_key: self.show_tab(k)
            )
            btn.grid(row=idx, column=0, padx=14, pady=6, sticky="ew")
            self.nav_buttons[tab_key] = btn

        # Status Pill in Sidebar
        self.status_pill_frame = ctk.CTkFrame(self.sidebar_frame, corner_radius=8, fg_color=("gray80", "#0f172a"))
        self.status_pill_frame.grid(row=6, column=0, padx=14, pady=(10, 15), sticky="ew")
        
        self.status_pill_dot = ctk.CTkLabel(
            self.status_pill_frame, 
            text="●", 
            font=ctk.CTkFont(size=14), 
            text_color="#10b981"
        )
        self.status_pill_dot.pack(side="left", padx=(12, 6), pady=8)

        self.status_pill_text = ctk.CTkLabel(
            self.status_pill_frame,
            text="System Idle",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("gray30", "#e2e8f0")
        )
        self.status_pill_text.pack(side="left", pady=8)

        # Appearance mode menu
        appearance_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Theme Mode:", 
            font=ctk.CTkFont(family="Segoe UI", size=11), 
            text_color=("gray40", "#94a3b8")
        )
        appearance_label.grid(row=7, column=0, padx=14, pady=(0, 4), sticky="w")

        self.appearance_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Dark", "Light", "System"],
            command=self.change_appearance_mode,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.appearance_menu.grid(row=8, column=0, padx=14, pady=(0, 20), sticky="ew")

    def show_tab(self, tab_key):
        for k, view in self.views.items():
            view.grid_forget()

        for k, btn in self.nav_buttons.items():
            if k == tab_key:
                btn.configure(fg_color=("#2563eb", "#1d4ed8"), text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color=("gray20", "#cbd5e1"))

        target_view = self.views.get(tab_key)
        if target_view:
            target_view.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)

        if tab_key == "history":
            self.history_view.load_history_runs()

    def change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode)

    def set_sidebar_status(self, text: str, color: str):
        self.status_pill_text.configure(text=text)
        self.status_pill_dot.configure(text_color=color)

    def get_configured_tests(self) -> list:
        return self.config_view.config_data.get("tests", [])

    def on_configs_updated(self, config_data: dict):
        tests = config_data.get("tests", [])
        suite_names = [t.get("name") for t in tests if t.get("name")]
        self.execution_view.update_suite_options(suite_names)

    def on_benchmark_finished(self):
        self.history_view.load_history_runs()

    def poll_log_queue(self):
        while not self.log_queue.empty():
            try:
                levelno, msg = self.log_queue.get_nowait()
                self.execution_view.handle_log_message(msg)
            except queue.Empty:
                break

        self.after(100, self.poll_log_queue)
