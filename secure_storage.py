#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoLive Studio - Secure Storage for Sensitive Data
Provides platform-specific secure storage for stream keys and passwords
"""

import sys
import base64
import json
from typing import Optional, Dict, Any
from pathlib import Path


class SecureStorage:
    """Platform-specific secure storage for sensitive data"""
    
    def __init__(self, service_name: str = "GoLive Studio"):
        """
        Initialize secure storage
        
        Args:
            service_name: Service name for keychain entries
        """
        self.service_name = service_name
        self._backend = self._init_backend()
    
    def _init_backend(self) -> str:
        """Determine which storage backend to use"""
        if sys.platform == 'darwin':
            try:
                import keyring
                return 'keyring'  # Use system keychain
            except ImportError:
                return 'encrypted'  # Fallback to encrypted file
        elif sys.platform.startswith('win'):
            try:
                import keyring
                return 'keyring'  # Use Windows Credential Manager
            except ImportError:
                return 'encrypted'
        else:  # Linux
            try:
                import keyring
                return 'keyring'  # Use Secret Service
            except ImportError:
                return 'encrypted'
    
    def store_stream_key(self, stream_id: str, url: str, key: str) -> bool:
        """
        Store stream URL and key securely
        
        Args:
            stream_id: Unique stream identifier (e.g., 'stream1', 'stream2')
            url: RTMP URL
            key: Stream key
            
        Returns:
            True if successful
        """
        try:
            # Combine URL and key for storage
            data = json.dumps({'url': url, 'key': key})
            
            if self._backend == 'keyring':
                import keyring
                keyring.set_password(self.service_name, f"stream_{stream_id}", data)
            else:
                self._store_encrypted(f"stream_{stream_id}", data)
            
            return True
        except Exception as e:
            print(f"Error storing stream key: {e}")
            return False
    
    def retrieve_stream_key(self, stream_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieve stream URL and key
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Dictionary with 'url' and 'key', or None if not found
        """
        try:
            if self._backend == 'keyring':
                import keyring
                data = keyring.get_password(self.service_name, f"stream_{stream_id}")
            else:
                data = self._retrieve_encrypted(f"stream_{stream_id}")
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error retrieving stream key: {e}")
            return None
    
    def delete_stream_key(self, stream_id: str) -> bool:
        """
        Delete stream credentials
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            True if successful
        """
        try:
            if self._backend == 'keyring':
                import keyring
                keyring.delete_password(self.service_name, f"stream_{stream_id}")
            else:
                self._delete_encrypted(f"stream_{stream_id}")
            return True
        except Exception as e:
            print(f"Error deleting stream key: {e}")
            return False
    
    def _get_encrypted_storage_path(self) -> Path:
        """Get path to encrypted storage file"""
        if sys.platform == 'darwin':
            base_dir = Path.home() / 'Library' / 'Application Support' / 'GoLive Studio'
        elif sys.platform.startswith('win'):
            import os
            base_dir = Path(os.environ.get('APPDATA', Path.home())) / 'GoLive Studio'
        else:
            base_dir = Path.home() / '.config' / 'golive-studio'
        
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / 'secure_storage.enc'
    
    def _get_encryption_key(self) -> bytes:
        """
        Get encryption key (derived from machine-specific data)
        
        Note: This is NOT cryptographically secure, just obfuscation.
        For true security, use system keychain via 'keyring' backend.
        """
        try:
            import hashlib
            import uuid
            
            # Use machine ID as key source
            machine_id = str(uuid.getnode())
            
            # Derive key
            key = hashlib.sha256(machine_id.encode()).digest()
            return key
        except Exception:
            # Fallback to static key (very insecure, but better than plaintext)
            return b'GoLiveStudioDefaultKey123456'
    
    def _encrypt_data(self, data: str) -> bytes:
        """Simple XOR encryption (obfuscation only)"""
        key = self._get_encryption_key()
        data_bytes = data.encode('utf-8')
        
        # XOR with repeating key
        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key[i % len(key)])
        
        return bytes(encrypted)
    
    def _decrypt_data(self, encrypted: bytes) -> str:
        """Simple XOR decryption"""
        key = self._get_encryption_key()
        
        # XOR with repeating key (XOR is reversible)
        decrypted = bytearray()
        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key[i % len(key)])
        
        return bytes(decrypted).decode('utf-8')
    
    def _store_encrypted(self, key: str, value: str) -> None:
        """Store encrypted data in file"""
        storage_path = self._get_encrypted_storage_path()
        
        # Load existing storage
        storage = {}
        if storage_path.exists():
            try:
                with open(storage_path, 'rb') as f:
                    encrypted = f.read()
                    if encrypted:
                        storage = json.loads(self._decrypt_data(encrypted))
            except Exception:
                pass
        
        # Add new entry
        storage[key] = value
        
        # Save encrypted
        data_json = json.dumps(storage)
        encrypted = self._encrypt_data(data_json)
        
        with open(storage_path, 'wb') as f:
            f.write(encrypted)
        
        # Set restrictive permissions
        try:
            storage_path.chmod(0o600)  # Owner read/write only
        except Exception:
            pass
    
    def _retrieve_encrypted(self, key: str) -> Optional[str]:
        """Retrieve encrypted data from file"""
        storage_path = self._get_encrypted_storage_path()
        
        if not storage_path.exists():
            return None
        
        try:
            with open(storage_path, 'rb') as f:
                encrypted = f.read()
                if not encrypted:
                    return None
                
                storage = json.loads(self._decrypt_data(encrypted))
                return storage.get(key)
        except Exception:
            return None
    
    def _delete_encrypted(self, key: str) -> None:
        """Delete encrypted data from file"""
        storage_path = self._get_encrypted_storage_path()
        
        if not storage_path.exists():
            return
        
        try:
            # Load existing
            with open(storage_path, 'rb') as f:
                encrypted = f.read()
                if not encrypted:
                    return
                storage = json.loads(self._decrypt_data(encrypted))
            
            # Remove key
            if key in storage:
                del storage[key]
            
            # Save back
            data_json = json.dumps(storage)
            encrypted = self._encrypt_data(data_json)
            
            with open(storage_path, 'wb') as f:
                f.write(encrypted)
        except Exception:
            pass
    
    def migrate_from_config(self, config: Dict[str, Any]) -> bool:
        """
        Migrate stream keys from old config.json to secure storage
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if migration successful
        """
        try:
            streaming_config = config.get('streaming', {})
            
            # Migrate stream 1
            if streaming_config.get('stream1_key'):
                self.store_stream_key(
                    'stream1',
                    streaming_config.get('stream1_url', ''),
                    streaming_config.get('stream1_key', '')
                )
            
            # Migrate stream 2
            if streaming_config.get('stream2_key'):
                self.store_stream_key(
                    'stream2',
                    streaming_config.get('stream2_url', ''),
                    streaming_config.get('stream2_key', '')
                )
            
            return True
        except Exception as e:
            print(f"Error migrating config: {e}")
            return False


# Global secure storage instance
_secure_storage: Optional[SecureStorage] = None


def get_secure_storage() -> SecureStorage:
    """Get or create global secure storage instance"""
    global _secure_storage
    if _secure_storage is None:
        _secure_storage = SecureStorage()
    return _secure_storage


def install_keyring_backend():
    """
    Install keyring library for platform-native secure storage
    
    Prints installation instructions for the user
    """
    print("\n" + "="*60)
    print("RECOMMENDED: Install 'keyring' for secure credential storage")
    print("="*60)
    print("\nFor maximum security, install the 'keyring' library:")
    print("\n  pip install keyring")
    print("\nThis will use:")
    print("  • macOS Keychain (macOS)")
    print("  • Windows Credential Manager (Windows)")
    print("  • Secret Service (Linux)")
    print("\nWithout 'keyring', credentials are encrypted but less secure.")
    print("="*60 + "\n")
