"""Main GUI window using CustomTkinter."""

import customtkinter as ctk
import threading
import time
import subprocess
from pathlib import Path
from typing import Optional
import tkinter as tk

from ..utils.config import Config
from ..utils.i18n import I18n
from ..core.mount_manager import MountManager
from ..core.restic_wrapper import ResticWrapper
from ..core.rclone_wrapper import RcloneWrapper
from ..core.hostname import get_hostname
from .theme import Theme, get_action_colors, get_text_color


class ToolTip:
    """Simple tooltip implementation for CustomTkinter widgets."""
    
    def __init__(self, widget, text):
        """Initialize tooltip.
        
        Args:
            widget: The widget to attach tooltip to
            text: Tooltip text
        """
        self.widget = widget
        self.text = text
        self.tip_window = None
        
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
    
    def show_tip(self, event=None):
        """Show tooltip."""
        if self.tip_window or not self.text:
            return
        
        x, y, _, _ = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#3c3c3c",
            foreground="white",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 9)
        )
        label.pack(ipadx=1)
    
    def hide_tip(self, event=None):
        """Hide tooltip."""
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class ToastNotification:
    """Toast notification for user feedback."""
    
    def __init__(self, parent):
        """Initialize toast notification.
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        self.toast_window = None
        self.timer = None
    
    def show(self, message: str, duration: int = 3000):
        """Show toast notification.
        
        Args:
            message: Message to display
            duration: Duration in milliseconds (default 3000)
        """
        if self.toast_window:
            self.toast_window.destroy()
            if self.timer:
                self.parent.after_cancel(self.timer)
        
        self.toast_window = tw = tk.Toplevel(self.parent)
        tw.wm_overrideredirect(True)
        
        # Position at bottom center of parent
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - 150
        y = self.parent.winfo_rooty() + self.parent.winfo_height() - 80
        tw.wm_geometry(f"+{x}+{y}")
        
        # Create frame with theme colors
        frame = tk.Frame(
            tw,
            background=Theme.PRIMARY,
            relief=tk.RAISED,
            borderwidth=2
        )
        frame.pack(ipadx=20, ipady=10)
        
        label = tk.Label(
            frame,
            text=message,
            background=Theme.PRIMARY,
            foreground="white",
            font=("Arial", 10, "bold")
        )
        label.pack()
        
        # Auto-hide after duration
        self.timer = self.parent.after(duration, self.hide)
    
    def hide(self):
        """Hide toast notification."""
        if self.toast_window:
            self.toast_window.destroy()
            self.toast_window = None
        if self.timer:
            self.parent.after_cancel(self.timer)
            self.timer = None


class MainWindow(ctk.CTk):
    """Main application window for The Memory Vault GUI."""
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        self.config = Config()
        self.i18n = I18n(self.config.get("ui.language", "auto"))
        self.mount_manager: Optional[MountManager] = None
        self.restic: Optional[ResticWrapper] = None
        self.rclone: Optional[RcloneWrapper] = None
        
        # Auto-sync variables
        self.auto_sync_enabled = False
        self.auto_sync_thread: Optional[threading.Thread] = None
        self.auto_sync_stop_event = threading.Event()
        
        # Sync status tracking
        self.sync_status = {
            "syncing_folders": [],
            "errors": [],
            "last_sync_time": None
        }
        
        # Panic button double-click tracking
        self.panic_click_count = 0
        self.panic_click_timer = None
        
        # Toast notification system
        self.toast = ToastNotification(self)
        
        self._setup_window()
        self._create_widgets()
        # Initialize UI with correct language
        self._refresh_ui_text()
        # Set initial status immediately (no blocking operations)
        self._set_initial_status()
        self._update_config_checklist()
        # Show onboarding for new users
        self._show_onboarding_if_needed()
        # Don't run async status check on startup - only when user interacts
    
    def _update_config_checklist(self):
        """Update the configuration status checklist."""
        sync_configured = self.config.is_sync_configured()
        snapshots_configured = self.config.is_snapshots_configured()
        shield_enabled = self.config.get("security.rm_shield", False)
        auto_sync_enabled = self.config.get("sync.auto_sync", False)
        
        # Update sync check
        if sync_configured:
            self.sync_check_label.configure(text="✓ Sync Configured", text_color=get_text_color('success'))
        else:
            self.sync_check_label.configure(text="☐ Sync Configured", text_color=get_text_color('neutral'))
        
        # Update snapshots check
        if snapshots_configured:
            self.snapshots_check_label.configure(text="✓ Snapshots Configured", text_color=get_text_color('success'))
        else:
            self.snapshots_check_label.configure(text="☐ Snapshots Configured", text_color=get_text_color('neutral'))
        
        # Update shield check
        if shield_enabled:
            self.shield_check_label.configure(text="✓ RM-Shield Enabled", text_color=get_text_color('success'))
        else:
            self.shield_check_label.configure(text="☐ RM-Shield Enabled", text_color=get_text_color('neutral'))
        
        # Update auto-sync check
        if auto_sync_enabled:
            self.auto_sync_check_label.configure(text="✓ Auto-Sync Enabled", text_color=get_text_color('success'))
        else:
            self.auto_sync_check_label.configure(text="☐ Auto-Sync Enabled", text_color=get_text_color('neutral'))
    
    def _show_onboarding_if_needed(self):
        """Show onboarding dialog for new users."""
        # Check if user has seen onboarding before
        has_seen_onboarding = self.config.get("ui.onboarding_seen", False)
        
        # Only show onboarding if user hasn't seen it and is not configured
        if not has_seen_onboarding and not self.config.is_configured():
            from tkinter import messagebox
            
            onboarding_message = """Welcome to The Memory Vault!

This is your secure encrypted storage system. Here's a quick guide:

1. SETUP: Click 'Setup' to configure your Wasabi S3 bucket
2. SYNC: Add folders to automatically sync to cloud storage
3. SNAPSHOTS: Create encrypted backups of your important data
4. SECURITY: Enable RM-Shield to protect against accidental deletion

Need help? Check the documentation for detailed instructions.

