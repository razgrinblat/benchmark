from typing import Dict, Any
import customtkinter as ctk


class SessionMetricsDialog(ctk.CTkToplevel):
    """
    High-visibility modal dialog presenting detailed performance metrics
    for a chosen benchmark session in large typography.
    """

    def __init__(self, parent, session_data: Dict[str, Any], **kwargs):
        super().__init__(parent, **kwargs)
        self.session_data = session_data

        s_name = session_data.get("session_name", "Session")
        self.title(f"Performance Telemetry - {s_name}")
        self.geometry("820x640")
        self.minsize(740, 560)
        self.transient(parent)

        try:
            self.grab_set()
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self, corner_radius=12, fg_color=("gray95", "#0f172a"))
        container.pack(fill="both", expand=True, padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)

        # Header Banner
        header = ctk.CTkFrame(container, corner_radius=10, fg_color=("gray90", "#1e293b"))
        header.pack(fill="x", pady=(0, 14))

        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="x", padx=18, pady=16)

        s_name = self.session_data.get("session_name", "Unknown Session")
        title_lbl = ctk.CTkLabel(
            h_inner,
            text=f"📦 {s_name}",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=("gray10", "#f8fafc")
        )
        title_lbl.pack(side="left")

        status = self.session_data.get("validation_status", "UNKNOWN")
        is_passed = (status == "PASSED")
        stat_color = "#10b981" if is_passed else "#ef4444"
        stat_text = "✅ PASSED" if is_passed else f"❌ {status}"

        status_pill = ctk.CTkLabel(
            h_inner,
            text=stat_text,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff",
            fg_color=stat_color,
            corner_radius=8,
            padx=14,
            pady=6
        )
        status_pill.pack(side="right")

        # KPI Metrics Grid (3 columns x 2 rows) with BIG FONTS
        kpi_grid = ctk.CTkFrame(container, fg_color="transparent")
        kpi_grid.pack(fill="x", pady=(0, 14))
        for c in range(3):
            kpi_grid.grid_columnconfigure(c, weight=1, uniform="metric_col")

        # 1. Throughput
        tp_raw = self.session_data.get("session_throughput_mbps", "0")
        try:
            tp_val = f"{float(tp_raw):.2f} MB/s"
        except Exception:
            tp_val = f"{tp_raw} MB/s"
        self._add_big_kpi_card(kpi_grid, 0, 0, "⚡ THROUGHPUT", tp_val, "#38bdf8", "Data transfer rate")

        # 2. Total Duration
        dur_raw = self.session_data.get("session_duration_seconds", "0")
        try:
            dur_val = f"{float(dur_raw):.2f}s"
        except Exception:
            dur_val = f"{dur_raw}s"
        self._add_big_kpi_card(kpi_grid, 0, 1, "⏱️ TOTAL DURATION", dur_val, "#fbbf24", "Elapsed transfer time")

        # 3. Total Files
        tot_files = self.session_data.get("total_files", "0")
        failed_files = self.session_data.get("failed_files", "0")
        files_sub = f"Failed: {failed_files}" if failed_files != "0" else "0 dropped files"
        self._add_big_kpi_card(kpi_grid, 0, 2, "📁 FILES TRANSFERRED", f"{tot_files}", "#10b981", files_sub)

        # 4. Total Bytes Transferred
        bytes_raw = int(self.session_data.get("total_bytes", 0) or 0)
        if bytes_raw >= 1024 * 1024:
            bytes_val = f"{bytes_raw / (1024 * 1024):.2f} MB"
        elif bytes_raw >= 1024:
            bytes_val = f"{bytes_raw / 1024:.1f} KB"
        else:
            bytes_val = f"{bytes_raw} B"
        self._add_big_kpi_card(kpi_grid, 1, 0, "💾 PAYLOAD SIZE", bytes_val, "#a855f7", f"{bytes_raw:,} bytes")

        # 5. Min File Latency
        min_lat = self.session_data.get("min_file_transfer_time_ms", "0")
        self._add_big_kpi_card(kpi_grid, 1, 1, "🚀 MIN FILE LATENCY", f"{min_lat} ms", "#38bdf8", "Fastest file transfer")

        # 6. Max File Latency
        max_lat = self.session_data.get("max_file_transfer_time_ms", "0")
        self._add_big_kpi_card(kpi_grid, 1, 2, "🐢 MAX FILE LATENCY", f"{max_lat} ms", "#f43f5e", "Slowest file transfer")

        # Error details card if present
        err_msg = self.session_data.get("error_message")
        if err_msg and err_msg.strip():
            err_card = ctk.CTkFrame(container, corner_radius=10, fg_color=("#fee2e2", "#450a0a"), border_width=1, border_color="#ef4444")
            err_card.pack(fill="x", pady=(0, 14))
            
            lbl_err_title = ctk.CTkLabel(err_card, text="⚠️ Failure Details", font=ctk.CTkFont(size=14, weight="bold"), text_color="#ef4444")
            lbl_err_title.pack(anchor="w", padx=16, pady=(12, 4))

            lbl_err_text = ctk.CTkLabel(err_card, text=err_msg, font=ctk.CTkFont(family="Consolas", size=12), text_color=("#991b1b", "#fca5a5"), justify="left", wraplength=720)
            lbl_err_text.pack(anchor="w", padx=16, pady=(0, 14))

        # Additional Raw Parameters Card
        raw_card = ctk.CTkFrame(container, corner_radius=10, fg_color=("gray90", "#1e293b"))
        raw_card.pack(fill="x", pady=(0, 14))

        raw_title = ctk.CTkLabel(
            raw_card,
            text="📋 Complete Session Telemetry",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        )
        raw_title.pack(anchor="w", padx=16, pady=(14, 8))

        raw_table = ctk.CTkFrame(raw_card, fg_color="transparent")
        raw_table.pack(fill="x", padx=16, pady=(0, 14))
        raw_table.grid_columnconfigure((0, 1), weight=1)

        row_idx = 0
        skip_keys = {"session_name", "validation_status", "error_message"}
        for k, v in self.session_data.items():
            if k in skip_keys:
                continue
            k_fmt = k.replace("_", " ").title()
            
            lbl_k = ctk.CTkLabel(raw_table, text=k_fmt, font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray40", "#94a3b8"), anchor="w")
            lbl_k.grid(row=row_idx, column=0, sticky="w", pady=3)

            lbl_v = ctk.CTkLabel(raw_table, text=str(v), font=ctk.CTkFont(family="Consolas", size=12), text_color=("gray20", "#f8fafc"), anchor="w")
            lbl_v.grid(row=row_idx, column=1, sticky="w", pady=3)

            row_idx += 1

        # Close Button
        btn_close = ctk.CTkButton(
            container,
            text="Close Metrics View",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self.destroy
        )
        btn_close.pack(pady=8)

    def _add_big_kpi_card(self, parent, r, c, title, value_str, val_color, subtitle_str):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

        lbl_t = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("gray40", "#94a3b8")
        )
        lbl_t.pack(anchor="w", padx=16, pady=(14, 2))

        lbl_v = ctk.CTkLabel(
            card,
            text=value_str,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=val_color
        )
        lbl_v.pack(anchor="w", padx=16, pady=(0, 2))

        lbl_sub = ctk.CTkLabel(
            card,
            text=subtitle_str,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray50", "#64748b")
        )
        lbl_sub.pack(anchor="w", padx=16, pady=(0, 14))
