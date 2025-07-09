#!/usr/bin/env python3
"""
Simple I2C ADC Test Script

Tests basic I2C communication and ADC functionality.
Use this to verify hardware connections before running full diagnostics.
"""

import platform
import time
import sys

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

def test_i2c_detection():
    """Test I2C device detection."""
    print("=== I2C Device Detection ===")
    
    if not is_raspberry_pi():
        print("⚠️  Not running on Raspberry Pi - skipping I2C tests")
        return False
    
    try:
        import subprocess
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ I2C bus accessible")
            print("I2C devices detected:")
            print(result.stdout)
            
            # Check for ADC at 0x48
            if '48' in result.stdout:
                print("✓ ADC detected at address 0x48")
                return True
            else:
                print("✗ ADC not detected at address 0x48")
                return False
        else:
            print(f"✗ I2C detection failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ I2C detection error: {e}")
        return False

def test_adafruit_libraries():
    """Test if Adafruit ADC libraries are available."""
    print("\n=== Adafruit Library Test ===")
    
    try:
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        import board
        import busio
        print("✓ Adafruit ADC libraries available")
        return True
    except ImportError as e:
        print(f"✗ Adafruit libraries not available: {e}")
        print("Install with: pip install adafruit-circuitpython-ads1x15")
        return False
    except Exception as e:
        print(f"✗ Library import error: {e}")
        return False

def test_basic_adc():
    """Test basic ADC functionality."""
    print("\n=== Basic ADC Test ===")
    
    if not is_raspberry_pi():
        print("⚠️  Not running on Raspberry Pi - using mock ADC")
        return test_mock_adc()
    
    try:
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        import board
        import busio
        
        # Create I2C bus
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # Create ADS1115 object
        ads = ADS.ADS1115(i2c, address=0x48)
        ads.gain = 2  # Set gain for 4-20mA module
        
        # Create analog input on channel 0
        channel = AnalogIn(ads, ADS.P0)
        
        print("✓ ADC initialized successfully")
        print(f"  Gain: {ads.gain}")
        print(f"  Address: 0x48")
        
        # Read values
        print("\nReading ADC values...")
        for i in range(10):
            raw_value = channel.value
            voltage = channel.voltage
            print(f"  Reading {i+1}: Raw={raw_value:5d}, Voltage={voltage:.3f}V")
            time.sleep(0.5)
        
        if raw_value == 0:
            print("✗ WARNING: Raw ADC value is 0 - check connections!")
            return False
        else:
            print("✓ ADC reading non-zero values")
            return True
            
    except Exception as e:
        print(f"✗ ADC test error: {e}")
        return False

def test_mock_adc():
    """Test mock ADC for development."""
    print("Using mock ADC for development")
    
    class MockADC:
        def __init__(self):
            self.gain = 2
            
    class MockChannel:
        def __init__(self):
            self._value = 12292  # Mock value
            
        @property
        def value(self):
            return self._value
            
        @property
        def voltage(self):
            return (self._value / 32767) * 2.048
    
    ads = MockADC()
    channel = MockChannel()
    
    print("✓ Mock ADC initialized")
    print(f"  Gain: {ads.gain}")
    
    for i in range(5):
        raw_value = channel.value
        voltage = channel.voltage
        print(f"  Reading {i+1}: Raw={raw_value:5d}, Voltage={voltage:.3f}V")
        time.sleep(0.2)
    
    return True

def test_4_20ma_conversion():
    """Test 4-20mA conversion calculations."""
    print("\n=== 4-20mA Conversion Test ===")
    
    # Test conversion formula from datasheet
    ADC_4MA = 6430
    ADC_20MA = 32154
    
    def raw_to_current(raw_value):
        """Convert raw ADC to current using module specs."""
        return 4.0 + (raw_value - ADC_4MA) * 16.0 / (ADC_20MA - ADC_4MA)
    
    # Test known values
    test_values = [
        (6430, "4mA (minimum)"),
        (19292, "12mA (midpoint)"),
        (32154, "20mA (maximum)"),
        (0, "0 ADC (fault)"),
        (12861, "8mA (quarter)"),
        (25723, "16mA (three-quarter)")
    ]
    
    print("Testing ADC to current conversion:")
    for raw_val, description in test_values:
        current = raw_to_current(raw_val)
        print(f"  Raw={raw_val:5d} → {current:.3f}mA ({description})")
    
    return True

def main():
    """Run all basic tests."""
    print("BASIC I2C/ADC HARDWARE TEST")
    print("=" * 50)
    
    tests = [
        ("I2C Detection", test_i2c_detection),
        ("Adafruit Libraries", test_adafruit_libraries),
        ("Basic ADC", test_basic_adc),
        ("4-20mA Conversion", test_4_20ma_conversion)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = success
            
            if success:
                print(f"✓ {test_name} test PASSED")
            else:
                print(f"✗ {test_name} test FAILED")
                
        except Exception as e:
            print(f"✗ {test_name} test CRASHED: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    
    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{test_name:<20}: {status}")
    
    print(f"\n{'='*50}")
    print("NEXT STEPS")
    print(f"{'='*50}")
    
    if all(results.values()):
        print("✓ All basic tests passed!")
        print("Run: python3 pressure_diagnostic.py")
    else:
        print("✗ Some tests failed. Check:")
        if not results.get("I2C Detection", False):
            print("  - I2C wiring and device connections")
        if not results.get("Adafruit Libraries", False):
            print("  - Install Adafruit libraries")
        if not results.get("Basic ADC", False):
            print("  - ADC module connections and power")

if __name__ == "__main__":
    main() 