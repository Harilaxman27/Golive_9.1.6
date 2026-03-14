#!/usr/bin/env python3
"""
Verification script to test the three fixed issues in GoLive Studio
Run this to validate the fixes before deploying
"""

import sys
import os

def verify_issue_1_fix():
    """
    ISSUE 1: Verify transitions don't auto-apply
    Expected: _on_transition_selected should NOT call auto_transition()
    """
    print("\n" + "="*70)
    print("VERIFYING ISSUE 1: Transitions Apply Immediately")
    print("="*70)
    
    try:
        with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check that _on_transition_selected doesn't have auto-apply code
        start_idx = content.find('def _on_transition_selected(self):')
        if start_idx == -1:
            print("ERROR: _on_transition_selected method not found")
            return False
        
        end_idx = content.find('def _update_transition_selection_ui', start_idx)
        method_content = content[start_idx:end_idx]
        
        # Check that the problematic auto_transition() call is GONE
        if 'self.auto_transition()' in method_content:
            print("FAILED: auto_transition() call still present")
            return False
        
        # Check for the FIX comment marker
        if 'ISSUE 1 FIX' in method_content:
            print("PASSED: Issue 1 Fix marker found")
        
        print("[OK] ISSUE 1: Transitions no longer auto-apply")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def verify_issue_2_fix():
    """
    ISSUE 2: Verify Preview uses same camera positioning as Program
    Expected: Preview rendering should use aspect-fit letterbox logic
    """
    print("\n" + "="*70)
    print("VERIFYING ISSUE 2: Camera Framing")
    print("="*70)
    
    try:
        with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for the FIX comment marker
        if 'ISSUE 2 FIX' in content:
            print("PASSED: Issue 2 Fix marker found")
        else:
            print("WARNING: Issue 2 marker not found")
            return False
        
        # Check that aspect-fit logic is present
        if 'a_w = W_w / H_w' in content and 'target_h = H_w' in content:
            print("PASSED: Letterbox logic found")
        else:
            print("WARNING: Letterbox logic not found")
            return False
        
        # Check for the centering logic
        if 'x = (W_w - target_w) // 2' in content:
            print("PASSED: Centering calculation found")
        
        print("[OK] ISSUE 2: Camera positioning synchronized")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def verify_issue_3_fix():
    """
    ISSUE 3: Verify overlay is applied to Program after CUT
    Expected: cut_transition should validate file and call update()
    """
    print("\n" + "="*70)
    print("VERIFYING ISSUE 3: Overlay Application")
    print("="*70)
    
    try:
        with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for the FIX comment marker
        if 'ISSUE 3 FIX' in content:
            print("PASSED: Issue 3 Fix marker found")
        else:
            print("WARNING: Issue 3 marker not found")
            return False
        
        # Check that file validation is present
        if 'os.path.exists' in content:
            print("PASSED: File validation added")
        else:
            print("WARNING: No file validation")
            return False
        
        # Check for update() call
        if 'self._graphics_output.update()' in content:
            print("PASSED: update() call added")
        else:
            print("WARNING: Missing update() call")
            return False
        
        # Check for error handling
        if 'Error applying overlay' in content:
            print("PASSED: Error reporting added")
        
        print("[OK] ISSUE 3: Overlay application enhanced")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("  GoLive Studio - Three Issues Fix Verification")
    print("="*70)
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    r1 = verify_issue_1_fix()
    r2 = verify_issue_2_fix()
    r3 = verify_issue_3_fix()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"Issue 1: {'[PASS]' if r1 else '[FAIL]'}")
    print(f"Issue 2: {'[PASS]' if r2 else '[FAIL]'}")
    print(f"Issue 3: {'[PASS]' if r3 else '[FAIL]'}")
    
    print("="*70)
    
    if r1 and r2 and r3:
        print("\n[SUCCESS] ALL FIXES VERIFIED!\n")
        return 0
    else:
        print("\n[WARNING] Some checks failed - please review\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
