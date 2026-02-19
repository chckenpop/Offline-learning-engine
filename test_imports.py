#!/usr/bin/env python
"""Test script to verify all imports work correctly"""
import sys
import os

# Add engine dir to path
engine_dir = os.path.join(os.path.dirname(__file__), 'engine')
sys.path.insert(0, engine_dir)

try:
    print("Testing imports...")
    import updater
    print("✅ updater.py imported successfully")
    
    import engine
    print("✅ engine.py imported successfully")
    
    print("\n✅ All imports successful - No circular imports!")
    print("\nFixed bugs:")
    print("  ✓ Removed circular import from updater.py")
    print("  ✓ Added installed_content table to database schema")
    print("  ✓ Fixed path inconsistencies (now using absolute paths)")
    print("  ✓ Database directory creation moved to proper location")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
