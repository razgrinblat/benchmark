from typing import Callable
import customtkinter as ctk


class ConfirmDeleteDialog(ctk.CTkToplevel):
    """
    Confirmation modal dialog for deleting a benchmark test suite.
    """

    def __init__(self, parent, test_name: str, on_confirm: Callable[[], None], **kwargs):
        super().__init__(parent, **kwargs)
        self.title("Confirm Test Deletion")
        self.geometry("450x220")
        self.resizable(False, False)
        self.transient(parent)

        try:
            self.grab_set()
        except Exception:
            pass

        self._build_ui(test_name, on_confirm)

    def _build_ui(self, test_name: str, on_confirm: Callable[[], None]):
        container = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray95", "#0f172a"))
        container.pack(fill="both", expand=True, padx=16, pady=16)

        icon_lbl = ctk.CTkLabel(
            container,
            text="⚠️ Delete Test Suite",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#ef4444"
        )
        icon_lbl.pack(pady=(16, 8))

        msg = (
            f"Are you sure you want to delete test suite '{test_name}'?\n"
            "This action removes it from the configuration and cannot be undone."
        )
        msg_lbl = ctk.CTkLabel(
            container,
            text=msg,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#cbd5e1"),
            justify="center",
            wraplength=380
        )
        msg_lbl.pack(pady=(0, 20))

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 10))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=("gray80", "#334155"),
            hover_color=("gray70", "#475569"),
            command=self.destroy
        )
        btn_cancel.pack(side="left", expand=True, padx=6)

        def do_delete():
            self.destroy()
            on_confirm()

        btn_delete = ctk.CTkButton(
            btn_row,
            text="🗑️ Delete",
            width=120,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=do_delete
        )
        btn_delete.pack(side="right", expand=True, padx=6)
