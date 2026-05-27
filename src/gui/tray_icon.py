"""System tray icon using pystray and Pillow."""

import pystray
from PIL import Image, ImageDraw
from threading import Thread
from typing import Optional

from ..utils.config import Config
from ..core.mount_manager import MountManager
from .theme import Theme


class TrayIcon:
    """System tray icon for The Memory Vault."""
    
    def __init__(self):
        """Initialize tray icon."""
        self.config = Config()
        self.mount_manager: Optional[MountManager] = None
        self.icon: Optional[pystray.Icon] = None
        self._running = False
    
    def _create_icon_image(self, status: str = "ok") -> Image.Image:
        """Create icon image with status color using theme colors.
        
        Args:
            status: Status color ('ok'=green, 'sync'=blue, 'error'=red)
        
        Returns:
            PIL Image
        """
        # Icon size
        size = 64
        
        # Create image
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Color based on status using theme colors
        colors = {
            "ok": self._hex_to_rgb(Theme.SUCCESS),
            "sync": self._hex_to_rgb(Theme.INFO),
            "error": self._hex_to_rgb(Theme.DANGER)
        }
        color = colors.get(status, colors["ok"])
        
        # Draw rounded vault icon
        padding = 12
        box_size = size - (padding * 2)
        radius = 8
        
        # Draw rounded rectangle (simulated with multiple rectangles)
        # Main body
        draw.rectangle(
            [padding + radius, padding, size - padding - radius, size - padding],
            fill=color,
            outline=None
        )
        draw.rectangle(
            [padding, padding + radius, size - padding, size - padding - radius],
            fill=color,
            outline=None
        )
        # Corners
        draw.ellipse(
            [padding, padding, padding + radius * 2, padding + radius * 2],
            fill=color
        )
        draw.ellipse(
            [size - padding - radius * 2, padding, size - padding, padding + radius * 2],
            fill=color
        )
        draw.ellipse(
            [padding, size - padding - radius * 2, padding + radius * 2, size - padding],
            fill=color
        )
        draw.ellipse(
            [size - padding - radius * 2, size - padding - radius * 2, size - padding, size - padding],
            fill=color
        )
        
        # Draw inner border
        border_width = 3
        inner_padding = padding + border_width
        inner_size = box_size - (border_width * 2)
        
        draw.rectangle(
            [inner_padding + radius, inner_padding, size - inner_padding - radius, size - inner_padding],
            outline=(255, 255, 255),
            width=2
        )
        draw.rectangle(
            [inner_padding, inner_padding + radius, size - inner_padding, size - inner_padding - radius],
            outline=(255, 255, 255),
            width=2
        )
        
        # Draw lock symbol (more refined)
        lock_x = size // 2
        lock_y = size // 2 + 2
        lock_width = 14
        lock_height = 12
        
        # Lock shackle (arc)
        shackle_radius = 8
        draw.arc(
            [lock_x - shackle_radius, lock_y - lock_height + 2,
             lock_x + shackle_radius, lock_y + 2],
            start=0,
            end=180,
            fill=(255, 255, 255),
            width=3
        )
        
        # Lock body (rounded rectangle)
        body_y = lock_y + 2
        body_radius = 3
        draw.rectangle(
            [lock_x - lock_width + body_radius, body_y,
             lock_x + lock_width - body_radius, body_y + lock_height],
            fill=(255, 255, 255)
        )
        draw.rectangle(
            [lock_x - lock_width, body_y + body_radius,
             lock_x + lock_width, body_y + lock_height - body_radius],
            fill=(255, 255, 255)
        )
        draw.ellipse(
            [lock_x - lock_width, body_y, lock_x - lock_width + body_radius * 2, body_y + body_radius * 2],
            fill=(255, 255, 255)
        )
        draw.ellipse(
            [lock_x + lock_width - body_radius * 2, body_y, lock_x + lock_width, body_y + body_radius * 2],
            fill=(255, 255, 255)
        )
        
        # Keyhole
        keyhole_x = lock_x
        keyhole_y = body_y + lock_height // 2 + 2
        keyhole_radius = 2
        draw.ellipse(
            [keyhole_x - keyhole_radius, keyhole_y - keyhole_radius,
             keyhole_x + keyhole_radius, keyhole_y + keyhole_radius],
            fill=color
        )
        draw.rectangle(
            [keyhole_x - 1, keyhole_y, keyhole_x + 1, body_y + lock_height - 2],
            fill=color
        )
        
        return image
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple.
        
        Args:
            hex_color: Hex color string (e.g., "#1a5fb4")
        
        Returns:
            RGB tuple (r, g, b)
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _get_status(self) -> str:
        """Get current vault status.
        
        Returns:
            Status string ('ok', 'sync', 'error')
        """
        if not self.config.is_configured():
            return "error"
        
        try:
            if self.mount_manager is None:
                self.mount_manager = MountManager(self.config._config)
            
            mount_status = self.mount_manager.get_mount_status()
            
            if mount_status["mounted"]:
                return "ok"
            else:
                return "error"
        except Exception:
            return "error"
    
    def _on_clicked(self, icon, item):
        """Handle menu item click."""
        from .main_window import launch_gui
        
        if item == "Open GUI":
            # Launch GUI in separate thread
            Thread(target=launch_gui, daemon=True).start()
        elif item == "Mount Vault":
            if self.mount_manager is None:
                self.mount_manager = MountManager(self.config._config)
            self.mount_manager.mount_with_retry()
            self._update_icon()
        elif item == "Unmount Vault":
            if self.mount_manager is None:
                self.mount_manager = MountManager(self.config._config)
            self.mount_manager.unmount()
            self._update_icon()
        elif item == "Exit":
            self.stop()
    
    def _update_icon(self):
        """Update icon based on current status."""
        if self.icon:
            status = self._get_status()
            self.icon.icon = self._create_icon_image(status)
    
    def _menu(self):
        """Create menu for tray icon."""
        return pystray.Menu(
            pystray.MenuItem("Open GUI", lambda icon, item: self._on_clicked(icon, "Open GUI")),
            pystray.MenuItem("Mount Vault", lambda icon, item: self._on_clicked(icon, "Mount Vault")),
            pystray.MenuItem("Unmount Vault", lambda icon, item: self._on_clicked(icon, "Unmount Vault")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda icon, item: self._on_clicked(icon, "Exit"))
        )
    
    def start(self):
        """Start tray icon."""
        if self._running:
            return
        
        self._running = True
        status = self._get_status()
        
        self.icon = pystray.Icon(
            "memory-vault",
            self._create_icon_image(status),
            "The Memory Vault",
            self._menu()
        )
        
        # Run in separate thread
        Thread(target=self.icon.run, daemon=True).start()
    
    def stop(self):
        """Stop tray icon."""
        if self.icon:
            self.icon.stop()
        self._running = False
    
    def set_status(self, status: str):
        """Set status and update icon.
        
        Args:
            status: Status string ('ok', 'sync', 'error')
        """
        if self.icon:
            self.icon.icon = self._create_icon_image(status)
