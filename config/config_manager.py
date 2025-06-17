#!/usr/bin/env python3
"""
Configuration Manager Module

Centralized configuration management for the EOL Leak Tester.
Loads configuration from YAML file and provides structured access to all parameters.
"""

import yaml
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GPIOConfig:
    """GPIO pin assignments."""
    fill: int
    exhaust: int
    extend: int
    retract: int

@dataclass
class ValveConfig:
    """Individual valve configuration."""
    name: str
    description: str
    type: str
    normally_closed: bool

@dataclass
class PressureCalibrationConfig:
    """Pressure transducer calibration parameters."""
    balance_current_ma: float
    full_scale_current_ma: float
    midpoint_current_ma: float
    midpoint_pressure_psi: float
    sensitivity_ma: float

@dataclass
class ADCConfig:
    """ADC configuration parameters."""
    i2c_address: int
    bus_number: int
    gain: int
    sample_rate: int
    module_type: str
    adc_range_4ma: int
    adc_range_20ma: int
    
    # High-speed data collection settings (optional)
    high_speed_mode: bool = False
    single_shot_mode: bool = False
    i2c_frequency: int = 100000

@dataclass
class PressureTransducerConfig:
    """Complete pressure transducer configuration."""
    min_pressure_psi: float
    max_pressure_psi: float
    calibration: PressureCalibrationConfig
    adc: ADCConfig

@dataclass
class TestTimingConfig:
    """Test sequence timing parameters."""
    cylinder_extend_time: float
    fill_time: float
    stabilize_time: float
    test_duration: float
    exhaust_time: float
    cylinder_retract_time: float

@dataclass
class TestPressureConfig:
    """Test pressure parameters."""
    target_fill_pressure: float
    pressure_tolerance: float
    max_leak_rate: float
    min_test_pressure: float

@dataclass
class TestSafetyConfig:
    """Test safety parameters."""
    max_pressure: float
    pressure_timeout: float
    emergency_stop_timeout: float
    max_fill_attempts: int
    pressure_overshoot_limit: float

@dataclass
class TestParametersConfig:
    """Complete test parameters configuration."""
    timing: TestTimingConfig
    pressure: TestPressureConfig
    safety: TestSafetyConfig

@dataclass
class UIColorsConfig:
    """UI color configuration."""
    pass_result: str
    fail_result: str
    error_result: str
    normal_pressure: str
    low_pressure: str
    high_pressure: str
    background: str
    panel_background: str
    text_primary: str
    text_secondary: str

@dataclass
class UIDisplayConfig:
    """UI display configuration."""
    fullscreen_on_pi: bool
    window_size: list
    pi_resolution: list
    cursor_visible: bool

@dataclass
class UIUpdateRatesConfig:
    """UI update rate configuration."""
    pressure_update_hz: int
    timer_update_hz: int
    ui_refresh_ms: int

@dataclass
class UIFontsConfig:
    """UI font configuration."""
    title_size: int
    large_display_size: int
    button_size: int
    normal_size: int
    small_size: int

@dataclass
class UIConfig:
    """Complete UI configuration."""
    display: UIDisplayConfig
    update_rates: UIUpdateRatesConfig
    colors: UIColorsConfig
    fonts: UIFontsConfig

