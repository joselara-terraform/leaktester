#!/usr/bin/env python3
"""
Test script to verify I2C access and device scanning.
Works on both development machines and Raspberry Pi.
"""

import sys
import platform
import subprocess

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

def test_i2c_access():
    """Test if I2C is enabled and can scan for devices."""
    print("=== I2C Access Test ===")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    
    # Check if we're on a Raspberry Pi
    is_pi = is_raspberry_pi()
    
    if not is_pi:
        print("⚠ Not on Raspberry Pi - I2C hardware tests will be skipped")
        print("  On Raspberry Pi, ensure I2C is enabled with:")
        print("  sudo raspi-config -> Interface Options -> I2C -> Enable")
        return True
    
    print("✓ Raspberry Pi detected - testing I2C hardware")
    
    try:
        # Test if i2cdetect command is available
        result = subprocess.run(['which', 'i2cdetect'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("✗ i2cdetect command not found")
            print("  Install with: sudo apt-get install i2c-tools")
            return False
        
        print("✓ i2cdetect command found")
        
        # Test I2C bus scan
        print("Scanning I2C bus 1...")
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ I2C bus 1 scan successful")
            print("I2C device scan results:")
            print(result.stdout)
            return True
        else:
            print(f"✗ I2C bus scan failed: {result.stderr}")
            print("  Ensure I2C is enabled: sudo raspi-config")
            return False
            
    except FileNotFoundError:
        print("✗ I2C tools not available")
        print("  Install with: sudo apt-get install i2c-tools")
        return False
    except Exception as e:
        print(f"✗ I2C test failed: {e}")
        return False

def test_i2c_python_access():
    """Test Python I2C library access."""
    print("\n=== Python I2C Library Test ===")
    
    try:
        # Test SMBus import (most common I2C library for Pi)
        import smbus2
        print("✓ smbus2 library available")
        
        # Test bus creation (will fail gracefully if no hardware)
        try:
            bus = smbus2.SMBus(1)
            print("✓ I2C bus 1 opened successfully")
            bus.close()
            print("✓ I2C bus closed properly")
        except Exception as e:
            print(f"⚠ Could not open I2C bus: {e}")
            print("  This is normal on non-Pi systems")
            
        return True
        
    except ImportError:
        print("✗ smbus2 library not found")
        print("  Install with: pip install smbus2")
        return False

if __name__ == "__main__":
    i2c_success = test_i2c_access()
    python_success = test_i2c_python_access()
    
    overall_success = i2c_success and python_success
    print(f"\n=== Overall I2C Test: {'PASSED' if overall_success else 'FAILED'} ===")
    
    sys.exit(0 if overall_success else 1) 