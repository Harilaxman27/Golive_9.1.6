#!/usr/bin/env python3
"""
Complete Environment Setup Script for GoLive Studio
This script will:
1. Create a virtual environment
2. Install all dependencies
3. Set up platform-specific requirements
4. Verify the installation
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
import venv

def print_step(message):
    print(f"\n{'='*80}\n{message}\n{'='*80}")

def run_command(cmd, check=True, shell=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=shell, check=check, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def create_venv():
    """Create a virtual environment"""
    print_step("Creating virtual environment...")
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists. Recreating...")
        shutil.rmtree(venv_path)
    
    venv.create(venv_path, with_pip=True)
    return venv_path

def get_python_executable():
    """Get the Python executable path in the virtual environment"""
    if platform.system() == "Windows":
        return Path("venv") / "Scripts" / "python.exe"
    return Path("venv") / "bin" / "python"

def install_dependencies(python_exec):
    """Install all required dependencies"""
    print_step("Installing dependencies...")
    
    # Upgrade pip first
    run_command(f'"{python_exec}" -m pip install --upgrade pip')
    
    # Install requirements
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False
    
    success, stdout, stderr = run_command(f'"{python_exec}" -m pip install -r "{requirements_file}"')
    if not success:
        print(f"❌ Failed to install dependencies:\n{stderr}")
        return False
    
    print("✅ Dependencies installed successfully")
    return True

def setup_platform_specific():
    """Setup platform-specific requirements"""
    system = platform.system()
    print_step(f"Setting up {system}-specific requirements...")
    
    if system == "Darwin":  # macOS
        # Check for Xcode Command Line Tools
        success, _, _ = run_command("xcode-select -p", check=False)
        if not success:
            print("Installing Xcode Command Line Tools...")
            run_command("xcode-select --install")
    
    elif system == "Windows":
        # Nothing specific needed for Windows at this point
        # PyWin32 is handled by requirements.txt
        pass

def verify_installation(python_exec):
    """Verify that all components are installed correctly"""
    print_step("Verifying installation...")
    
    # Try importing key dependencies
    test_imports = [
        "PyQt6",
        "cv2",
        "numpy",
        "av",
        "OpenGL",
        "psutil"
    ]
    
    for module in test_imports:
        cmd = f'"{python_exec}" -c "import {module}"'
        success, _, stderr = run_command(cmd, check=False)
        if success:
            print(f"✅ {module} successfully installed")
        else:
            print(f"❌ {module} failed: {stderr}")

def main():
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Create virtual environment
    venv_path = create_venv()
    python_exec = get_python_executable()
    
    # Ensure the virtual environment was created
    if not python_exec.exists():
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(python_exec):
        sys.exit(1)
    
    # Setup platform-specific requirements
    setup_platform_specific()
    
    # Verify installation
    verify_installation(python_exec)
    
    print_step("Setup Complete!")
    print("\nTo activate the virtual environment:")
    if platform.system() == "Windows":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("\nThen you can run the application:")
    print("   python main.py")

if __name__ == "__main__":
    main()