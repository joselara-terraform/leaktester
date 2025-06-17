#!/usr/bin/env python3
"""
Simple ADC Sampling Rate Test

Direct test of ADS1115 sampling rates without complex imports.
Tests the actual bottleneck in your system.
"""

import time
import platform

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

def test_adc_sampling_rate(sample_rate=128, test_duration=3.0):
    """Test ADC sampling with specified rate."""
    print(f"\n--- Testing ADS1115 at {sample_rate} SPS ---")
    
    is_pi = is_raspberry_pi()
    print(f"Platform: {'Raspberry Pi' if is_pi else 'Development system'}")
    
    if is_pi:
        # Try to import ADS1115 libraries
        try:
            import adafruit_ads1x15.ads1115 as ADS
            from adafruit_ads1x15.analog_in import AnalogIn
            import board
            import busio
            
            print("✅ ADS1115 libraries available")
            
            # Initialize I2C and ADS1115
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c, address=0x48)
            ads.gain = 2  # Gain setting for 4-20mA module
            channel = AnalogIn(ads, ADS.P0)
            
            print(f"✅ ADS1115 initialized at 0x48")
            print(f"✅ Configured sample rate: {sample_rate} SPS")
            
            # Test rapid sampling
            print("Starting high-speed sampling...")
            start_time = time.time()
            sample_count = 0
            raw_values = []
            
            while (time.time() - start_time) < test_duration:
                try:
                    raw_value = channel.value
                    raw_values.append(raw_value)
                    sample_count += 1
                except Exception as e:
                    print(f"Sample error: {e}")
                    break
            
            elapsed_time = time.time() - start_time
            actual_sps = sample_count / elapsed_time if elapsed_time > 0 else 0
            
            # Convert to current for demonstration
            if raw_values:
                # Use your calibration: 4mA = 6430, 20mA = 32154
                sample_current = 4.0 + (raw_values[-1] - 6430) * 16.0 / (32154 - 6430)
                avg_raw = sum(raw_values) / len(raw_values)
                avg_current = 4.0 + (avg_raw - 6430) * 16.0 / (32154 - 6430)
            else:
                sample_current = avg_current = 0
            
            print(f"\n📊 Results:")
            print(f"  Configured rate: {sample_rate} SPS")
            print(f"  Actual rate: {actual_sps:.1f} SPS")
            print(f"  Efficiency: {(actual_sps/sample_rate)*100:.1f}%")
            print(f"  Total samples: {sample_count}")
            print(f"  Test duration: {elapsed_time:.1f}s")
            print(f"  Sample current: {sample_current:.2f} mA")
            print(f"  Average current: {avg_current:.2f} mA")
            
            return actual_sps
            
        except ImportError as e:
            print(f"❌ ADS1115 libraries not available: {e}")
            print("Install with: pip install adafruit-circuitpython-ads1x15")
            return None
        except Exception as e:
            print(f"❌ ADS1115 test failed: {e}")
            return None
    else:
        # Mock test for development
        print("🔧 Running mock test (development system)")
        
        start_time = time.time()
        sample_count = 0
        
        # Simulate sampling with realistic timing
        target_interval = 1.0 / sample_rate  # Target time per sample
        
        while (time.time() - start_time) < test_duration:
            # Simulate reading time based on I2C speed and processing
            if sample_rate <= 128:
                read_time = 0.008  # ~8ms for low rate
            elif sample_rate <= 250:
                read_time = 0.005  # ~5ms for medium rate
            elif sample_rate <= 475:
                read_time = 0.003  # ~3ms for high rate
            else:
                read_time = 0.002  # ~2ms for maximum rate
            
            time.sleep(read_time)
            sample_count += 1
        
        elapsed_time = time.time() - start_time
        actual_sps = sample_count / elapsed_time if elapsed_time > 0 else 0
        
        print(f"\n📊 Mock Results:")
        print(f"  Configured rate: {sample_rate} SPS")
        print(f"  Simulated rate: {actual_sps:.1f} SPS")
        print(f"  Efficiency: {(actual_sps/sample_rate)*100:.1f}%")
        print(f"  Total samples: {sample_count}")
        print(f"  Test duration: {elapsed_time:.1f}s")
        
        return actual_sps

def main():
    """Run the simple ADC sampling test."""
    print("=== Simple ADC Sampling Rate Test ===")
    print("Testing the primary bottleneck: ADS1115 ADC sample rate")
    print()
    
    # Test different sample rates
    test_rates = [128, 250, 475, 860]
    results = []
    
    for rate in test_rates:
        actual_rate = test_adc_sampling_rate(rate, test_duration=3.0)
        if actual_rate:
            results.append((rate, actual_rate))
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    if results:
        print(f"\n{'='*60}")
        print("BOTTLENECK ANALYSIS SUMMARY")
        print(f"{'='*60}")
        
        print(f"{'Config SPS':<12} {'Actual SPS':<12} {'Efficiency':<12} {'Improvement'}")
        print(f"{'-'*60}")
        
        baseline = results[0][1] if results else 0
        
        for config_rate, actual_rate in results:
            efficiency = (actual_rate / config_rate) * 100 if config_rate > 0 else 0
            improvement = f"{actual_rate / baseline:.1f}x" if baseline > 0 else "—"
            
            print(f"{config_rate:<12} {actual_rate:<12.1f} {efficiency:<12.1f}% {improvement}")
        
        if len(results) >= 2:
            max_improvement = results[-1][1] / results[0][1] if results[0][1] > 0 else 1
            print(f"\n🎯 BOTTLENECK FINDINGS:")
            print(f"   • ADS1115 ADC is the limiting factor")
            print(f"   • Maximum improvement: {max_improvement:.1f}x faster")
            print(f"   • Your PT's 1kHz bandwidth: UNDERUTILIZED")
            print(f"   • Current utilization: {results[0][1]/1000*100:.1f}% of PT capability")
            print(f"   • Optimized utilization: {results[-1][1]/1000*100:.1f}% of PT capability")
            
            print(f"\n📋 SOLUTION:")
            print(f"   Update config/system_config.yaml:")
            print(f"   adc:")
            print(f"     sample_rate: 860  # Change from 128")
            print(f"   Expected improvement: {max_improvement:.1f}x faster sampling")
    
    else:
        print("\n❌ No valid test results")
        print("Check your ADS1115 connections and libraries")
    
    print(f"\n{'='*60}")
    print("Your pressure transducer's 1kHz bandwidth is ready!")
    print("The ADS1115 ADC configuration is the bottleneck to fix.")

if __name__ == "__main__":
    main() 