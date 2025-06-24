#!/usr/bin/env python3
"""
ADC Reader Module

Reads analog values from ADS1115/ADS1015 ADC and converts to 4-20mA current readings.
Designed for pressure transducer input in the leak test system.
"""

import platform
import time
import logging
from typing import Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

class ADCReader:
    """
    High-level ADC reader for pressure transducer input.
    
    Reads values from ADS1115/ADS1015 and converts to 4-20mA current readings.
    Handles both real hardware on Pi and mock readings for development.
    """
    
    def __init__(self, 
                 i2c_address: int = 0x48,
                 bus_number: int = 1,
                 gain: int = 2,
                 sample_rate: int = 860):
        """
        Initialize the ADC reader.
        
        Args:
            i2c_address: I2C address of the ADC (default 0x48)
            bus_number: I2C bus number (default 1)
            gain: ADC gain setting (default 2 for 4-20mA module)
            sample_rate: Sample rate in samples per second (max 860 for ADS1115)
        """
        self.i2c_address = i2c_address
        self.bus_number = bus_number
        self.gain = gain
        self.sample_rate = sample_rate
        self.is_pi = is_raspberry_pi()
        
        # High-speed sampling settings
        self.high_speed_mode = False
        self.continuous_mode = False
        
        # Initialize ADC
        self._initialize_adc()
        
        logger.info(f"ADCReader initialized on {'Pi' if self.is_pi else 'development'} system")
        logger.info(f"ADC address: 0x{i2c_address:02X}, gain: {gain}, sample_rate: {sample_rate}")
    
    def _initialize_adc(self):
        """Initialize the ADC hardware or mock."""
        if self.is_pi:
            try:
                import adafruit_ads1x15.ads1115 as ADS
                from adafruit_ads1x15.analog_in import AnalogIn
                import board
                import busio
                
                # Create I2C bus
                i2c = busio.I2C(board.SCL, board.SDA)
                
                # Create ADS1115 object
                self.ads = ADS.ADS1115(i2c, address=self.i2c_address)
                
                # Configure gain (determines voltage range)
                self.ads.gain = self.gain
                
                # Configure sample rate for high-speed operation
                self._configure_sample_rate()
                
                # Create analog input on channel 0 (for pressure transducer)
                self.channel = AnalogIn(self.ads, ADS.P0)
                
                logger.info("✓ ADS1115 initialized successfully")
                logger.info(f"✓ Configured for {self.sample_rate} SPS operation")
                
            except ImportError as e:
                logger.error(f"Failed to import ADS1115 libraries: {e}")
                logger.info("Falling back to mock ADC")
                self._use_mock_adc()
            except Exception as e:
                logger.error(f"Failed to initialize ADS1115: {e}")
                logger.info("Falling back to mock ADC")
                self._use_mock_adc()
        else:
            self._use_mock_adc()
    
    def _use_mock_adc(self):
        """Use mock ADC for development."""
        logger.info("Using mock ADC for development")
        
        class MockADC:
            def __init__(self):
                self.gain = 2  # Updated for 4-20mA module
                self._mock_raw_value = 12292  # Simulate ~12mA (mid-range for 4-20mA)
                
        class MockChannel:
            def __init__(self, mock_adc):
                self.ads = mock_adc
                
            @property
            def voltage(self):
                # Convert mock raw value back to voltage for compatibility
                # Using gain=2 range (±2.048V)
                voltage_range = 2.048  # For gain=2
                return (self.ads._mock_raw_value / 32767) * voltage_range
                
            @property
            def value(self):
                # Return mock raw value with small variation
                import time
                base_value = self.ads._mock_raw_value
                # Add small variation to simulate real readings
                variation = int(100 * (time.time() % 10 - 5) / 5)  # ±100 ADC counts variation
                return base_value + variation
        
        self.ads = MockADC()
        self.channel = MockChannel(self.ads)
    
    def read_raw_value(self) -> int:
        """
        Read raw ADC value.
        
        Returns:
            int: Raw ADC reading (0-32767 for ADS1115)
        """
        try:
            raw_value = self.channel.value
            return raw_value
        except Exception as e:
            logger.error(f"Failed to read raw ADC value: {e}")
            return 0
    
    def read_voltage(self) -> float:
        """
        Read voltage from ADC.
        
        Returns:
            float: Voltage in volts
        """
        try:
            voltage = self.channel.voltage
            return voltage
        except Exception as e:
            logger.error(f"Failed to read ADC voltage: {e}")
            return 0.0
    
    def voltage_to_current_ma(self, voltage: float, shunt_resistor: float = 250.0) -> float:
        """
        Convert voltage reading to 4-20mA current.
        
        Args:
            voltage: Voltage reading in volts
            shunt_resistor: Shunt resistor value in ohms (for current measurement)
            
        Returns:
            float: Current in milliamps
        """
        # For 4-20mA measurement, typical setup uses a shunt resistor
        # Current = Voltage / Resistance (Ohm's law)
        # Convert to milliamps
        current_ma = (voltage / shunt_resistor) * 1000.0
        return current_ma
    
    def raw_adc_to_current_ma(self, raw_value: int) -> float:
        """
        Convert raw ADC value directly to 4-20mA current for 4-20mA loop receiver module.
        
        Based on module datasheet:
        - 4mA = ~6430 raw ADC value
        - 20mA = ~32154 raw ADC value
        
        Args:
            raw_value: Raw ADC reading (0-32767 for ADS1115)
            
        Returns:
            float: Current in milliamps
        """
        # Module specifications from datasheet
        ADC_4MA = 6430
        ADC_20MA = 32154
        
        # Linear interpolation: current = 4 + (raw - 6430) * (20-4) / (32154-6430)
        if raw_value <= ADC_4MA:
            # Below 4mA range - extrapolate
            current_ma = 4.0 + (raw_value - ADC_4MA) * 16.0 / (ADC_20MA - ADC_4MA)
        elif raw_value >= ADC_20MA:
            # Above 20mA range - extrapolate  
            current_ma = 4.0 + (raw_value - ADC_4MA) * 16.0 / (ADC_20MA - ADC_4MA)
        else:
            # Normal range - interpolate
            current_ma = 4.0 + (raw_value - ADC_4MA) * 16.0 / (ADC_20MA - ADC_4MA)
        
        return current_ma
    
    def read_current_ma(self, shunt_resistor: float = 250.0) -> float:
        """
        Read current in milliamps from 4-20mA loop receiver module.
        
        Args:
            shunt_resistor: Ignored - kept for compatibility
            
        Returns:
            float: Current in milliamps (should be 4-20mA range)
        """
        # For 4-20mA loop receiver module, use raw ADC value directly
        raw_value = self.read_raw_value()
        current_ma = self.raw_adc_to_current_ma(raw_value)
        return current_ma
    
    def read_multiple_samples(self, num_samples: int = 10, delay: float = 0.1) -> Tuple[float, float, float]:
        """
        Read multiple samples and return statistics.
        
        Args:
            num_samples: Number of samples to take
            delay: Delay between samples in seconds
            
        Returns:
            tuple: (average_current, min_current, max_current) in mA
        """
        samples = []
        
        for i in range(num_samples):
            current = self.read_current_ma()
            samples.append(current)
            if i < num_samples - 1:  # Don't delay after last sample
                time.sleep(delay)
        
        if samples:
            avg_current = sum(samples) / len(samples)
            min_current = min(samples)
            max_current = max(samples)
            return avg_current, min_current, max_current
        else:
            return 0.0, 0.0, 0.0
    
    def is_current_in_range(self, current_ma: float, min_ma: float = 4.0, max_ma: float = 20.0) -> bool:
        """
        Check if current reading is in valid 4-20mA range.
        
        Args:
            current_ma: Current reading in milliamps
            min_ma: Minimum valid current (default 4mA)
            max_ma: Maximum valid current (default 20mA)
            
        Returns:
            bool: True if current is in valid range
        """
        return min_ma <= current_ma <= max_ma
    
    def get_adc_info(self) -> dict:
        """
        Get ADC configuration information.
        
        Returns:
            dict: ADC configuration details
        """
        return {
            "i2c_address": f"0x{self.i2c_address:02X}",
            "bus_number": self.bus_number,
            "gain": self.gain,
            "voltage_range": "±2.048V" if self.gain == 2 else "±4.096V",
            "sample_rate": self.sample_rate,
            "high_speed_mode": self.high_speed_mode,
            "continuous_mode": self.continuous_mode,
            "is_pi": self.is_pi,
            "mock_mode": not self.is_pi,
            "module_type": "4-20mA Current Loop Receiver",
            "adc_range_4ma": 6430,
            "adc_range_20ma": 32154
        }
    
    def _configure_sample_rate(self):
        """Configure the ADC sample rate for high-speed operation."""
        if self.is_pi and hasattr(self, 'ads'):
            try:
                # Valid sample rates for ADS1115
                valid_rates = [8, 16, 32, 64, 128, 250, 475, 860]
                
                # Find closest supported sample rate
                if self.sample_rate in valid_rates:
                    target_rate = self.sample_rate
                elif self.sample_rate >= 860:
                    target_rate = 860
                    self.sample_rate = 860
                else:
                    # Find closest lower rate
                    target_rate = 128  # Default
                    for rate in sorted(valid_rates, reverse=True):
                        if rate <= self.sample_rate:
                            target_rate = rate
                            self.sample_rate = rate
                            break
                
                # Set the data rate directly (library expects SPS value, not register value)
                self.ads.data_rate = target_rate
                logger.info(f"✓ ADC sample rate configured to {self.sample_rate} SPS")
                
            except Exception as e:
                logger.warning(f"Could not configure sample rate: {e}")
                logger.info(f"Using default sample rate instead")
    
    def enable_high_speed_mode(self, enable: bool = True):
        """
        Enable or disable high-speed sampling mode.
        
        Args:
            enable: True to enable high-speed mode, False to disable
        """
        self.high_speed_mode = enable
        if enable:
            logger.info("✓ High-speed sampling mode enabled")
        else:
            logger.info("✓ High-speed sampling mode disabled")
    
    def enable_continuous_mode(self, enable: bool = True):
        """
        Enable or disable continuous sampling mode.
        
        Args:
            enable: True for continuous sampling, False for single-shot
        """
        self.continuous_mode = enable
        if enable:
            logger.info("✓ Continuous sampling mode enabled")
        else:
            logger.info("✓ Single-shot sampling mode enabled")
    
    def read_current_fast(self) -> float:
        """
        Read current with minimal latency for high-speed applications.
        
        Returns:
            float: Current in milliamps
        """
        # Single read with no averaging for maximum speed
        raw_value = self.read_raw_value()
        current_ma = self.raw_adc_to_current_ma(raw_value)
        return current_ma
    
    def read_burst_samples(self, num_samples: int = 10, target_rate_hz: float = 860) -> list:
        """
        Read a burst of samples at high speed.
        
        Args:
            num_samples: Number of samples to collect
            target_rate_hz: Target sampling rate in Hz
            
        Returns:
            list: List of current readings in mA
        """
        samples = []
        sample_interval = 1.0 / target_rate_hz if target_rate_hz > 0 else 0.001
        
        # Clamp to maximum ADC rate
        if sample_interval < (1.0 / 860):
            sample_interval = 1.0 / 860
        
        start_time = time.time()
        
        for i in range(num_samples):
            current = self.read_current_fast()
            samples.append(current)
            
            # Precise timing for next sample
            if i < num_samples - 1:  # Don't delay after last sample
                next_sample_time = start_time + (i + 1) * sample_interval
                sleep_time = next_sample_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        actual_duration = time.time() - start_time
        actual_rate = (num_samples - 1) / actual_duration if actual_duration > 0 else 0
        
        if num_samples > 1:
            logger.debug(f"Burst sampling: {num_samples} samples in {actual_duration:.3f}s ({actual_rate:.1f} Hz)")
        
        return samples

