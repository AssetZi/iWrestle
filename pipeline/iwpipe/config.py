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
DEFAULT_CONTACT_PHONE = os.getenv("DEFAULT_CONTACT_PHONE", "")
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "")

# --- Presentation ---------------------------------------------------------
# iWrestle/DesignSystem/Theme.swift
SLATE_800 = (0x2F, 0x36, 0x3D)
GOLD = (0xFB, 0xDB, 0xAC)
INK = (0x0A, 0x0B, 0x0C)
SLATE_200 = (0xAE, 0xB6, 0xBD)

EVENT_TZ = "America/New_York"
SCHEMA_VERSION = 1
