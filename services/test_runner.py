#!/usr/bin/env python3
"""
Test Runner Service

Orchestrates the full EOL leak test sequence.
Controls all hardware modules and manages the test state machine.
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

# Handle imports for both module use and standalone testing
try:
    from ..controllers.solenoid_valves import SolenoidValves
    from ..controllers.cylinders import Cylinders
    from ..controllers.pressure_calibration import PressureCalibration
    from ..controllers.relay_controller import RelayController
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from controllers.solenoid_valves import SolenoidValves
    from controllers.cylinders import Cylinders
    from controllers.pressure_calibration import PressureCalibration
    from controllers.relay_controller import RelayController

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPhase(Enum):
    """Enumeration of test phases."""
    READY = "Ready"
    EXTENDING_CYLINDERS = "Extending cylinders"
    FILLING_DUT = "Filling DUT"
    STABILIZING = "Stabilizing"
    ISOLATING = "Isolating"
    TESTING = "Testing"
    EVALUATING = "Evaluating"
    EXHAUSTING = "Exhausting"
    RETRACTING_CYLINDERS = "Retracting cylinders"
    COMPLETE = "Complete"
    ERROR = "Error"

class TestResult(Enum):
    """Test result enumeration."""
    NONE = None
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"

@dataclass
class TestConfig:
    """Test configuration parameters."""
    # Timing parameters (seconds)
    cylinder_extend_time: float = 3.0
    fill_time: float = 5.0
    stabilize_time: float = 10.0
    test_duration: float = 30.0
    exhaust_time: float = 5.0
    cylinder_retract_time: float = 3.0
    
    # Pressure parameters (PSI)
    target_fill_pressure: float = 10.0
    pressure_tolerance: float = 0.5
    max_leak_rate: float = 0.1  # PSI per second
    
    # Safety parameters
    max_pressure: float = 15.0
    pressure_timeout: float = 60.0

class TestRunner:
    """
    Test runner service that orchestrates the complete leak test sequence.
    
    Manages the test state machine and coordinates all hardware controllers
    to perform the leak test according to the defined sequence.
    """
    
    def __init__(self, 
                 config: Optional[TestConfig] = None,
                 phase_callback: Optional[Callable[[TestPhase], None]] = None):
        """
        Initialize the test runner.
        
        Args:
            config: Test configuration, or None for defaults
            phase_callback: Optional callback function called on phase changes
        """
        self.config = config or TestConfig()
        self.phase_callback = phase_callback
        
        # Initialize hardware controllers
        self._initialize_hardware()
        
        # Test state
        self.current_phase = TestPhase.READY
        self.test_result = TestResult.NONE
        self.test_data = {}
        self.is_testing = False
        self.start_time = None
        
        logger.info("TestRunner initialized")
        logger.info(f"Test config: {self.config}")
    
    def _initialize_hardware(self):
        """Initialize all hardware controllers."""
        try:
            # Initialize relay controller (shared by all)
            self.relay_controller = RelayController()
            
            # Initialize solenoid valves
            self.solenoid_valves = SolenoidValves(self.relay_controller)
            
            # Initialize cylinders
            self.cylinders = Cylinders(self.relay_controller)
            
            # Initialize pressure calibration
            self.pressure_calibration = PressureCalibration(
                min_pressure_psi=0.0,
                max_pressure_psi=15.0
            )
            
            logger.info("✓ All hardware controllers initialized")
            
        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            raise
    
    def _set_phase(self, phase: TestPhase):
        """
        Set the current test phase and notify callback.
        
        Args:
            phase: New test phase
        """
        if self.current_phase != phase:
            old_phase = self.current_phase
            self.current_phase = phase
            
            logger.info(f"Phase transition: {old_phase.value} → {phase.value}")
            
            # Call phase callback if provided
            if self.phase_callback:
                try:
                    self.phase_callback(phase)
                except Exception as e:
                    logger.error(f"Phase callback error: {e}")
    
    def _log_pressure(self, context: str = ""):
        """Log current pressure reading."""
        try:
            pressure = self.pressure_calibration.read_pressure_psi(num_samples=3)
            logger.info(f"Pressure reading{' (' + context + ')' if context else ''}: {pressure:.2f} PSI")
            return pressure
        except Exception as e:
            logger.error(f"Failed to read pressure: {e}")
            return 0.0
    
    def _check_safety_limits(self) -> bool:
        """
        Check if system is within safety limits.
        
        Returns:
            bool: True if safe, False if safety limit exceeded
        """
        try:
            pressure = self.pressure_calibration.read_pressure_psi()
            
            if pressure > self.config.max_pressure:
                logger.error(f"Pressure safety limit exceeded: {pressure:.2f} > {self.config.max_pressure} PSI")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            return False
    
    def run_test(self) -> TestResult:
        """
        Run the complete leak test sequence.
        
        Returns:
            TestResult: Final test result
        """
        logger.info("=" * 50)
        logger.info("STARTING LEAK TEST")
        logger.info("=" * 50)
        
        self.is_testing = True
        self.start_time = datetime.now()
        self.test_result = TestResult.NONE
        self.test_data = {
            "start_time": self.start_time,
            "pressure_readings": [],
            "phases": []
        }
        
        try:
            # Execute test sequence
            if self._phase_extend_cylinders():
                if self._phase_fill_dut():
                    if self._phase_stabilize():
                        if self._phase_isolate():
                            if self._phase_test():
                                if self._phase_evaluate():
                                    # Test completed successfully
                                    pass
            
            # Always run cleanup phases
            self._phase_exhaust()
            self._phase_retract_cylinders()
            
            # Set final phase
            if self.test_result == TestResult.NONE:
                self.test_result = TestResult.ERROR
                
            self._set_phase(TestPhase.COMPLETE)
            
        except Exception as e:
            logger.error(f"Test sequence error: {e}")
            self.test_result = TestResult.ERROR
            self._set_phase(TestPhase.ERROR)
            
            # Emergency cleanup
            self._emergency_stop()
            
        finally:
            self.is_testing = False
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds()
            
            self.test_data["end_time"] = end_time
            self.test_data["duration"] = duration
            self.test_data["result"] = self.test_result.value
            
            logger.info("=" * 50)
            logger.info(f"TEST COMPLETED: {self.test_result.value}")
            logger.info(f"Duration: {duration:.1f} seconds")
            logger.info("=" * 50)
        
        return self.test_result
    
    def _phase_extend_cylinders(self) -> bool:
        """Phase 1: Extend pneumatic cylinders."""
        self._set_phase(TestPhase.EXTENDING_CYLINDERS)
        
        try:
            logger.info(f"Extending cylinders for {self.config.cylinder_extend_time}s")
            success = self.cylinders.extend(duration=self.config.cylinder_extend_time)
            
            if success:
                logger.info("✓ Cylinders extended successfully")
                return True
            else:
                logger.error("✗ Failed to extend cylinders")
                self.test_result = TestResult.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Cylinder extension error: {e}")
            self.test_result = TestResult.ERROR
            return False
    
    def _phase_fill_dut(self) -> bool:
        """Phase 2: Fill DUT with pressurized air."""
        self._set_phase(TestPhase.FILLING_DUT)
        
        try:
            logger.info(f"Filling DUT for {self.config.fill_time}s")
            self._log_pressure("before fill")
            
            # Open fill valve
            success = self.solenoid_valves.fill(duration=self.config.fill_time)
            
            if success:
                # Check pressure after filling
                pressure = self._log_pressure("after fill")
                
                if pressure >= (self.config.target_fill_pressure - self.config.pressure_tolerance):
                    logger.info("✓ DUT filled successfully")
                    return True
                else:
                    logger.warning(f"Fill pressure low: {pressure:.2f} < {self.config.target_fill_pressure:.2f} PSI")
                    # Continue test anyway for now
                    return True
            else:
                logger.error("✗ Failed to fill DUT")
                self.test_result = TestResult.ERROR
                return False
                
        except Exception as e:
            logger.error(f"DUT fill error: {e}")
            self.test_result = TestResult.ERROR
            return False
    
    def _phase_stabilize(self) -> bool:
        """Phase 3: Allow pressure to stabilize."""
        self._set_phase(TestPhase.STABILIZING)
        
        try:
            logger.info(f"Stabilizing pressure for {self.config.stabilize_time}s")
            
            # Log pressure every few seconds during stabilization
            stabilize_start = time.time()
            while (time.time() - stabilize_start) < self.config.stabilize_time:
                if not self._check_safety_limits():
                    self.test_result = TestResult.ERROR
                    return False
                
                self._log_pressure("stabilizing")
                time.sleep(2.0)  # Log every 2 seconds
            
            logger.info("✓ Pressure stabilization complete")
            return True
            
        except Exception as e:
            logger.error(f"Stabilization error: {e}")
            self.test_result = TestResult.ERROR
            return False
    
    def _phase_isolate(self) -> bool:
        """Phase 4: Isolate DUT (close all valves)."""
        self._set_phase(TestPhase.ISOLATING)
        
        try:
            logger.info("Isolating DUT (closing all valves)")
            
            # Ensure all valves are closed
            success = self.solenoid_valves.close_all_valves()
            
            if success:
                self._log_pressure("isolated")
                logger.info("✓ DUT isolated successfully")
                return True
            else:
                logger.error("✗ Failed to isolate DUT")
                self.test_result = TestResult.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Isolation error: {e}")
            self.test_result = TestResult.ERROR
            return False
    
    def _phase_test(self) -> bool:
        """Phase 5: Record pressure during test period."""
        self._set_phase(TestPhase.TESTING)
        
        try:
            logger.info(f"Recording pressure for {self.config.test_duration}s")
            
            # Record initial pressure
            start_pressure = self._log_pressure("test start")
            test_start_time = time.time()
            
            pressure_readings = [(0.0, start_pressure)]
            
            # Record pressure throughout test
            while (time.time() - test_start_time) < self.config.test_duration:
                if not self._check_safety_limits():
                    self.test_result = TestResult.ERROR
                    return False
                
                elapsed = time.time() - test_start_time
                pressure = self.pressure_calibration.read_pressure_psi()
                pressure_readings.append((elapsed, pressure))
                
                logger.info(f"Test pressure [{elapsed:.1f}s]: {pressure:.2f} PSI")
                
                time.sleep(1.0)  # Record every second
            
            # Store pressure data for evaluation
            self.test_data["pressure_readings"] = pressure_readings
            
            logger.info("✓ Pressure recording complete")
            return True
            
        except Exception as e:
            logger.error(f"Test recording error: {e}")
            self.test_result = TestResult.ERROR
            return False
    
    def _phase_evaluate(self) -> bool:
        """Phase 6: Evaluate test results."""
        self._set_phase(TestPhase.EVALUATING)
        
        try:
            logger.info("Evaluating test results")
            
            pressure_readings = self.test_data.get("pressure_readings", [])
            
            if len(pressure_readings) < 2:
                logger.error("Insufficient pressure data for evaluation")
                self.test_result = TestResult.ERROR
                return False
            
            # Calculate pressure drop rate
            start_pressure = pressure_readings[0][1]
            end_pressure = pressure_readings[-1][1]
            duration = pressure_readings[-1][0]
            
            pressure_drop = start_pressure - end_pressure
            leak_rate = pressure_drop / duration if duration > 0 else 0
            
            logger.info(f"Start pressure: {start_pressure:.2f} PSI")
            logger.info(f"End pressure: {end_pressure:.2f} PSI")
            logger.info(f"Pressure drop: {pressure_drop:.2f} PSI")
            logger.info(f"Leak rate: {leak_rate:.3f} PSI/s")
            logger.info(f"Max allowed leak rate: {self.config.max_leak_rate:.3f} PSI/s")
            
            # Store evaluation data
            self.test_data["start_pressure"] = start_pressure
            self.test_data["end_pressure"] = end_pressure
            self.test_data["pressure_drop"] = pressure_drop
            self.test_data["leak_rate"] = leak_rate
            
            # Determine pass/fail
            if leak_rate <= self.config.max_leak_rate:
                self.test_result = TestResult.PASS
                logger.info("✓ TEST RESULT: PASS")
            else:
                self.test_result = TestResult.FAIL
                logger.info("✗ TEST RESULT: FAIL")
            
            return True
            
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            self.test_result = TestResult.ERROR
            return False
    
    def _phase_exhaust(self) -> bool:
        """Phase 7: Exhaust pressure from DUT."""
        self._set_phase(TestPhase.EXHAUSTING)
        
        try:
            logger.info(f"Exhausting DUT for {self.config.exhaust_time}s")
            self._log_pressure("before exhaust")
            
            success = self.solenoid_valves.exhaust(duration=self.config.exhaust_time)
            
            if success:
                self._log_pressure("after exhaust")
                logger.info("✓ DUT exhausted successfully")
                return True
            else:
                logger.error("✗ Failed to exhaust DUT")
                return False
                
        except Exception as e:
            logger.error(f"Exhaust error: {e}")
            return False
    
    def _phase_retract_cylinders(self) -> bool:
        """Phase 8: Retract pneumatic cylinders."""
        self._set_phase(TestPhase.RETRACTING_CYLINDERS)
        
        try:
            logger.info(f"Retracting cylinders for {self.config.cylinder_retract_time}s")
            success = self.cylinders.retract(duration=self.config.cylinder_retract_time)
            
            if success:
                logger.info("✓ Cylinders retracted successfully")
                return True
            else:
                logger.error("✗ Failed to retract cylinders")
                return False
                
        except Exception as e:
            logger.error(f"Cylinder retraction error: {e}")
            return False
    
    def _emergency_stop(self):
        """Emergency stop - turn off all hardware."""
        logger.warning("EMERGENCY STOP - Turning off all hardware")
        
        try:
            # Turn off all solenoids
            self.solenoid_valves.close_all_valves()
            self.cylinders.stop()
            
            # Turn off all relays
            self.relay_controller.turn_off_all()
            
            logger.info("Emergency stop completed")
            
        except Exception as e:
            logger.error(f"Emergency stop error: {e}")
    
    def get_test_data(self) -> Dict[str, Any]:
        """Get complete test data."""
        return self.test_data.copy()
    
    def is_test_running(self) -> bool:
        """Check if test is currently running."""
        return self.is_testing
    
    def get_current_phase(self) -> TestPhase:
        """Get current test phase."""
        return self.current_phase
    
    def close(self):
        """Clean up resources."""
        logger.info("Closing test runner")
        
        if self.is_testing:
            logger.warning("Test in progress - performing emergency stop")
            self._emergency_stop()
        
        # Close hardware controllers
        try:
            self.solenoid_valves.close()
            self.cylinders.close()
            # relay_controller is closed by solenoid_valves
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Test the test runner framework."""
    print("=== Test Runner Framework Test ===")
    
    try:
        # Create test configuration
        config = TestConfig(
            # Use shorter times for testing
            cylinder_extend_time=1.0,
            fill_time=2.0,
            stabilize_time=3.0,
            test_duration=5.0,
            exhaust_time=1.0,
            cylinder_retract_time=1.0
        )
        
        # Phase callback for testing
        def phase_callback(phase: TestPhase):
            print(f"UI UPDATE: Phase changed to {phase.value}")
        
        # Create and run test
        test_runner = TestRunner(config=config, phase_callback=phase_callback)
        
        print("Starting test sequence...")
        result = test_runner.run_test()
        
        print(f"\nTest completed with result: {result.value}")
        print("\nTest data:")
        test_data = test_runner.get_test_data()
        for key, value in test_data.items():
            if key != "pressure_readings":  # Skip detailed pressure data
                print(f"  {key}: {value}")
        
        test_runner.close()
        
    except Exception as e:
        print(f"Test runner test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 