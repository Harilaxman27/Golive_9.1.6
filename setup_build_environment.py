#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Environment Setup for GoLive Studio
Prepares the development environment for building executables
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class BuildEnvironmentSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.is_windows = sys.platform.startswith('win')
        self.is_macos = sys.platform == 'darwin'
        self.is_linux = sys.platform.startswith('linux')
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        print("🐍 Checking Python version...")
        
        version = sys.version_info
        if version.major != 3 or version.minor < 8:
            print(f"❌ Python 3.8+ required, got {version.major}.{version.minor}")
            print("Please install Python 3.8 or higher from https://python.org")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    
    def check_virtual_environment(self):
        """Check if running in virtual environment"""
        print("🔍 Checking virtual environment...")
        
        in_venv = (
            hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        )
        
        if in_venv:
            print("✅ Running in virtual environment")
            return True
        else:
            print("⚠️  Not running in virtual environment")
            print("💡 It's recommended to use a virtual environment:")
            if self.is_windows:
                print("   python -m venv venv")
                print("   venv\\Scripts\\activate")
            else:
                print("   python3 -m venv venv")
                print("   source venv/bin/activate")
            
            response = input("Continue without virtual environment? (y/N): ")
            return response.lower() == 'y'
    
    def install_pip_dependencies(self):
        """Install Python dependencies"""
        print("📦 Installing Python dependencies...")
        
        requirements_file = self.project_root / 'requirements.txt'
        if not requirements_file.exists():
            print("❌ requirements.txt not found")
            return False
        
        try:
            # Upgrade pip first
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'
            ], check=True)
            
            # Install requirements
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
            ], check=True)
            
            print("✅ Python dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    def check_system_dependencies(self):
        """Check platform-specific system dependencies"""
        print("🔧 Checking system dependencies...")
        
        if self.is_macos:
            return self._check_macos_dependencies()
        elif self.is_windows:
            return self._check_windows_dependencies()
        else:
            return self._check_linux_dependencies()
    
    def _check_macos_dependencies(self):
        """Check macOS-specific dependencies"""
        dependencies = {
            'xcode-select': 'Xcode Command Line Tools (run: xcode-select --install)',
            'brew': 'Homebrew (install from https://brew.sh)',
        }
        
        missing = []
        
        # Check Xcode Command Line Tools
        try:
            subprocess.run(['xcode-select', '--print-path'], 
                         check=True, capture_output=True)
            print("✅ Xcode Command Line Tools installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append('xcode-select')
        
        # Check Homebrew (optional but recommended)
        if shutil.which('brew'):
            print("✅ Homebrew installed")
        else:
            print("⚠️  Homebrew not found (optional but recommended)")
        
        if missing:
            print("❌ Missing dependencies:")
            for dep in missing:
                print(f"   • {dependencies[dep]}")
            return False
        
        return True
    
    def _check_windows_dependencies(self):
        """Check Windows-specific dependencies"""
        print("✅ Windows dependencies check complete")
        
        # Check for Visual Studio Build Tools (optional)
        vs_paths = [
            "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools",
            "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools",
            "C:\\Program Files\\Microsoft Visual Studio\\2019\\Community",
            "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community",
        ]
        
        vs_found = any(Path(path).exists() for path in vs_paths)
        if vs_found:
            print("✅ Visual Studio Build Tools found")
        else:
            print("⚠️  Visual Studio Build Tools not found (may be needed for some packages)")
        
        return True
    
    def _check_linux_dependencies(self):
        """Check Linux-specific dependencies"""
        dependencies = ['gcc', 'g++', 'make', 'pkg-config']
        missing = []
        
        for dep in dependencies:
            if shutil.which(dep):
                print(f"✅ {dep} installed")
            else:
                missing.append(dep)
        
        if missing:
            print("❌ Missing dependencies:")
            print(f"   Install with: sudo apt-get install {' '.join(missing)}")
            return False
        
        return True
    
    def verify_installation(self):
        """Verify that all required modules can be imported"""
        print("🧪 Verifying installation...")
        
        test_imports = [
            ('PyQt6.QtCore', 'PyQt6 Core'),
            ('PyQt6.QtWidgets', 'PyQt6 Widgets'),
            ('PyQt6.QtGui', 'PyQt6 GUI'),
            ('PyQt6.QtMultimedia', 'PyQt6 Multimedia'),
            ('numpy', 'NumPy'),
            ('cv2', 'OpenCV'),
            ('PIL', 'Pillow'),
            ('av', 'PyAV'),
            ('OpenGL', 'PyOpenGL'),
            ('PyInstaller', 'PyInstaller'),
        ]
        
        # Platform-specific imports
        if self.is_macos:
            test_imports.extend([
                ('objc', 'PyObjC'),
                ('Foundation', 'Foundation framework'),
            ])
        elif self.is_windows:
            test_imports.extend([
                ('win32api', 'pywin32'),
            ])
        
        failed_imports = []
        
        for module, name in test_imports:
            try:
                __import__(module)
                print(f"✅ {name}")
            except ImportError as e:
                print(f"❌ {name}: {e}")
                failed_imports.append(name)
        
        if failed_imports:
            print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
            return False
        
        print("✅ All modules imported successfully")
        return True
    
    def create_build_info(self):
        """Create build information file"""
        print("📝 Creating build information...")
        
        build_info = {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'build_ready': True,
        }
        
        import json
        with open(self.project_root / 'build_info.json', 'w') as f:
            json.dump(build_info, f, indent=2)
        
        print("✅ Build information created")
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\n" + "="*60)
        print("🎉 BUILD ENVIRONMENT SETUP COMPLETE!")
        print("="*60)
        print("\n💡 Next steps:")
        
        if self.is_windows:
            print("   1. Run: build_windows.bat")
            print("   2. Or run: python build_complete.py")
        elif self.is_macos:
            print("   1. Run: ./build_macos.sh")
            print("   2. Or run: python3 build_complete.py")
        else:
            print("   1. Run: python3 build_complete.py")
        
        print("\n📁 This will create:")
        if self.is_windows:
            print("   • dist/GoLive Studio/ (executable folder)")
            print("   • GoLive Studio Installer.exe (if NSIS is installed)")
        elif self.is_macos:
            print("   • dist/GoLive Studio.app (app bundle)")
            print("   • dist/GoLive Studio.dmg (DMG installer)")
        
        print("="*60)
    
    def setup(self):
        """Run the complete setup process"""
        print("🚀 Setting up GoLive Studio build environment...")
        print(f"🖥️  Platform: {platform.system()} {platform.machine()}")
        print()
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Checking virtual environment", self.check_virtual_environment),
            ("Installing Python dependencies", self.install_pip_dependencies),
            ("Checking system dependencies", self.check_system_dependencies),
            ("Verifying installation", self.verify_installation),
            ("Creating build info", self.create_build_info),
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"\n❌ Setup failed at: {step_name}")
                print("Please fix the issues above and run this script again.")
                sys.exit(1)
        
        self.print_next_steps()

def main():
    """Main entry point"""
    setup = BuildEnvironmentSetup()
    setup.setup()

if __name__ == '__main__':
    main()