Click OK to start using The Memory Vault."""
            
            messagebox.showinfo(
                "Welcome to The Memory Vault",
                onboarding_message,
                icon='info'
            )
            
            # Mark onboarding as seen
            self.config.set("ui.onboarding_seen", True)
    
    def _toggle_language(self, event=None):
        """Toggle between English and Spanish."""
        # Toggle language
        new_language = "es_ES" if self.current_language == "en_US" else "en_US"
        self.i18n.set_language(new_language)
        self.current_language = new_language
        
        # Update display
        self.language_display.configure(text="🌐 EN" if new_language == "en_US" else "🌐 ES")
        
        # Save to config
        self.config.set("ui.language", new_language)
        
        # Refresh all UI text
        self._refresh_ui_text()
        
        # Show toast notification
        self.toast.show(f"Language changed to {'English' if new_language == 'en_US' else 'Spanish'}")
        self._log("INFO", f"Language changed to {new_language}")
    
    def _refresh_ui_text(self):
        """Refresh all UI text with current language translations."""
        # Update tab names (CustomTkinter 5.2+: rename(), set() only switches tabs)
        tab_i18n_keys = [
            "gui_dashboard",
            "gui_snapshots",
            "gui_sync",
            "gui_logs",
        ]
        for i, i18n_key in enumerate(tab_i18n_keys):
            old_name = self._tab_display_names[i]
            new_name = self.i18n.t(i18n_key)
            if old_name != new_name:
                try:
                    self.tabview.rename(old_name, new_name)
                    self._tab_display_names[i] = new_name
                except Exception:
                    pass
        
        # Update button texts
        self.setup_button.configure(text=self.i18n.t("gui_setup"))
        self.edit_button.configure(text=self.i18n.t("gui_edit"))
        self.open_button.configure(text=self.i18n.t("gui_open_vault"))
        self.close_button.configure(text=self.i18n.t("gui_close_vault"))
        self.sync_button.configure(text=self.i18n.t("gui_sync_folders"))
        self.snap_button.configure(text=self.i18n.t("gui_create_snapshot"))
        self.list_snapshots_button.configure(text=self.i18n.t("gui_list_snapshots"))
        self.add_folder_button.configure(text=self.i18n.t("gui_add_folder"))
        self.remove_folder_button.configure(text=self.i18n.t("gui_remove_folder"))
        self.clear_logs_button.configure(text=self.i18n.t("gui_clear_logs"))
        
        # Update switch texts
        self.shield_switch.configure(text=self.i18n.t("gui_rm_shield"))
        self.auto_sync_switch.configure(text=self.i18n.t("gui_auto_sync"))
        
        # Update subtitles
        self.shield_subtitle.configure(text=self.i18n.t("gui_shield_subtitle"))
        self.auto_sync_subtitle.configure(text=self.i18n.t("gui_auto_sync_subtitle"))
        
        # Update labels
        self.emergency_label.configure(text=self.i18n.t("gui_emergency_actions"))
        self.panic_button.configure(text=self.i18n.t("gui_panic_button"))
        self.config_status_label.configure(text=self.i18n.t("gui_config_status"))
        self.quick_actions_label.configure(text=self.i18n.t("gui_quick_actions"))
        self.language_label.configure(text=self.i18n.t("gui_language"))
        self.security_label.configure(text=self.i18n.t("gui_security_center"))
        self.sync_label.configure(text=self.i18n.t("gui_sync_filter"))
        
        # Update checklist items
        self.sync_check_label.configure(
            text=f"{'✓' if self.config.is_sync_configured() else '☐'} {self.i18n.t('gui_sync_configured')}"
        )
        self.snapshots_check_label.configure(
            text=f"{'✓' if self.config.is_snapshots_configured() else '☐'} {self.i18n.t('gui_snapshots_configured')}"
        )
        self.shield_check_label.configure(
            text=f"{'✓' if self.config.get('security.rm_shield', False) else '☐'} {self.i18n.t('gui_shield_enabled')}"
        )
        self.auto_sync_check_label.configure(
            text=f"{'✓' if self.config.get('sync.auto_sync', False) else '☐'} {self.i18n.t('gui_auto_sync_enabled')}"
        )
    
    def _set_initial_status(self):
        """Set initial status without blocking operations."""
        sync_configured = self.config.is_sync_configured()
        snapshots_configured = self.config.is_snapshots_configured()
        
        if not sync_configured and not snapshots_configured:
            self.status_label.configure(text="Not configured - Run setup first to configure Wasabi S3 buckets")
            self.setup_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.edit_button.pack_forget()
            self.open_button.pack_forget()
            self.close_button.pack_forget()
            self.snap_button.pack_forget()
            self.security_frame.pack_forget()
            self.sync_frame.pack_forget()
            self.language_frame.pack_forget()
            self.quick_actions_frame.pack_forget()
            self.emergency_frame.pack_forget()
        else:
            self.status_label.configure(text="Configured - Click 'Open Vault' to mount your encrypted vault")
            self.setup_button.pack_forget()
            self.edit_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL, before=self.open_button)
            
            # Show sync elements if configured
            if sync_configured:
                self.open_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
                self.close_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
                self.sync_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
                self.security_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
            
            # Show snapshots elements if configured
            if snapshots_configured:
                self.snap_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
                self.list_snapshots_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            
            # Show language frame
            self.quick_actions_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
            self.language_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
            
            # Show panic button if sync is configured
            if sync_configured:
                self.emergency_frame.pack(fill="x", pady=(Theme.PADDING_MEDIUM, Theme.PADDING_LARGE))
            
            # Update switches based on config
            shield_enabled = self.config.get("security.rm_shield", False)
            if shield_enabled:
                self.shield_switch.select()
            else:
                self.shield_switch.deselect()
            
            auto_sync_enabled = self.config.get("sync.auto_sync", False)
            if auto_sync_enabled:
                self.auto_sync_switch.select()
                self.auto_sync_enabled = True
                self.auto_sync_stop_event.clear()
                self.auto_sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
                self.auto_sync_thread.start()
            else:
                self.auto_sync_switch.deselect()
            
            # Update sync list
            if sync_configured:
                hostname = get_hostname()
                device_config = self.config.get_device_config(hostname)
                sync_folders = device_config.get("sync_folders", [])
                self.sync_listbox.delete("0.0", "end")
                for folder in sync_folders:
                    self.sync_listbox.insert("end", f"• {folder}\n")
    
    def _setup_window(self):
        """Setup window properties."""
        self.title("The Memory Vault")
        self.geometry("800x600")
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=Theme.PADDING_LARGE, pady=Theme.PADDING_LARGE)
        
        # Create tabs (use translated labels from the start; rename() fails during __init__)
        dash_name = self.i18n.t("gui_dashboard")
        snap_name = self.i18n.t("gui_snapshots")
        sync_name = self.i18n.t("gui_sync")
        logs_name = self.i18n.t("gui_logs")
        self.tab_dashboard = self.tabview.add(dash_name)
        self.tab_snapshots = self.tabview.add(snap_name)
        self.tab_sync = self.tabview.add(sync_name)
        self.tab_logs = self.tabview.add(logs_name)
        self._tab_display_names = [dash_name, snap_name, sync_name, logs_name]
        
        # Create widgets for each tab
        self._create_dashboard_tab()
        self._create_snapshots_tab()
        self._create_sync_tab()
        self._create_logs_tab()
        
    def _create_dashboard_tab(self):
        """Create dashboard tab widgets."""
        # Title
        self.title_label = ctk.CTkLabel(
            self.tab_dashboard,
            text="The Memory Vault",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_XXLARGE, weight="bold")
        )
        self.title_label.pack(pady=(Theme.PADDING_XLARGE, Theme.PADDING_XLARGE))
        
        # Status Section
        self.status_frame = ctk.CTkFrame(self.tab_dashboard)
        self.status_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Loading...",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_MEDIUM)
        )
        self.status_label.pack(pady=Theme.PADDING_MEDIUM)
        
        # Progress bar (hidden by default)
        self.progress_bar = ctk.CTkProgressBar(self.status_frame)
        self.progress_bar.pack(fill="x", padx=Theme.PADDING_LARGE, pady=(0, Theme.PADDING_SMALL))
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()
        
        # Progress percentage label
        self.progress_label = ctk.CTkLabel(
            self.status_frame,
            text="0%",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.progress_label.pack(pady=(0, Theme.PADDING_SMALL))
        self.progress_label.pack_forget()
        
        # Configuration Status Checklist
        self.config_status_frame = ctk.CTkFrame(self.tab_dashboard)
        self.config_status_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        
        self.config_status_label = ctk.CTkLabel(
            self.config_status_frame,
            text="Configuration Status",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_LARGE, weight="bold")
        )
        self.config_status_label.pack(pady=(Theme.PADDING_MEDIUM, Theme.PADDING_SMALL))
        
        self.checklist_frame = ctk.CTkFrame(self.config_status_frame)
        self.checklist_frame.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        
        # Initialize checklist items
        self.sync_check_label = ctk.CTkLabel(
            self.checklist_frame,
            text="☐ Sync Configured",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.sync_check_label.pack(anchor="w", padx=Theme.PADDING_SMALL, pady=2)
        
        self.snapshots_check_label = ctk.CTkLabel(
            self.checklist_frame,
            text="☐ Snapshots Configured",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.snapshots_check_label.pack(anchor="w", padx=Theme.PADDING_SMALL, pady=2)
        
        self.shield_check_label = ctk.CTkLabel(
            self.checklist_frame,
            text="☐ RM-Shield Enabled",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.shield_check_label.pack(anchor="w", padx=Theme.PADDING_SMALL, pady=2)
        
        self.auto_sync_check_label = ctk.CTkLabel(
            self.checklist_frame,
            text="☐ Auto-Sync Enabled",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.auto_sync_check_label.pack(anchor="w", padx=Theme.PADDING_SMALL, pady=2)
        
        # Quick Actions
        self.quick_actions_frame = ctk.CTkFrame(self.tab_dashboard)
        self.quick_actions_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        
        self.quick_actions_label = ctk.CTkLabel(
            self.quick_actions_frame,
            text="Quick Actions",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_LARGE, weight="bold")
        )
        self.quick_actions_label.pack(pady=(Theme.PADDING_MEDIUM, Theme.PADDING_SMALL))
        
        self.quick_actions_button_frame = ctk.CTkFrame(self.quick_actions_frame)
        self.quick_actions_button_frame.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        
        # Quick action: Open Vault
        quick_open_fg, quick_open_hover = get_action_colors('success')
        self.quick_open_button = ctk.CTkButton(
            self.quick_actions_button_frame,
            text="📂 Open Vault",
            command=self._open_vault,
            height=Theme.BUTTON_HEIGHT_SMALL,
            fg_color=quick_open_fg,
            hover_color=quick_open_hover
        )
        self.quick_open_button.pack(side="left", fill="x", expand=True, padx=(0, Theme.PADDING_SMALL))
        ToolTip(self.quick_open_button, "Quick access to open the vault")
        
        # Quick action: Sync Now
        quick_sync_fg, quick_sync_hover = get_action_colors('info')
        self.quick_sync_button = ctk.CTkButton(
            self.quick_actions_button_frame,
            text="🔄 Sync Now",
            command=self._sync_folders,
            height=Theme.BUTTON_HEIGHT_SMALL,
            fg_color=quick_sync_fg,
            hover_color=quick_sync_hover
        )
        self.quick_sync_button.pack(side="left", fill="x", expand=True, padx=(Theme.PADDING_SMALL, Theme.PADDING_SMALL))
        ToolTip(self.quick_sync_button, "Quick access to sync folders")
        
        # Quick action: Create Snapshot
        quick_snap_fg, quick_snap_hover = get_action_colors('special')
        self.quick_snap_button = ctk.CTkButton(
            self.quick_actions_button_frame,
            text="📸 Snapshot",
            command=self._create_snapshot,
            height=Theme.BUTTON_HEIGHT_SMALL,
            fg_color=quick_snap_fg,
            hover_color=quick_snap_hover
        )
        self.quick_snap_button.pack(side="right", fill="x", expand=True, padx=(Theme.PADDING_SMALL, 0))
        ToolTip(self.quick_snap_button, "Quick access to create a snapshot")
        
        # Language indicator
        self.language_frame = ctk.CTkFrame(self.tab_dashboard)
        self.language_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        
        self.language_label = ctk.CTkLabel(
            self.language_frame,
            text="Language",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.language_label.pack(side="left", padx=Theme.PADDING_MEDIUM)
        
        self.current_language = self.i18n.language
        self.language_display = ctk.CTkLabel(
            self.language_frame,
            text="🌐 EN" if self.current_language == "en_US" else "🌐 ES",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL, weight="bold"),
            cursor="hand2"
        )
        self.language_display.pack(side="right", padx=Theme.PADDING_MEDIUM)
        self.language_display.bind("<Button-1>", self._toggle_language)
        ToolTip(self.language_display, "Click to toggle language (English/Spanish)")
        self.button_frame = ctk.CTkFrame(self.tab_dashboard)
        self.button_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))

        # Setup button (only shown if not configured)
        setup_fg, setup_hover = get_action_colors('warning')
        self.setup_button = ctk.CTkButton(
            self.button_frame,
            text="Setup",
            command=self._run_setup,
            height=Theme.BUTTON_HEIGHT_MEDIUM,
            fg_color=setup_fg,
            hover_color=setup_hover
        )
        self.setup_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        ToolTip(self.setup_button, "Configure Wasabi S3 buckets and encryption settings")

        # Edit button (only shown if configured)
        edit_fg, edit_hover = get_action_colors('primary')
        self.edit_button = ctk.CTkButton(
            self.button_frame,
            text="Edit Configuration",
            command=self._run_edit,
            height=Theme.BUTTON_HEIGHT_MEDIUM,
            fg_color=edit_fg,
            hover_color=edit_hover
        )
        self.edit_button.pack(fill="x", padx=10, pady=5)
        ToolTip(self.edit_button, "Modify existing configuration settings")

        self.open_button = ctk.CTkButton(
            self.button_frame,
            text="Open Vault",
            command=self._open_vault,
            height=Theme.BUTTON_HEIGHT_MEDIUM
        )
        self.open_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        ToolTip(self.open_button, "Mount the vault as a local drive at ~/Vault")

        self.close_button = ctk.CTkButton(
            self.button_frame,
            text="Close Vault",
            command=self._close_vault,
            height=Theme.BUTTON_HEIGHT_MEDIUM
        )
        self.close_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        ToolTip(self.close_button, "Unmount the vault and clean up cache")

        sync_fg, sync_hover = get_action_colors('success')
        self.sync_button = ctk.CTkButton(
            self.button_frame,
            text="Sync Folders",
            command=self._sync_folders,
            height=Theme.BUTTON_HEIGHT_MEDIUM,
            fg_color=sync_fg,
            hover_color=sync_hover
        )
        self.sync_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        ToolTip(self.sync_button, "Sync configured folders to Wasabi S3")

        # Security Center
        self.security_frame = ctk.CTkFrame(self.tab_dashboard)
        self.security_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))

        self.security_label = ctk.CTkLabel(
            self.security_frame,
            text="Security Center",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_LARGE, weight="bold")
        )
        self.security_label.pack(pady=(Theme.PADDING_MEDIUM, Theme.PADDING_SMALL))

        self.shield_switch = ctk.CTkSwitch(
            self.security_frame,
            text="RM-Shield Protection",
            command=self._toggle_shield
        )
        self.shield_switch.pack(pady=Theme.PADDING_SMALL)
        ToolTip(self.shield_switch, "Protect against accidental rm commands by replacing with trash")
        
        self.shield_subtitle = ctk.CTkLabel(
            self.security_frame,
            text="Replaces 'rm' with trash to prevent accidental file deletion",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.shield_subtitle.pack(pady=(0, Theme.PADDING_MEDIUM))

        self.auto_sync_switch = ctk.CTkSwitch(
            self.security_frame,
            text="Auto-Sync (every 5 min)",
            command=self._toggle_auto_sync
        )
        self.auto_sync_switch.pack(pady=Theme.PADDING_SMALL)
        ToolTip(self.auto_sync_switch, "Automatically sync folders every 5 minutes")
        
        self.auto_sync_subtitle = ctk.CTkLabel(
            self.security_frame,
            text="Automatically sync configured folders to Wasabi every 5 minutes",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.auto_sync_subtitle.pack(pady=(0, Theme.PADDING_MEDIUM))

        # Emergency Section
        self.emergency_frame = ctk.CTkFrame(self.tab_dashboard)
        self.emergency_frame.pack(fill="x", pady=(Theme.PADDING_MEDIUM, Theme.PADDING_LARGE))

        self.emergency_label = ctk.CTkLabel(
            self.emergency_frame,
            text="Emergency Actions",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_LARGE, weight="bold"),
            text_color=get_text_color('danger')
        )
        self.emergency_label.pack(pady=(Theme.PADDING_MEDIUM, Theme.PADDING_SMALL))

        # Panic Button with double-click protection
        panic_fg, panic_hover = get_action_colors('danger')
        self.panic_button = ctk.CTkButton(
            self.emergency_frame,
            text="PANIC - Close All (Double-Click)",
            command=self._panic_click_handler,
            fg_color=panic_fg,
            hover_color=panic_hover,
            height=Theme.BUTTON_HEIGHT_LARGE
        )
        self.panic_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        ToolTip(self.panic_button, "Emergency: Double-click to close vault and stop all operations immediately")

        # Sync Status Panel
        self.sync_status_frame = ctk.CTkFrame(self.tab_dashboard)
        self.sync_status_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))

        self.sync_status_label = ctk.CTkLabel(
            self.sync_status_frame,
            text="Sync Status",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_LARGE, weight="bold")
        )
        self.sync_status_label.pack(pady=(Theme.PADDING_MEDIUM, Theme.PADDING_SMALL))

        # Status counters
        self.status_counters_frame = ctk.CTkFrame(self.sync_status_frame)
        self.status_counters_frame.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)

        self.syncing_count_label = ctk.CTkLabel(
            self.status_counters_frame,
            text="⏳ Syncing: 0",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL)
        )
        self.syncing_count_label.pack(side="left", padx=Theme.PADDING_MEDIUM)

        self.error_count_label = ctk.CTkLabel(
            self.status_counters_frame,
            text="⚠️ Errors: 0",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('danger')
        )
        self.error_count_label.pack(side="right", padx=Theme.PADDING_MEDIUM)

        # Error list
        self.error_list_label = ctk.CTkLabel(
            self.sync_status_frame,
            text="⚠️ Recent Errors:",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('danger')
        )
        self.error_list_label.pack(pady=(Theme.PADDING_SMALL, 0), anchor="w", padx=Theme.PADDING_MEDIUM)

        self.error_listbox = ctk.CTkTextbox(self.sync_status_frame, height=80)
        self.error_listbox.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        self.error_listbox.insert("end", "No errors")
        self.error_listbox.configure(state="disabled")

        # Signature
        signature_label = ctk.CTkLabel(
            self.tab_dashboard,
            text="Coded with ❤ by Daniquir",
            font=ctk.CTkFont(size=10),
            text_color=get_text_color('neutral')
        )
        signature_label.pack(pady=(Theme.PADDING_LARGE, Theme.PADDING_MEDIUM))
        
        # Make signature clickable
        signature_label.bind("<Button-1>", lambda e: self._open_github_link("https://github.com/Daniquir"))
        signature_label.configure(cursor="hand2")

    def _create_snapshots_tab(self):
        """Create snapshots tab widgets."""
        # Title
        ctk.CTkLabel(
            self.tab_snapshots,
            text="Snapshots Management",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_XLARGE, weight="bold")
        ).pack(pady=(Theme.PADDING_XLARGE, Theme.PADDING_XLARGE))
        
        # Status label for snapshots tab
        self.snap_status_label = ctk.CTkLabel(
            self.tab_snapshots,
            text="",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_MEDIUM)
        )
        self.snap_status_label.pack(pady=(0, Theme.PADDING_MEDIUM))
        
        # Progress bar for snapshots tab (hidden by default)
        self.snap_progress_bar = ctk.CTkProgressBar(self.tab_snapshots)
        self.snap_progress_bar.pack(fill="x", padx=Theme.PADDING_LARGE, pady=(0, Theme.PADDING_SMALL))
        self.snap_progress_bar.set(0)
        self.snap_progress_bar.pack_forget()
        
        # Snapshot progress percentage label
        self.snap_progress_label = ctk.CTkLabel(
            self.tab_snapshots,
            text="0%",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL),
            text_color=get_text_color('neutral')
        )
        self.snap_progress_label.pack(pady=(0, Theme.PADDING_MEDIUM))
        self.snap_progress_label.pack_forget()
        
        # Buttons
        self.snap_button_frame = ctk.CTkFrame(self.tab_snapshots)
        self.snap_button_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        
        self.snap_button = ctk.CTkButton(
            self.snap_button_frame,
            text="Create Snapshot",
            command=self._create_snapshot,
            height=Theme.BUTTON_HEIGHT_MEDIUM
        )
        self.snap_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        ToolTip(self.snap_button, "Create an encrypted backup snapshot of selected directory")

        snap_fg, snap_hover = get_action_colors('special')
        self.list_snapshots_button = ctk.CTkButton(
            self.snap_button_frame,
            text="View & Restore Snapshots",
            command=self._show_snapshots_window,
            height=Theme.BUTTON_HEIGHT_MEDIUM,
            fg_color=snap_fg,
            hover_color=snap_hover
        )
        self.list_snapshots_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        ToolTip(self.list_snapshots_button, "View all snapshots and restore files from backup")
        
        # Info
        info_label = ctk.CTkLabel(
            self.tab_snapshots,
            text="Snapshots are encrypted backups stored in Wasabi S3.\nUse 'View & Restore' to see all snapshots and restore files.",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL)
        )
        info_label.pack(pady=(0, Theme.PADDING_LARGE))

    def _create_sync_tab(self):
        """Create sync tab widgets."""
        # Title
        ctk.CTkLabel(
            self.tab_sync,
            text="Sync Folders Configuration",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_XLARGE, weight="bold")
        ).pack(pady=(Theme.PADDING_XLARGE, Theme.PADDING_XLARGE))
        
        # Sync Filter
        self.sync_frame = ctk.CTkFrame(self.tab_sync)
        self.sync_frame.pack(fill="both", expand=True, pady=(0, Theme.PADDING_LARGE), padx=Theme.PADDING_LARGE)

        self.sync_label = ctk.CTkLabel(
            self.sync_frame,
            text="Sync Folders",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_LARGE, weight="bold")
        )
        self.sync_label.pack(pady=(Theme.PADDING_MEDIUM, Theme.PADDING_SMALL))

        self.sync_listbox = ctk.CTkTextbox(self.sync_frame, height=200)
        self.sync_listbox.pack(fill="both", expand=True, padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)

        self.sync_button_frame = ctk.CTkFrame(self.sync_frame)
        self.sync_button_frame.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)

        self.add_folder_button = ctk.CTkButton(
            self.sync_button_frame,
            text="Add Folder",
            command=self._add_folder,
            height=Theme.BUTTON_HEIGHT_SMALL
        )
        self.add_folder_button.pack(side="left", fill="x", expand=True, padx=(0, Theme.PADDING_SMALL))
        ToolTip(self.add_folder_button, "Add a folder to the sync list")

        remove_fg, remove_hover = get_action_colors('danger')
        self.remove_folder_button = ctk.CTkButton(
            self.sync_button_frame,
            text="Remove Selected",
            command=self._remove_folder,
            height=Theme.BUTTON_HEIGHT_SMALL,
            fg_color=remove_fg,
            hover_color=remove_hover
        )
        self.remove_folder_button.pack(side="right", fill="x", expand=True, padx=(Theme.PADDING_SMALL, 0))
        ToolTip(self.remove_folder_button, "Remove selected folder from sync list")
        
        # Info
        info_label = ctk.CTkLabel(
            self.tab_sync,
            text="These folders will be synced to the Wasabi S3 bucket when mounted.\nSelect a folder and click 'Remove Selected' to remove it from sync.",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_SMALL)
        )
        info_label.pack(pady=(0, Theme.PADDING_LARGE))

    def _create_logs_tab(self):
        """Create logs tab widgets."""
        # Title
        ctk.CTkLabel(
            self.tab_logs,
            text="Activity Logs",
            font=ctk.CTkFont(size=Theme.FONT_SIZE_XLARGE, weight="bold")
        ).pack(pady=(Theme.PADDING_XLARGE, Theme.PADDING_XLARGE))
        
        # Logs display
        self.log_textbox = ctk.CTkTextbox(self.tab_logs, height=300)
        self.log_textbox.pack(fill="both", expand=True, padx=Theme.PADDING_LARGE, pady=(0, Theme.PADDING_LARGE))
        
        # Clear button
        clear_fg, clear_hover = get_action_colors('neutral')
        self.clear_logs_button = ctk.CTkButton(
            self.tab_logs,
            text="Clear Logs",
            command=self._clear_logs,
            height=Theme.BUTTON_HEIGHT_SMALL,
            fg_color=clear_fg,
            hover_color=clear_hover
        )
        self.clear_logs_button.pack(pady=(0, Theme.PADDING_LARGE))
        
        # Initialize logs list
        self.logs = []
        self._log("INFO", "Application started")
    
    def _update_status(self):
        """Update status display (must be called from main thread)."""
        sync_configured = self.config.is_sync_configured()
        snapshots_configured = self.config.is_snapshots_configured()

        if not sync_configured and not snapshots_configured:
            # Nothing configured
            self.status_label.configure(text="Not configured - Run setup first to configure Wasabi S3 buckets")
            self.setup_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.edit_button.pack_forget()
            # Hide all other elements
            self.open_button.pack_forget()
            self.close_button.pack_forget()
            self.snap_button.pack_forget()
            self.security_frame.pack_forget()
            self.sync_frame.pack_forget()
            self.language_frame.pack_forget()
            self.quick_actions_frame.pack_forget()
            self.emergency_frame.pack_forget()
            return

        # At least one functionality is configured
        self.setup_button.pack_forget()
        self.edit_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL, before=self.open_button)

        # Show/hide sync elements
        if sync_configured:
            self.open_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.close_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.sync_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.security_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        else:
            self.open_button.pack_forget()
            self.close_button.pack_forget()
            self.sync_button.pack_forget()
            self.security_frame.pack_forget()

        # Show/hide snapshots elements
        if snapshots_configured:
            self.snap_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.list_snapshots_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        else:
            self.snap_button.pack_forget()
            self.list_snapshots_button.pack_forget()

        # Show language frame
        self.language_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        
        # Show panic button if sync is configured
        if sync_configured:
            self.emergency_frame.pack(fill="x", pady=(Theme.PADDING_MEDIUM, Theme.PADDING_LARGE))
        else:
            self.emergency_frame.pack_forget()
        
        try:
            if self.mount_manager is None:
                self.mount_manager = MountManager(self.config._config, output_callback=self._log_console)
            
            mount_status = self.mount_manager.get_mount_status()
            
            if mount_status["mounted"]:
                status_text = f"Mounted at {mount_status['mount_point']}"
            else:
                status_text = "Not mounted"
            
            # Check last snapshot
            hostname = get_hostname()
            device_config = self.config.get_device_config(hostname)
            last_snap = device_config.get("last_snap")
            
            if last_snap:
                status_text += f"\nLast snapshot: {last_snap}"
            else:
                status_text += "\nNo snapshots yet"
            
            self.status_label.configure(text=status_text)
            
            # Update shield switch
            shield_enabled = self.config.get("security.rm_shield", False)
            if shield_enabled:
                self.shield_switch.select()
            else:
                self.shield_switch.deselect()
            
            # Update auto-sync switch
            auto_sync_enabled = self.config.get("sync.auto_sync", False)
            if auto_sync_enabled and not self.auto_sync_enabled:
                self.auto_sync_switch.select()
                self._toggle_auto_sync()
            elif not auto_sync_enabled and self.auto_sync_enabled:
                self.auto_sync_switch.deselect()
                self._toggle_auto_sync()
            
            # Update sync list
            sync_folders = device_config.get("sync_folders", [])
            self.sync_listbox.delete("0.0", "end")
            for folder in sync_folders:
                self.sync_listbox.insert("end", f"• {folder}\n")
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
    
    def _update_status_async(self):
        """Update status in background thread to avoid blocking GUI."""
        def check_thread():
            try:
                # Get configuration status (fast, no GUI calls)
                sync_configured = self.config.is_sync_configured()
                snapshots_configured = self.config.is_snapshots_configured()
                
                # Get mount status (may be slow)
                mount_status = None
                mount_error = None
                try:
                    if self.mount_manager is None:
                        self.mount_manager = MountManager(self.config._config, output_callback=self._log_console)
                    mount_status = self.mount_manager.get_mount_status()
                except Exception as e:
                    mount_error = str(e)
                
                # Get device config
                hostname = get_hostname()
                device_config = self.config.get_device_config(hostname)
                last_snap = device_config.get("last_snap")
                sync_folders = device_config.get("sync_folders", [])
                
                # Schedule GUI update on main thread
                self.after(0, lambda: self._update_gui_from_status(
                    sync_configured, snapshots_configured, mount_status, mount_error,
                    hostname, device_config, last_snap, sync_folders
                ))
            except Exception as e:
                err = str(e)
                self.after(0, lambda err=err: self.status_label.configure(text=f"Error: {err}"))
        
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def _update_gui_from_status(self, sync_configured, snapshots_configured, mount_status, mount_error,
                                 hostname, device_config, last_snap, sync_folders):
        """Update GUI from status data (must be called from main thread)."""
        if not sync_configured and not snapshots_configured:
            self.status_label.configure(text="Not configured - Run setup first to configure Wasabi S3 buckets")
            self.setup_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.edit_button.pack_forget()
            self.open_button.pack_forget()
            self.close_button.pack_forget()
            self.snap_button.pack_forget()
            self.security_frame.pack_forget()
            self.sync_frame.pack_forget()
            self.language_frame.pack_forget()
            self.quick_actions_frame.pack_forget()
            self.emergency_frame.pack_forget()
            return

        self.setup_button.pack_forget()
        self.edit_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL, before=self.open_button)

        if sync_configured:
            self.open_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.close_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.sync_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.security_frame.pack(fill="x", pady=(0, Theme.PADDING_LARGE))
        else:
            self.open_button.pack_forget()
            self.close_button.pack_forget()
            self.sync_button.pack_forget()
            self.security_frame.pack_forget()

        if snapshots_configured:
            self.snap_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
            self.list_snapshots_button.pack(fill="x", padx=Theme.PADDING_MEDIUM, pady=Theme.PADDING_SMALL)
        else:
            self.snap_button.pack_forget()
            self.list_snapshots_button.pack_forget()

        if sync_configured:
            self.panic_button.pack(fill="x", pady=(Theme.PADDING_MEDIUM, 0))
        else:
            self.emergency_frame.pack_forget()
        
        if mount_error:
            self.status_label.configure(text=f"Error: {mount_error}")
        elif mount_status:
            if mount_status["mounted"]:
                status_text = f"Mounted at {mount_status['mount_point']}"
            else:
                status_text = "Not mounted"
            
            if last_snap:
                status_text += f"\nLast snapshot: {last_snap}"
            else:
                status_text += "\nNo snapshots yet"
            
            self.status_label.configure(text=status_text)
        
        shield_enabled = self.config.get("security.rm_shield", False)
        if shield_enabled:
            self.shield_switch.select()
        else:
            self.shield_switch.deselect()
        
        auto_sync_enabled = self.config.get("sync.auto_sync", False)
        if auto_sync_enabled and not self.auto_sync_enabled:
            self.auto_sync_switch.select()
            self._toggle_auto_sync()
        elif not auto_sync_enabled and self.auto_sync_enabled:
            self.auto_sync_switch.deselect()
            self._toggle_auto_sync()
        
        self.sync_listbox.delete("0.0", "end")
        for folder in sync_folders:
            self.sync_listbox.insert("end", f"• {folder}\n")
    
    def _open_vault(self):
        """Open/mount the vault."""
        if not self.config.is_configured():
            self.status_label.configure(text="Not configured - Run setup first to configure Wasabi S3 buckets")
            self._log("ERROR", "Attempted to open vault but not configured")
            return
        
        # Show progress
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10), before=self.status_label)
        self.progress_bar.set(0.3)
        self.progress_label.pack(before=self.status_label)
        self.progress_label.configure(text="30%")
        self.status_label.configure(text="Mounting vault... (this may take 10-30 seconds)")
        self.update()
        self._log("INFO", "Mounting vault...")
        
        try:
            if self.mount_manager is None:
                self.mount_manager = MountManager(self.config._config, output_callback=self._log_console)
            
            self.progress_bar.set(0.6)
            self.progress_label.configure(text="60%")
            self.update()
            
            success, msg = self.mount_manager.mount_with_retry()
            
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="100%")
            self.update()
            
            if success:
                self.status_label.configure(text=f"{msg}")
                self.toast.show("Vault mounted successfully!")
                self._log("INFO", f"Vault mounted successfully: {msg}")
            else:
                self.status_label.configure(text=f"{msg}")
                self._log("ERROR", f"Failed to mount vault: {msg}")
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
            self._log("ERROR", f"Error mounting vault: {str(e)}")
        finally:
            # Hide progress bar after a short delay
            self.after(1000, lambda: self.progress_bar.pack_forget())
            self.after(1000, lambda: self.progress_label.pack_forget())
    
    def _close_vault(self):
        """Close/unmount the vault."""
        # Show confirmation dialog
        if not self._show_confirmation_dialog(
            "Confirm Close Vault",
            "Are you sure you want to close the vault? This will unmount it and stop all operations."
        ):
            return
        
        # Show progress
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10), before=self.status_label)
        self.progress_bar.set(0.3)
        self.progress_label.pack(before=self.status_label)
        self.progress_label.configure(text="30%")
        self.status_label.configure(text="Unmounting vault... (this may take a few seconds)")
        self.update()
        self._log("INFO", "Unmounting vault...")
        
        try:
            if self.mount_manager is None:
                self.mount_manager = MountManager(self.config._config, output_callback=self._log_console)
            
            self.progress_bar.set(0.6)
            self.progress_label.configure(text="60%")
            self.update()
            
            success, msg = self.mount_manager.unmount()
            
            if success:
                self.progress_bar.set(0.8)
                self.progress_label.configure(text="80%")
                self.update()
                self.mount_manager.cleanup_cache()
                self.progress_bar.set(1.0)
                self.progress_label.configure(text="100%")
                self.status_label.configure(text=f"{msg}")
                self.toast.show("Vault unmounted successfully!")
                self._log("INFO", f"Vault unmounted successfully: {msg}")
            else:
                self.status_label.configure(text=f"{msg}")
                self._log("ERROR", f"Failed to unmount vault: {msg}")
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
            self._log("ERROR", f"Error unmounting vault: {str(e)}")
        finally:
            # Hide progress bar after a short delay
            self.after(1000, lambda: self.progress_bar.pack_forget())
            self.after(1000, lambda: self.progress_label.pack_forget())
    
    def _create_snapshot(self):
        """Create a snapshot."""
        if not self.config.is_configured():
            self.snap_status_label.configure(text="Not configured - Run setup first to configure backup settings")
            self._log("ERROR", "Attempted to create snapshot but not configured")
            return
        
        # Show dialog to select directory
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select directory to snapshot")
        if not folder:
            self.snap_status_label.configure(text="No directory selected - Please choose a folder to backup")
            self._log("WARN", "No directory selected for snapshot")
            return
        
        # Disable button during snapshot
        self.snap_button.configure(state="disabled", text="Snapshotting...")
        
        # Show progress
        self.snap_progress_bar.pack(fill="x", padx=20, pady=(0, 10), before=self.snap_button_frame)
        self.snap_progress_bar.set(0.3)
        self.snap_progress_label.pack(before=self.snap_button_frame)
        self.snap_progress_label.configure(text="30%")
        self.snap_status_label.configure(text=f"Snapshotting: {folder} (this may take several minutes depending on size)")
        self.update()
        self._log("INFO", f"Snapshotting: {folder}")
        
        # Run snapshot in background thread
        import threading
        thread = threading.Thread(target=self._run_snapshot_thread, args=(folder,))
        thread.daemon = True
        thread.start()
    
    def _run_snapshot_thread(self, folder):
        """Run snapshot in background thread."""
        try:
            if self.restic is None:
                self.restic = ResticWrapper(self.config._config, output_callback=self._log_console)
            
            hostname = get_hostname()
            
            # Update progress
            self.after(0, lambda: self.snap_progress_bar.set(0.5))
            self.after(0, lambda: self.snap_progress_label.configure(text="50%"))
            
            success, msg = self.restic.backup(folder, hostname)
            
            if success:
                self.after(0, lambda: self.snap_progress_bar.set(1.0))
                self.after(0, lambda: self.snap_progress_label.configure(text="100%"))
                self.after(0, lambda: self.snap_status_label.configure(text=f"Snapshot created: {folder}"))
                self.after(0, lambda: self.toast.show("Snapshot created successfully!"))
                self._log("INFO", f"Snapshot created successfully: {folder}")
                
                # Update last snap timestamp
                from datetime import datetime
                device_config = self.config.get_device_config(hostname)
                device_config["last_snap"] = datetime.now().isoformat()
                self.config.update_device_config(hostname, device_config)
                self.after(0, self._update_status)
                self.after(0, self._update_config_checklist())
            else:
                self.after(0, lambda: self.snap_status_label.configure(text=f"Error: {msg}"))
                self._log("ERROR", f"Failed to create snapshot: {msg}")
                self.after(0, lambda: self.snap_progress_bar.pack_forget())
                self.after(0, lambda: self.snap_progress_label.pack_forget())
            
        except Exception as e:
            err = str(e)
            self.after(0, lambda err=err: self.snap_status_label.configure(text=f"Error: {err}"))
            self._log("ERROR", f"Error creating snapshot: {err}")
        finally:
            # Re-enable button and hide progress bar
            self.after(0, lambda: self.snap_button.configure(state="normal", text="Create Snapshot"))
            self.after(1000, lambda: self.snap_progress_bar.pack_forget())
            self.after(1000, lambda: self.snap_progress_label.pack_forget())
    
    def _toggle_shield(self):
        """Toggle RM-Shield protection."""
        from ..utils.shield import Shield
        
        shield = Shield()
        
        if self.shield_switch.get():
            self._log("INFO", "Enabling RM-Shield protection...")
            success, msg = shield.enable()
            if success:
                self.config.set("security.rm_shield", True)
                self.config.save()
                self.status_label.configure(text=f"{msg}")
                self._log("INFO", f"RM-Shield enabled: {msg}")
            else:
                self.status_label.configure(text=f"{msg}")
                self._log("ERROR", f"Failed to enable RM-Shield: {msg}")
                self.shield_switch.deselect()
        else:
            self._log("INFO", "Disabling RM-Shield protection...")
            success, msg = shield.disable()
            if success:
                self.config.set("security.rm_shield", False)
                self.config.save()
                self.status_label.configure(text=f"{msg}")
                self._log("INFO", f"RM-Shield disabled: {msg}")
            else:
                self.status_label.configure(text=f"{msg}")
                self._log("ERROR", f"Failed to disable RM-Shield: {msg}")
                self.shield_switch.select()
    
    def _toggle_auto_sync(self):
        """Toggle auto-sync."""
        if self.auto_sync_switch.get():
            self._log("INFO", "Enabling auto-sync...")
            self.auto_sync_enabled = True
            self.config.set("sync.auto_sync", True)
            self.config.save()
            self.auto_sync_stop_event.clear()
            self.auto_sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
            self.auto_sync_thread.start()
            self.status_label.configure(text="Auto-sync enabled")
            self._log("INFO", "Auto-sync enabled (every 5 minutes)")
        else:
            self._log("INFO", "Disabling auto-sync...")
            self.auto_sync_enabled = False
            self.config.set("sync.auto_sync", False)
            self.config.save()
            self.auto_sync_stop_event.set()
            if self.auto_sync_thread:
                self.auto_sync_thread.join(timeout=2)
            self.status_label.configure(text="Auto-sync disabled")
            self._log("INFO", "Auto-sync disabled")

    def _open_github_link(self, url):
        """Open a URL in the default web browser."""
        import webbrowser
        webbrowser.open(url)
    
    def _auto_sync_loop(self):
        """Auto-sync loop running in background."""
        while not self.auto_sync_stop_event.is_set():
            # Wait for 5 minutes (300 seconds) or until stop event
            for _ in range(300):
                if self.auto_sync_stop_event.is_set():
                    return
                time.sleep(1)
            
            # Perform sync
            if self.auto_sync_enabled and not self.auto_sync_stop_event.is_set():
                self._log("INFO", "Auto-sync triggered")
                hostname = get_hostname()
                device_config = self.config.get_device_config(hostname)
                sync_folders = device_config.get("sync_folders", [])
                
                if sync_folders:
                    try:
                        if self.rclone is None:
                            self.rclone = RcloneWrapper(self.config._config)
                        
                        storage = self.config.get("storage", {})
                        bucket = storage.get("sync_bucket", "")
                        region = storage.get("sync_region", "us-east-1")
                        endpoint = f"{region}.wasabisys.com"
                        
                        # Clear previous sync status for auto-sync
                        self.sync_status["syncing_folders"] = []
                        self.sync_status["errors"] = []
                        self.after(0, self._update_sync_status_panel)
                        
                        for folder in sync_folders:
                            if self.auto_sync_stop_event.is_set():
                                break
                            folder_name = Path(folder).name
                            self._log("INFO", f"Auto-syncing: {folder}")
                            
                            # Add to syncing list
                            self.sync_status["syncing_folders"].append(folder)
                            self.after(0, self._update_sync_status_panel)
                            
                            success, msg = self.rclone.sync_to_cloud(folder, folder_name)
                            
                            # Remove from syncing list
                            if folder in self.sync_status["syncing_folders"]:
                                self.sync_status["syncing_folders"].remove(folder)
                            
                            if success:
                                self._log("INFO", f"Auto-synced: {folder}")
                            else:
                                error_msg = f"{folder}: {msg}"
                                self.sync_status["errors"].append(error_msg)
                                self._log("ERROR", f"Auto-sync failed {folder}: {msg}")
                                self.after(0, self._update_sync_status_panel)
                        
                        # Update last sync time
                        from datetime import datetime
                        self.sync_status["last_sync_time"] = datetime.now().isoformat()
                        self.after(0, self._update_sync_status_panel)
                        
                        # Send notification for auto-sync
                        if self.sync_status["errors"]:
                            error_count = len(self.sync_status["errors"])
                            self._send_notification(
                                "Memory Vault Auto-Sync",
                                f"Auto-sync completed with {error_count} error(s)",
                                urgency="normal"
                            )
                        
                    except Exception as e:
                        self._log("ERROR", f"Auto-sync error: {str(e)}")
                        self._send_notification(
                            "Memory Vault Error",
                            f"Auto-sync failed: {str(e)}",
                            urgency="critical"
                        )
                    finally:
                        # Clear syncing list
                        self.sync_status["syncing_folders"] = []
                        self.after(0, self._update_sync_status_panel)

    def _log(self, level, message):
        """Add a log entry.
        
        Args:
            level: Log level (INFO, WARN, ERROR)
            message: Log message
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        self.logs.append(log_entry)
        
        # Update log textbox
        self.log_textbox.insert("end", log_entry)
        self.log_textbox.see("end")
    
    def _log_console(self, line):
        """Add a line to the console output (thread-safe).
        
        Args:
            line: Output line from command
        """
        self.after(0, self._insert_log_line, line)
    
    def _send_notification(self, title: str, message: str, urgency: str = "normal"):
        """Send a desktop notification using notify-send.
        
        Args:
            title: Notification title
            message: Notification message
            urgency: Urgency level (low, normal, critical)
        """
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, title, message],
                check=True,
                capture_output=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # notify-send not available, silently fail
            pass
    
    def _update_sync_status_panel(self):
        """Update the sync status panel with current state."""
        # Update counters
        syncing_count = len(self.sync_status["syncing_folders"])
        error_count = len(self.sync_status["errors"])
        
        self.syncing_count_label.configure(text=f"⏳ Syncing: {syncing_count}")
        self.error_count_label.configure(text=f"⚠️ Errors: {error_count}")
        
        # Update error list (show last 5 errors)
        self.error_listbox.configure(state="normal")
        self.error_listbox.delete("0.0", "end")
        
        if self.sync_status["errors"]:
            recent_errors = self.sync_status["errors"][-5:]
            for error in recent_errors:
                self.error_listbox.insert("end", f"• {error}\n")
        else:
            self.error_listbox.insert("end", "No errors")
        
        self.error_listbox.configure(state="disabled")
    
    def _insert_log_line(self, line):
        """Insert a log line into the textbox (called from main thread)."""
        self.log_textbox.insert("end", f"{line}\n")
        self.log_textbox.see("end")

    def _clear_logs(self):
        """Clear all logs."""
        # Show confirmation dialog
        if not self._show_confirmation_dialog(
            "Confirm Clear Logs",
            "Are you sure you want to clear all logs? This action cannot be undone."
        ):
            return
        
        self.logs = []
        self.log_textbox.delete("0.0", "end")
        self._log("INFO", "Logs cleared")
    
    def _add_folder(self):
        """Add folder to sync list."""
        from tkinter import filedialog
        
        folder = filedialog.askdirectory(title="Select folder to sync")
        if folder:
            hostname = get_hostname()
            device_config = self.config.get_device_config(hostname)
            sync_folders = device_config.get("sync_folders", [])
            
            if folder not in sync_folders:
                sync_folders.append(folder)
                device_config["sync_folders"] = sync_folders
                self.config.update_device_config(hostname, device_config)
                self._update_status()
                self._update_config_checklist()
                self.status_label.configure(text=f"Folder added: {folder} - It will sync on next sync operation")
                self.toast.show(f"Folder added: {folder}")
                self._log("INFO", f"Folder added to sync: {folder}")
            else:
                self.status_label.configure(text="Folder already in sync list - No changes made")
                self._log("WARN", f"Folder already in sync list: {folder}")

    def _remove_folder(self):
        """Remove selected folder from sync list."""
        try:
            # Get selected text from textbox
            selected_text = self.sync_listbox.get("sel.first", "sel.last")
            if not selected_text:
                self.status_label.configure(text="Please select a folder to remove")
                self._log("WARN", "Attempted to remove folder but none selected")
                return
        except Exception:
            self.status_label.configure(text="Please select a folder to remove")
            self._log("WARN", "Attempted to remove folder but none selected")
            return
        
        # Extract folder path from selected text (format: "• /path/to/folder")
        folder = selected_text.strip().replace("• ", "")
        
        # Show confirmation dialog
        if not self._show_confirmation_dialog(
            "Confirm Remove Folder",
            f"Are you sure you want to remove '{folder}' from the sync list? It will no longer be synced to Wasabi."
        ):
            return
        
        hostname = get_hostname()
        device_config = self.config.get_device_config(hostname)
        sync_folders = device_config.get("sync_folders", [])
        
        if folder in sync_folders:
            sync_folders.remove(folder)
            device_config["sync_folders"] = sync_folders
            self.config.update_device_config(hostname, device_config)
            self._update_status()
            self._update_config_checklist()
            self.status_label.configure(text=f"Folder removed: {folder} - It will no longer be synced")
            self.toast.show(f"Folder removed: {folder}")
            self._log("INFO", f"Folder removed from sync: {folder}")
        else:
            self.status_label.configure(text="Folder not found in sync list")
            self._log("ERROR", f"Folder not found in sync list: {folder}")
    
    def _show_confirmation_dialog(self, title: str, message: str) -> bool:
        """Show a confirmation dialog.
        
        Args:
            title: Dialog title
            message: Dialog message
        
        Returns:
            True if user confirmed, False otherwise
        """
        from tkinter import messagebox
        return messagebox.askyesno(title, message, icon='warning')
    
    def _panic_click_handler(self):
        """Handle panic button click with double-click protection."""
        self.panic_click_count += 1
        
        # Reset click count after 1 second if no second click
        if self.panic_click_timer:
            self.after_cancel(self.panic_click_timer)
        
        self.panic_click_timer = self.after(1000, self._reset_panic_clicks)
        
        # Execute panic action on second click within 1 second
        if self.panic_click_count >= 2:
            self._panic_close()
            self._reset_panic_clicks()
    
    def _reset_panic_clicks(self):
        """Reset panic button click count."""
        self.panic_click_count = 0
        if self.panic_click_timer:
            self.after_cancel(self.panic_click_timer)
            self.panic_click_timer = None
    
    def _panic_close(self):
        """Emergency close all operations."""
        self._close_vault()
        self.status_label.configure(text="Vault closed - All operations stopped safely")
    
    def _sync_folders(self):
        """Sync configured folders to Wasabi."""
        if not self.config.is_sync_configured():
            self.status_label.configure(text="Sync not configured - Add folders in the Sync tab first")
            self._log("ERROR", "Attempted to sync but sync not configured")
            return
        
        hostname = get_hostname()
        device_config = self.config.get_device_config(hostname)
        sync_folders = device_config.get("sync_folders", [])
        
        if not sync_folders:
            self.status_label.configure(text="No folders configured for sync - Add folders in the Sync tab")
            self._log("WARN", "No folders configured for sync")
            return
        
        # Disable button during sync
        self.sync_button.configure(state="disabled", text="Syncing...")
        
        # Show progress
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10), before=self.status_label)
        self.progress_bar.set(0.1)
        self.progress_label.pack(before=self.status_label)
        self.progress_label.configure(text="10%")
        self.status_label.configure(text="Syncing folders... (progress shown below)")
        self.update()
        self._log("INFO", f"Syncing {len(sync_folders)} folder(s)")
        
        # Run sync in background thread
        import threading
        thread = threading.Thread(target=self._run_sync_thread, args=(sync_folders,))
        thread.daemon = True
        thread.start()
    
    def _run_sync_thread(self, sync_folders):
        """Run sync in background thread."""
        try:
            if self.rclone is None:
                self.rclone = RcloneWrapper(self.config._config)
            
            storage = self.config.get("storage", {})
            bucket = storage.get("sync_bucket", "")
            region = storage.get("sync_region", "us-east-1")
            endpoint = f"{region}.wasabisys.com"
            
            # Clear previous sync status
            self.sync_status["syncing_folders"] = []
            self.sync_status["errors"] = []
            self.after(0, self._update_sync_status_panel)
            
            total_folders = len(sync_folders)
            for i, folder in enumerate(sync_folders):
                folder_name = Path(folder).name
                self.after(0, lambda: self.progress_bar.set((i + 1) / total_folders))
                self.after(0, lambda: self.progress_label.configure(text=f"{int(((i + 1) / total_folders) * 100)}%"))
                self._log("INFO", f"Syncing: {folder} -> {bucket}/{folder_name}")
                
                # Add to syncing list
                self.sync_status["syncing_folders"].append(folder)
                self.after(0, self._update_sync_status_panel)
                
                # Sync to cloud
                success, msg = self.rclone.sync_to_cloud(folder, folder_name)
                
                # Remove from syncing list
                if folder in self.sync_status["syncing_folders"]:
                    self.sync_status["syncing_folders"].remove(folder)
                
                if success:
                    self._log("INFO", f"Synced: {folder}")
                else:
                    error_msg = f"{folder}: {msg}"
                    self.sync_status["errors"].append(error_msg)
                    self._log("ERROR", f"Failed to sync {folder}: {msg}")
                    self.after(0, self._update_sync_status_panel)
            
            # Update last sync time
            from datetime import datetime
            self.sync_status["last_sync_time"] = datetime.now().isoformat()
            
            self.after(0, lambda: self.progress_bar.set(1.0))
            self.after(0, lambda: self.status_label.configure(text="Sync completed - Check logs for details"))
            self.after(0, lambda: self.toast.show("Sync completed!"))
            self.after(0, self._update_sync_status_panel)
            self._log("INFO", "Sync completed")
            
            # Send notification
            if self.sync_status["errors"]:
                error_count = len(self.sync_status["errors"])
                self._send_notification(
                    "Memory Vault Sync",
                    f"Sync completed with {error_count} error(s)",
                    urgency="normal"
                )
            else:
                self._send_notification(
                    "Memory Vault Sync",
                    "Sync completed successfully",
                    urgency="low"
                )
            
        except Exception as e:
            err = str(e)
            self.after(0, lambda err=err: self.status_label.configure(text=f"Error: {err}"))
            self._log("ERROR", f"Error syncing folders: {err}")
            self._send_notification(
                "Memory Vault Error",
                f"Sync failed: {err}",
                urgency="critical"
            )
        finally:
            # Clear syncing list
            self.sync_status["syncing_folders"] = []
            self.after(0, self._update_sync_status_panel)
            # Re-enable button and hide progress bar
            self.after(0, lambda: self.sync_button.configure(state="normal", text="Sync Folders"))
            self.after(1000, lambda: self.progress_bar.pack_forget())
            self.after(1000, lambda: self.progress_label.pack_forget())

    def _run_setup(self):
        """Run the setup wizard in a new window."""
        setup_window = SetupWindow(self)
        self.wait_window(setup_window)
        self._update_status()
        self._update_config_checklist()

    def _run_edit(self):
        """Run the edit wizard in a new window."""
        setup_window = SetupWindow(self, edit_mode=True)
        self.wait_window(setup_window)
        self._update_status()
        self._update_config_checklist()

    def _show_snapshots_window(self):
        """Show snapshots viewer window."""
        snapshots_window = SnapshotsWindow(self)
        self.wait_window(snapshots_window)
        self._update_status()


