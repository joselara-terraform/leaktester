#!/usr/bin/env python3
"""
Test script to verify GPIO access and gpiozero functionality.
Works on both development machines (with mock) and Raspberry Pi.
"""

import sys
import platform

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    # Check for ARM architecture (armv7l, aarch64, etc.) 
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    
    # Check for Raspberry Pi specific strings in kernel release
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

def test_gpio_access():
    """Test if gpiozero can be imported and basic GPIO functionality works."""
    print("=== GPIO Access Test ===")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print(f"Python: {sys.version}")
    
    try:
        # Try importing gpiozero
        from gpiozero import LED, Device
        print("✓ gpiozero imported successfully")
        
        # Check if we're on a Pi or need to use mock
        if not is_raspberry_pi():
            print("⚠ Not on Raspberry Pi - using MockFactory for testing")
            from gpiozero.pins.mock import MockFactory
            Device.pin_factory = MockFactory()
        else:
            print("✓ Raspberry Pi detected - using real GPIO")
        
        # Test basic LED control (using GPIO 18 as example)
        led = LED(18)
        print("✓ LED object created on GPIO 18")
        
        # Test basic operations
        led.on()
        print("✓ LED turned on")
        
        led.off()
        print("✓ LED turned off")
        
        led.close()
        print("✓ LED object closed properly")
        
        print("✓ GPIO access test PASSED")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import gpiozero: {e}")
        print("  Install with: pip install gpiozero")
        return False
    except Exception as e:
        print(f"✗ GPIO test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_gpio_access()
    sys.exit(0 if success else 1) 