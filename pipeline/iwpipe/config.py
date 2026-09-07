"""Shared constants and .env loading.

Values that must agree with the Swift app are named here once so the two
cannot drift silently.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_ROOT.parent
DATA_DIR = PIPELINE_ROOT / "data"
ASSET_DIR = DATA_DIR / "assets"
FIXTURE_DIR = PIPELINE_ROOT / "fixtures"
LEDGER_PATH = DATA_DIR / "pushed.json"
GEOCACHE_PATH = DATA_DIR / "geocache.json"

load_dotenv(PIPELINE_ROOT / ".env")

# --- CloudKit -------------------------------------------------------------
TEAM_ID = "RLZG42V7Y4"
CONTAINER_ID = "iCloud.zacherlInvestmentsLLC.iWrestle"
RECORD_TYPE = "Event"
DATABASE_TYPE = "public"

# iWrestle/Models/Constants.swift
ADMIN_RECORD_NAME = os.getenv(
    "ADMIN_RECORD_NAME", "_992916714084805f440379cb506634d2"
)

# --- Defaults for fields the app requires but sources often omit ----------
DEFAULT_CONTACT_EMAIL = os.getenv("DEFAULT_CONTACT_EMAIL", "")
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "")

# --- AI enrichment ----------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ENRICH_MODEL = "claude-opus-5"
ENRICH_CACHE_PATH = DATA_DIR / "enrich-cache.json"
BANNER_MAX_BYTES = 5 * 1024 * 1024

# --- CloudKit Web Services (server-to-server) -------------------------------
# A key that never expires, unlike cktool's browser-session token. Set
# CLOUDKIT_KEY_ID in .env and the pipeline writes through the REST API;
# leave it empty and it falls back to cktool.
CLOUDKIT_KEY_ID = os.getenv("CLOUDKIT_KEY_ID", "")
CLOUDKIT_KEY_PATH = PIPELINE_ROOT / "secrets" / "cloudkit-s2s.pem"

# --- Presentation ---------------------------------------------------------
# iWrestle/DesignSystem/Theme.swift
SLATE_800 = (0x2F, 0x36, 0x3D)
GOLD = (0xFB, 0xDB, 0xAC)
INK = (0x0A, 0x0B, 0x0C)
SLATE_200 = (0xAE, 0xB6, 0xBD)

EVENT_TZ = "America/New_York"

# Directory scope: every event the sources list, this far ahead.
MONTHS_AHEAD = 12
# College opens are not youth wrestling; they are classified as "Open" and
# skipped unless this is true.
INCLUDE_COLLEGE = os.getenv("INCLUDE_COLLEGE", "").lower() in ("1", "true", "yes")
SCHEMA_VERSION = 1