class SetupWindow(ctk.CTkToplevel):
    """Setup wizard window for initial configuration."""

    def __init__(self, parent, edit_mode=False):
        """Initialize setup window.

        Args:
            parent: Parent window
            edit_mode: If True, window is in edit mode (pre-fill with existing config)
        """
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.i18n = I18n("auto")
        self.edit_mode = edit_mode

        self.title("Edit Configuration" if edit_mode else "Setup Wizard")
        self.geometry("600x600")
        self.transient(parent)

        # Ensure theme is set
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._create_widgets()
        self._pre_fill_fields()
        self.update()
        self.lift()
        self.grab_set()

    def _create_widgets(self):
        """Create setup form widgets."""
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.main_frame = self.scrollable_frame

        # Title
        ctk.CTkLabel(
            self.main_frame,
            text="The Memory Vault Setup",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(0, 20))

        # Functionality selection
        ctk.CTkLabel(self.main_frame, text="Select functionalities to configure:").pack(anchor="w")
        self.sync_check = ctk.CTkCheckBox(self.main_frame, text="Sync (Rclone for daily use)", command=self._toggle_frames)
        self.sync_check.pack(anchor="w", pady=(0, 5))
        self.snapshots_check = ctk.CTkCheckBox(self.main_frame, text="Snapshots (Restic for backups)", command=self._toggle_frames)
        self.snapshots_check.pack(anchor="w", pady=(0, 20))

        # Common credentials
        ctk.CTkLabel(self.main_frame, text="Wasabi Credentials:").pack(anchor="w")
        self.access_key_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Access Key")
        self.access_key_entry.pack(fill="x", pady=(0, 10))

        self.secret_key_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Secret Key", show="*")
        self.secret_key_entry.pack(fill="x", pady=(0, 20))

        # Sync configuration frame
        self.sync_frame = ctk.CTkFrame(self.main_frame)
        self.sync_frame.pack(fill="x", pady=(0, 20))
        self.sync_frame.pack_forget()  # Initially hidden

        ctk.CTkLabel(self.sync_frame, text="Sync Configuration:").pack(anchor="w")
        self.sync_bucket_entry = ctk.CTkEntry(self.sync_frame, placeholder_text="my-sync-bucket")
        self.sync_bucket_entry.pack(fill="x", pady=(0, 10))

        self.sync_region_entry = ctk.CTkEntry(self.sync_frame, placeholder_text="us-east-1")
        self.sync_region_entry.insert(0, "us-east-1")
        self.sync_region_entry.pack(fill="x", pady=(0, 10))

        # Snapshots configuration frame
        self.snapshots_frame = ctk.CTkFrame(self.main_frame)
        self.snapshots_frame.pack(fill="x", pady=(0, 20))
        self.snapshots_frame.pack_forget()  # Initially hidden

        ctk.CTkLabel(self.snapshots_frame, text="Snapshots Configuration:").pack(anchor="w")
        self.vault_bucket_entry = ctk.CTkEntry(self.snapshots_frame, placeholder_text="my-vault-bucket")
        self.vault_bucket_entry.pack(fill="x", pady=(0, 10))

        self.vault_region_entry = ctk.CTkEntry(self.snapshots_frame, placeholder_text="us-east-1")
        self.vault_region_entry.insert(0, "us-east-1")
        self.vault_region_entry.pack(fill="x", pady=(0, 10))

        self.password_entry = ctk.CTkEntry(self.snapshots_frame, placeholder_text="Password", show="*")
        self.password_entry.pack(fill="x", pady=(0, 10))

        # Snapshot Retention Policy
        ctk.CTkLabel(self.snapshots_frame, text="Snapshot Retention Policy:").pack(anchor="w")
        self.keep_last_entry = ctk.CTkEntry(self.snapshots_frame, placeholder_text="3")
        self.keep_last_entry.insert(0, "3")
        self.keep_last_entry.pack(fill="x", pady=(0, 10))

        # Auto Snap Interval
        ctk.CTkLabel(self.snapshots_frame, text="Auto Snap Interval:").pack(anchor="w")
        self.auto_snap_entry = ctk.CTkEntry(self.snapshots_frame, placeholder_text="daily")
        self.auto_snap_entry.insert(0, "daily")
        self.auto_snap_entry.pack(fill="x", pady=(0, 20))

        # Buttons
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x")

        ctk.CTkButton(
            self.button_frame,
            text="Cancel",
            command=self.destroy,
            height=40
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        save_fg, save_hover = get_action_colors('success')
        ctk.CTkButton(
            self.button_frame,
            text="Save",
            command=self._save_config,
            height=40,
            fg_color=save_fg,
            hover_color=save_hover
        ).pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _toggle_lock_days(self):
        """Toggle visibility of lock days field based on switch state."""
        if self.object_lock_switch.get():
            # Show lock days field (between switch and buttons)
            self.lock_days_label.pack(anchor="w", pady=(10, 0), before=self.button_frame)
            self.lock_days_entry.pack(fill="x", pady=(0, 10), before=self.button_frame)
        else:
            # Hide lock days field
            self.lock_days_label.pack_forget()
            self.lock_days_entry.pack_forget()

    def _toggle_frames(self):
        """Toggle visibility of sync and snapshots frames based on checkboxes."""
        if self.sync_check.get():
            self.sync_frame.pack(fill="x", pady=(0, 20), before=self.button_frame)
        else:
            self.sync_frame.pack_forget()

        if self.snapshots_check.get():
            self.snapshots_frame.pack(fill="x", pady=(0, 20), before=self.button_frame)
        else:
            self.snapshots_frame.pack_forget()

    def _pre_fill_fields(self):
        """Pre-fill fields with existing configuration when in edit mode."""
        if not self.edit_mode:
            return

        storage = self.config._config.get("storage", {})
        snapshots = self.config._config.get("snapshots", {})
        security = self.config._config.get("security", {})

        # Set checkboxes based on existing configuration
        sync_configured = self.config.is_sync_configured()
        snapshots_configured = self.config.is_snapshots_configured()

        self.sync_check.select() if sync_configured else self.sync_check.deselect()
        self.snapshots_check.select() if snapshots_configured else self.snapshots_check.deselect()

        # Clear default values first
        self.access_key_entry.delete(0, "end")
        self.secret_key_entry.delete(0, "end")
        self.sync_bucket_entry.delete(0, "end")
        self.sync_region_entry.delete(0, "end")
        self.vault_bucket_entry.delete(0, "end")
        self.vault_region_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.keep_last_entry.delete(0, "end")
        self.auto_snap_entry.delete(0, "end")

        # Pre-fill common credentials
        self.access_key_entry.insert(0, storage.get("access_key", ""))
        self.secret_key_entry.insert(0, storage.get("secret_key", ""))

        # Pre-fill sync configuration
        if sync_configured:
            self.sync_bucket_entry.insert(0, storage.get("sync_bucket", ""))
            self.sync_region_entry.insert(0, storage.get("sync_region", "us-east-1"))

        # Pre-fill snapshots configuration
        if snapshots_configured:
            self.vault_bucket_entry.insert(0, storage.get("vault_bucket", ""))
            self.vault_region_entry.insert(0, storage.get("vault_region", "us-east-1"))
            self.password_entry.insert(0, security.get("encryption_password", ""))
            self.keep_last_entry.insert(0, str(snapshots.get("keep_last", 3)))
            self.auto_snap_entry.insert(0, snapshots.get("auto_snap_interval", "daily"))

        # Show frames based on checkboxes - force pack with correct order
        if sync_configured:
            self.sync_frame.pack(fill="x", pady=(0, 20), before=self.button_frame)
        if snapshots_configured:
            self.snapshots_frame.pack(fill="x", pady=(0, 20), before=self.button_frame)

    def _save_config(self):
        """Save configuration and initialize restic."""
        sync_enabled = self.sync_check.get()
        snapshots_enabled = self.snapshots_check.get()

        if not sync_enabled and not snapshots_enabled:
            from tkinter import messagebox
            messagebox.showerror("Error", "Please select at least one functionality")
            return

        access_key = self.access_key_entry.get().strip()
        secret_key = self.secret_key_entry.get().strip()

        # Validation for common credentials
        if not all([access_key, secret_key]):
            from tkinter import messagebox
            messagebox.showerror("Error", "Please fill in all Wasabi credentials")
            return

        # Sync configuration
        sync_bucket = ""
        sync_region = "us-east-1"
        if sync_enabled:
            sync_bucket = self.sync_bucket_entry.get().strip()
            sync_region = self.sync_region_entry.get().strip()
            if not sync_bucket:
                from tkinter import messagebox
                messagebox.showerror("Error", "Please fill in Sync Bucket Name")
                return
            if not sync_region:
                sync_region = "us-east-1"

        # Snapshots configuration
        vault_bucket = ""
        vault_region = "us-east-1"
        password = ""
        keep_last = 3
        auto_snap_interval = "daily"
        if snapshots_enabled:
            vault_bucket = self.vault_bucket_entry.get().strip()
            vault_region = self.vault_region_entry.get().strip()
            password = self.password_entry.get().strip()
            keep_last = self.keep_last_entry.get().strip()
            auto_snap_interval = self.auto_snap_entry.get().strip()

            if not all([vault_bucket, password]):
                from tkinter import messagebox
                messagebox.showerror("Error", "Please fill in Vault Bucket Name and Password")
                return
            if not vault_region:
                vault_region = "us-east-1"

            try:
                keep_last = int(keep_last)
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Error", "Keep last must be a number")
                return

            if auto_snap_interval not in ["daily", "weekly", "none"]:
                auto_snap_interval = "daily"

        # Save configuration
        self.config.set("storage.access_key", access_key)
        self.config.set("storage.secret_key", secret_key)

        if sync_enabled:
            self.config.set("storage.sync_bucket", sync_bucket)
            self.config.set("storage.sync_region", sync_region)

        if snapshots_enabled:
            self.config.set("storage.vault_bucket", vault_bucket)
            self.config.set("storage.vault_region", vault_region)
            self.config.set("snapshots.keep_last", keep_last)
            self.config.set("snapshots.auto_snap_interval", auto_snap_interval)
            self.config.set("security.encryption_password", password)

        self.config.save()

        # Initialize restic repository only in initial setup, not in edit mode
        if snapshots_enabled and not self.edit_mode:
            try:
                from ..core.restic_wrapper import ResticWrapper
                restic = ResticWrapper(self.config._config, output_callback=lambda x: None)
                success, msg = restic.init_repo()
                if not success:
                    from tkinter import messagebox
                    messagebox.showerror("Error", f"Failed to initialize restic: {msg}")
                    return
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error", f"Setup failed: {str(e)}")
                return

        from tkinter import messagebox
        messagebox.showinfo("Success", "Configuration saved successfully!")
        self.destroy()


class SnapshotsWindow(ctk.CTkToplevel):
    """Window for viewing and restoring snapshots."""

    def __init__(self, parent):
        """Initialize snapshots window.
        
        Args:
            parent: Parent window
        """
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.restic = ResticWrapper(self.config._config, output_callback=self._log_console)
        self.selected_snapshot = None
        self.snapshots = []

        self.title("Snapshots Viewer")
        self.geometry("700x500")
        self.transient(parent)

        # Ensure theme is set
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._create_widgets()
        self._load_snapshots()
        self.update()
        self.lift()
        try:
            self.grab_set()
        except:
            pass

    def _create_widgets(self):
        """Create snapshots viewer widgets."""
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        ctk.CTkLabel(
            self.main_frame,
            text="Snapshots",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(0, 20))

        # Host filter
        self.filter_frame = ctk.CTkFrame(self.main_frame)
        self.filter_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(self.filter_frame, text="Filter by device:").pack(side="left", padx=(10, 5))
        self.host_combobox = ctk.CTkComboBox(
            self.filter_frame,
            values=["All Devices"],
            command=self._filter_snapshots
        )
        self.host_combobox.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.host_combobox.set("All Devices")

        self.refresh_button = ctk.CTkButton(
            self.filter_frame,
            text="Refresh",
            command=self._load_snapshots,
            width=80
        )
        self.refresh_button.pack(side="right", padx=(0, 10))

        # Snapshots list
        self.snapshots_frame = ctk.CTkFrame(self.main_frame)
        self.snapshots_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.snapshots_listbox = ctk.CTkTextbox(self.snapshots_frame, height=250)
        self.snapshots_listbox.pack(fill="both", expand=True, padx=10, pady=10)

        # Action buttons
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x")

        restore_fg, restore_hover = get_action_colors('success')
        self.restore_button = ctk.CTkButton(
            self.button_frame,
            text="Restore Selected",
            command=self._restore_snapshot,
            height=40,
            fg_color=restore_fg,
            hover_color=restore_hover
        )
        self.restore_button.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.close_button = ctk.CTkButton(
            self.button_frame,
            text="Close",
            command=self.destroy,
            height=40
        )
        self.close_button.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _load_snapshots(self):
        """Load snapshots from restic."""
        hostname = get_hostname()
        
        # Load all devices for filter
        devices = self.config.get_all_devices()
        device_list = ["All Devices"] + list(devices.keys())
        self.host_combobox.configure(values=device_list)
        
        # Load snapshots
        success, snapshots = self.restic.list_snapshots()
        if success and snapshots:
            self.snapshots = snapshots
            self._display_snapshots()
        else:
            self.snapshots_listbox.delete("0.0", "end")
            self.snapshots_listbox.insert("end", "No snapshots found")

    def _filter_snapshots(self, choice):
        """Filter snapshots by hostname."""
        if choice == "All Devices":
            self._display_snapshots()
        else:
            filtered = [s for s in self.snapshots if s.get("hostname") == choice]
            self._display_snapshots(filtered)

    def _display_snapshots(self, snapshots=None):
        """Display snapshots in listbox.
        
        Args:
            snapshots: List of snapshots to display (default: all)
        """
        if snapshots is None:
            snapshots = self.snapshots
        
        self.snapshots_listbox.delete("0.0", "end")
        
        for snap in snapshots:
            snap_id = snap.get("id", "")
            time = snap.get("time", "")
            paths = snap.get("paths", [])
            hostname = snap.get("hostname", "unknown")
            
            self.snapshots_listbox.insert("end", f"ID: {snap_id}\n")
            self.snapshots_listbox.insert("end", f"  Time: {time}\n")
            self.snapshots_listbox.insert("end", f"  Device: {hostname}\n")
            self.snapshots_listbox.insert("end", f"  Paths: {', '.join(paths)}\n")
            self.snapshots_listbox.insert("end", "-" * 50 + "\n\n")

    def _log_console(self, line):
        """Add a line to the parent's console output (thread-safe).
        
        Args:
            line: Output line from command
        """
        if hasattr(self.parent, '_log_console'):
            # Schedule the update on the parent's main thread
            self.parent.after(0, self.parent._log_console, line)
    
    def _restore_snapshot(self):
        """Restore selected snapshot."""
        # Get selected text
        selected_text = self.snapshots_listbox.get("sel.first", "sel.last")
        if not selected_text:
            from tkinter import messagebox
            messagebox.showerror("Error", "Please select a snapshot to restore")
            return
        
        # Extract snapshot ID from selected text (format: "ID: abc123")
        for line in selected_text.split("\n"):
            if line.startswith("ID:"):
                snapshot_id = line.replace("ID:", "").strip()
                break
        else:
            from tkinter import messagebox
            messagebox.showerror("Error", "Could not extract snapshot ID")
            return
        
        # Ask for target directory
        from tkinter import filedialog, messagebox
        target_dir = filedialog.askdirectory(title="Select restore target directory")
        if not target_dir:
            return
        
        # Confirm restore
        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"Restore snapshot {snapshot_id} to {target_dir}?"
        )
        if not confirm:
            return
        
        # Show progress
        self.restore_button.configure(state="disabled", text="Restoring...")
        self.update()
        
        # Run restore in background thread
        import threading
        thread = threading.Thread(target=self._run_restore_thread, args=(snapshot_id, target_dir))
        thread.daemon = True
        thread.start()
    
    def _run_restore_thread(self, snapshot_id, target_dir):
        """Run restore in background thread."""
        # Perform restore
        success, msg = self.restic.restore(snapshot_id, target_dir)
        
        # Update UI from main thread
        self.after(0, lambda: self.restore_button.configure(state="normal", text="Restore Selected"))
        
        if success:
            from tkinter import messagebox
            self.after(0, lambda: messagebox.showinfo("Success", f"Snapshot restored to {target_dir}"))
        else:
            from tkinter import messagebox
            self.after(0, lambda: messagebox.showerror("Error", f"Restore failed: {msg}"))


