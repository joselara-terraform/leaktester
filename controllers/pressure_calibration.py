#!/usr/bin/env python3
"""
Pressure Calibration Module

Converts 4-20mA current readings to PSI pressure values.
Provides calibration capabilities for pressure transducers.
"""

import logging
import time
import json
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# Handle imports for both module use and standalone testing
try:
    from .adc_reader import ADCReader
except ImportError:
    from adc_reader import ADCReader

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CalibrationPoint:
    """Single calibration point mapping current to pressure."""
    current_ma: float
    pressure_psi: float
    
    def __str__(self):
        return f"{self.current_ma:.2f}mA → {self.pressure_psi:.1f}PSI"

class PressureCalibration:
    """
    Pressure calibration system for converting 4-20mA current to PSI.
    
    Supports both linear calibration and multi-point calibration curves.
    Handles typical pressure transducer ranges and provides validation.
    """
    
    def __init__(self, 
                 adc_reader: Optional[ADCReader] = None,
                 min_pressure_psi: float = 0.0,
                 max_pressure_psi: float = 1.0,
                 min_current_ma: float = 4.0,
                 max_current_ma: float = 20.0):
        """
        Initialize pressure calibration.
        
        Args:
            adc_reader: ADC reader instance, or None to create new one
            min_pressure_psi: Minimum pressure reading (at 4mA)
            max_pressure_psi: Maximum pressure reading (at 20mA)
            min_current_ma: Minimum current (typically 4mA)
            max_current_ma: Maximum current (typically 20mA)
        """
        self.adc_reader = adc_reader or ADCReader()
        self.min_pressure_psi = min_pressure_psi
        self.max_pressure_psi = max_pressure_psi
        self.min_current_ma = min_current_ma
        self.max_current_ma = max_current_ma
        
        # Calibration points (current_mA, pressure_PSI)
        self.calibration_points: List[CalibrationPoint] = []
        
        # Set default linear calibration
        self._set_linear_calibration()
        
        logger.info(f"PressureCalibration initialized: {min_pressure_psi}-{max_pressure_psi} PSI")
        logger.info(f"Current range: {min_current_ma}-{max_current_ma} mA")
    
    def _set_linear_calibration(self):
        """Set default linear calibration (4mA=min_pressure, 20mA=max_pressure)."""
        self.calibration_points = [
            CalibrationPoint(self.min_current_ma, self.min_pressure_psi),
            CalibrationPoint(self.max_current_ma, self.max_pressure_psi)
        ]
        logger.info("Using linear calibration")
    
    def current_to_pressure_linear(self, current_ma: float) -> float:
        """
        Convert current to pressure using linear interpolation.
        
        Args:
            current_ma: Current reading in milliamps
            
        Returns:
            float: Pressure in PSI
        """
        # Linear interpolation: y = mx + b
        # Where y = pressure, x = current
        current_range = self.max_current_ma - self.min_current_ma
        pressure_range = self.max_pressure_psi - self.min_pressure_psi
        
        if current_range == 0:
            return self.min_pressure_psi
        
        # Calculate slope (m) and intercept (b)
        slope = pressure_range / current_range
        intercept = self.min_pressure_psi - (slope * self.min_current_ma)
        
        pressure_psi = slope * current_ma + intercept
        
        return pressure_psi
    
    def current_to_pressure_multipoint(self, current_ma: float) -> float:
        """
        Convert current to pressure using multi-point interpolation.
        
        Args:
            current_ma: Current reading in milliamps
            
        Returns:
            float: Pressure in PSI
        """
        if len(self.calibration_points) < 2:
            return self.current_to_pressure_linear(current_ma)
        
        # Sort calibration points by current
        points = sorted(self.calibration_points, key=lambda p: p.current_ma)
        
        # Find the two points to interpolate between
        if current_ma <= points[0].current_ma:
            # Extrapolate below range
            return points[0].pressure_psi
        elif current_ma >= points[-1].current_ma:
            # Extrapolate above range  
            return points[-1].pressure_psi
        else:
            # Interpolate between points
            for i in range(len(points) - 1):
                if points[i].current_ma <= current_ma <= points[i + 1].current_ma:
                    # Linear interpolation between these two points
                    x1, y1 = points[i].current_ma, points[i].pressure_psi
                    x2, y2 = points[i + 1].current_ma, points[i + 1].pressure_psi
                    
                    if x2 == x1:
                        return y1
                    
                    # Linear interpolation formula
                    pressure_psi = y1 + (y2 - y1) * (current_ma - x1) / (x2 - x1)
                    return pressure_psi
        
        # Fallback to linear
        return self.current_to_pressure_linear(current_ma)
    
    def current_to_pressure(self, current_ma: float) -> float:
        """
        Convert current to pressure (uses multi-point if available, otherwise linear).
        
        Args:
            current_ma: Current reading in milliamps
            
        Returns:
            float: Pressure in PSI
        """
        return self.current_to_pressure_multipoint(current_ma)
    
    def read_pressure_psi(self, num_samples: int = 5) -> float:
        """
        Read current pressure in PSI.
        
        Args:
            num_samples: Number of samples to average
            
        Returns:
            float: Current pressure in PSI
        """
        # Read current from ADC
        if num_samples == 1:
            current_ma = self.adc_reader.read_current_ma()
        else:
            avg_current, _, _ = self.adc_reader.read_multiple_samples(num_samples, delay=0.05)
            current_ma = avg_current
        
        # Convert to pressure
        pressure_psi = self.current_to_pressure(current_ma)
        
        return pressure_psi
    
    def add_calibration_point(self, current_ma: float, pressure_psi: float):
        """
        Add a calibration point.
        
        Args:
            current_ma: Current reading in milliamps
            pressure_psi: Known pressure in PSI
        """
        point = CalibrationPoint(current_ma, pressure_psi)
        self.calibration_points.append(point)
        logger.info(f"Added calibration point: {point}")
    
    def calibrate_from_known_pressure(self, known_pressure_psi: float, num_samples: int = 10) -> bool:
        """
        Add calibration point by reading current at known pressure.
        
        Args:
            known_pressure_psi: Known pressure being applied
            num_samples: Number of samples to average
            
        Returns:
            bool: True if calibration successful
        """
        try:
            # Read current at this pressure
            avg_current, min_current, max_current = self.adc_reader.read_multiple_samples(
                num_samples, delay=0.1)
            
            # Check if readings are stable (low variation)
            current_variation = max_current - min_current
            if current_variation > 0.5:  # mA
                logger.warning(f"High current variation: {current_variation:.2f}mA")
                logger.warning("Readings may be unstable - check connections")
            
            # Add calibration point
            self.add_calibration_point(avg_current, known_pressure_psi)
            
            logger.info(f"Calibration point added: {avg_current:.2f}mA = {known_pressure_psi:.1f}PSI")
            logger.info(f"Current stability: ±{current_variation/2:.2f}mA")
            
            return True
            
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            return False
    
    def validate_calibration(self) -> Dict[str, float]:
        """
        Validate calibration by checking linearity and range.
        
        Returns:
            dict: Validation metrics
        """
        if len(self.calibration_points) < 2:
            return {"error": "Insufficient calibration points"}
        
        # Sort points by current
        points = sorted(self.calibration_points, key=lambda p: p.current_ma)
        
        # Check current range coverage
        current_span = points[-1].current_ma - points[0].current_ma
        expected_span = self.max_current_ma - self.min_current_ma
        range_coverage = (current_span / expected_span) * 100
        
        # Check linearity (R-squared for linear fit)
        n = len(points)
        if n >= 3:
            # Calculate linear regression R-squared
            sum_x = sum(p.current_ma for p in points)
            sum_y = sum(p.pressure_psi for p in points)
            sum_xy = sum(p.current_ma * p.pressure_psi for p in points)
            sum_x2 = sum(p.current_ma ** 2 for p in points)
            sum_y2 = sum(p.pressure_psi ** 2 for p in points)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2)) ** 0.5
            
            if denominator != 0:
                r_squared = (numerator / denominator) ** 2
            else:
                r_squared = 0.0
        else:
            r_squared = 1.0  # Perfect for 2 points
        
        return {
            "num_points": n,
            "current_range_ma": current_span,
            "range_coverage_percent": range_coverage,
            "linearity_r_squared": r_squared,
            "min_current_ma": points[0].current_ma,
            "max_current_ma": points[-1].current_ma,
            "min_pressure_psi": points[0].pressure_psi,
            "max_pressure_psi": points[-1].pressure_psi
        }
    
    def get_calibration_info(self) -> Dict:
        """
        Get calibration information and current status.
        
        Returns:
            dict: Calibration status and configuration
        """
        return {
            "pressure_range": f"{self.min_pressure_psi}-{self.max_pressure_psi} PSI",
            "current_range": f"{self.min_current_ma}-{self.max_current_ma} mA",
            "num_calibration_points": len(self.calibration_points),
            "calibration_points": [str(p) for p in self.calibration_points],
            "adc_info": self.adc_reader.get_adc_info()
        }
    
    def save_calibration(self, filename: str = "pressure_calibration.json"):
        """Save calibration to file."""
        calibration_data = {
            "min_pressure_psi": self.min_pressure_psi,
            "max_pressure_psi": self.max_pressure_psi,
            "min_current_ma": self.min_current_ma,
            "max_current_ma": self.max_current_ma,
            "calibration_points": [
                {"current_ma": p.current_ma, "pressure_psi": p.pressure_psi} 
                for p in self.calibration_points
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(calibration_data, f, indent=2)
        
        logger.info(f"Calibration saved to {filename}")
    
    def load_calibration(self, filename: str = "pressure_calibration.json") -> bool:
        """Load calibration from file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.min_pressure_psi = data["min_pressure_psi"]
            self.max_pressure_psi = data["max_pressure_psi"]
            self.min_current_ma = data["min_current_ma"]
            self.max_current_ma = data["max_current_ma"]
            
            self.calibration_points = [
                CalibrationPoint(p["current_ma"], p["pressure_psi"])
                for p in data["calibration_points"]
            ]
            
            logger.info(f"Calibration loaded from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load calibration: {e}")
            return False

if __name__ == "__main__":
    # Test pressure calibration
    print("=== Pressure Calibration Test ===")
    
    try:
        # Initialize with typical 0-100 PSI transducer
        calibration = PressureCalibration(
            min_pressure_psi=0.0,    # 4mA = 0 PSI
            max_pressure_psi=15.0   # 20mA = 100 PSI
        )
        
        print(f"Calibration info: {calibration.get_calibration_info()}")
        
        print("\n--- Linear Conversion Test ---")
        
        # Test linear conversion with various currents
        test_currents = [4.0, 8.0, 12.0, 16.0, 20.0]
        
        for current in test_currents:
            pressure = calibration.current_to_pressure(current)
            print(f"{current:.1f}mA → {pressure:.1f}PSI")
        
        print("\n--- Live Pressure Reading ---")
        
        # Read actual pressure from ADC
        for i in range(3):
            pressure = calibration.read_pressure_psi(num_samples=5)
            print(f"Reading {i+1}: {pressure:.2f} PSI")
            time.sleep(1)
        
        print("\n--- Multi-point Calibration Test ---")
        
        # Add some calibration points (simulated)
        calibration.add_calibration_point(4.0, 0.0)    # 0 PSI at 4mA
        calibration.add_calibration_point(12.0, 50.0)  # 50 PSI at 12mA  
        calibration.add_calibration_point(20.0, 100.0) # 100 PSI at 20mA
        
        # Test conversion with multi-point calibration
        for current in test_currents:
            pressure = calibration.current_to_pressure(current)
            print(f"{current:.1f}mA → {pressure:.1f}PSI (multi-point)")
        
        print("\n--- Calibration Validation ---")
        
        validation = calibration.validate_calibration()
        for key, value in validation.items():
            if isinstance(value, float):
                print(f"{key}: {value:.3f}")
            else:
                print(f"{key}: {value}")
        
        print("\n✓ Pressure calibration test completed successfully")
        
    except Exception as e:
        print(f"✗ Pressure calibration test failed: {e}")
        exit(1) 