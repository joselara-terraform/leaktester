#!/usr/bin/env python3
"""
ADC Module Detection Test

Scans I2C bus for ADC modules and verifies communication.
Tests for common ADC chips used with pressure transducers.
"""

import platform
import subprocess
import sys
import time

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

def scan_i2c_bus(bus_number=1):
    """
    Scan I2C bus for connected devices.
    
    Args:
        bus_number: I2C bus number (usually 1 on Pi)
        
    Returns:
        list: List of detected device addresses
    """
    if not is_raspberry_pi():
        print("⚠ Not on Raspberry Pi - cannot scan I2C hardware")
        return []
    
    try:
        print(f"Scanning I2C bus {bus_number}...")
        result = subprocess.run(['i2cdetect', '-y', str(bus_number)], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"✗ I2C scan failed: {result.stderr}")
            return []
        
        # Parse i2cdetect output to find device addresses
        devices = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            parts = line.split()
            if len(parts) > 1:
                for i, part in enumerate(parts[1:], 0):
                    if part != '--' and part != 'UU':
                        # Calculate address: row_base + column
                        row_base = int(parts[0].rstrip(':'), 16)
                        address = row_base + i
                        devices.append(address)
        
        print(f"✓ I2C scan completed")
        print("Raw scan output:")
        print(result.stdout)
        
        return devices
        
    except FileNotFoundError:
        print("✗ i2cdetect command not found. Install with: sudo apt-get install i2c-tools")
        return []
    except Exception as e:
        print(f"✗ I2C scan error: {e}")
        return []

def identify_adc_devices(device_addresses):
    """
    Identify potential ADC devices from I2C addresses.
    
    Args:
        device_addresses: List of detected I2C addresses
        
    Returns:
        dict: Mapping of addresses to potential device types
    """
    # Common ADC device addresses and types
    known_adcs = {
        0x48: "ADS1115/ADS1015 (default)",
        0x49: "ADS1115/ADS1015 (ADDR to VDD)",
        0x4A: "ADS1115/ADS1015 (ADDR to SDA)", 
        0x4B: "ADS1115/ADS1015 (ADDR to SCL)",
        0x68: "PCF8591 or other ADC",
        0x6A: "MCP3421/MCP3422/MCP3423/MCP3424",
        0x6B: "MCP3421/MCP3422/MCP3423/MCP3424",
        0x6C: "MCP3421/MCP3422/MCP3423/MCP3424",
        0x6D: "MCP3421/MCP3422/MCP3423/MCP3424",
        0x6E: "MCP3421/MCP3422/MCP3423/MCP3424",
        0x6F: "MCP3421/MCP3422/MCP3423/MCP3424",
    }
    
    identified = {}
    
    for addr in device_addresses:
        if addr in known_adcs:
            identified[addr] = known_adcs[addr]
        else:
            identified[addr] = "Unknown device"
    
    return identified

def test_adc_communication(address, bus_number=1):
    """
    Test basic communication with an ADC device.
    
    Args:
        address: I2C address to test
        bus_number: I2C bus number
        
    Returns:
        bool: True if communication successful
    """
    if not is_raspberry_pi():
        print(f"⚠ Cannot test I2C communication on non-Pi system")
        return False
    
    try:
        import smbus2
        
        with smbus2.SMBus(bus_number) as bus:
            # Try to read from the device (most ADCs respond to simple read)
            try:
                # Try reading a byte (works for most ADCs)
                data = bus.read_byte(address)
                print(f"✓ Communication successful with device at 0x{address:02X}")
                print(f"  Response: 0x{data:02X}")
                return True
                
            except OSError as e:
                if e.errno == 121:  # Remote I/O error
                    print(f"✗ Device at 0x{address:02X} not responding")
                else:
                    print(f"✗ Communication error with 0x{address:02X}: {e}")
                return False
                
    except ImportError:
        print("✗ smbus2 library not available")
        return False
    except Exception as e:
        print(f"✗ Communication test failed: {e}")
        return False

def main():
    """Main ADC detection test."""
    print("=== ADC Module Detection Test ===")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    print(f"Raspberry Pi: {'Yes' if is_raspberry_pi() else 'No'}")
    
    if not is_raspberry_pi():
        print("\n⚠ This test requires a Raspberry Pi with I2C enabled")
        print("⚠ Mock ADC detection not implemented for development systems")
        return False
    
    # Scan for devices
    print("\n--- I2C Bus Scan ---")
    devices = scan_i2c_bus()
    
    if not devices:
        print("✗ No I2C devices detected")
        print("\nTroubleshooting:")
        print("1. Check I2C is enabled: sudo raspi-config")
        print("2. Check wiring connections")
        print("3. Verify ADC module power supply")
        print("4. Check device address jumpers/configuration")
        return False
    
    print(f"\n✓ Found {len(devices)} I2C device(s)")
    
    # Identify potential ADCs
    print("\n--- Device Identification ---")
    identified = identify_adc_devices(devices)
    
    adc_found = False
    for addr, device_type in identified.items():
        print(f"0x{addr:02X}: {device_type}")
        if "ADS" in device_type or "MCP" in device_type or "ADC" in device_type:
            adc_found = True
    
    if not adc_found:
        print("\n⚠ No known ADC devices identified")
        print("Detected devices might be other I2C peripherals")
    
    # Test communication with potential ADCs
    print("\n--- Communication Test ---")
    comm_success = False
    
    for addr in devices:
        if addr in [0x48, 0x49, 0x4A, 0x4B]:  # Focus on ADS1115/1015 addresses
            print(f"\nTesting communication with 0x{addr:02X}...")
            if test_adc_communication(addr):
                comm_success = True
                print(f"✓ ADC at 0x{addr:02X} is ready for pressure transducer input")
    
    # Summary
    print(f"\n--- Detection Summary ---")
    print(f"I2C devices found: {len(devices)}")
    print(f"Potential ADCs: {len([a for a in identified.values() if 'ADS' in a or 'MCP' in a])}")
    print(f"Communication verified: {'Yes' if comm_success else 'No'}")
    
    if comm_success:
        print("\n✓ ADC module detection successful!")
        print("Ready to proceed with pressure transducer calibration")
        return True
    else:
        print("\n✗ No functional ADC modules detected")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 