#!/usr/bin/env python3
"""
Data Logger Service

Comprehensive data logging system for the EOL Leak Tester.
Records test results, pressure data, and system events to CSV files.
"""

import csv
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from dataclasses import dataclass, asdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestRecord:
    """Data class for test result records."""
    timestamp: str
    test_id: str
    result: str  # PASS, FAIL, ERROR
    duration: float
    start_pressure: float
    end_pressure: float
    pressure_drop: float
    leak_rate: float
    max_pressure_reached: float
    target_fill_pressure: float
    max_leak_rate_allowed: float
    cylinder_extend_time: float
    fill_time: float
    stabilize_time: float
    test_duration: float
    exhaust_time: float
    cylinder_retract_time: float
    notes: str = ""

@dataclass
class PressureReading:
    """Data class for individual pressure readings."""
    timestamp: str
    test_id: str
    phase: str
    elapsed_time: float
    pressure_psi: float
    raw_current_ma: float = 0.0

@dataclass
class SystemEvent:
    """Data class for system events."""
    timestamp: str
    level: str  # INFO, WARNING, ERROR
    component: str
    event: str
    details: str = ""

class DataLogger:
    """
    Data logging service for the EOL Leak Tester.
    
    Manages logging of:
    - Test results and metadata
    - Detailed pressure readings during tests
    - System events and errors
    - Performance metrics
    """
    
    def __init__(self, log_directory: str = "data/logs"):
        """
        Initialize the data logger.
        
        Args:
            log_directory: Directory to store log files
        """
        self.log_directory = Path(log_directory)
        self.current_test_id = None
        self.current_test_data = {}
        
        # Create log directory if it doesn't exist
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Define file paths
        self.test_results_file = self.log_directory / "test_results.csv"
        self.pressure_data_file = self.log_directory / "pressure_data.csv"
        self.system_events_file = self.log_directory / "system_events.csv"
        self.daily_summary_file = self.log_directory / f"daily_summary_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Initialize CSV files with headers
        self._initialize_csv_files()
        
        logger.info(f"DataLogger initialized with log directory: {self.log_directory}")
        
    def _initialize_csv_files(self):
        """Initialize CSV files with appropriate headers."""
        # Test results file
        if not self.test_results_file.exists():
            with open(self.test_results_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'test_id', 'result', 'duration', 'start_pressure',
                    'end_pressure', 'pressure_drop', 'leak_rate', 'max_pressure_reached',
                    'target_fill_pressure', 'max_leak_rate_allowed', 'cylinder_extend_time',
                    'fill_time', 'stabilize_time', 'test_duration', 'exhaust_time',
                    'cylinder_retract_time', 'notes'
                ])
        
        # Pressure data file
        if not self.pressure_data_file.exists():
            with open(self.pressure_data_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'test_id', 'phase', 'elapsed_time',
                    'pressure_psi', 'raw_current_ma'
                ])
        
        # System events file
        if not self.system_events_file.exists():
            with open(self.system_events_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'level', 'component', 'event', 'details'
                ])
        
        # Daily summary file
        if not self.daily_summary_file.exists():
            with open(self.daily_summary_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'date', 'total_tests', 'pass_count', 'fail_count', 'error_count',
                    'pass_rate', 'avg_test_duration', 'avg_leak_rate', 'min_pressure',
                    'max_pressure', 'avg_pressure_drop'
                ])
    
    def start_test_session(self, config: Dict[str, Any]) -> str:
        """
        Start a new test session.
        
        Args:
            config: Test configuration parameters
            
        Returns:
            str: Unique test ID
        """
        # Generate unique test ID
        timestamp = datetime.now()
        self.current_test_id = f"TEST_{timestamp.strftime('%Y%m%d_%H%M%S')}_{timestamp.microsecond//1000:03d}"
        
        # Store test configuration
        self.current_test_data = {
            'test_id': self.current_test_id,
            'start_time': timestamp,
            'config': config,
            'pressure_readings': [],
            'events': []
        }
        
        # Log test start event
        self.log_system_event('INFO', 'TestRunner', f'Test session started: {self.current_test_id}')
        
        logger.info(f"Started test session: {self.current_test_id}")
        return self.current_test_id
    
    def log_pressure_reading(self, 
                           phase: str, 
                           elapsed_time: float, 
                           pressure_psi: float,
                           raw_current_ma: float = 0.0):
        """
        Log a pressure reading during test.
        
        Args:
            phase: Current test phase
            elapsed_time: Elapsed time since test start (seconds)
            pressure_psi: Pressure reading in PSI
            raw_current_ma: Raw current reading in mA
        """
        if not self.current_test_id:
            logger.warning("No active test session for pressure reading")
            return
        
        timestamp = datetime.now().isoformat()
        
        # Create pressure reading record
        reading = PressureReading(
            timestamp=timestamp,
            test_id=self.current_test_id,
            phase=phase,
            elapsed_time=elapsed_time,
            pressure_psi=pressure_psi,
            raw_current_ma=raw_current_ma
        )
        
        # Store in current test data
        self.current_test_data['pressure_readings'].append(asdict(reading))
        
        # Write to CSV file
        try:
            with open(self.pressure_data_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    reading.timestamp, reading.test_id, reading.phase,
                    reading.elapsed_time, reading.pressure_psi, reading.raw_current_ma
                ])
        except Exception as e:
            logger.error(f"Failed to write pressure reading to CSV: {e}")
    
    def log_test_result(self, 
                       result: str,
                       duration: float,
                       test_data: Dict[str, Any],
                       notes: str = ""):
        """
        Log final test result.
        
        Args:
            result: Test result (PASS, FAIL, ERROR)
            duration: Test duration in seconds
            test_data: Complete test data from TestRunner
            notes: Optional notes about the test
        """
        if not self.current_test_id:
            logger.warning("No active test session for test result")
            return
        
        timestamp = datetime.now().isoformat()
        
        # Extract data with defaults
        start_pressure = test_data.get('start_pressure', 0.0)
        end_pressure = test_data.get('end_pressure', 0.0)
        pressure_drop = test_data.get('pressure_drop', 0.0)
        leak_rate = test_data.get('leak_rate', 0.0)
        
        # Calculate max pressure from readings
        pressure_readings = test_data.get('pressure_readings', [])
        max_pressure = max([reading[1] for reading in pressure_readings]) if pressure_readings else 0.0
        
        # Get config parameters
        config = self.current_test_data.get('config', {})
        
        # Create test record
        test_record = TestRecord(
            timestamp=timestamp,
            test_id=self.current_test_id,
            result=result,
            duration=duration,
            start_pressure=start_pressure,
            end_pressure=end_pressure,
            pressure_drop=pressure_drop,
            leak_rate=leak_rate,
            max_pressure_reached=max_pressure,
            target_fill_pressure=config.get('target_fill_pressure', 0.0),
            max_leak_rate_allowed=config.get('max_leak_rate', 0.0),
            cylinder_extend_time=config.get('cylinder_extend_time', 0.0),
            fill_time=config.get('fill_time', 0.0),
            stabilize_time=config.get('stabilize_time', 0.0),
            test_duration=config.get('test_duration', 0.0),
            exhaust_time=config.get('exhaust_time', 0.0),
            cylinder_retract_time=config.get('cylinder_retract_time', 0.0),
            notes=notes
        )
        
        # Write to CSV file
        try:
            with open(self.test_results_file, 'a', newline='') as f:
                writer = csv.writer(f)
                row_data = [getattr(test_record, field.name) for field in test_record.__dataclass_fields__.values()]
                writer.writerow(row_data)
                
            logger.info(f"Test result logged: {result} for {self.current_test_id}")
            
        except Exception as e:
            logger.error(f"Failed to write test result to CSV: {e}")
        
        # Log test completion event
        self.log_system_event('INFO', 'TestRunner', 
                             f'Test completed: {result} in {duration:.1f}s, leak rate: {leak_rate:.3f} PSI/s')
        
        # Save detailed test data as JSON
        self._save_detailed_test_data(test_record, test_data)
        
        # Update daily summary
        self._update_daily_summary()
        
        # Clear current test data
        self.current_test_id = None
        self.current_test_data = {}
    
    def log_system_event(self, 
                        level: str, 
                        component: str, 
                        event: str, 
                        details: str = ""):
        """
        Log a system event.
        
        Args:
            level: Event level (INFO, WARNING, ERROR)
            component: System component that generated the event
            event: Event description
            details: Additional event details
        """
        timestamp = datetime.now().isoformat()
        
        # Create system event record
        system_event = SystemEvent(
            timestamp=timestamp,
            level=level,
            component=component,
            event=event,
            details=details
        )
        
        # Store in current test data if test is active
        if self.current_test_id:
            self.current_test_data['events'].append(asdict(system_event))
        
        # Write to CSV file
        try:
            with open(self.system_events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    system_event.timestamp, system_event.level, system_event.component,
                    system_event.event, system_event.details
                ])
        except Exception as e:
            logger.error(f"Failed to write system event to CSV: {e}")
    
    def _save_detailed_test_data(self, test_record: TestRecord, test_data: Dict[str, Any]):
        """Save detailed test data as JSON file."""
        try:
            # Create detailed test data directory
            detailed_dir = self.log_directory / "detailed_tests"
            detailed_dir.mkdir(exist_ok=True)
            
            # Prepare detailed data
            detailed_data = {
                'test_record': asdict(test_record),
                'test_data': test_data,
                'current_test_data': self.current_test_data
            }
            
            # Save as JSON file
            json_file = detailed_dir / f"{self.current_test_id}_detailed.json"
            with open(json_file, 'w') as f:
                json.dump(detailed_data, f, indent=2, default=str)
                
            logger.info(f"Detailed test data saved: {json_file}")
            
        except Exception as e:
            logger.error(f"Failed to save detailed test data: {e}")
    
    def _update_daily_summary(self):
        """Update daily summary statistics."""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Read existing test results for today
            today_tests = []
            if self.test_results_file.exists():
                with open(self.test_results_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        test_date = row['timestamp'][:10]  # Extract date part
                        if test_date == today:
                            today_tests.append(row)
            
            if not today_tests:
                return
            
            # Calculate statistics
            total_tests = len(today_tests)
            pass_count = sum(1 for test in today_tests if test['result'] == 'PASS')
            fail_count = sum(1 for test in today_tests if test['result'] == 'FAIL')
            error_count = sum(1 for test in today_tests if test['result'] == 'ERROR')
            pass_rate = (pass_count / total_tests * 100) if total_tests > 0 else 0
            
            # Calculate averages (only for successful tests)
            successful_tests = [test for test in today_tests if test['result'] in ['PASS', 'FAIL']]
            if successful_tests:
                avg_duration = sum(float(test['duration']) for test in successful_tests) / len(successful_tests)
                avg_leak_rate = sum(float(test['leak_rate']) for test in successful_tests) / len(successful_tests)
                min_pressure = min(float(test['start_pressure']) for test in successful_tests)
                max_pressure = max(float(test['max_pressure_reached']) for test in successful_tests)
                avg_pressure_drop = sum(float(test['pressure_drop']) for test in successful_tests) / len(successful_tests)
            else:
                avg_duration = avg_leak_rate = min_pressure = max_pressure = avg_pressure_drop = 0.0
            
            # Write/update daily summary
            summary_row = [
                today, total_tests, pass_count, fail_count, error_count,
                f"{pass_rate:.1f}%", f"{avg_duration:.1f}", f"{avg_leak_rate:.3f}",
                f"{min_pressure:.2f}", f"{max_pressure:.2f}", f"{avg_pressure_drop:.2f}"
            ]
            
            # Read existing summary and update or append
            existing_summaries = []
            if self.daily_summary_file.exists():
                with open(self.daily_summary_file, 'r') as f:
                    reader = csv.reader(f)
                    existing_summaries = list(reader)
            
            # Find and update today's entry or append new one
            updated = False
            for i, row in enumerate(existing_summaries[1:], 1):  # Skip header
                if row and row[0] == today:
                    existing_summaries[i] = summary_row
                    updated = True
                    break
            
            if not updated:
                existing_summaries.append(summary_row)
            
            # Write back to file
            with open(self.daily_summary_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(existing_summaries)
                
            logger.info(f"Daily summary updated: {total_tests} tests, {pass_rate:.1f}% pass rate")
            
        except Exception as e:
            logger.error(f"Failed to update daily summary: {e}")
    
    def get_test_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get test statistics for the specified number of days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict containing test statistics
        """
        try:
            from datetime import timedelta
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Read test results
            test_results = []
            if self.test_results_file.exists():
                with open(self.test_results_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        test_date = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None)
                        if start_date <= test_date <= end_date:
                            test_results.append(row)
            
            # Calculate statistics
            total_tests = len(test_results)
            if total_tests == 0:
                return {'error': 'No test data available for the specified period'}
            
            pass_count = sum(1 for test in test_results if test['result'] == 'PASS')
            fail_count = sum(1 for test in test_results if test['result'] == 'FAIL')
            error_count = sum(1 for test in test_results if test['result'] == 'ERROR')
            
            successful_tests = [test for test in test_results if test['result'] in ['PASS', 'FAIL']]
            
            stats = {
                'period_days': days,
                'total_tests': total_tests,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'error_count': error_count,
                'pass_rate': (pass_count / total_tests * 100) if total_tests > 0 else 0,
                'avg_duration': 0,
                'avg_leak_rate': 0,
                'min_pressure': 0,
                'max_pressure': 0,
                'avg_pressure_drop': 0
            }
            
            if successful_tests:
                stats.update({
                    'avg_duration': sum(float(test['duration']) for test in successful_tests) / len(successful_tests),
                    'avg_leak_rate': sum(float(test['leak_rate']) for test in successful_tests) / len(successful_tests),
                    'min_pressure': min(float(test['start_pressure']) for test in successful_tests),
                    'max_pressure': max(float(test['max_pressure_reached']) for test in successful_tests),
                    'avg_pressure_drop': sum(float(test['pressure_drop']) for test in successful_tests) / len(successful_tests)
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate test statistics: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Clean up data logger resources."""
        logger.info("Closing data logger")
        
        # Log final system event if test is active
        if self.current_test_id:
            self.log_system_event('WARNING', 'DataLogger', 
                                f'Test session {self.current_test_id} terminated during logging cleanup')

def main():
    """Test the data logger."""
    print("=== Data Logger Test ===")
    
    try:
        # Create data logger
        logger = DataLogger()
        
        # Test configuration
        test_config = {
            'target_fill_pressure': 10.0,
            'max_leak_rate': 0.1,
            'cylinder_extend_time': 3.0,
            'fill_time': 5.0,
            'stabilize_time': 10.0,
            'test_duration': 30.0,
            'exhaust_time': 5.0,
            'cylinder_retract_time': 3.0
        }
        
        # Start test session
        test_id = logger.start_test_session(test_config)
        print(f"Started test session: {test_id}")
        
        # Log some pressure readings
        phases = ['Extending cylinders', 'Filling DUT', 'Stabilizing', 'Testing']
        for i, phase in enumerate(phases):
            for j in range(3):
                elapsed = i * 10 + j * 2
                pressure = 5.0 + i * 2 + j * 0.5
                logger.log_pressure_reading(phase, elapsed, pressure, 12.0 + pressure * 0.8)
        
        # Log some system events
        logger.log_system_event('INFO', 'SolenoidValves', 'Fill valve opened')
        logger.log_system_event('WARNING', 'PressureTransducer', 'Pressure reading fluctuation detected')
        
        # Log test result
        test_data = {
            'start_pressure': 10.5,
            'end_pressure': 10.3,
            'pressure_drop': 0.2,
            'leak_rate': 0.007,
            'pressure_readings': [(0, 10.5), (30, 10.3)]
        }
        logger.log_test_result('PASS', 56.7, test_data, 'Normal test completion')
        
        # Get statistics
        stats = logger.get_test_statistics(7)
        print("\nTest Statistics (7 days):")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Close logger
        logger.close()
        
        print("\nData logger test completed successfully")
        print(f"Check log files in: {logger.log_directory}")
        
    except Exception as e:
        print(f"Data logger test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 