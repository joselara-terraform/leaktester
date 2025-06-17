#!/usr/bin/env python3
"""
Quick Sampling Speed Test

Compare current vs optimized ADC sampling rates to demonstrate
the performance improvement from removing the ADC bottleneck.
"""

import time
import sys
import os

# Add path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_sampling_rate(sample_rate, test_duration=3.0):
    """Test a specific ADC sample rate configuration."""
    print(f"\n--- Testing {sample_rate} SPS Configuration ---")
    
    try:
        from controllers.adc_reader import ADCReader
        from controllers.pressure_calibration import PressureCalibration
        
        # Create ADC with specified sample rate
        adc = ADCReader(sample_rate=sample_rate)
        pressure_cal = PressureCalibration(adc_reader=adc)
        
        print(f"ADC configured for {sample_rate} SPS")
        
        # Test rapid sampling
        start_time = time.time()
        sample_count = 0
        pressures = []
        
        print("Collecting samples...")
        while (time.time() - start_time) < test_duration:
            try:
                # Use fastest reading method
                pressure = pressure_cal.read_pressure_psi(num_samples=1)
                pressures.append(pressure)
                sample_count += 1
            except Exception as e:
                print(f"Reading error: {e}")
                break
        
        elapsed_time = time.time() - start_time
        effective_sps = sample_count / elapsed_time if elapsed_time > 0 else 0
        
        # Calculate statistics
        if pressures:
            avg_pressure = sum(pressures) / len(pressures)
            min_pressure = min(pressures)
            max_pressure = max(pressures)
            pressure_range = max_pressure - min_pressure
        else:
            avg_pressure = min_pressure = max_pressure = pressure_range = 0
        
        # Results
        print(f"Results:")
        print(f"  Configured rate: {sample_rate} SPS")
        print(f"  Actual rate: {effective_sps:.1f} SPS")
        print(f"  Efficiency: {(effective_sps/sample_rate)*100:.1f}%")
        print(f"  Total samples: {sample_count}")
        print(f"  Test duration: {elapsed_time:.1f}s")
        print(f"  Pressure stats: {avg_pressure:.3f} PSI (±{pressure_range/2:.3f})")
        
        return {
            'configured_sps': sample_rate,
            'actual_sps': effective_sps,
            'efficiency': (effective_sps/sample_rate)*100 if sample_rate > 0 else 0,
            'sample_count': sample_count,
            'duration': elapsed_time,
            'avg_pressure': avg_pressure,
            'pressure_range': pressure_range
        }
        
    except ImportError as e:
        print(f"Import error: {e}")
        return None
    except Exception as e:
        print(f"Test error: {e}")
        return None

def main():
    """Run sampling speed comparison test."""
    print("=== Pressure Sampling Speed Test ===")
    print("This test demonstrates the performance improvement from")
    print("increasing the ADC sample rate from 128 to 860 SPS.")
    print()
    
    # Test configurations
    test_configs = [
        {'sps': 128, 'description': 'Current configuration'},
        {'sps': 250, 'description': 'Medium optimization'},
        {'sps': 475, 'description': 'High optimization'},
        {'sps': 860, 'description': 'Maximum optimization'},
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\n{'='*50}")
        print(f"Testing: {config['description']} ({config['sps']} SPS)")
        print(f"{'='*50}")
        
        result = test_sampling_rate(config['sps'], test_duration=3.0)
        if result:
            results.append(result)
        
        # Brief pause between tests
        time.sleep(1)
    
    # Summary comparison
    if results:
        print(f"\n{'='*60}")
        print("PERFORMANCE COMPARISON SUMMARY")
        print(f"{'='*60}")
        
        baseline = results[0] if results else None
        
        print(f"{'Configuration':<20} {'Actual SPS':<12} {'Improvement':<12} {'Efficiency':<12}")
        print(f"{'-'*60}")
        
        for result in results:
            improvement = "—"
            if baseline and baseline['actual_sps'] > 0:
                improvement_factor = result['actual_sps'] / baseline['actual_sps']
                improvement = f"{improvement_factor:.1f}x"
            
            print(f"{result['configured_sps']} SPS{'':<13} "
                  f"{result['actual_sps']:.1f}{'':<7} "
                  f"{improvement:<12} "
                  f"{result['efficiency']:.1f}%")
        
        # Key findings
        if len(results) >= 2:
            baseline_sps = results[0]['actual_sps']
            optimized_sps = results[-1]['actual_sps']
            
            if baseline_sps > 0:
                improvement_factor = optimized_sps / baseline_sps
                improvement_percent = (improvement_factor - 1) * 100
                
                print(f"\n🎯 KEY FINDINGS:")
                print(f"   • Maximum configuration: {improvement_factor:.1f}x faster")
                print(f"   • Performance gain: +{improvement_percent:.0f}%")
                print(f"   • Sampling rate: {baseline_sps:.0f} → {optimized_sps:.0f} SPS")
                
                if improvement_factor > 5:
                    print(f"   • 🚀 EXCELLENT improvement potential!")
                elif improvement_factor > 3:
                    print(f"   • ✅ GOOD improvement potential")
                elif improvement_factor > 1.5:
                    print(f"   • 📈 MODERATE improvement potential")
                else:
                    print(f"   • ⚠️  Limited improvement (check system)")
        
        print(f"\n📋 RECOMMENDATIONS:")
        print(f"   1. Update config/system_config.yaml:")
        print(f"      adc:")
        print(f"        sample_rate: 860  # Change from 128")
        print(f"   2. Test with: python3 controllers/high_speed_pressure.py")
        print(f"   3. Monitor performance during leak testing")
        
        print(f"\n💡 YOUR PRESSURE TRANSDUCER:")
        print(f"   • Bandwidth: DC to 1kHz (very fast)")
        print(f"   • Current ADC limit: {results[0]['actual_sps']:.0f} SPS")
        print(f"   • Optimized potential: {results[-1]['actual_sps']:.0f} SPS")
        print(f"   • Transducer utilization: {(results[-1]['actual_sps']/1000)*100:.1f}%")
    
    print(f"\n{'='*60}")
    print("Test completed! Your PT's 1kHz bandwidth is ready for optimization.")

if __name__ == "__main__":
    main() 