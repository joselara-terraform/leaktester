#!/usr/bin/env python3
"""
Simple UI for EOL Leak Tester

Minimal dependencies version that should work even with import issues.
Shows pressure readings and basic test control.
"""

import tkinter as tk
from tkinter import ttk
import platform
import time
import threading
from datetime import datetime

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

class SimplePressureReader:
    """Simple pressure reader that works without complex imports."""
    
    def __init__(self):
        self.is_pi = is_raspberry_pi()
        self.mock_pressure = 0.0
        
    def read_pressure_psi(self):
        """Read pressure - mock version or real if possible."""
        if self.is_pi:
            try:
                # Try to import and use real ADC
                import adafruit_ads1x15.ads1115 as ADS
                from adafruit_ads1x15.analog_in import AnalogIn
                import board
                import busio
                
                # Quick ADC read
                i2c = busio.I2C(board.SCL, board.SDA)
                ads = ADS.ADS1115(i2c, address=0x48)
                ads.gain = 2
                channel = AnalogIn(ads, ADS.P0)
                
                # Convert raw ADC to current to pressure
                raw_value = channel.value
                current_ma = 4.0 + (raw_value - 6430) * 16.0 / (32154 - 6430)
                pressure_psi = max(0.0, (current_ma - 4.025) / 16.012)
                
                return pressure_psi
                
            except Exception as e:
                print(f"ADC read error: {e}")
                # Fall back to mock
                pass
        
        # Mock pressure that varies slowly
        import time
        self.mock_pressure = 0.1 + 0.05 * (time.time() % 20 - 10) / 10
        return max(0.0, self.mock_pressure)

