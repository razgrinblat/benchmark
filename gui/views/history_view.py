import os
import csv
import logging
from pathlib import Path
import customtkinter as ctk

from gui.views.dialogs.session_metrics_dialog import SessionMetricsDialog

TESTS_DIR = Path("Tests")


class HistoryView(ctk.CTkFrame):
    """
    History View displaying historical benchmark runs, session metrics, and logs.
    """

    def __init__(self, parent, app_controller, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app_controller

        self.loaded_runs_data = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()
        self.load_history_runs()

    def _build_ui(self):
        # Header bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        title = ctk.CTkLabel(
            header,
            text="📊 Benchmark Run History & Performance",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        )
        title.pack(side="left")

        btn_refresh = ctk.CTkButton(
            header,
            text="🔄 Refresh Runs",
            width=120,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self.load_history_runs
        )
        btn_refresh.pack(side="right")

        # Two-column layout: Left (Runs List), Right (Run Details)
        self.history_runs_list = ctk.CTkScrollableFrame(
            self, 
            width=280, 
            corner_radius=12, 
            fg_color=("gray90", "#1e293b")
        )
        self.history_runs_list.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        self.history_runs_list.grid_columnconfigure(0, weight=1)

        self.history_detail_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=12,
            fg_color=("gray90", "#1e293b")
        )
        self.history_detail_frame.grid(row=1, column=1, sticky="nsew")
        self.history_detail_frame.grid_columnconfigure(0, weight=1)

    def load_history_runs(self):
        for w in self.history_runs_list.winfo_children():
            w.destroy()

        for w in self.history_detail_frame.winfo_children():
            w.destroy()

        if not TESTS_DIR.exists():
            lbl = ctk.CTkLabel(self.history_runs_list, text="No 'Tests' directory found.", font=ctk.CTkFont(size=12))
            lbl.pack(pady=20)
            return

        run_dirs = sorted([d for d in TESTS_DIR.iterdir() if d.is_dir()], key=os.path.getmtime, reverse=True)
        if not run_dirs:
            lbl = ctk.CTkLabel(self.history_runs_list, text="No historical benchmark runs found.", font=ctk.CTkFont(size=12))
            lbl.pack(pady=20)
            return

        self.loaded_runs_data = []

        for r_dir in run_dirs:
            run_data = self._parse_run_directory(r_dir)
            self.loaded_runs_data.append(run_data)

            card = ctk.CTkFrame(self.history_runs_list, corner_radius=8, fg_color=("gray85", "#0f172a"))
            card.pack(fill="x", pady=4, padx=2)

            is_pass = run_data["all_passed"]
            badge_color = "#10b981" if is_pass else "#ef4444"
            badge_text = "PASSED" if is_pass else "FAILED"

            header_row = ctk.CTkFrame(card, fg_color="transparent")
            header_row.pack(fill="x", padx=10, pady=(8, 2))

            date_lbl = ctk.CTkLabel(header_row, text=f"🕒 {run_data['timestamp_str']}", font=ctk.CTkFont(size=12, weight="bold"))
            date_lbl.pack(side="left")

            badge = ctk.CTkLabel(header_row, text=badge_text, font=ctk.CTkFont(size=10, weight="bold"), text_color=badge_color)
            badge.pack(side="right")

            info_row = ctk.CTkFrame(card, fg_color="transparent")
            info_row.pack(fill="x", padx=10, pady=(0, 6))

            info_lbl = ctk.CTkLabel(
                info_row,
                text=f"{run_data['total_sessions']} sessions | {run_data['total_duration']:.1f}s",
                font=ctk.CTkFont(size=11),
                text_color=("gray40", "#94a3b8")
            )
            info_lbl.pack(side="left")

            btn_view = ctk.CTkButton(
                card,
                text="View Details",
                height=24,
                corner_radius=6,
                font=ctk.CTkFont(size=10),
                fg_color=("gray75", "#334155"),
                hover_color=("gray65", "#475569"),
                command=lambda r=run_data: self._display_run_details(r)
            )
            btn_view.pack(fill="x", padx=10, pady=(0, 8))

        if self.loaded_runs_data:
            self._display_run_details(self.loaded_runs_data[0])

    def _parse_run_directory(self, r_dir: Path) -> dict:
        results_dir = r_dir / "Results"
        timestamp_str = r_dir.name

        sessions = []
        all_passed = True
        total_duration = 0.0
        total_files = 0
        total_bytes = 0

        if results_dir.exists():
            csv_files = list(results_dir.glob("*/*_summary.csv"))
            for cf in csv_files:
                try:
                    with open(cf, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        raw_headers = next(reader, None)
                        if not raw_headers:
                            continue
                        headers = [h.strip() for h in raw_headers]

                        for row in reader:
                            if not any(row):
                                continue
                            row_dict = {headers[i]: row[i].strip() for i in range(min(len(headers), len(row)))}
                            status = row_dict.get("validation_status", "UNKNOWN")
                            if status != "PASSED":
                                all_passed = False

                            dur = float(row_dict.get("session_duration_seconds", 0) or 0)
                            total_duration += dur
                            total_files += int(row_dict.get("total_files", 0) or 0)
                            total_bytes += int(row_dict.get("total_bytes", 0) or 0)

                            sessions.append(row_dict)
                except Exception as e:
                    logging.warning(f"Failed parsing CSV {cf}: {e}")

        log_files = list(results_dir.glob("benchmark_*.log")) if results_dir.exists() else []
        log_file = log_files[0] if log_files else None

        return {
            "dir": r_dir,
            "results_dir": results_dir,
            "timestamp_str": timestamp_str,
            "all_passed": all_passed if sessions else False,
            "total_sessions": len(sessions),
            "total_duration": total_duration,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "sessions": sessions,
            "log_file": log_file
        }

    def _display_run_details(self, run_data: dict):
        for w in self.history_detail_frame.winfo_children():
            w.destroy()

        header_card = ctk.CTkFrame(self.history_detail_frame, corner_radius=10, fg_color=("gray85", "#0f172a"))
        header_card.pack(fill="x", padx=10, pady=(0, 14))

        h_top = ctk.CTkFrame(header_card, fg_color="transparent")
        h_top.pack(fill="x", padx=16, pady=(14, 6))

        title = ctk.CTkLabel(
            h_top,
            text=f"Benchmark Run: {run_data['timestamp_str']}",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=("gray10", "#f8fafc")
        )
        title.pack(side="left")

        status_text = "✅ ALL SESSIONS PASSED" if run_data["all_passed"] else "❌ ONE OR MORE FAILED"
        status_color = "#10b981" if run_data["all_passed"] else "#ef4444"
        badge = ctk.CTkLabel(
            h_top,
            text=status_text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=status_color
        )
        badge.pack(side="right")

        h_btn_row = ctk.CTkFrame(header_card, fg_color="transparent")
        h_btn_row.pack(fill="x", padx=16, pady=(0, 14))

        btn_open = ctk.CTkButton(
            h_btn_row,
            text="📂 Open Run Directory",
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray75", "#334155"),
            hover_color=("gray65", "#475569"),
            command=lambda: os.startfile(run_data["dir"]) if hasattr(os, 'startfile') else None
        )
        btn_open.pack(side="left", padx=(0, 8))

        if run_data["log_file"] and run_data["log_file"].exists():
            btn_log = ctk.CTkButton(
                h_btn_row,
                text="📜 View Execution Log",
                height=28,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                fg_color=("gray75", "#334155"),
                hover_color=("gray65", "#475569"),
                command=lambda: self._open_log_modal(run_data["log_file"])
            )
            btn_log.pack(side="left")

        kpi_row = ctk.CTkFrame(self.history_detail_frame, fg_color="transparent")
        kpi_row.pack(fill="x", padx=10, pady=(0, 14))
        for c in range(4):
            kpi_row.grid_columnconfigure(c, weight=1, uniform="hist_kpi")

        self._create_kpi_card(kpi_row, 0, "📦 Total Sessions", str(run_data["total_sessions"]))
        self._create_kpi_card(kpi_row, 1, "📁 Files Transferred", f"{run_data['total_files']:,}")
        
        b = run_data["total_bytes"]
        b_str = f"{b / (1024*1024):.2f} MB" if b > 1024*1024 else f"{b / 1024:.1f} KB"
        self._create_kpi_card(kpi_row, 2, "💾 Total Data", b_str)
        self._create_kpi_card(kpi_row, 3, "⏱️ Cumulative Time", f"{run_data['total_duration']:.2f}s")

        sec_title = ctk.CTkLabel(
            self.history_detail_frame,
            text="Detailed Session Results",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=("gray20", "#cbd5e1")
        )
        sec_title.pack(anchor="w", padx=12, pady=(8, 6))

        if not run_data["sessions"]:
            no_s = ctk.CTkLabel(self.history_detail_frame, text="No session CSV summaries found for this run.", font=ctk.CTkFont(size=12))
            no_s.pack(padx=12, pady=10)
            return

        for s in run_data["sessions"]:
            card_s = ctk.CTkFrame(self.history_detail_frame, corner_radius=10, fg_color=("gray85", "#0f172a"))
            card_s.pack(fill="x", padx=10, pady=5)

            s_name = s.get("session_name", "Unknown Session")
            s_stat = s.get("validation_status", "UNKNOWN")
            is_passed = (s_stat == "PASSED")
            stat_color = "#10b981" if is_passed else "#ef4444"

            # Top action bar / button row
            s_top = ctk.CTkFrame(card_s, fg_color="transparent")
            s_top.pack(fill="x", padx=12, pady=(10, 6))

            btn_session = ctk.CTkButton(
                s_top,
                text=f"📦 {s_name}",
                anchor="w",
                height=32,
                corner_radius=6,
                font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                fg_color=("gray75", "#1e293b"),
                hover_color=("gray65", "#334155"),
                command=lambda sess=s: self._open_session_metrics(sess)
            )
            btn_session.pack(side="left", fill="x", expand=True, padx=(0, 10))

            lbl_stat = ctk.CTkLabel(
                s_top,
                text=f"● {s_stat}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=stat_color
            )
            lbl_stat.pack(side="left", padx=(0, 10))

            btn_inspect = ctk.CTkButton(
                s_top,
                text="📊 View Metrics ➔",
                width=140,
                height=32,
                corner_radius=6,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                fg_color=("#2563eb", "#1d4ed8"),
                hover_color=("#1d4ed8", "#1e40af"),
                command=lambda sess=s: self._open_session_metrics(sess)
            )
            btn_inspect.pack(side="right")

            # Metrics Preview Row with enlarged fonts
            s_bot = ctk.CTkFrame(card_s, fg_color="transparent")
            s_bot.pack(fill="x", padx=14, pady=(0, 10))

            tp = s.get("session_throughput_mbps", "0")
            dur = s.get("session_duration_seconds", "0")
            tot_f = s.get("total_files", "0")
            min_l = s.get("min_file_transfer_time_ms", "0")
            max_l = s.get("max_file_transfer_time_ms", "0")

            metrics_summary = (
                f"⚡ Throughput: {tp} MB/s   |   "
                f"⏱️ Duration: {dur}s   |   "
                f"📁 Files: {tot_f}   |   "
                f"🚀 Latency: {min_l}ms - {max_l}ms"
            )
            lbl_metrics = ctk.CTkLabel(
                s_bot, 
                text=metrics_summary, 
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), 
                text_color=("gray30", "#cbd5e1")
            )
            lbl_metrics.pack(anchor="w")

            err = s.get("error_message")
            if err:
                lbl_err = ctk.CTkLabel(s_bot, text=f"⚠️ Error: {err}", font=ctk.CTkFont(size=11), text_color="#ef4444")
                lbl_err.pack(anchor="w", pady=(2, 0))

    def _open_session_metrics(self, session_data: dict):
        """
        Opens a dedicated modal with large-font metrics for the chosen session.
        """
        SessionMetricsDialog(parent=self.winfo_toplevel(), session_data=session_data)

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

    def _open_log_modal(self, log_path: Path):
        modal = ctk.CTkToplevel(self)
        modal.title(f"Log Viewer - {log_path.name}")
        modal.geometry("900x600")
        modal.transient(self)

        txt = ctk.CTkTextbox(modal, wrap="none", font=ctk.CTkFont(family="Consolas", size=11))
        txt.pack(fill="both", expand=True, padx=16, pady=16)

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                txt.insert("1.0", f.read())
        except Exception as e:
            txt.insert("1.0", f"Error reading log file: {e}")
