# EOL Leak Tester Configuration System

This directory contains the centralized configuration system for the EOL Leak Tester. All important system parameters are now stored in a single YAML configuration file for easy management and customization.

## Configuration Files

### `system_config.yaml`
The main configuration file containing all system parameters:

- **GPIO Assignments** - Pin mappings for all valves and hardware
- **Pressure Transducer Settings** - Calibration data and ADC configuration  
- **Test Parameters** - Timing, pressure limits, and test criteria
- **UI Settings** - Display options, colors, and update rates
- **Safety Parameters** - Maximum pressures and timeouts
- **Logging Configuration** - File locations and retention policies

### `config_manager.py`
Python module that loads and manages configuration data with:

- **Structured Data Classes** - Type-safe access to configuration
- **Validation** - Checks for invalid or conflicting parameters
- **Defaults** - Fallback values if configuration file is missing
- **Runtime Updates** - Ability to modify parameters during operation

## Key Configuration Sections

### GPIO Configuration
```yaml
gpio:
  fill: 24          # Fill solenoid valve
  exhaust: 23       # Exhaust solenoid valve
  extend: 9         # Cylinder extend solenoid
  retract: 10       # Cylinder retract solenoid
```

### Pressure Transducer
```yaml
pressure_transducer:
  min_pressure_psi: 0.0
  max_pressure_psi: 1.0
  calibration:
    balance_current_ma: 4.025      # Your PT's actual 0 PSI reading
    full_scale_current_ma: 20.037  # Your PT's actual 1 PSI reading
    midpoint_current_ma: 12.029    # Your PT's 0.5 PSI reading
```

### Test Parameters
```yaml
test_parameters:
  timing:
    fill_time: 5.0                 # Seconds to fill DUT
    test_duration: 30.0            # Leak test measurement time
    cylinder_extend_time: 3.0      # Time to extend cylinders
  pressure:
    target_fill_pressure: 0.8      # Target test pressure (PSI)
    max_leak_rate: 0.005           # Maximum acceptable leak rate (PSI/s)
  safety:
    max_pressure: 1.2              # Emergency pressure limit
    pressure_timeout: 60.0         # Safety timeout for operations
```

## How to Use

### 1. Testing Configuration
Run the configuration test to verify everything loads correctly:
```bash
python3 test_config.py
```

### 2. Modifying Parameters
Edit `config/system_config.yaml` with any text editor:

**To change GPIO pins:**
```yaml
gpio:
  fill: 25          # Changed from 24 to 25
```

**To adjust test timing:**
```yaml
test_parameters:
  timing:
    fill_time: 10.0   # Increased from 5.0 to 10.0 seconds
```

**To update pressure calibration:**
```yaml
pressure_transducer:
  calibration:
    balance_current_ma: 4.030     # Update with your PT's values
```

### 3. Applying Changes
Restart the application for changes to take effect:
```bash
python3 ui/main_ui.py
```

## Module Integration

All major modules now load configuration automatically:

### RelayController
```python
from controllers.relay_controller import RelayController
relay_controller = RelayController()  # Loads GPIO config automatically
```

### PressureCalibration  
```python
from controllers.pressure_calibration import PressureCalibration
pressure_cal = PressureCalibration()  # Loads PT calibration automatically
```

### TestRunner
```python
from services.test_runner import create_test_config_from_file
test_config = create_test_config_from_file()  # Loads test parameters
```

### MainUI
```python
from ui.main_ui import MainUI
ui = MainUI()  # Loads all UI settings automatically
```

## Benefits

### ✅ **Centralized Management**
- All parameters in one place
- No need to hunt through code for hardcoded values
- Easy to see relationships between parameters

### ✅ **Easy Customization**
- Change GPIO pins without code modifications
- Adjust test timing and pressures for different DUTs
- Customize UI colors and behavior

### ✅ **Version Control Friendly**
- Configuration changes are tracked in git
- Easy to compare different setups
- Can maintain different configs for different stations

### ✅ **Validation & Safety**
- Automatic validation of parameter ranges
- Warns about conflicting settings
- Prevents invalid configurations

### ✅ **Documentation**
- Self-documenting configuration with comments
- Clear parameter names and descriptions
- Examples and units included

## Common Customizations

### Different Pressure Transducer
If you get a new PT with different specs:
```yaml
pressure_transducer:
  max_pressure_psi: 5.0           # Changed from 1.0 to 5.0 PSI
  calibration:
    balance_current_ma: 4.000     # New PT's 0 PSI reading
    full_scale_current_ma: 20.000 # New PT's 5 PSI reading
```

### Different Test Requirements
For tighter leak specifications:
```yaml
test_parameters:
  pressure:
    max_leak_rate: 0.001          # More stringent: 0.001 PSI/s
  timing:
    test_duration: 60.0           # Longer test: 60 seconds
```

### Development vs Production
You can maintain separate config files:
- `system_config_dev.yaml` - Development settings
- `system_config_prod.yaml` - Production settings

Load specific config:
```python
from config.config_manager import ConfigManager
config = ConfigManager("config/system_config_prod.yaml")
```

## Troubleshooting

### Configuration Not Loading
1. Check that `PyYAML` is installed: `pip install PyYAML`
2. Verify the YAML syntax is valid
3. Run `python3 test_config.py` to diagnose issues

### Invalid Parameters
The system will warn about:
- Duplicate GPIO pin assignments
- Invalid pressure ranges  
- Negative timing values
- Conflicting safety limits

### Missing Configuration File
If the config file is missing, the system will:
- Use built-in default values
- Log a warning message
- Continue operating normally

## Advanced Features

### Runtime Parameter Updates
```python
config = get_config_manager()
config.update_parameter('test_parameters', 'target_fill_pressure', 0.9)
```

### Save Modified Configuration
```python
config.save_config(backup=True)  # Saves with backup
```

### Access Any Parameter
```python
# Direct access
fill_time = config.get_nested_parameter('test_parameters', 'timing', 'fill_time')

# Section access  
ui_colors = config.get_system_config('ui')['colors']

# Structured access
max_pressure = config.test_safety.max_pressure
```

## Support

If you have questions about the configuration system:

1. **Test first**: Run `python3 test_config.py`
2. **Check syntax**: Validate your YAML online
3. **Review logs**: Look for configuration warnings
4. **Use defaults**: Delete config file to test with defaults

The configuration system is designed to be robust and will fall back to safe defaults if there are any issues. 