class SimpleUI:
    """Simple UI for leak testing."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.is_pi = is_raspberry_pi()
        
        # Initialize pressure reader
        self.pressure_reader = SimplePressureReader()
        
        # UI state
        self.current_pressure = 0.0
        self.is_testing = False
        self.test_result = None
        self.pressure_update_running = False
        
        # Setup UI
        self._setup_window()
        self._create_widgets()
        self._start_pressure_updates()
        
        print(f"Simple UI initialized on {'Raspberry Pi' if self.is_pi else 'development system'}")
    
    def _setup_window(self):
        """Configure the main window."""
        self.root.title("EOL Leak Tester - Simple UI")
        
        if self.is_pi:
            # Full screen on Pi
            self.root.geometry("800x480")
            self.root.attributes('-fullscreen', True)
        else:
            # Window on development
            self.root.geometry("800x600")
        
        self.root.configure(bg='#2c3e50')
        
        # Bind ESC to exit
        self.root.bind('<Escape>', lambda e: self.exit_app())
    
    def _create_widgets(self):
        """Create UI widgets."""
        # Title
        title_label = tk.Label(
            self.root,
            text="EOL LEAK TESTER",
            font=('Arial', 24, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(pady=20)
        
        # Platform info
        platform_text = f"Platform: {'Raspberry Pi' if self.is_pi else 'Development'}"
        platform_label = tk.Label(
            self.root,
            text=platform_text,
            font=('Arial', 12),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        platform_label.pack()
        
        # Pressure display
        pressure_frame = tk.Frame(self.root, bg='#34495e')
        pressure_frame.pack(pady=30, padx=20, fill='x')
        
        tk.Label(
            pressure_frame,
            text="PRESSURE",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#34495e'
        ).pack(pady=10)
        
        self.pressure_label = tk.Label(
            pressure_frame,
            text="0.00",
            font=('Arial', 48, 'bold'),
            fg='#3498db',
            bg='#34495e'
        )
        self.pressure_label.pack(pady=10)
        
        tk.Label(
            pressure_frame,
            text="PSI",
            font=('Arial', 16),
            fg='#95a5a6',
            bg='#34495e'
        ).pack(pady=5)
        
        # Test controls
        control_frame = tk.Frame(self.root, bg='#2c3e50')
        control_frame.pack(pady=20)
        
        self.test_button = tk.Button(
            control_frame,
            text="START TEST",
            font=('Arial', 18, 'bold'),
            bg='#27ae60',
            fg='white',
            width=15,
            height=2,
            command=self.start_test
        )
        self.test_button.pack(pady=10)
        
        # Results
        self.result_label = tk.Label(
            control_frame,
            text="Ready",
            font=('Arial', 24, 'bold'),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        self.result_label.pack(pady=20)
        
        # Status
        self.status_label = tk.Label(
            self.root,
            text="System ready - Simple UI mode",
            font=('Arial', 10),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        self.status_label.pack(side='bottom', pady=10)
        
        # Exit button for development
        if not self.is_pi:
            exit_button = tk.Button(
                self.root,
                text="Exit",
                command=self.exit_app,
                bg='#e74c3c',
                fg='white'
            )
            exit_button.pack(side='bottom', pady=5)
    
    def _start_pressure_updates(self):
        """Start pressure reading updates."""
        if not self.pressure_update_running:
            self.pressure_update_running = True
            self._update_pressure()
    
    def _update_pressure(self):
        """Update pressure display."""
        if self.pressure_update_running:
            try:
                pressure = self.pressure_reader.read_pressure_psi()
                self.current_pressure = pressure
                
                # Update display
                self.pressure_label.config(text=f"{pressure:.3f}")
                
                # Color based on pressure
                if pressure < 0.1:
                    color = '#95a5a6'  # Gray
                elif pressure < 0.5:
                    color = '#f39c12'  # Orange
                else:
                    color = '#3498db'  # Blue
                
                self.pressure_label.config(fg=color)
                
            except Exception as e:
                print(f"Pressure update error: {e}")
                self.pressure_label.config(text="ERROR", fg='#e74c3c')
            
            # Schedule next update
            self.root.after(250, self._update_pressure)
    
    def start_test(self):
        """Start a simple test."""
        if self.is_testing:
            return
        
        self.is_testing = True
        self.test_button.config(text="TESTING...", state='disabled', bg='#f39c12')
        self.result_label.config(text="Testing...", fg='#f39c12')
        self.status_label.config(text="Simple test in progress...")
        
        # Run simple test in thread
        threading.Thread(target=self._run_simple_test, daemon=True).start()
    
    def _run_simple_test(self):
        """Run a simple pressure test."""
        try:
            # Simple test: monitor pressure for 10 seconds
            start_pressure = self.current_pressure
            time.sleep(10)
            end_pressure = self.current_pressure
            
            # Simple leak calculation
            pressure_drop = start_pressure - end_pressure
            leak_rate = pressure_drop / 10.0  # PSI per second
            
            # Simple pass/fail logic
            if leak_rate < 0.005:  # Less than 0.005 PSI/s leak
                result = "PASS"
                color = '#27ae60'
            else:
                result = "FAIL"
                color = '#e74c3c'
            
            # Update UI in main thread
            self.root.after(0, lambda: self._finish_test(result, color, leak_rate))
            
        except Exception as e:
            print(f"Test error: {e}")
            self.root.after(0, lambda: self._finish_test("ERROR", '#f39c12', 0))
    
    def _finish_test(self, result, color, leak_rate):
        """Finish test and update UI."""
        self.is_testing = False
        self.test_result = result
        
        self.test_button.config(text="START TEST", state='normal', bg='#27ae60')
        self.result_label.config(text=result, fg=color)
        self.status_label.config(text=f"Test complete: {result} (leak rate: {leak_rate:.4f} PSI/s)")
        
        print(f"Simple test completed: {result}")
    
    def exit_app(self):
        """Exit the application."""
        print("Shutting down Simple UI")
        self.pressure_update_running = False
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the UI."""
        print("Starting Simple UI...")
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nUI interrupted")
        finally:
            self.pressure_update_running = False

def main():
    """Main entry point."""
    print("=== Simple EOL Leak Tester UI ===")
    
    try:
        ui = SimpleUI()
        ui.run()
    except Exception as e:
        print(f"Failed to start Simple UI: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 