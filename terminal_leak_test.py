#!/usr/bin/env python3
"""
Terminal Leak Test Script

Standalone leak tester that runs in terminal without pneumatic cylinders.
Uses existing architecture and follows same process logic as full-scale tester.

Test Sequence:
1. Fill: Open fill valve
2. Stabilize: Close fill valve  
3. Test: Monitor pressure decay
4. Exhaust: Open exhaust valve

Continuously outputs pressure and reports final metrics.
"""

import time
import signal
import sys
from datetime import datetime
from typing import Optional
import numpy as np

# Import existing controllers
from controllers.pressure_calibration import PressureCalibration
from controllers.solenoid_valves import SolenoidValves
from controllers.relay_controller import RelayController
from config.config_manager import get_config_manager

class TerminalLeakTester:
    """
    Terminal-based leak tester using existing architecture.
    Simplified test sequence without pneumatic cylinders.
    """
    
    def __init__(self):
        """Initialize the terminal leak tester."""
        print("=== Terminal Leak Tester ===")
        print("Initializing system...")
        
        # Load configuration
        self.config_manager = get_config_manager()
        
        # Initialize hardware controllers
        try:
            # Initialize relay controller and solenoid valves
            self.relay_controller = RelayController()
            self.solenoid_valves = SolenoidValves(self.relay_controller)
            
            # Initialize pressure calibration
            self.pressure_calibration = PressureCalibration()
            
            print("✓ Hardware controllers initialized")
            
        except Exception as e:
            print(f"✗ Hardware initialization failed: {e}")
            raise
        
        # Load test configuration
        self.test_config = self.config_manager.get_test_config_for_runner()
        
        # Test parameters (simplified for isolated testing)
        self.fill_time = self.test_config['fill_time']
        self.stabilize_time = self.test_config['stabilize_time'] 
        self.test_duration = self.test_config['test_duration']
        self.exhaust_time = self.test_config['exhaust_time']
        
        # Volume for leak rate calculation
        volume_config = self.config_manager.get_system_config('test_parameters')
        self.test_volume_cc = volume_config.get('volume', {}).get('test_volume_cc', 100.0)
        
        # Test data storage
        self.test_data = {
            'times': [],
            'pressures': [],
            'start_pressure': 0.0,
            'end_pressure': 0.0,
            'pressure_decay': 0.0,
            'leak_rate_sccm': 0.0
        }
        
        # Set up signal handler for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        print(f"✓ Test configuration loaded:")
        print(f"  Fill time: {self.fill_time}s")
        print(f"  Stabilize time: {self.stabilize_time}s") 
        print(f"  Test duration: {self.test_duration}s")
        print(f"  Exhaust time: {self.exhaust_time}s")
        print(f"  Test volume: {self.test_volume_cc} cc")
        print()
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C for clean shutdown."""
        print("\n\n=== Emergency Stop ===")
        print("Stopping test and closing all valves...")
        try:
            self.solenoid_valves.close_all_valves()
            print("✓ All valves closed safely")
        except Exception as e:
            print(f"✗ Error closing valves: {e}")
        print("Test terminated by user")
        sys.exit(0)
    
    def _read_pressure(self) -> float:
        """Read current pressure with error handling."""
        try:
            return self.pressure_calibration.read_pressure_psi()
        except Exception as e:
            print(f"⚠ Pressure reading error: {e}")
            return 0.0
    
    def _log_pressure(self, phase: str, elapsed_time: float) -> float:
        """Log pressure reading with timestamp."""
        pressure = self._read_pressure()
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        
        print(f"[{timestamp}] {phase:<12} | {elapsed_time:6.1f}s | {pressure:8.4f} PSI")
        
        return pressure
    
    def _calculate_pressure_decay(self, times, pressures):
        """Calculate pressure decay rate using linear regression."""
        if len(times) < 2 or len(pressures) < 2:
            return 0.0
        
        try:
            times_array = np.array(times)
            pressures_array = np.array(pressures)
            
            # Calculate best fit slope (dP/dT)
            slope, intercept = np.polyfit(times_array, pressures_array, 1)
            
            return slope  # PSI/s (negative for decay)
            
        except Exception as e:
            print(f"⚠ Pressure decay calculation error: {e}")
            return 0.0
    
    def _calculate_leak_rate(self, pressure_decay_psi_s):
        """Calculate leak rate in sccm from pressure decay."""
        try:
            # Formula: LR [sccm] = V[cc] * dP/dT * 60[s/min] / 14.69[psi]
            leak_rate_sccm = (self.test_volume_cc * 
                             pressure_decay_psi_s * 
                             60.0) / 14.69
            
            return abs(leak_rate_sccm)  # Return positive leak rate
            
        except Exception as e:
            print(f"⚠ Leak rate calculation error: {e}")
            return 0.0
    
    def _phase_fill(self) -> bool:
        """Phase 1: Fill DUT by opening fill valve."""
        start_time = time.time()
        
        try:
            # Open fill valve
            if not self.solenoid_valves.fill(duration=self.fill_time):
                print("✗ Failed to operate fill valve")
                return False
            
            # Monitor pressure during fill
            while (time.time() - start_time) < self.fill_time:
                elapsed = time.time() - start_time
                self._log_pressure("FILLING", elapsed)
                time.sleep(0.2)  # High frequency monitoring (5 Hz)
            return True
            
        except Exception as e:
            print(f"✗ Fill phase error: {e}")
            return False
    
    def _phase_stabilize(self) -> bool:
        """Phase 2: Stabilize pressure with all valves closed."""
        start_time = time.time()
        
        try:
            # Ensure all valves are closed
            if not self.solenoid_valves.close_all_valves():
                print("✗ Failed to close valves")
                return False
            
            # Monitor pressure during stabilization
            while (time.time() - start_time) < self.stabilize_time:
                elapsed = time.time() - start_time
                self._log_pressure("STABILIZING", elapsed)
                time.sleep(0.2)  # High frequency monitoring (5 Hz)
            return True
            
        except Exception as e:
            print(f"✗ Stabilization phase error: {e}")
            return False
    
    def _phase_test(self) -> bool:
        """Phase 3: Test phase - monitor pressure decay."""
        start_time = time.time()
        test_times = []
        test_pressures = []
        
        try:
            # Record initial pressure
            initial_pressure = self._read_pressure()
            self.test_data['start_pressure'] = initial_pressure
            
            # Monitor pressure throughout test
            while (time.time() - start_time) < self.test_duration:
                elapsed = time.time() - start_time
                pressure = self._log_pressure("TESTING", elapsed)
                
                # Store data for analysis
                test_times.append(elapsed)
                test_pressures.append(pressure)
                
                time.sleep(0.2)  # High frequency monitoring (5 Hz)
            
            # Record final pressure
            final_pressure = self._read_pressure()
            self.test_data['end_pressure'] = final_pressure
            
            # Store test data
            self.test_data['times'] = test_times
            self.test_data['pressures'] = test_pressures
            return True
            
        except Exception as e:
            print(f"✗ Test phase error: {e}")
            return False
    
    def _phase_exhaust(self) -> bool:
        """Phase 4: Exhaust DUT by opening exhaust valve."""
        start_time = time.time()
        
        try:
            # Open exhaust valve
            if not self.solenoid_valves.exhaust(duration=self.exhaust_time):
                print("✗ Failed to operate exhaust valve")
                return False
            
            # Monitor pressure during exhaust
            while (time.time() - start_time) < self.exhaust_time:
                elapsed = time.time() - start_time
                self._log_pressure("EXHAUSTING", elapsed)
                time.sleep(0.2)  # High frequency monitoring (5 Hz)
            return True
            
        except Exception as e:
            print(f"✗ Exhaust phase error: {e}")
            return False
    
    def _analyze_results(self):
        """Analyze test results and calculate metrics."""
        print("\n" + "=" * 60)
        print("LEAK TEST ANALYSIS")
        print("=" * 60)
        
        if len(self.test_data['times']) < 2:
            print("✗ Insufficient data for analysis")
            return
        
        # Calculate pressure loss
        pressure_loss = self.test_data['start_pressure'] - self.test_data['end_pressure']
        
        # Calculate pressure decay rate (dP/dT)
        pressure_decay = self._calculate_pressure_decay(
            self.test_data['times'], 
            self.test_data['pressures']
        )
        
        # Calculate leak rate
        leak_rate = self._calculate_leak_rate(pressure_decay)
        
        # Store results
        self.test_data['pressure_decay'] = pressure_decay
        self.test_data['leak_rate_sccm'] = leak_rate
        
        # Display results
        print(f"Test Duration:       {self.test_duration:.1f} seconds")
        print(f"Test Volume:         {self.test_volume_cc:.0f} cc")
        print()
        print("PRESSURE ANALYSIS:")
        print(f"  Start Pressure:    {self.test_data['start_pressure']:.4f} PSI")
        print(f"  End Pressure:      {self.test_data['end_pressure']:.4f} PSI")
        print(f"  Total Loss:        {pressure_loss:.4f} PSI")
        print()
        print("LEAK ANALYSIS:")
        print(f"  Pressure Decay:    {pressure_decay:.4f} PSI/s")
        print(f"  Leak Rate:         {leak_rate:.3f} sccm")
        
        print("=" * 60)
    
    def run_test(self) -> bool:
        """Run the complete leak test sequence."""
        print(f"\nStarting leak test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C at any time to emergency stop")
        print()
        
        # Display table header for continuous pressure monitoring
        print("Time     | Phase        | Elapsed | Pressure")
        print("-" * 50)
        
        try:
            # Run test sequence
            if not self._phase_fill():
                return False
            
            if not self._phase_stabilize():
                return False
            
            if not self._phase_test():
                return False
            
            if not self._phase_exhaust():
                return False
            
            # Analyze results
            self._analyze_results()
            
            return True
            
        except Exception as e:
            print(f"\n✗ Test sequence error: {e}")
            return False
        
        finally:
            # Ensure all valves are closed
            try:
                print("\nClosing all valves...")
                self.solenoid_valves.close_all_valves()
                print("✓ All valves closed safely")
            except Exception as e:
                print(f"⚠ Error closing valves: {e}")

def main():
    """Main entry point for terminal leak tester."""
    try:
        # Create and run leak tester
        tester = TerminalLeakTester()
        
        # Wait for user to start test
        input("\nPress Enter to start leak test (Ctrl+C to exit)...")
        
        # Run the test
        success = tester.run_test()
        
        if success:
            print("\n✓ Leak test completed successfully")
            return 0
        else:
            print("\n✗ Leak test failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        return 0
    except Exception as e:
        print(f"\n✗ Terminal leak tester error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 