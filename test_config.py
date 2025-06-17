#!/usr/bin/env python3
"""
Configuration System Test Script

Tests that the centralized configuration system is working correctly
and all parameters are being loaded from the YAML file.
"""

import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_configuration():
    """Test the configuration system."""
    print("=== Configuration System Test ===\n")
    
    try:
        from config.config_manager import get_config_manager
        
        # Get configuration manager
        config = get_config_manager()
        
        print("✓ Configuration manager loaded successfully")
        
        # Test GPIO configuration
        print("\n--- GPIO Configuration ---")
        gpio_config = config.get_gpio_config()
        for valve, pin in gpio_config.items():
            print(f"  {valve.capitalize()}: GPIO {pin}")
        
        # Test pressure transducer configuration
        print("\n--- Pressure Transducer Configuration ---")
        pt_config = config.pressure_transducer
        print(f"  Range: {pt_config.min_pressure_psi} - {pt_config.max_pressure_psi} PSI")
        print(f"  Balance current: {pt_config.calibration.balance_current_ma} mA")
        print(f"  Full scale current: {pt_config.calibration.full_scale_current_ma} mA")
        print(f"  ADC address: 0x{pt_config.adc.i2c_address:02X}")
        print(f"  ADC gain: {pt_config.adc.gain}")
        
        # Test test parameters
        print("\n--- Test Parameters ---")
        test_config = config.test_parameters
        print(f"  Fill time: {test_config.timing.fill_time}s")
        print(f"  Test duration: {test_config.timing.test_duration}s")
        print(f"  Target pressure: {test_config.pressure.target_fill_pressure} PSI")
        print(f"  Max leak rate: {test_config.pressure.max_leak_rate} PSI/s")
        print(f"  Max safe pressure: {test_config.safety.max_pressure} PSI")
        
        # Test UI configuration (if available)
        if config.ui:
            print("\n--- UI Configuration ---")
            ui_config = config.ui
            print(f"  Fullscreen on Pi: {ui_config.display.fullscreen_on_pi}")
            print(f"  Pi resolution: {ui_config.display.pi_resolution}")
            print(f"  Update rate: {ui_config.update_rates.pressure_update_hz} Hz")
            print(f"  Colors loaded: {len(vars(ui_config.colors))} colors")
        else:
            print("\n--- UI Configuration ---")
            print("  UI configuration not available (optional)")
        
        # Test valve information
        print("\n--- Valve Information ---")
        for valve_id in ['fill', 'exhaust', 'extend', 'retract']:
            valve_info = config.get_valve_info(valve_id)
            if valve_info:
                print(f"  {valve_id.capitalize()}: {valve_info.get('name', 'Unknown')}")
        
        # Test configuration validation
        print("\n--- Configuration Validation ---")
        issues = config.validate_config()
        
        if issues['errors']:
            print("  ✗ Configuration errors found:")
            for error in issues['errors']:
                print(f"    - {error}")
        else:
            print("  ✓ No configuration errors found")
        
        if issues['warnings']:
            print("  ⚠ Configuration warnings:")
            for warning in issues['warnings']:
                print(f"    - {warning}")
        else:
            print("  ✓ No configuration warnings")
        
        # Test parameter access methods
        print("\n--- Parameter Access Test ---")
        
        # Test nested parameter access
        fill_time = config.get_nested_parameter('test_parameters', 'timing', 'fill_time')
        print(f"  Fill time (nested access): {fill_time}s")
        
        # Test single parameter access
        log_level = config.get_parameter('logging', 'level', 'INFO')
        print(f"  Logging level: {log_level}")
        
        # Test system config access
        system_config = config.get_system_config('system')
        if system_config:
            auto_detect = system_config.get('auto_detect_platform', True)
            print(f"  Auto detect platform: {auto_detect}")
        
        # Print configuration summary
        print("\n--- Configuration Summary ---")
        config.print_config_summary()
        
        print("\n✓ Configuration system test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import configuration manager: {e}")
        print("Make sure PyYAML is installed: pip install PyYAML")
        return False
        
    except FileNotFoundError as e:
        print(f"✗ Configuration file not found: {e}")
        print("The system will use default values if config file is missing")
        return False
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_module_integration():
    """Test that modules can load configuration correctly."""
    print("\n=== Module Integration Test ===\n")
    
    try:
        # Test RelayController with config
        print("Testing RelayController...")
        from controllers.relay_controller import RelayController
        relay_controller = RelayController()  # Should load from config
        print(f"  ✓ RelayController loaded with GPIO config: {relay_controller.relay_config}")
        
        # Test PressureCalibration with config
        print("Testing PressureCalibration...")
        from controllers.pressure_calibration import PressureCalibration
        pressure_cal = PressureCalibration()  # Should load from config
        print(f"  ✓ PressureCalibration loaded: {pressure_cal.min_pressure_psi}-{pressure_cal.max_pressure_psi} PSI")
        
        # Test TestRunner with config
        print("Testing TestRunner...")
        from services.test_runner import create_test_config_from_file
        test_config = create_test_config_from_file()
        print(f"  ✓ TestConfig loaded: target={test_config.target_fill_pressure} PSI, duration={test_config.test_duration}s")
        
        print("\n✓ Module integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Module integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing EOL Leak Tester Configuration System")
    print("=" * 50)
    
    # Test configuration loading
    config_test = test_configuration()
    
    # Test module integration
    integration_test = test_module_integration()
    
    # Overall result
    print("\n" + "=" * 50)
    if config_test and integration_test:
        print("🎉 All configuration tests PASSED!")
        print("\nYour configuration system is working correctly!")
        print("All modules will now load parameters from config/system_config.yaml")
    else:
        print("❌ Some configuration tests FAILED!")
        print("Check the errors above and ensure PyYAML is installed")
        
    print("\nTo modify system parameters, edit: config/system_config.yaml")
    print("Changes will take effect after restarting the application.") 