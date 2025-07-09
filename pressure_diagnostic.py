#!/usr/bin/env python3
"""
Pressure Reading Diagnostic Script

Troubleshoots pressure reading issues by testing each step of the conversion chain:
1. Raw ADC values
2. ADC to current conversion
3. Current to pressure conversion
4. Configuration validation

Run this script to identify where the pressure reading is failing.
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.adc_reader import ADCReader
from controllers.pressure_calibration import PressureCalibration
from config.config_manager import get_config_manager

def diagnostic_header(title):
    """Print a diagnostic section header."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")

def diagnostic_subheader(title):
    """Print a diagnostic subsection header."""
    print(f"\n{'-'*40}")
    print(f"{title}")
    print(f"{'-'*40}")

def test_configuration():
    """Test configuration loading and validation."""
    diagnostic_header("CONFIGURATION VALIDATION")
    
    try:
        config_manager = get_config_manager()
        
        # Test pressure calibration config
        cal_config = config_manager.pressure_calibration
        print(f"✓ Pressure calibration config loaded")
        print(f"  Balance current: {cal_config.balance_current_ma} mA → 0 PSI")
        print(f"  Midpoint current: {cal_config.midpoint_current_ma} mA → {cal_config.midpoint_pressure_psi} PSI")
        print(f"  Full scale current: {cal_config.full_scale_current_ma} mA → 1.0 PSI")
        
        # Test ADC config
        adc_config = config_manager.get_adc_config_for_reader()
        print(f"✓ ADC config loaded")
        print(f"  I2C Address: 0x{adc_config['i2c_address']:02X}")
        print(f"  Gain: {adc_config['gain']}")
        print(f"  Sample Rate: {adc_config['sample_rate']} SPS")
        
        # Test system config
        system_config = config_manager.get_system_config('system')
        print(f"✓ System config loaded")
        print(f"  Pressure reading samples: {system_config.get('pressure_reading_samples', 'Not set')}")
        print(f"  High-speed mode: {system_config.get('enable_burst_sampling', 'Not set')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_adc_reader():
    """Test ADC reader functionality."""
    diagnostic_header("ADC READER TEST")
    
    try:
        # Initialize ADC reader
        adc = ADCReader()
        
        # Show ADC info
        adc_info = adc.get_adc_info()
        print(f"✓ ADC initialized successfully")
        print(f"  Platform: {'Raspberry Pi' if adc_info['is_pi'] else 'Development'}")
        print(f"  Mock mode: {adc_info['mock_mode']}")
        print(f"  I2C Address: {adc_info['i2c_address']}")
        print(f"  Gain: {adc_info['gain']}")
        print(f"  Sample Rate: {adc_info['sample_rate']} SPS")
        
        diagnostic_subheader("Raw ADC Readings")
        
        # Test raw ADC readings
        for i in range(5):
            raw_value = adc.read_raw_value()
            voltage = adc.read_voltage()
            print(f"  Reading {i+1}: Raw={raw_value:5d}, Voltage={voltage:.3f}V")
            time.sleep(0.2)
        
        diagnostic_subheader("Current Conversion Test")
        
        # Test current conversion
        for i in range(5):
            raw_value = adc.read_raw_value()
            current = adc.read_current_ma()
            expected_current = adc.raw_adc_to_current_ma(raw_value)
            
            print(f"  Reading {i+1}: Raw={raw_value:5d} → Current={current:.3f}mA (Expected={expected_current:.3f}mA)")
            
            # Check if current is in expected range
            if 4.0 <= current <= 20.0:
                print(f"    ✓ Current is in valid 4-20mA range")
            else:
                print(f"    ✗ Current is outside 4-20mA range!")
            
            time.sleep(0.2)
        
        diagnostic_subheader("ADC Module Calibration Check")
        
        # Test known ADC values from module datasheet
        test_values = [
            (6430, "4mA (module minimum)"),
            (19292, "12mA (expected ~0.5 PSI)"),
            (32154, "20mA (module maximum)")
        ]
        
        for raw_val, description in test_values:
            current = adc.raw_adc_to_current_ma(raw_val)
            print(f"  {description}: Raw={raw_val} → {current:.3f}mA")
        
        return True
        
    except Exception as e:
        print(f"✗ ADC reader error: {e}")
        return False

def test_pressure_calibration():
    """Test pressure calibration functionality."""
    diagnostic_header("PRESSURE CALIBRATION TEST")
    
    try:
        # Initialize pressure calibration
        calibration = PressureCalibration()
        
        # Show calibration info
        cal_info = calibration.get_calibration_info()
        print(f"✓ Pressure calibration initialized")
        print(f"  Pressure range: {cal_info['pressure_range']}")
        print(f"  Current range: {cal_info['current_range']}")
        print(f"  Calibration points: {cal_info['num_calibration_points']}")
        
        for point in cal_info['calibration_points']:
            print(f"    {point}")
        
        diagnostic_subheader("Calibration Point Test")
        
        # Test calibration conversion with known points
        test_currents = [
            (4.025, "Balance (0 PSI)"),
            (12.029, "Midpoint (0.5 PSI)"),
            (20.037, "Full scale (1.0 PSI)"),
            (8.0, "Quarter scale (~0.25 PSI)"),
            (16.0, "Three-quarter scale (~0.75 PSI)")
        ]
        
        for current, description in test_currents:
            pressure = calibration.current_to_pressure(current)
            print(f"  {current:.3f}mA ({description}) → {pressure:.4f} PSI")
        
        diagnostic_subheader("Live Pressure Readings")
        
        # Test live pressure readings
        for i in range(10):
            pressure = calibration.read_pressure_psi(num_samples=1)
            print(f"  Reading {i+1}: {pressure:.4f} PSI")
            time.sleep(0.5)
        
        return True
        
    except Exception as e:
        print(f"✗ Pressure calibration error: {e}")
        return False

def test_complete_chain():
    """Test the complete ADC to pressure conversion chain."""
    diagnostic_header("COMPLETE CONVERSION CHAIN TEST")
    
    try:
        # Initialize both components
        adc = ADCReader()
        calibration = PressureCalibration()
        
        diagnostic_subheader("Step-by-Step Conversion")
        
        for i in range(5):
            # Step 1: Read raw ADC
            raw_value = adc.read_raw_value()
            
            # Step 2: Convert to voltage
            voltage = adc.read_voltage()
            
            # Step 3: Convert to current
            current = adc.read_current_ma()
            
            # Step 4: Convert to pressure
            pressure = calibration.current_to_pressure(current)
            
            # Step 5: Direct pressure reading
            direct_pressure = calibration.read_pressure_psi(num_samples=1)
            
            print(f"  Reading {i+1}:")
            print(f"    Raw ADC: {raw_value}")
            print(f"    Voltage: {voltage:.3f} V")
            print(f"    Current: {current:.3f} mA")
            print(f"    Pressure (calculated): {pressure:.4f} PSI")
            print(f"    Pressure (direct): {direct_pressure:.4f} PSI")
            
            # Check for issues
            if raw_value == 0:
                print(f"    ✗ WARNING: Raw ADC is 0 - check hardware connection")
            if current < 4.0:
                print(f"    ✗ WARNING: Current below 4mA - check sensor/wiring")
            if pressure == 0.0 and current > 4.0:
                print(f"    ✗ WARNING: Pressure is 0 but current is valid - check calibration")
            
            time.sleep(0.5)
        
        return True
        
    except Exception as e:
        print(f"✗ Complete chain test error: {e}")
        return False

def main():
    """Run complete pressure diagnostic."""
    print("PRESSURE READING DIAGNOSTIC")
    print("This script will test each step of the pressure reading system")
    print("to identify where the issue is occurring.")
    
    # Run all diagnostic tests
    tests = [
        ("Configuration", test_configuration),
        ("ADC Reader", test_adc_reader),
        ("Pressure Calibration", test_pressure_calibration),
        ("Complete Chain", test_complete_chain)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*80}")
            print(f"Running {test_name} test...")
            success = test_func()
            results[test_name] = success
            
            if success:
                print(f"✓ {test_name} test completed successfully")
            else:
                print(f"✗ {test_name} test failed")
                
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*80}")
    print("DIAGNOSTIC SUMMARY")
    print(f"{'='*80}")
    
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:<20}: {status}")
    
    print(f"\n{'='*80}")
    print("TROUBLESHOOTING GUIDE")
    print(f"{'='*80}")
    
    print("\nIf you're getting 0 PSI readings:")
    print("1. Check if Raw ADC values are 0 - indicates hardware/wiring issue")
    print("2. Check if Current is below 4mA - indicates sensor or power issue")
    print("3. Check if Current is valid but Pressure is 0 - indicates calibration issue")
    print("4. Verify your pressure transducer is actually connected and powered")
    print("5. Check I2C connections between Pi and ADC module")
    print("6. Verify 4-20mA loop is complete and powered")
    
    print("\nExpected values at 0.5 PSI:")
    print("- Raw ADC: ~19,292 (for 12mA)")
    print("- Current: ~12.029 mA")
    print("- Pressure: ~0.5 PSI")
    
    if not results.get("ADC Reader", False):
        print("\n⚠️  ADC Reader failed - check hardware connections!")
    
    if not results.get("Pressure Calibration", False):
        print("\n⚠️  Pressure Calibration failed - check configuration!")

if __name__ == "__main__":
    main() 