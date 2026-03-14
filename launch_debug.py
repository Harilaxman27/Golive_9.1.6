#!/usr/bin/env python3
"""Debug launcher for GoLive Studio - catches and prints all startup errors."""

import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70, flush=True)
print(f"Starting GoLive Studio (Python {sys.version})", flush=True)
print("=" * 70, flush=True)

try:
    print("[1] Importing main...", flush=True)
    import main
    print("[2] main imported successfully", flush=True)
    
except Exception as e:
    print(f"[ERROR] Import failed: {e}", flush=True)
    print(traceback.format_exc(), flush=True)
    sys.exit(1)

print("[3] Done.", flush=True)
