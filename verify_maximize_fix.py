#!/usr/bin/env python3
"""
Quick verification script to test the maximize layout fixes.
Run this after applying the maximize layout fixes to verify they work.
"""

import sys
import os

def verify_fixes():
    """Verify that the maximize layout fixes are in place"""
    main_py_path = os.path.join(os.path.dirname(__file__), 'main.py')
    
    if not os.path.exists(main_py_path):
        print("❌ ERROR: main.py not found")
        return False
    
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        {
            'name': 'Duplicate workspace_stack add removed',
            'pattern': 'NOTE: Do NOT add workspace_stack here',
            'description': 'Fixes layout stretch ratio breaking on maximize'
        },
        {
            'name': 'AspectRatioFrame 0.92 Windows safety multiplier',
            'pattern': 'return int(calculated * 0.92)',
            'description': 'Prevents bottom clipping after layout fix'
        },
        {
            'name': 'Inputs grid row stretch settings',
            'pattern': 'inputs_grid.setRowStretch(row, 0)',
            'description': 'Prevents input cards from overlapping'
        },
        {
            'name': 'Media grid row stretch settings',
            'pattern': 'media_grid.setRowStretch(row, 0)',
            'description': 'Prevents media cards from overlapping'
        },
        {
            'name': 'AspectRatioFrame clip region in paintEvent',
            'pattern': "painter.setClipRect(self.rect())",
            'description': 'Provides safety boundary for overlay graphics'
        }
    ]
    
    all_passed = True
    print("\n" + "="*70)
    print("MAXIMIZE LAYOUT FIX VERIFICATION")
    print("="*70 + "\n")
    
    for check in checks:
        has_pattern = check['pattern'] in content
        should_not_have = check.get('should_not_contain', '')
        has_bad_pattern = should_not_have and should_not_have in content
        
        if has_pattern and not has_bad_pattern:
            print(f"✅ {check['name']}")
            if 'description' in check:
                print(f"   └─ {check['description']}")
        else:
            print(f"❌ {check['name']}")
            if not has_pattern:
                print(f"   └─ Missing: {check['pattern']}")
            if has_bad_pattern:
                print(f"   └─ Still contains: {should_not_have}")
            all_passed = False
        print()
    
    print("="*70)
    
    if all_passed:
        print("\n✅ ALL FIXES VERIFIED!\n")
        print("Next steps:")
        print("1. Launch GoLive Studio: python main.py")
        print("2. Test with window NOT maximized - verify overlay looks complete")
        print("3. Click maximize button (□) - verify:")
        print("   • Grass/flowers overlay visible at bottom")
        print("   • All monitor area shows without clipping")
        print("   • Input/Media/Effects cards don't overlap")
        print("4. Restore window - verify everything looks normal")
        print("5. Resize window - verify layout stays neat\n")
    else:
        print("\n❌ SOME FIXES NOT FOUND\n")
        print("Please ensure the fixes from MAXIMIZE_LAYOUT_FIX.md were applied.\n")
    
    return all_passed

if __name__ == '__main__':
    success = verify_fixes()
    sys.exit(0 if success else 1)
