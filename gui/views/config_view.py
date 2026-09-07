import json
import logging
import configparser
from pathlib import Path
import customtkinter as ctk

from gui.views.dialogs.confirm_delete_dialog import ConfirmDeleteDialog
from gui.views.dialogs.add_test_wizard_dialog import AddTestWizardDialog

CONFIG_JSON_PATH = Path("config.json")
DUT_INI_PATH = Path("dut_settings.ini")

__all__ = ["ConfigView", "ConfirmDeleteDialog", "AddTestWizardDialog"]


class ConfigView(ctk.CTkFrame):
    """
    Configuration View with form-based visual editing for config.json and dut_settings.ini.
    Provides subtabs for DUT Endpoints, Host & Shares (SMB), Test Suites (with step wizard & deletion),
    and DUT System Paths (INI).
    """

    def __init__(self, parent, app_controller, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.app = app_controller

        self.config_data = {}
        self.ini_data = configparser.ConfigParser()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_ui()
        self.reload_all_configs()

    def _build_ui(self):
        # Header Title & Action Buttons
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        title_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_box.pack(side="left")

        title = ctk.CTkLabel(
            title_box,
            text="⚙️ Benchmark & DUT Configuration",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            title_box,
            text="Form-based visual editor for config.json and dut_settings.ini. Changes persist directly to disk.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=("gray40", "#94a3b8")
        )
        subtitle.pack(anchor="w")

        actions_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions_box.pack(side="right", fill="y")

        self.save_feedback_label = ctk.CTkLabel(
            actions_box,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#10b981"
        )
        self.save_feedback_label.pack(side="left", padx=10)

        btn_reload = ctk.CTkButton(
            actions_box,
            text="🔄 Reload",
            width=90,
            height=34,
            corner_radius=8,
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self.reload_all_configs
        )
        btn_reload.pack(side="left", padx=5)

        btn_save = ctk.CTkButton(
            actions_box,
            text="💾 Save Configurations",
            width=160,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.save_all_configs
        )
        btn_save.pack(side="left", padx=5)

        # Tabview for domains (Cleaned: File Profiles & FEC/Chunks removed as managed in Wizard)
        self.config_tabview = ctk.CTkTabview(self, corner_radius=12)
        self.config_tabview.grid(row=2, column=0, sticky="nsew")

        self.tab_endpoints = self.config_tabview.add("📡 DUT Endpoints")
        self.tab_host = self.config_tabview.add("🖥️ Host & Shares")
        self.tab_tests = self.config_tabview.add("🧪 Test Suites")
        self.tab_dut_ini = self.config_tabview.add("⚙️ DUT System Paths (INI)")

        self._build_form_endpoints()
        self._build_form_host()
        self._build_form_test_suites()
        self._build_form_dut_ini()

    def _build_form_endpoints(self):
        tab = self.tab_endpoints
        tab.grid_columnconfigure((0, 1), weight=1)

        card_tx = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card_tx.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        
        lbl_tx = ctk.CTkLabel(card_tx, text="📡 Transmitter (Tx) DUT", font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8")
        lbl_tx.pack(anchor="w", padx=16, pady=(16, 12))

        self.tx_ip_entry = self._add_form_entry(card_tx, "IP Address:")
        self.tx_user_entry = self._add_form_entry(card_tx, "SSH Username:")
        self.tx_pass_entry = self._add_form_entry(card_tx, "SSH Password:", show="*")

        card_rx = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card_rx.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")
        
        lbl_rx = ctk.CTkLabel(card_rx, text="📡 Receiver (Rx) DUT", font=ctk.CTkFont(size=15, weight="bold"), text_color="#a855f7")
        lbl_rx.pack(anchor="w", padx=16, pady=(16, 12))

        self.rx_ip_entry = self._add_form_entry(card_rx, "IP Address:")
        self.rx_user_entry = self._add_form_entry(card_rx, "SSH Username:")
        self.rx_pass_entry = self._add_form_entry(card_rx, "SSH Password:", show="*")

    def _build_form_host(self):
        tab = self.tab_host
        tab.grid_columnconfigure((0, 1), weight=1)

        card_host = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card_host.grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="nsew")

        lbl_host = ctk.CTkLabel(card_host, text="🖥️ Benchmark Controller Host Settings", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8")
        lbl_host.pack(anchor="w", padx=16, pady=(14, 8))

        host_grid = ctk.CTkFrame(card_host, fg_color="transparent")
        host_grid.pack(fill="x", padx=16, pady=(0, 12))
        host_grid.grid_columnconfigure((0, 1), weight=1)

        self.host_ip_entry = self._add_grid_entry(host_grid, 0, 0, "Host IP Address:")
        self.host_user_entry = self._add_grid_entry(host_grid, 0, 1, "Host Username:")
        self.host_pass_entry = self._add_grid_entry(host_grid, 1, 0, "Host Password:", show="*")
        self.host_results_entry = self._add_grid_entry(host_grid, 1, 1, "Results Base Path:")

        # Tx File Share (SMB fixed, no protocol selector)
        card_tx_share = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card_tx_share.grid(row=1, column=0, padx=12, pady=6, sticky="nsew")

        h_tx = ctk.CTkFrame(card_tx_share, fg_color="transparent")
        h_tx.pack(fill="x", padx=16, pady=(14, 8))

        lbl_tx_s = ctk.CTkLabel(h_tx, text="📁 Tx File Share", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8")
        lbl_tx_s.pack(side="left")

        proto_badge_tx = ctk.CTkLabel(
            h_tx, 
            text="SMB", 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#2563eb", "#1d4ed8"),
            text_color="#ffffff",
            corner_radius=6,
            padx=8,
            pady=2
        )
        proto_badge_tx.pack(side="right")

        self.tx_share_name = self._add_form_entry(card_tx_share, "Share Name:")
        self.tx_share_path = self._add_form_entry(card_tx_share, "Local Storage Path:")

        # Rx File Share (SMB fixed, no protocol selector)
        card_rx_share = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card_rx_share.grid(row=1, column=1, padx=12, pady=6, sticky="nsew")

        h_rx = ctk.CTkFrame(card_rx_share, fg_color="transparent")
        h_rx.pack(fill="x", padx=16, pady=(14, 8))

        lbl_rx_s = ctk.CTkLabel(h_rx, text="📁 Rx File Share", font=ctk.CTkFont(size=14, weight="bold"), text_color="#a855f7")
        lbl_rx_s.pack(side="left")

        proto_badge_rx = ctk.CTkLabel(
            h_rx, 
            text="SMB", 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#2563eb", "#1d4ed8"),
            text_color="#ffffff",
            corner_radius=6,
            padx=8,
            pady=2
        )
        proto_badge_rx.pack(side="right")

        self.rx_share_name = self._add_form_entry(card_rx_share, "Share Name:")
        self.rx_share_path = self._add_form_entry(card_rx_share, "Local Storage Path:")

    def _build_form_test_suites(self):
        tab = self.tab_tests
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Top Action Bar
        action_bar = ctk.CTkFrame(tab, fg_color="transparent")
        action_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        title_lbl = ctk.CTkLabel(
            action_bar,
            text="🧪 Configured Benchmark Test Suites",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        title_lbl.pack(side="left")

        btn_add_wizard = ctk.CTkButton(
            action_bar,
            text="➕ Add Test Suite (Step Wizard)",
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self._launch_add_test_wizard
        )
        btn_add_wizard.pack(side="right")

        self.tests_scroll_frame = ctk.CTkScrollableFrame(tab, corner_radius=10, fg_color="transparent")
        self.tests_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self.tests_scroll_frame.grid_columnconfigure(0, weight=1)

    def _build_form_dut_ini(self):
        tab = self.tab_dut_ini
        tab.grid_columnconfigure((0, 1), weight=1)

        card_paths = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card_paths.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        lbl_p = ctk.CTkLabel(card_paths, text="📁 Remote System Paths", font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8")
        lbl_p.pack(anchor="w", padx=16, pady=(16, 12))

        self.ini_service_name = self._add_form_entry(card_paths, "Systemd Service Name:")
        self.ini_tx_mount = self._add_form_entry(card_paths, "Tx Mount Point:")
        self.ini_rx_mount = self._add_form_entry(card_paths, "Rx Mount Point:")
        self.ini_session_config = self._add_form_entry(card_paths, "Session Config Directory:")

        card_logs = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray90", "#1e293b"))
        card_logs.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

        lbl_l = ctk.CTkLabel(card_logs, text="📜 Journalctl Log Matching Patterns", font=ctk.CTkFont(size=15, weight="bold"), text_color="#a855f7")
        lbl_l.pack(anchor="w", padx=16, pady=(16, 12))

        self.ini_success_fmt = self._add_form_entry(card_logs, "Success Log Format:")
        self.ini_failure_fmt = self._add_form_entry(card_logs, "Failure Log Format:")

    def _add_form_entry(self, parent, label_text, show=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=6)
        
        lbl = ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=12), text_color=("gray30", "#94a3b8"))
        lbl.pack(anchor="w")

        entry = ctk.CTkEntry(frame, corner_radius=6, height=32, show=show)
        entry.pack(fill="x", pady=(2, 0))
        return entry

    def _add_grid_entry(self, parent, r, c, label_text, show=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=r, column=c, padx=8, pady=6, sticky="ew")

        lbl = ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=12), text_color=("gray30", "#94a3b8"))
        lbl.pack(anchor="w")

        entry = ctk.CTkEntry(frame, corner_radius=6, height=32, show=show)
        entry.pack(fill="x", pady=(2, 0))
        return entry

    def reload_all_configs(self):
        if CONFIG_JSON_PATH.exists():
            try:
                with open(CONFIG_JSON_PATH, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception as e:
                logging.error(f"Error reading {CONFIG_JSON_PATH}: {e}")

        if DUT_INI_PATH.exists():
            try:
                self.ini_data = configparser.ConfigParser()
                self.ini_data.read(DUT_INI_PATH, encoding="utf-8")
            except Exception as e:
                logging.error(f"Error reading {DUT_INI_PATH}: {e}")

        self._populate_forms()
        self.app.on_configs_updated(self.config_data)

    def _populate_forms(self):
        ep = self.config_data.get("endpoint_setting", {})
        tx = ep.get("tx", {})
        rx = ep.get("rx", {})

        self._set_entry_val(self.tx_ip_entry, tx.get("ip", ""))
        self._set_entry_val(self.tx_user_entry, tx.get("username", ""))
        self._set_entry_val(self.tx_pass_entry, tx.get("password", ""))

        self._set_entry_val(self.rx_ip_entry, rx.get("ip", ""))
        self._set_entry_val(self.rx_user_entry, rx.get("username", ""))
        self._set_entry_val(self.rx_pass_entry, rx.get("password", ""))

        hs = self.config_data.get("host_settings", {})
        self._set_entry_val(self.host_ip_entry, hs.get("ip", ""))
        self._set_entry_val(self.host_user_entry, hs.get("username", ""))
        self._set_entry_val(self.host_pass_entry, hs.get("password", ""))
        self._set_entry_val(self.host_results_entry, hs.get("results_path", "."))

        tx_s = hs.get("tx", {})
        self._set_entry_val(self.tx_share_name, tx_s.get("share_name", ""))
        self._set_entry_val(self.tx_share_path, tx_s.get("path", ""))

        rx_s = hs.get("rx", {})
        self._set_entry_val(self.rx_share_name, rx_s.get("share_name", ""))
        self._set_entry_val(self.rx_share_path, rx_s.get("path", ""))

        self._render_test_suites(self.config_data.get("tests", []))

        if self.ini_data.has_section("paths"):
            self._set_entry_val(self.ini_service_name, self.ini_data.get("paths", "service_name", fallback=""))
            self._set_entry_val(self.ini_tx_mount, self.ini_data.get("paths", "tx_mount_point", fallback=""))
            self._set_entry_val(self.ini_rx_mount, self.ini_data.get("paths", "rx_mount_point", fallback=""))
            self._set_entry_val(self.ini_session_config, self.ini_data.get("paths", "session_config_path", fallback=""))

        if self.ini_data.has_section("log_formats"):
            self._set_entry_val(self.ini_success_fmt, self.ini_data.get("log_formats", "success_log_format", fallback=""))
            self._set_entry_val(self.ini_failure_fmt, self.ini_data.get("log_formats", "failure_log_format", fallback=""))

    def _set_entry_val(self, entry: ctk.CTkEntry, val: str):
        entry.delete(0, "end")
        entry.insert(0, str(val))

    def _resolve_session_details(self, s_name: str) -> dict:
        """
        Resolves session parameters from session_definitions or legacy 4-part string.
        """
        session_defs = self.config_data.get("session_definitions", {})
        if s_name in session_defs:
            s_data = session_defs[s_name]
            f_set = s_data.get("file_setting", {})
            cnt = s_data.get("file_count", f_set.get("file_count", 1))
            sz = s_data.get("file_size", f_set.get("file_size", 1))
            sc = s_data.get("file_scale", f_set.get("file_scale", "MB"))
            return {
                "name": s_name,
                "mode": s_data.get("mode", "sequential"),
                "file_count": cnt,
                "file_size": sz,
                "file_scale": sc,
                "fec_value": s_data.get("fec_value", 0),
                "chunk_value": s_data.get("chunk_value", 65000)
            }

        # Check legacy format: fec_key-files_key-chunk_key-mode
        parts = s_name.split("-")
        if len(parts) == 4:
            fec_k, files_k, chunk_k, mode = parts
            fs = self.config_data.get("file_settings", {}).get(files_k, {})
            fec_val = self.config_data.get("fec_settings", {}).get(fec_k, 0)
            chunk_val = self.config_data.get("chunkSize_setting", {}).get(chunk_k, 65000)
            clean_mode = "parallel" if "parallel" in mode.lower() else "sequential"
            return {
                "name": s_name,
                "mode": clean_mode,
                "file_count": fs.get("file_count", 1),
                "file_size": fs.get("file_size", 1),
                "file_scale": fs.get("file_scale", "KB"),
                "fec_value": fec_val,
                "chunk_value": chunk_val
            }

        return {
            "name": s_name,
            "mode": "sequential",
            "file_count": 1,
            "file_size": 1,
            "file_scale": "KB",
            "fec_value": 0,
            "chunk_value": 65000
        }

    def _render_test_suites(self, tests: list):
        for widget in self.tests_scroll_frame.winfo_children():
            widget.destroy()

        if not tests:
            empty_lbl = ctk.CTkLabel(
                self.tests_scroll_frame,
                text="No test suites configured. Click '➕ Add Test Suite (Step Wizard)' above to create one!",
                font=ctk.CTkFont(size=13),
                text_color=("gray40", "#94a3b8")
            )
            empty_lbl.pack(pady=30)
            return

        for idx, t in enumerate(tests):
            t_name = t.get("name", f"test-{idx+1}")
            sessions = t.get("sessions", [])

            card = ctk.CTkFrame(self.tests_scroll_frame, corner_radius=10, fg_color=("gray90", "#1e293b"))
            card.pack(fill="x", padx=12, pady=6)

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=14, pady=(12, 6))

            lbl_suite = ctk.CTkLabel(
                header,
                text=f"🧪 Suite: {t_name}",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="#38bdf8"
            )
            lbl_suite.pack(side="left")

            badge_sessions = ctk.CTkLabel(
                header,
                text=f"{len(sessions)} Session(s)",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray40", "#cbd5e1"),
                fg_color=("gray80", "#334155"),
                corner_radius=6,
                padx=8,
                pady=2
            )
            badge_sessions.pack(side="left", padx=10)

            # Option to delete this chosen test suite
            btn_delete = ctk.CTkButton(
                header,
                text="🗑️ Delete Test",
                width=100,
                height=28,
                corner_radius=6,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#ef4444",
                hover_color="#dc2626",
                command=lambda name=t_name: self._prompt_delete_test(name)
            )
            btn_delete.pack(side="right")

            # Session items container
            sess_container = ctk.CTkFrame(card, fg_color="transparent")
            sess_container.pack(fill="x", padx=14, pady=(0, 12))

            for s_idx, s_str in enumerate(sessions):
                info = self._resolve_session_details(s_str)
                s_card = ctk.CTkFrame(sess_container, corner_radius=6, fg_color=("gray85", "#0f172a"))
                s_card.pack(fill="x", pady=3)

                r1 = ctk.CTkFrame(s_card, fg_color="transparent")
                r1.pack(fill="x", padx=10, pady=(6, 2))

                s_lbl = ctk.CTkLabel(
                    r1,
                    text=f"📦 {info['name']}",
                    font=ctk.CTkFont(family="Consolas", size=12, weight="bold")
                )
                s_lbl.pack(side="left")

                mode_color = "#38bdf8" if info["mode"] == "parallel" else "#fbbf24"
                mode_badge = ctk.CTkLabel(
                    r1,
                    text=f"⚡ {info['mode'].upper()}",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=mode_color
                )
                mode_badge.pack(side="right")

                r2 = ctk.CTkFrame(s_card, fg_color="transparent")
                r2.pack(fill="x", padx=10, pady=(0, 6))

                details_text = (
                    f"📁 Payload: {info['file_count']} × {info['file_size']}{info['file_scale']}  |  "
                    f"🛡️ FEC: {info['fec_value']}%  |  "
                    f"📦 Chunk: {info['chunk_value']:,} B"
                )
                det_lbl = ctk.CTkLabel(
                    r2,
                    text=details_text,
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=("gray40", "#94a3b8")
                )
                det_lbl.pack(anchor="w")

    def _launch_add_test_wizard(self):
        """
        Opens the multi-step test creation wizard.
        """
        AddTestWizardDialog(
            parent=self.winfo_toplevel(),
            config_data=self.config_data,
            on_success=self._on_wizard_test_created
        )

    def _on_wizard_test_created(self, new_test: dict, session_defs: dict):
        tests = self.config_data.setdefault("tests", [])
        tests.append(new_test)

        all_session_defs = self.config_data.setdefault("session_definitions", {})
        all_session_defs.update(session_defs)

        self._render_test_suites(tests)
        self.save_all_configs()
        logging.info(f"Created new test suite '{new_test['name']}' with {len(new_test['sessions'])} sessions.")

    def _prompt_delete_test(self, test_name: str):
        """
        Shows confirmation dialog before deleting a chosen test suite.
        """
        ConfirmDeleteDialog(
            parent=self.winfo_toplevel(),
            test_name=test_name,
            on_confirm=lambda: self._execute_delete_test(test_name)
        )

    def _execute_delete_test(self, test_name: str):
        tests = self.config_data.get("tests", [])
        updated_tests = [t for t in tests if t.get("name") != test_name]
        self.config_data["tests"] = updated_tests

        self._render_test_suites(updated_tests)
        self.save_all_configs()
        logging.info(f"Deleted test suite '{test_name}'.")

    def save_all_configs(self):
        try:
            ep = self.config_data.setdefault("endpoint_setting", {})
            ep["tx"] = {
                "ip": self.tx_ip_entry.get().strip(),
                "username": self.tx_user_entry.get().strip(),
                "password": self.tx_pass_entry.get().strip(),
            }
            ep["rx"] = {
                "ip": self.rx_ip_entry.get().strip(),
                "username": self.rx_user_entry.get().strip(),
                "password": self.rx_pass_entry.get().strip(),
            }

            hs = self.config_data.setdefault("host_settings", {})
            hs["ip"] = self.host_ip_entry.get().strip()
            hs["username"] = self.host_user_entry.get().strip()
            hs["password"] = self.host_pass_entry.get().strip()
            hs["results_path"] = self.host_results_entry.get().strip()
            hs["tx"] = {
                "protocol": "smb",  # Locked to smb
                "share_name": self.tx_share_name.get().strip(),
                "path": self.tx_share_path.get().strip(),
            }
            hs["rx"] = {
                "protocol": "smb",  # Locked to smb
                "share_name": self.rx_share_name.get().strip(),
                "path": self.rx_share_path.get().strip(),
            }

            with open(CONFIG_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2)

            if not self.ini_data.has_section("paths"):
                self.ini_data.add_section("paths")
            self.ini_data.set("paths", "service_name", self.ini_service_name.get().strip())
            self.ini_data.set("paths", "tx_mount_point", self.ini_tx_mount.get().strip())
            self.ini_data.set("paths", "rx_mount_point", self.ini_rx_mount.get().strip())
            self.ini_data.set("paths", "session_config_path", self.ini_session_config.get().strip())

            if not self.ini_data.has_section("log_formats"):
                self.ini_data.add_section("log_formats")
            self.ini_data.set("log_formats", "success_log_format", self.ini_success_fmt.get().strip())
            self.ini_data.set("log_formats", "failure_log_format", self.ini_failure_fmt.get().strip())

            with open(DUT_INI_PATH, "w", encoding="utf-8") as f:
                self.ini_data.write(f)

            self.app.on_configs_updated(self.config_data)
            self.save_feedback_label.configure(text="✅ Saved successfully!", text_color="#10b981")
            self.after(3000, lambda: self.save_feedback_label.configure(text=""))
            logging.info("Configuration saved successfully to config.json and dut_settings.ini")
        except Exception as exc:
            self.save_feedback_label.configure(text=f"❌ Save error: {exc}", text_color="#ef4444")
            logging.error(f"Failed to save configuration: {exc}")
