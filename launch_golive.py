#!/usr/bin/env python3
"""
GoLive Studio - Production Launcher
Handles environment setup, error recovery, and graceful startup.
Usage: python launch_golive.py
"""
import sys
import os
import subprocess

def _looks_like_windows_path(path: str) -> bool:
    if not path:
        return False
    return (":" in path) or path.startswith("\\\\")

def _read_pyvenv_cfg(venv_root: str) -> dict:
    cfg_path = os.path.join(venv_root, "pyvenv.cfg")
    if not os.path.exists(cfg_path):
        return {}
    cfg = {}
    try:
        with open(cfg_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    except Exception:
        return {}
    return cfg

def _find_venv_python(script_dir: str):
    venv_root = os.path.join(script_dir, "venv_py312")
    if not os.path.isdir(venv_root):
        return None, "venv_py312 directory not found"

    # Common layouts
    candidates = [
        os.path.join(venv_root, "Scripts", "python.exe"),
        os.path.join(venv_root, "Scripts", "python"),
        os.path.join(venv_root, "bin", "python"),
        os.path.join(venv_root, "bin", "python3"),
        os.path.join(venv_root, "bin", "python3.12"),
    ]

    for c in candidates:
        if os.path.isfile(c):
            # On Windows, a non-.exe "python" is almost certainly a POSIX shim and won't run.
            if os.name == "nt" and not c.lower().endswith(".exe"):
                continue
            return c, None

    # If we have a pyvenv.cfg, sanity check if it looks like it was created on this OS.
    cfg = _read_pyvenv_cfg(venv_root)
    home = cfg.get("home", "")
    executable = cfg.get("executable", "")
    if os.name == "nt":
        if (home.startswith("/") or executable.startswith("/")) and not _looks_like_windows_path(home) and not _looks_like_windows_path(executable):
            return None, "venv_py312 appears to be a macOS/Linux venv (pyvenv.cfg points to /opt/...)"

    return None, "venv_py312 python executable not found"

def main():
    # Get project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("\n" + "="*75)
    print(" "*15 + "GoLive Studio - Streaming Application")
    print("="*75)
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Project Root: {script_dir}")
    print("="*75 + "\n")
    
    # Verify venv_py312 exists (optional) and locate its python
    venv_python, venv_error = _find_venv_python(script_dir)
    if venv_python:
        print("[OK] Python venv found")
        python_to_use = venv_python
    else:
        print("[WARN] venv_py312 not usable")
        if venv_error:
            print(f"Reason: {venv_error}")
        print("[WARN] Falling back to current Python interpreter")
        python_to_use = sys.executable

        print("\nTo (re)create a Windows venv, run:")
        print("  py -3.12 -m venv venv_py312")
        print("  .\\venv_py312\\Scripts\\python -m pip install --upgrade pip")
        print("  .\\venv_py312\\Scripts\\python -m pip install -r requirements.txt")

    print("[>>] Starting GoLive Studio application...\n")
    
    # Run main.py in the venv
    try:
        result = subprocess.run(
            [python_to_use, "main.py"],
            cwd=script_dir,
            capture_output=False
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\n[•] GoLive Studio closed by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
