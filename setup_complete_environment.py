#!/usr/bin/env python3
"""
Complete Environment Setup Script for GoLive Studio
This script will:
1. Create a virtual environment
2. Install all dependencies
3. Download and bundle FFmpeg
4. Set up platform-specific requirements
5. Create a standalone distributable package
"""

import os
import sys
import platform
import subprocess
import shutil
import venv
import urllib.request
import zipfile
import tarfile
import tempfile
from pathlib import Path
import json

class GoLiveEnvironmentSetup:
    def __init__(self):
        self.root_dir = Path(__file__).parent.absolute()
        self.venv_dir = self.root_dir / "venv"
        self.ffmpeg_dir = self.root_dir / "ffmpeg"
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"

    def print_step(self, message):
        print(f"\n{'='*80}\n{message}\n{'='*80}")

    def run_command(self, cmd, check=True, shell=True):
        try:
            result = subprocess.run(cmd, shell=shell, check=check, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr

    def create_venv(self):
        """Create a virtual environment"""
        self.print_step("Creating virtual environment...")
        
        if self.venv_dir.exists():
            print("Virtual environment already exists. Recreating...")
            shutil.rmtree(self.venv_dir)
        
        venv.create(self.venv_dir, with_pip=True)
        
        # Get the python executable path
        if self.is_windows:
            python_exec = self.venv_dir / "Scripts" / "python.exe"
        else:
            python_exec = self.venv_dir / "bin" / "python"
        
        return python_exec

    def setup_ffmpeg(self):
        """Download and setup FFmpeg"""
        self.print_step("Setting up FFmpeg...")
        
        self.ffmpeg_dir.mkdir(exist_ok=True)
        ffmpeg_exe = self.ffmpeg_dir / ('ffmpeg.exe' if self.is_windows else 'ffmpeg')
        
        if ffmpeg_exe.exists():
            print(f"FFmpeg already exists at {ffmpeg_exe}")
            return True

        try:
            if self.is_windows:
                url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
                self._download_ffmpeg_windows(url)
            elif self.is_macos:
                self._download_ffmpeg_macos()
            else:
                self._download_ffmpeg_linux()
            return True
        except Exception as e:
            print(f"Failed to download FFmpeg: {e}")
            return False

    def _download_ffmpeg_windows(self, url):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / 'ffmpeg.zip'
            
            print("Downloading FFmpeg...")
            urllib.request.urlretrieve(url, zip_path)
            
            print("Extracting FFmpeg...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            # Find and copy ffmpeg.exe
            for ffmpeg_exe in temp_path.rglob('ffmpeg.exe'):
                if 'bin' in str(ffmpeg_exe):
                    shutil.copy2(ffmpeg_exe, self.ffmpeg_dir / 'ffmpeg.exe')
                    break

    def _download_ffmpeg_macos(self):
        # Try to copy from Homebrew first
        homebrew_paths = [
            '/opt/homebrew/bin/ffmpeg',
            '/usr/local/bin/ffmpeg'
        ]
        
        for path in homebrew_paths:
            if os.path.exists(path):
                shutil.copy2(path, self.ffmpeg_dir / 'ffmpeg')
                os.chmod(self.ffmpeg_dir / 'ffmpeg', 0o755)
                print(f"Copied FFmpeg from {path}")
                return
                
        # If Homebrew version not found, download static build
        url = "https://evermeet.cx/ffmpeg/getrelease/zip"
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "ffmpeg.zip"
            print("Downloading FFmpeg...")
            urllib.request.urlretrieve(url, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.ffmpeg_dir)
            
            os.chmod(self.ffmpeg_dir / 'ffmpeg', 0o755)

    def _download_ffmpeg_linux(self):
        # Try to use system FFmpeg first
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
        if result.returncode == 0:
            ffmpeg_path = result.stdout.strip()
            shutil.copy2(ffmpeg_path, self.ffmpeg_dir / 'ffmpeg')
            os.chmod(self.ffmpeg_dir / 'ffmpeg', 0o755)
            print(f"Copied system FFmpeg from {ffmpeg_path}")
            return
            
        # Download static build if system version not available
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            archive_path = temp_path / "ffmpeg.tar.xz"
            
            print("Downloading FFmpeg...")
            urllib.request.urlretrieve(url, archive_path)
            
            print("Extracting FFmpeg...")
            with tarfile.open(archive_path) as tar:
                tar.extractall(temp_path)
            
            # Find and copy ffmpeg binary
            for ffmpeg_bin in temp_path.rglob('ffmpeg'):
                if ffmpeg_bin.is_file():
                    shutil.copy2(ffmpeg_bin, self.ffmpeg_dir / 'ffmpeg')
                    os.chmod(self.ffmpeg_dir / 'ffmpeg', 0o755)
                    break

    def install_dependencies(self, python_exec):
        """Install all required dependencies"""
        self.print_step("Installing dependencies...")
        
        # Upgrade pip first
        self.run_command(f'"{python_exec}" -m pip install --upgrade pip')
        
        # Install requirements
        success, stdout, stderr = self.run_command(
            f'"{python_exec}" -m pip install -r "{self.root_dir / "requirements.txt"}"'
        )
        
        if not success:
            print(f"Failed to install dependencies: {stderr}")
            return False
            
        print("Dependencies installed successfully")
        return True

    def verify_installation(self, python_exec):
        """Verify that all components are installed correctly"""
        self.print_step("Verifying installation...")
        
        # Core dependencies to test
        test_imports = [
            'PyQt6.QtCore',
            'PyQt6.QtWidgets',
            'PyQt6.QtMultimedia',
            'cv2',
            'numpy',
            'av',
            'PIL',
            'OpenGL.GL'
        ]
        
        all_success = True
        for module in test_imports:
            cmd = f'"{python_exec}" -c "import {module}"'
            success, _, stderr = self.run_command(cmd, check=False)
            if success:
                print(f"✅ {module} successfully installed")
            else:
                print(f"❌ {module} failed: {stderr}")
                all_success = False
        
        return all_success

    def create_activation_scripts(self):
        """Create convenient activation scripts"""
        self.print_step("Creating activation scripts...")
        
        if self.is_windows:
            # Windows activation script
            with open(self.root_dir / "activate.bat", "w") as f:
                f.write(f"@echo off\ncall {self.venv_dir}\\Scripts\\activate.bat\n")
        else:
            # Unix activation script
            with open(self.root_dir / "activate.sh", "w") as f:
                f.write(f"#!/bin/bash\nsource {self.venv_dir}/bin/activate\n")
            os.chmod(self.root_dir / "activate.sh", 0o755)

    def setup(self):
        """Run the complete setup process"""
        try:
            # Create virtual environment
            python_exec = self.create_venv()
            if not python_exec.exists():
                print("Failed to create virtual environment")
                return False

            # Install dependencies
            if not self.install_dependencies(python_exec):
                return False

            # Setup FFmpeg
            if not self.setup_ffmpeg():
                print("Warning: FFmpeg setup failed, some features may not work")

            # Verify installation
            if not self.verify_installation(python_exec):
                print("Warning: Some components failed verification")

            # Create activation scripts
            self.create_activation_scripts()

            self.print_step("Setup Complete!")
            print("\nTo activate the virtual environment:")
            if self.is_windows:
                print("   .\\activate.bat")
            else:
                print("   source ./activate.sh")
            
            print("\nThen you can run the application:")
            print("   python main.py")
            
            # Save environment info
            env_info = {
                "python_version": platform.python_version(),
                "platform": platform.system(),
                "ffmpeg_bundled": self.ffmpeg_dir.exists(),
                "venv_path": str(self.venv_dir),
                "setup_date": subprocess.check_output(["date"]).decode().strip()
            }
            
            with open(self.root_dir / "env_info.json", "w") as f:
                json.dump(env_info, f, indent=2)

            return True

        except Exception as e:
            print(f"Setup failed: {e}")
            return False

def main():
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    setup = GoLiveEnvironmentSetup()
    success = setup.setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()