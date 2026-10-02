"""
ui/theme.py
-----------
Single source of truth for colors, spacing and shadows so every screen
looks consistent. All colors are plain hex strings so this works the
same regardless of which Flet color-constant API is installed.
"""

import flet as ft

# Brand palette - a deep indigo/violet gives a premium, trustworthy
# "finance app" feel without copying any existing khata app's branding.
PRIMARY = "#5B4FE9"
PRIMARY_DARK = "#4038B0"
PRIMARY_LIGHT = "#EDEBFF"

BG = "#F5F6FB"
SURFACE = "#FFFFFF"

TEXT_PRIMARY = "#1A1B25"
TEXT_SECONDARY = "#767A8C"
BORDER = "#E7E8F1"

# You Got / receivable-positive = green. You Gave / owed = red.
GREEN = "#1AA260"
GREEN_BG = "#E5F7EE"
RED = "#E4483F"
RED_BG = "#FDEAEA"
AMBER = "#F5A623"
AMBER_BG = "#FFF3E0"

WHATSAPP_GREEN = "#25D366"

RADIUS_SM = 10
RADIUS_MD = 16
RADIUS_LG = 22


def card_shadow() -> ft.BoxShadow:
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=18,
        color="#14000000",
        offset=ft.Offset(0, 6),
    )


def soft_shadow(hex_color: str, alpha_hex: str = "33") -> ft.BoxShadow:
    """A colored, slightly stronger shadow used under accent/gradient cards."""
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=24,
        color=f"#{alpha_hex}{hex_color.lstrip('#')}",
        offset=ft.Offset(0, 10),
    )
