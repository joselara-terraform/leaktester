#!/usr/bin/env python3
"""
4-20mA Current Loop Diagnostic Test

Tests the 4-20mA current loop to identify power and wiring issues.
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.adc_reader import ADCReader

def test_current_loop():
    """Test 4-20mA current loop functionality."""
    print("=== 4-20mA CURRENT LOOP DIAGNOSTIC ===")
    print("This test will help identify current loop issues.")
    print()
    
    try:
        # Initialize ADC reader
        adc = ADCReader()
        
        print("Reading current loop values...")
        print("=" * 50)
        
        # Take multiple readings to check stability
        readings = []
        for i in range(10):
            raw_value = adc.read_raw_value()
            voltage = adc.read_voltage()
            current = adc.read_current_ma()
            readings.append((raw_value, voltage, current))
            
            print(f"Reading {i+1:2d}: Raw={raw_value:5d}, Voltage={voltage:.3f}V, Current={current:.2f}mA")
            time.sleep(0.5)
        
        print("=" * 50)
        
        # Analyze readings
        avg_current = sum(r[2] for r in readings) / len(readings)
        min_current = min(r[2] for r in readings)
        max_current = max(r[2] for r in readings)
        current_stability = max_current - min_current
        
        print(f"Average Current: {avg_current:.2f} mA")
        print(f"Current Range: {min_current:.2f} - {max_current:.2f} mA")
        print(f"Stability: ±{current_stability/2:.2f} mA")
        print()
        
        # Diagnostic analysis
        print("DIAGNOSTIC ANALYSIS:")
        print("=" * 50)
        
        if avg_current < 4.0:
            print("✗ ISSUE DETECTED: Current below 4mA minimum")
            print("  This indicates a 4-20mA loop power or wiring issue.")
            print()
            print("TROUBLESHOOTING STEPS:")
            print("1. Check 24V power supply to pressure transducer")
            print("2. Verify 4-20mA loop wiring:")
            print("   - Power supply (+) → Pressure transducer (+)")
            print("   - Pressure transducer (-) → 4-20mA module (+)")
            print("   - 4-20mA module (-) → Power supply (-)")
            print("3. Test with multimeter:")
            print("   - Measure 24V across power supply")
            print("   - Measure current in series with loop")
            print("4. Check 4-20mA converter module power")
            print("5. Verify pressure transducer is working")
            
        elif 4.0 <= avg_current <= 20.0:
            print("✓ Current is in valid 4-20mA range")
            
            if 4.0 <= avg_current <= 4.5:
                print("  Reading ~4mA suggests 0 PSI (minimum)")
            elif 11.5 <= avg_current <= 12.5:
                print("  Reading ~12mA suggests 0.5 PSI (midpoint)")
            elif 19.5 <= avg_current <= 20.5:
                print("  Reading ~20mA suggests 1.0 PSI (maximum)")
            else:
                print(f"  Reading {avg_current:.1f}mA suggests pressure proportional to current")
                
            if current_stability > 0.1:
                print("  ⚠️  Current readings are unstable - check connections")
        
        else:
            print("✗ ISSUE DETECTED: Current above 20mA maximum")
            print("  This suggests a wiring or module configuration issue.")
        
        print()
        print("EXPECTED VALUES:")
        print("- 0.0 PSI → 4.025 mA (Raw ADC ~6430)")
        print("- 0.5 PSI → 12.029 mA (Raw ADC ~19292)")
        print("- 1.0 PSI → 20.037 mA (Raw ADC ~32154)")
        print()
        
        # Provide specific guidance based on current reading
        if avg_current < 4.0:
            print("IMMEDIATE ACTIONS:")
            print("1. Check if 24V power supply is connected and turned on")
            print("2. Use multimeter to verify 24V across power supply terminals")
            print("3. Check all wire connections are secure")
            print("4. Verify pressure transducer is getting power")
            print("5. Test 4-20mA converter module with known good signal")
            
        return avg_current >= 4.0
        
    except Exception as e:
        print(f"✗ Current loop test failed: {e}")
        return False

def main():
    """Run current loop diagnostic."""
    success = test_current_loop()
    
    if success:
        print("\n✓ Current loop appears to be functioning")
        print("If you're still getting 0 PSI readings, run:")
        print("python3 pressure_diagnostic.py")
    else:
        print("\n✗ Current loop has issues that need to be resolved")
        print("Fix the current loop before proceeding with pressure calibration")

if __name__ == "__main__":
    main() 