class ConfigManager:
    """
    Central configuration manager for the EOL Leak Tester.
    
    Loads configuration from YAML file and provides structured access
    to all system parameters with validation and defaults.
    """
    
    def __init__(self, config_file: str = "config/system_config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration YAML file
        """
        self.config_file = Path(config_file)
        self.config_data = {}
        
        # Load configuration
        self._load_config()
        
        # Create structured configuration objects
        self._create_config_objects()
        
        logger.info(f"Configuration loaded from {self.config_file}")
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
            
            with open(self.config_file, 'r') as f:
                self.config_data = yaml.safe_load(f)
            
            logger.info(f"Configuration loaded successfully from {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.info("Using default configuration values")
            self._load_default_config()
    
    def _load_default_config(self):
        """Load default configuration if file loading fails."""
        self.config_data = {
            'gpio': {'fill': 24, 'exhaust': 23, 'extend': 9, 'retract': 10},
            'pressure_transducer': {
                'min_pressure_psi': 0.0,
                'max_pressure_psi': 1.0,
                'calibration': {
                    'balance_current_ma': 4.025,
                    'full_scale_current_ma': 20.037,
                    'midpoint_current_ma': 12.029,
                    'midpoint_pressure_psi': 0.5,
                    'sensitivity_ma': 16.012
                },
                'adc': {
                    'i2c_address': 0x48,
                    'bus_number': 1,
                    'gain': 2,
                    'sample_rate': 128,
                    'module_type': '4-20mA Current Loop Receiver',
                    'adc_range_4ma': 6430,
                    'adc_range_20ma': 32154,
                    'high_speed_mode': False,
                    'single_shot_mode': False,
                    'i2c_frequency': 100000
                }
            },
            'test_parameters': {
                'timing': {
                    'cylinder_extend_time': 3.0,
                    'fill_time': 5.0,
                    'stabilize_time': 10.0,
                    'test_duration': 30.0,
                    'exhaust_time': 5.0,
                    'cylinder_retract_time': 3.0
                },
                'pressure': {
                    'target_fill_pressure': 0.8,
                    'pressure_tolerance': 0.05,
                    'max_leak_rate': 0.005,
                    'min_test_pressure': 0.1
                },
                'safety': {
                    'max_pressure': 1.2,
                    'pressure_timeout': 60.0,
                    'emergency_stop_timeout': 5.0,
                    'max_fill_attempts': 3,
                    'pressure_overshoot_limit': 1.5
                }
            }
        }
    
    def _create_config_objects(self):
        """Create structured configuration objects from loaded data."""
        # GPIO Configuration
        gpio_data = self.config_data.get('gpio', {})
        self.gpio = GPIOConfig(**gpio_data)
        
        # Pressure Transducer Configuration
        pt_data = self.config_data.get('pressure_transducer', {})
        cal_data = pt_data.get('calibration', {})
        adc_data = pt_data.get('adc', {})
        
        self.pressure_calibration = PressureCalibrationConfig(**cal_data)
        self.adc = ADCConfig(**adc_data)
        self.pressure_transducer = PressureTransducerConfig(
            min_pressure_psi=pt_data.get('min_pressure_psi', 0.0),
            max_pressure_psi=pt_data.get('max_pressure_psi', 1.0),
            calibration=self.pressure_calibration,
            adc=self.adc
        )
        
        # Test Parameters Configuration
        test_data = self.config_data.get('test_parameters', {})
        timing_data = test_data.get('timing', {})
        pressure_data = test_data.get('pressure', {})
        safety_data = test_data.get('safety', {})
        
        self.test_timing = TestTimingConfig(**timing_data)
        self.test_pressure = TestPressureConfig(**pressure_data)
        self.test_safety = TestSafetyConfig(**safety_data)
        self.test_parameters = TestParametersConfig(
            timing=self.test_timing,
            pressure=self.test_pressure,
            safety=self.test_safety
        )
        
        # UI Configuration (if present)
        ui_data = self.config_data.get('ui', {})
        if ui_data:
            display_data = ui_data.get('display', {})
            rates_data = ui_data.get('update_rates', {})
            colors_data = ui_data.get('colors', {})
            fonts_data = ui_data.get('fonts', {})
            
            self.ui_display = UIDisplayConfig(**display_data) if display_data else None
            self.ui_update_rates = UIUpdateRatesConfig(**rates_data) if rates_data else None
            self.ui_colors = UIColorsConfig(**colors_data) if colors_data else None
            self.ui_fonts = UIFontsConfig(**fonts_data) if fonts_data else None
            
            if all([self.ui_display, self.ui_update_rates, self.ui_colors, self.ui_fonts]):
                self.ui = UIConfig(
                    display=self.ui_display,
                    update_rates=self.ui_update_rates,
                    colors=self.ui_colors,
                    fonts=self.ui_fonts
                )
            else:
                self.ui = None
        else:
            self.ui = None
    
    def get_gpio_config(self) -> Dict[str, int]:
        """Get GPIO configuration as dictionary for relay controller."""
        return {
            "fill": self.gpio.fill,
            "exhaust": self.gpio.exhaust,
            "extend": self.gpio.extend,
            "retract": self.gpio.retract
        }
    
    def get_valve_info(self, valve_id: str) -> Dict[str, Any]:
        """Get valve information by ID."""
        valves_data = self.config_data.get('valves', {})
        return valves_data.get(valve_id, {})
    
    def get_test_config_for_runner(self) -> Dict[str, Any]:
        """Get test configuration in format expected by TestRunner."""
        return {
            'cylinder_extend_time': self.test_timing.cylinder_extend_time,
            'fill_time': self.test_timing.fill_time,
            'stabilize_time': self.test_timing.stabilize_time,
            'test_duration': self.test_timing.test_duration,
            'exhaust_time': self.test_timing.exhaust_time,
            'cylinder_retract_time': self.test_timing.cylinder_retract_time,
            'target_fill_pressure': self.test_pressure.target_fill_pressure,
            'pressure_tolerance': self.test_pressure.pressure_tolerance,
            'max_leak_rate': self.test_pressure.max_leak_rate,
            'max_pressure': self.test_safety.max_pressure,
            'pressure_timeout': self.test_safety.pressure_timeout
        }
    
    def get_adc_config_for_reader(self) -> Dict[str, Any]:
        """Get ADC configuration in format expected by ADCReader."""
        return {
            'i2c_address': self.adc.i2c_address,
            'bus_number': self.adc.bus_number,
            'gain': self.adc.gain,
            'sample_rate': self.adc.sample_rate
        }
    
    def get_pressure_calibration_config(self) -> Dict[str, Any]:
        """Get pressure calibration configuration."""
        return {
            'min_pressure_psi': self.pressure_transducer.min_pressure_psi,
            'max_pressure_psi': self.pressure_transducer.max_pressure_psi,
            'min_current_ma': self.pressure_calibration.balance_current_ma,
            'max_current_ma': self.pressure_calibration.full_scale_current_ma
        }
    
    def get_system_config(self, section: str) -> Dict[str, Any]:
        """Get configuration section by name."""
        return self.config_data.get(section, {})
    
    def get_parameter(self, section: str, key: str, default: Any = None) -> Any:
        """Get specific parameter from configuration."""
        section_data = self.config_data.get(section, {})
        return section_data.get(key, default)
    
    def get_nested_parameter(self, section: str, subsection: str, key: str, default: Any = None) -> Any:
        """Get nested parameter from configuration."""
        section_data = self.config_data.get(section, {})
        subsection_data = section_data.get(subsection, {})
        return subsection_data.get(key, default)
    
    def update_parameter(self, section: str, key: str, value: Any):
        """Update a configuration parameter (runtime only, not saved to file)."""
        if section not in self.config_data:
            self.config_data[section] = {}
        self.config_data[section][key] = value
        
        # Recreate config objects if needed
        self._create_config_objects()
    
    def save_config(self, backup: bool = True):
        """Save current configuration to file."""
        try:
            if backup and self.config_file.exists():
                backup_file = self.config_file.with_suffix('.yaml.backup')
                self.config_file.rename(backup_file)
                logger.info(f"Configuration backed up to {backup_file}")
            
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def validate_config(self) -> Dict[str, list]:
        """Validate configuration and return any issues found."""
        issues = {
            'errors': [],
            'warnings': []
        }
        
        # Validate GPIO pins
        gpio_pins = [self.gpio.fill, self.gpio.exhaust, self.gpio.extend, self.gpio.retract]
        if len(set(gpio_pins)) != len(gpio_pins):
            issues['errors'].append("Duplicate GPIO pin assignments detected")
        
        # Validate pressure ranges
        if self.pressure_transducer.min_pressure_psi >= self.pressure_transducer.max_pressure_psi:
            issues['errors'].append("Invalid pressure range: min >= max")
        
        # Validate test parameters
        if self.test_pressure.target_fill_pressure > self.test_safety.max_pressure:
            issues['warnings'].append("Target fill pressure exceeds maximum safe pressure")
        
        if self.test_pressure.max_leak_rate <= 0:
            issues['errors'].append("Maximum leak rate must be positive")
        
        # Validate timing parameters
        timing_params = [
            self.test_timing.cylinder_extend_time,
            self.test_timing.fill_time,
            self.test_timing.stabilize_time,
            self.test_timing.test_duration,
            self.test_timing.exhaust_time,
            self.test_timing.cylinder_retract_time
        ]
        if any(t <= 0 for t in timing_params):
            issues['errors'].append("All timing parameters must be positive")
        
        return issues
    
    def print_config_summary(self):
        """Print a summary of current configuration."""
        print("=== EOL Leak Tester Configuration Summary ===")
        print(f"GPIO Pins: Fill={self.gpio.fill}, Exhaust={self.gpio.exhaust}, "
              f"Extend={self.gpio.extend}, Retract={self.gpio.retract}")
        print(f"Pressure Range: {self.pressure_transducer.min_pressure_psi}-"
              f"{self.pressure_transducer.max_pressure_psi} PSI")
        print(f"Target Test Pressure: {self.test_pressure.target_fill_pressure} PSI")
        print(f"Max Leak Rate: {self.test_pressure.max_leak_rate} PSI/s")
        print(f"Test Duration: {self.test_timing.test_duration}s")
        print(f"ADC: 0x{self.adc.i2c_address:02X}, Gain={self.adc.gain}")
        print("=" * 50)

# Global configuration instance
_config_manager = None

def get_config_manager(config_file: str = None) -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        if config_file is None:
            # Try to find config file in common locations
            possible_paths = [
                "config/system_config.yaml",
                "../config/system_config.yaml",
                "system_config.yaml"
            ]
            
            config_file = None
            for path in possible_paths:
                if Path(path).exists():
                    config_file = path
                    break
            
            if config_file is None:
                config_file = "config/system_config.yaml"  # Will use defaults
        
        _config_manager = ConfigManager(config_file)
    
    return _config_manager

if __name__ == "__main__":
    # Test configuration manager
    print("=== Configuration Manager Test ===")
    
    try:
        config = ConfigManager()
        
        # Print configuration summary
        config.print_config_summary()
        
        # Validate configuration
        issues = config.validate_config()
        if issues['errors']:
            print(f"\nConfiguration Errors: {issues['errors']}")
        if issues['warnings']:
            print(f"\nConfiguration Warnings: {issues['warnings']}")
        
        # Test parameter access
        print(f"\nTest Parameter Examples:")
        print(f"GPIO config: {config.get_gpio_config()}")
        print(f"Fill valve info: {config.get_valve_info('fill')}")
        print(f"System logging level: {config.get_parameter('logging', 'level', 'INFO')}")
        
        print("\n✓ Configuration manager test completed successfully")
        
    except Exception as e:
        print(f"✗ Configuration manager test failed: {e}")
        exit(1) 