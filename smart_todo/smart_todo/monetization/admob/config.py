"""
monetization/admob/config.py
AdMob configuration - the ONLY place ad unit / app IDs live.

Test and production IDs are kept in clearly separate constants so they can
never be accidentally mixed. Which set is active is controlled by a single
DEBUG flag, defaulting to test ads so a fresh checkout never accidentally
serves (or clicks) real ads during development.

IMPORTANT: the AdMob App ID also has to be duplicated into pyproject.toml
under [tool.flet.android.meta_data] - that's a build-time manifest entry
flet build reads literally, so it can't import this file. If you change
the App ID here for a production build, update pyproject.toml to match.
"""

from dataclasses import dataclass

# Flip this to False for a production/Play Store build. Nothing else in the
# app needs to change - every ad unit ID is looked up through get_config().
DEBUG = True


@dataclass(frozen=True)
class AdMobConfig:
    app_id: str
    banner_ad_unit_id: str
    interstitial_ad_unit_id: str


# Google's published demo/test ad units. Safe to use in any app during
# development - never associated with a real AdMob account, so there's no
# risk of generating invalid traffic.
#
# NOTE on the banner ID: flet-ads's own docs (flet.dev/docs/controls/ads)
# list two different Android test banner IDs in two different sections -
# "ca-app-pub-3940256099942544/9214589741" under "Test Values" (the
# authoritative reference table for this exact library) and the older,
# more widely-published "ca-app-pub-3940256099942544/6300978111" (used in
# Google's general AdMob test-ads docs and in flet-ads's own example code
# block) elsewhere on the same page. Both are genuine Google demo units;
# this uses the "Test Values" one since it's the section specifically
# curated as the current reference for flet-ads. If it ever stops
# serving test creatives, swap in the older ID above instead.
TEST_CONFIG = AdMobConfig(
    app_id="ca-app-pub-3940256099942544~3347511713",
    banner_ad_unit_id="ca-app-pub-3940256099942544/9214589741",
    interstitial_ad_unit_id="ca-app-pub-3940256099942544/1033173712",
)

# Fill these in with your real AdMob App ID and ad unit IDs from the AdMob
# console before a production build. Placeholders are intentionally
# obviously-fake so a production build never silently ships test ads (or
# real ads with malformed IDs).
PRODUCTION_CONFIG = AdMobConfig(
    app_id="ca-app-pub-REPLACE_ME~REPLACE_ME",
    banner_ad_unit_id="ca-app-pub-REPLACE_ME/REPLACE_ME",
    interstitial_ad_unit_id="ca-app-pub-REPLACE_ME/REPLACE_ME",
)


def get_config() -> AdMobConfig:
    """The active AdMob config for this build."""
    return TEST_CONFIG if DEBUG else PRODUCTION_CONFIG


def is_production_ready() -> bool:
    """False if DEBUG is off but the placeholder IDs were never filled in -
    lets the app refuse to ship a broken production build instead of
    silently requesting ads with a fake ID."""
    if DEBUG:
        return True
    cfg = get_config()
    return "REPLACE_ME" not in cfg.app_id and "REPLACE_ME" not in cfg.banner_ad_unit_id
