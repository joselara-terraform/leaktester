#!/usr/bin/env python3
"""
High-Speed Pressure Data Collection Module

Optimized for maximum sampling rate from pressure transducer.
Minimizes overhead and maximizes data collection performance.
"""

import time
import logging
import threading
from datetime import datetime
from typing import List, Tuple, Optional, Callable
from collections import deque
import numpy as np

# Handle imports for both module use and standalone testing
try:
    from .adc_reader import ADCReader
    from ..config.config_manager import get_config_manager
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from controllers.adc_reader import ADCReader
    from config.config_manager import get_config_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HighSpeedPressureCollector:
    """
    High-speed pressure data collector optimized for maximum sampling rate.
    
    Features:
    - Continuous sampling without delays
    - Minimal processing overhead
    - Real-time data streaming
    - Configurable buffer sizes
    - Thread-safe operation
    """
    
    def __init__(self, 
                 adc_reader: Optional[ADCReader] = None,
                 buffer_size: int = 1000,
                 callback: Optional[Callable] = None):
        """
        Initialize high-speed pressure collector.
        
        Args:
            adc_reader: ADC reader instance (creates optimized one if None)
            buffer_size: Maximum number of samples to buffer
            callback: Optional callback for real-time data (timestamp, pressure)
        """
        # Load configuration
        self.config_manager = get_config_manager()
        
        # Initialize optimized ADC reader
        if adc_reader is None:
            adc_config = self.config_manager.get_adc_config_for_reader()
            # Override with maximum sample rate
            adc_config['sample_rate'] = 860  # Maximum ADS1115 rate
            self.adc_reader = ADCReader(**adc_config)
        else:
            self.adc_reader = adc_reader
            
        # Configuration
        self.buffer_size = buffer_size
        self.callback = callback
        
        # Data storage
        self.data_buffer = deque(maxlen=buffer_size)
        self.is_collecting = False
        self.collection_thread = None
        
        # Performance tracking
        self.start_time = None
        self.sample_count = 0
        self.last_sample_time = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info(f"HighSpeedPressureCollector initialized")
        logger.info(f"Buffer size: {buffer_size} samples")
        logger.info(f"ADC sample rate: {self.adc_reader.sample_rate} SPS")
    
    def start_collection(self) -> bool:
        """
        Start high-speed data collection.
        
        Returns:
            bool: True if started successfully
        """
        if self.is_collecting:
            logger.warning("Collection already in progress")
            return False
        
        logger.info("Starting high-speed pressure collection")
        
        self.is_collecting = True
        self.start_time = time.time()
        self.sample_count = 0
        
        # Start collection thread
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        
        logger.info("High-speed collection started")
        return True
    
    def stop_collection(self) -> dict:
        """
        Stop data collection and return performance statistics.
        
        Returns:
            dict: Collection statistics
        """
        if not self.is_collecting:
            logger.warning("Collection not in progress")
            return {}
        
        logger.info("Stopping high-speed pressure collection")
        
        self.is_collecting = False
        
        # Wait for thread to finish
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=2.0)
        
        # Calculate statistics
        stats = self._calculate_stats()
        
        logger.info(f"Collection stopped. Stats: {stats}")
        return stats
    
    def _collection_loop(self):
        """Main data collection loop (runs in separate thread)."""
        logger.info("Collection loop started")
        
        try:
            while self.is_collecting:
                # Get timestamp as close to reading as possible
                timestamp = time.time()
                
                # Read raw ADC value (fastest method)
                raw_value = self.adc_reader.read_raw_value()
                
                # Convert to pressure (minimal processing)
                current_ma = self.adc_reader.raw_adc_to_current_ma(raw_value)
                pressure_psi = self._fast_current_to_pressure(current_ma)
                
                # Store data point
                data_point = (timestamp, pressure_psi, current_ma, raw_value)
                
                with self._lock:
                    self.data_buffer.append(data_point)
                    self.sample_count += 1
                    self.last_sample_time = timestamp
                
                # Call real-time callback if provided
                if self.callback:
                    try:
                        self.callback(timestamp, pressure_psi)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                # Minimal delay to prevent CPU hogging (adjust as needed)
                # For maximum speed, you can remove this entirely
                time.sleep(0.0001)  # 100 microseconds
                
        except Exception as e:
            logger.error(f"Collection loop error: {e}")
        finally:
            logger.info("Collection loop ended")
    
    def _fast_current_to_pressure(self, current_ma: float) -> float:
        """
        Fast current to pressure conversion (minimal overhead).
        
        Args:
            current_ma: Current in milliamps
            
        Returns:
            float: Pressure in PSI
        """
        # Use linear interpolation for speed (avoid complex multi-point calculations)
        cal_config = self.config_manager.pressure_calibration
        
        # Linear conversion: P = (I - I_min) * (P_max - P_min) / (I_max - I_min) + P_min
        current_span = cal_config.full_scale_current_ma - cal_config.balance_current_ma
        pressure_span = self.config_manager.pressure_transducer.max_pressure_psi
        
        if current_span == 0:
            return 0.0
        
        pressure_psi = ((current_ma - cal_config.balance_current_ma) * pressure_span / current_span)
        return max(0.0, pressure_psi)  # Clamp to positive values
    
    def get_latest_data(self, num_samples: int = 10) -> List[Tuple[float, float, float, int]]:
        """
        Get the latest data samples.
        
        Args:
            num_samples: Number of latest samples to return
            
        Returns:
            List of (timestamp, pressure_psi, current_ma, raw_value) tuples
        """
        with self._lock:
            if len(self.data_buffer) == 0:
                return []
            
            # Get last N samples
            samples = list(self.data_buffer)[-num_samples:]
            return samples
    
    def get_all_data(self) -> List[Tuple[float, float, float, int]]:
        """
        Get all buffered data.
        
        Returns:
            List of (timestamp, pressure_psi, current_ma, raw_value) tuples
        """
        with self._lock:
            return list(self.data_buffer)
    
    def get_current_sampling_rate(self) -> float:
        """
        Get current effective sampling rate.
        
        Returns:
            float: Samples per second
        """
        if not self.start_time or self.sample_count == 0:
            return 0.0
        
        elapsed_time = time.time() - self.start_time
        if elapsed_time == 0:
            return 0.0
        
        return self.sample_count / elapsed_time
    
    def _calculate_stats(self) -> dict:
        """Calculate collection statistics."""
        if not self.start_time:
            return {}
        
        elapsed_time = time.time() - self.start_time
        avg_sample_rate = self.sample_count / elapsed_time if elapsed_time > 0 else 0
        
        # Get data statistics
        data = self.get_all_data()
        pressures = [point[1] for point in data] if data else []
        
        stats = {
            'total_samples': self.sample_count,
            'collection_time': elapsed_time,
            'avg_sample_rate': avg_sample_rate,
            'buffer_utilization': len(data) / self.buffer_size * 100,
            'pressure_stats': {
                'min': min(pressures) if pressures else 0,
                'max': max(pressures) if pressures else 0,
                'avg': sum(pressures) / len(pressures) if pressures else 0,
                'std': np.std(pressures) if pressures and len(pressures) > 1 else 0
            }
        }
        
        return stats
    
    def export_data(self, filename: str = None) -> str:
        """
        Export collected data to CSV file.
        
        Args:
            filename: Output filename (auto-generated if None)
            
        Returns:
            str: Filename of exported data
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"high_speed_pressure_data_{timestamp}.csv"
        
        data = self.get_all_data()
        
        try:
            with open(filename, 'w') as f:
                # Write header
                f.write("timestamp,elapsed_time,pressure_psi,current_ma,raw_adc\n")
                
                # Write data
                start_time = data[0][0] if data else 0
                for timestamp, pressure, current, raw_value in data:
                    elapsed = timestamp - start_time
                    f.write(f"{timestamp:.6f},{elapsed:.6f},{pressure:.6f},{current:.6f},{raw_value}\n")
            
            logger.info(f"Data exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ""
    
    def clear_buffer(self):
        """Clear the data buffer."""
        with self._lock:
            self.data_buffer.clear()
        logger.info("Data buffer cleared")

def benchmark_sampling_rates():
    """Benchmark different sampling configurations."""
    print("=== High-Speed Pressure Sampling Benchmark ===\n")
    
    config_manager = get_config_manager()
    
    # Test different configurations
    test_configs = [
        {'sample_rate': 128, 'description': 'Current (128 SPS)'},
        {'sample_rate': 250, 'description': 'Medium (250 SPS)'},
        {'sample_rate': 475, 'description': 'High (475 SPS)'},
        {'sample_rate': 860, 'description': 'Maximum (860 SPS)'},
    ]
    
    for config in test_configs:
        print(f"Testing {config['description']}...")
        
        # Create ADC with specific sample rate
        adc_config = config_manager.get_adc_config_for_reader()
        adc_config['sample_rate'] = config['sample_rate']
        adc_reader = ADCReader(**adc_config)
        
        # Create collector
        collector = HighSpeedPressureCollector(adc_reader=adc_reader, buffer_size=500)
        
        # Collect data for 2 seconds
        collector.start_collection()
        time.sleep(2.0)
        stats = collector.stop_collection()
        
        # Report results
        actual_rate = stats.get('avg_sample_rate', 0)
        efficiency = (actual_rate / config['sample_rate']) * 100 if config['sample_rate'] > 0 else 0
        
        print(f"  Configured: {config['sample_rate']} SPS")
        print(f"  Actual: {actual_rate:.1f} SPS")
        print(f"  Efficiency: {efficiency:.1f}%")
        print(f"  Samples: {stats.get('total_samples', 0)}")
        print()

if __name__ == "__main__":
    print("=== High-Speed Pressure Collection Test ===")
    
    try:
        # Real-time callback for demonstration
        def data_callback(timestamp, pressure):
            # Print every 100th sample to avoid spam
            if int(timestamp * 100) % 100 == 0:
                print(f"Real-time: {pressure:.3f} PSI at {timestamp:.3f}s")
        
        # Create collector
        collector = HighSpeedPressureCollector(
            buffer_size=1000,
            callback=data_callback
        )
        
        print("Starting 5-second high-speed collection...")
        collector.start_collection()
        
        # Monitor progress
        for i in range(5):
            time.sleep(1)
            rate = collector.get_current_sampling_rate()
            print(f"Current sampling rate: {rate:.1f} SPS")
        
        # Stop and get results
        stats = collector.stop_collection()
        
        print("\n--- Collection Results ---")
        print(f"Total samples: {stats['total_samples']}")
        print(f"Average rate: {stats['avg_sample_rate']:.1f} SPS")
        print(f"Collection time: {stats['collection_time']:.1f}s")
        print(f"Buffer utilization: {stats['buffer_utilization']:.1f}%")
        
        pressure_stats = stats['pressure_stats']
        print(f"Pressure range: {pressure_stats['min']:.3f} - {pressure_stats['max']:.3f} PSI")
        print(f"Average pressure: {pressure_stats['avg']:.3f} PSI")
        print(f"Pressure std dev: {pressure_stats['std']:.4f} PSI")
        
        # Export data
        filename = collector.export_data()
        print(f"Data exported to: {filename}")
        
        # Run benchmark
        print("\n")
        benchmark_sampling_rates()
        
        print("✓ High-speed pressure collection test completed successfully")
        
    except Exception as e:
        print(f"✗ High-speed pressure collection test failed: {e}")
        exit(1) 