if __name__ == "__main__":
    # Test the ADC reader
    print("=== ADC Reader Test ===")
    
    try:
        # Initialize ADC reader
        adc = ADCReader()
        
        print(f"ADC Configuration: {adc.get_adc_info()}")
        
        print("\n--- Single Reading Test ---")
        
        # Test single readings
        raw_value = adc.read_raw_value()
        voltage = adc.read_voltage()
        current = adc.read_current_ma()
        
        # Also show old voltage-based calculation for comparison
        current_old_method = adc.voltage_to_current_ma(voltage)
        
        print(f"Raw ADC value: {raw_value}")
        print(f"Voltage: {voltage:.3f} V")
        print(f"Current (4-20mA module): {current:.2f} mA")
        print(f"Current (old shunt method): {current_old_method:.2f} mA")
        print(f"In valid range (4-20mA): {adc.is_current_in_range(current)}")
        
        # Show expected values based on datasheet
        expected_current = adc.raw_adc_to_current_ma(raw_value)
        print(f"Expected current from raw ADC: {expected_current:.2f} mA")
        
        print("\n--- Multiple Samples Test ---")
        
        # Test multiple samples
        avg_current, min_current, max_current = adc.read_multiple_samples(num_samples=5, delay=0.2)
        
        print(f"Average current: {avg_current:.2f} mA")
        print(f"Min current: {min_current:.2f} mA") 
        print(f"Max current: {max_current:.2f} mA")
        print(f"Range: {max_current - min_current:.2f} mA")
        
        print("\n--- Current Range Test ---")
        
        # Test different current calculations
        test_voltages = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        for voltage in test_voltages:
            current = adc.voltage_to_current_ma(voltage)
            in_range = adc.is_current_in_range(current)
            print(f"Voltage: {voltage:.1f}V → Current: {current:.1f}mA → Valid: {in_range}")
        
        print("\n✓ ADC reader test completed successfully")
        
    except Exception as e:
        print(f"✗ ADC reader test failed: {e}")
        exit(1) 