def launch_gui():
    """Launch the GUI application with system tray icon."""
    import sys
    from .tray_icon import TrayIcon
    import pystray
    import threading
    
    # Global reference to keep window alive
    global _app_window
    _app_window = None
    
    # Create and show main window FIRST
    _app_window = MainWindow()
    
    # Start tray icon in background (daemon to not block mainloop)
    tray = TrayIcon()
    
    def hide_window():
        if _app_window:
            _app_window.withdraw()  # Hide window
        tray._update_icon()
    
    def toggle_window():
        global _app_window
        if _app_window:
            try:
                _app_window.deiconify()  # Show window
                _app_window.lift()  # Bring to front
            except:
                # Window was destroyed, create new one
                _app_window = MainWindow()
                _app_window.protocol("WM_DELETE_WINDOW", lambda: hide_window())
    
    # Set window close handler (X hides to tray; app keeps running)
    _app_window.protocol("WM_DELETE_WINDOW", lambda: hide_window())
    
    # Optional: start hidden in tray (e.g. autostart)
    if _app_window.config.get("ui.start_minimized", True):
        _app_window.after(300, hide_window)
    
    # Patch tray icon to use our toggle function
    original_on_clicked = tray._on_clicked
    def patched_on_clicked(icon, item):
        if item == "Open GUI":
            toggle_window()
        elif item == "Exit":
            _app_window.destroy()
            tray.stop()
        else:
            original_on_clicked(icon, item)
    
    tray._on_clicked = patched_on_clicked
    
    # Initialize tray icon
    status = tray._get_status()
    tray.icon = pystray.Icon(
        "memory-vault",
        tray._create_icon_image(status),
        "The Memory Vault",
        tray._menu()
    )
    
    # Start tray icon as daemon thread (won't block mainloop)
    def _run_tray():
        try:
            tray.icon.run()
        except Exception as exc:
            print(f"Warning: system tray unavailable ({exc})", file=sys.stderr)
    
    tray_thread = threading.Thread(target=_run_tray, daemon=True)
    tray_thread.start()
    
    # Run CustomTkinter mainloop
    _app_window.mainloop()
