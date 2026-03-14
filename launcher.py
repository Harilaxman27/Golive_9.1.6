#!/usr/bin/env python3
"""
Minimal launcher for GoLive Studio that provides detailed error diagnostics.
"""
import sys
import os
import subprocess
import json

# Get the project root
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Run main.py in a subprocess with Python's verbose import tracing
print("\n" + "="*70)
print("GOL IVE STUDIO LAUNCHER")
print("="*70)
print(f"Python: {sys.version}")
print(f"Working Dir: {os.getcwd()}")
print("="*70 + "\n")

# Try to run it directly first
print("[LAUNCHER] Attempting to run main.py directly...\n")
try:
    import main
    print("[LAUNCHER] main.py imported successfully (should not reach here)")
except SystemExit as e:
    print(f"[LAUNCHER] SystemExit({e.code})")
    sys.exit(e.code if e.code else 0)
except Exception as e:
    print(f"[LAUNCHER] ERROR during import: {type(e).__name__}: {e}")
    import traceback
    print("\nFull traceback:")
    print(traceback.format_exc())
    sys.exit(1)
