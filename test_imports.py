#!/usr/bin/env python3
"""
Import Diagnostic Test

Test imports to troubleshoot module loading issues.
"""

import sys
import os

print("=== Import Diagnostic Test ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")
print()

# Check directory structure
print("Directory contents:")
for item in os.listdir('.'):
    if os.path.isdir(item):
        print(f"  📁 {item}/")
        if item == 'controllers':
            print(f"     Controllers contents:")
            try:
                for subitem in os.listdir(item):
                    print(f"       📄 {subitem}")
            except:
                print(f"       ❌ Cannot read controllers directory")
    else:
        print(f"  📄 {item}")

print()

# Test individual imports
test_imports = [
    "controllers.adc_reader",
    "controllers.pressure_calibration", 
    "controllers.relay_controller",
    "config.config_manager"
]

for module_name in test_imports:
    try:
        print(f"Testing import: {module_name}")
        
        if module_name == "controllers.adc_reader":
            from controllers.adc_reader import ADCReader
            print(f"  ✅ Successfully imported ADCReader")
        elif module_name == "controllers.pressure_calibration":
            from controllers.pressure_calibration import PressureCalibration
            print(f"  ✅ Successfully imported PressureCalibration")
        elif module_name == "controllers.relay_controller":
            from controllers.relay_controller import RelayController
            print(f"  ✅ Successfully imported RelayController")
        elif module_name == "config.config_manager":
            from config.config_manager import get_config_manager
            print(f"  ✅ Successfully imported get_config_manager")
            
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
    except Exception as e:
        print(f"  ⚠️  Other error: {e}")

print()

# Check for __init__.py files
print("Checking for __init__.py files:")
for directory in ['controllers', 'config', 'services', 'ui']:
    if os.path.exists(directory):
        init_file = os.path.join(directory, '__init__.py')
        if os.path.exists(init_file):
            print(f"  ✅ {directory}/__init__.py exists")
        else:
            print(f"  ❌ {directory}/__init__.py missing")
            # Create missing __init__.py
            try:
                with open(init_file, 'w') as f:
                    f.write('# Package init file\n')
                print(f"     ✨ Created {init_file}")
            except Exception as e:
                print(f"     ❌ Failed to create {init_file}: {e}")
    else:
        print(f"  ❌ {directory}/ directory not found")

print()
print("=== Diagnostic Complete ===")
print("If imports are still failing, run this script to see the issue.") 