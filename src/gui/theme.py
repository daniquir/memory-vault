"""Theme and color system for The Memory Vault GUI."""

from typing import Dict, Tuple


class Theme:
    """Centralized theme and color palette for consistent UI design."""
    
    # Color palette - using semantic names instead of hardcoded colors
    PRIMARY = "#1a5fb4"          # Blue for primary actions
    PRIMARY_HOVER = "#164fa0"    # Darker blue for hover
    
    SUCCESS = "#26a269"          # Green for success states
    SUCCESS_HOVER = "#1e8b5a"    # Darker green for hover
    
    WARNING = "#e66100"          # Orange for warnings
    WARNING_HOVER = "#c45200"    # Darker orange for hover
    
    DANGER = "#c01c28"           # Red for destructive actions
    DANGER_HOVER = "#a01822"     # Darker red for hover
    
    INFO = "#3584e4"             # Blue for info
    INFO_HOVER = "#2a6ec4"       # Darker blue for hover
    
    NEUTRAL = "#6c6c6c"          # Gray for neutral actions
    NEUTRAL_HOVER = "#5a5a5a"    # Darker gray for hover
    
    SPECIAL = "#9141ac"          # Purple for special actions
    SPECIAL_HOVER = "#7a3591"    # Darker purple for hover
    
    # Text colors
    TEXT_DANGER = "#c01c28"      # Red for error text
    TEXT_NEUTRAL = "#6c6c6c"     # Gray for neutral text
    
    # Spacing constants
    PADDING_SMALL = 5
    PADDING_MEDIUM = 10
    PADDING_LARGE = 20
    PADDING_XLARGE = 30
    
    # Font sizes
    FONT_SIZE_SMALL = 12
    FONT_SIZE_MEDIUM = 14
    FONT_SIZE_LARGE = 16
    FONT_SIZE_XLARGE = 20
    FONT_SIZE_XXLARGE = 24
    
    # Button heights
    BUTTON_HEIGHT_SMALL = 30
    BUTTON_HEIGHT_MEDIUM = 40
    BUTTON_HEIGHT_LARGE = 50


def get_action_colors(action_type: str) -> Tuple[str, str]:
    """Get foreground and hover colors for action type.
    
    Args:
        action_type: Type of action ('primary', 'success', 'warning', 
                    'danger', 'info', 'neutral', 'special')
    
    Returns:
        Tuple of (fg_color, hover_color)
    """
    colors_map: Dict[str, Tuple[str, str]] = {
        'primary': (Theme.PRIMARY, Theme.PRIMARY_HOVER),
        'success': (Theme.SUCCESS, Theme.SUCCESS_HOVER),
        'warning': (Theme.WARNING, Theme.WARNING_HOVER),
        'danger': (Theme.DANGER, Theme.DANGER_HOVER),
        'info': (Theme.INFO, Theme.INFO_HOVER),
        'neutral': (Theme.NEUTRAL, Theme.NEUTRAL_HOVER),
        'special': (Theme.SPECIAL, Theme.SPECIAL_HOVER),
    }
    
    return colors_map.get(action_type, (Theme.PRIMARY, Theme.PRIMARY_HOVER))


def get_text_color(text_type: str) -> str:
    """Get text color for text type.
    
    Args:
        text_type: Type of text ('danger', 'neutral', 'default')
    
    Returns:
        Text color hex code
    """
    colors_map: Dict[str, str] = {
        'danger': Theme.TEXT_DANGER,
        'neutral': Theme.TEXT_NEUTRAL,
        'default': Theme.PRIMARY,
    }
    
    return colors_map.get(text_type, Theme.PRIMARY)
