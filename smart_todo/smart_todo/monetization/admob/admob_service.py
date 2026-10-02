"""
monetization/admob/admob_service.py
Clean interface the Flet UI calls for AdMob banner ads. All flet_ads
implementation detail stays in this file - frontend/ never imports
flet_ads directly, only this service.

Built on the official flet-ads package (flet-dev/flet-ads), which wraps
Google's google_mobile_ads Flutter plugin - that's the real, currently
supported way to show native AdMob ads from a Flet app. See:
https://flet.dev/docs/controls/ads/
"""

import logging
from typing import Optional

import flet as ft

from monetization.admob.config import get_config

logger = logging.getLogger(__name__)

try:
    import flet_ads as fta

    _FLET_ADS_AVAILABLE = True
except ImportError:
    # flet-ads isn't installed, or we're running somewhere it doesn't ship
    # (desktop during development, an older Flet). AdMob is optional at
    # runtime - Smart Todo must never crash just because ads aren't
    # available, per the "do not crash" requirement.
    fta = None
    _FLET_ADS_AVAILABLE = False


class AdmobService:
    """Owns (at most) one banner ad and loads/shows/hides it safely.
    Never raises - a failed or unsupported ad request just means no
    banner is shown, and the rest of the app is unaffected."""

    def __init__(self, page: ft.Page):
        self._page = page
        self._config = get_config()
        self._banner: Optional["fta.BannerAd"] = None
        self._load_failed = False

    def is_supported(self) -> bool:
        """flet-ads only supports Android/iOS - never attempt to request
        an ad on desktop/web, where the control isn't available."""
        if not _FLET_ADS_AVAILABLE:
            return False
        platform = getattr(self._page, "platform", None)
        is_mobile = getattr(platform, "is_mobile", None)
        if not callable(is_mobile):
            return False
        try:
            return bool(is_mobile())
        except Exception:  # noqa: BLE001 - never let a platform check crash the app
            return False

    def should_show_ads(self, is_premium: bool) -> bool:
        return (not is_premium) and self.is_supported() and not self._load_failed

    def banner_control(self, is_premium: bool) -> Optional["fta.BannerAd"]:
        """A ready-to-display BannerAd control for a free user on a
        supported platform, or None if ads shouldn't show right now
        (premium, unsupported platform, flet-ads missing, or a previous
        load already failed this session)."""
        if not self.should_show_ads(is_premium):
            return None

        if self._banner is None:
            self._banner = fta.BannerAd(
                unit_id=self._config.banner_ad_unit_id,
                width=320,
                height=50,
                on_load=self._on_load,
                on_error=self._on_error,
            )
        return self._banner

    def _on_load(self, e) -> None:
        logger.info("AdMob banner loaded")

    def _on_error(self, e) -> None:
        # No internet, no fill, a misconfigured unit ID, etc. all land
        # here. Log it and move on: the caller's next banner_control()
        # call returns None instead of showing a broken/empty ad slot.
        # Deliberately does not retry automatically this session, to
        # avoid hammering a network that's already failing.
        logger.warning("AdMob banner failed to load: %s", getattr(e, "data", e))
        self._load_failed = True
