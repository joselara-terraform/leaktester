#!/usr/bin/env python3
"""
Main UI Module

Comprehensive user interface for the EOL Leak Tester.
Shows pressure, test phase, result, and includes test button.
Integrates all system components into a unified touchscreen interface.
"""

import tkinter as tk
from tkinter import ttk
import platform
import time
import threading
from datetime import datetime
from typing import Optional
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# Handle imports for both module use and standalone testing
try:
    from ..controllers.pressure_calibration import PressureCalibration
    from ..services.test_runner import TestRunner, TestConfig, TestPhase, TestResult, create_test_config_from_file
    from ..config.config_manager import get_config_manager
    from .test_button import TestButton
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from controllers.pressure_calibration import PressureCalibration
    from services.test_runner import TestRunner, TestConfig, TestPhase, TestResult, create_test_config_from_file
    from config.config_manager import get_config_manager
    # test_button is optional for now
    try:
        from ui.test_button import TestButton
    except ImportError:
        TestButton = None

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

class MainUI:
    """
    Main user interface for the EOL Leak Tester.
    
    Provides a comprehensive touchscreen interface showing:
    - Live pressure readings
    - Current test phase
    - Test results (Pass/Fail)
    - Test control button
    - System status
    """
    
    def __init__(self):
        """Initialize the main UI."""
        self.root = tk.Tk()
        self.is_pi = is_raspberry_pi()
        
        # Load configuration
        self.config_manager = get_config_manager()
        
        # Initialize pressure calibration system from config
        self.pressure_calibration = PressureCalibration()
        
        # Initialize test runner with configuration-based TestConfig
        self.test_runner = TestRunner(
            config=create_test_config_from_file(),
            phase_callback=self._on_test_phase_change
        )
        
        # UI state variables
        self.current_pressure = 0.0
        self.test_phase = "Ready"
        self.test_result = None  # None, "PASS", "FAIL"
        self.is_testing = False
        self.pressure_update_running = False
        
        # Test statistics
        self.test_count = 0
        self.last_test_time = None
        self.last_test_duration = None
        
        # Test timer variables
        self.test_start_time = None
        self.timer_update_running = False
        
        # Plot data variables
        self.plot_data = {
            'times': [],
            'pressures': [],
            'phase_markers': {},  # phase_name: time
            'test_active': False,
            'test_start_time': None
        }
        self.figure = None
        self.canvas = None
        self.ax = None
        
        # Setup UI
        self._setup_window()
        self._create_widgets()
        self._start_pressure_updates()
        
        print("Main UI initialized")
        print(f"Platform: {'Raspberry Pi' if self.is_pi else 'Development'}")
        print("TestRunner integrated with UI")
    
    def _setup_window(self):
        """Configure the main window."""
        self.root.title("EOL Leak Tester")
        
        # Get UI configuration
        ui_config = self.config_manager.ui
        
        # Set window size and fullscreen
        if self.is_pi and ui_config and ui_config.display.fullscreen_on_pi:
            pi_res = ui_config.display.pi_resolution
            self.root.geometry(f"{pi_res[0]}x{pi_res[1]}")
            self.root.attributes('-fullscreen', True)
            if not ui_config.display.cursor_visible:
                self.root.configure(cursor='none')
        else:
            # Development or fallback settings
            # First try to maximize the window
            try:
                self.root.state('zoomed')  # Windows/Linux maximize
            except:
                try:
                    # macOS maximize alternative
                    self.root.attributes('-zoomed', True)
                except:
                    # If maximization fails, set a large default size
                    if ui_config and ui_config.display.window_size:
                        win_size = ui_config.display.window_size
                        self.root.geometry(f"{win_size[0]}x{win_size[1]}")
                    else:
                        self.root.geometry("1200x800")  # Larger default size
        
        # Set background from config
        bg_color = '#2c3e50'  # Default
        if ui_config and ui_config.colors:
            bg_color = ui_config.colors.background
        
        self.root.configure(bg=bg_color)
        
        # Bind ESC to exit (for development)
        self.root.bind('<Escape>', lambda e: self.exit_app())
    
    def _create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container with grid layout
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Configure grid weights
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Title header
        self._create_header(main_frame)
        
        # Left panel - Pressure and Status
        self._create_left_panel(main_frame)
        
        # Right panel - Test Control and Results
        self._create_right_panel(main_frame)
    
    def _create_header(self, parent):
        """Create the header section."""
        header_frame = tk.Frame(parent, bg='#34495e', relief='raised', bd=2)
        header_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 20))
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="EOL LEAK TESTER",
            font=('Arial', 28, 'bold'),
            fg='white',
            bg='#34495e'
        )
        title_label.pack(pady=15)
        
        # Current time and exit button container
        time_container = tk.Frame(header_frame, bg='#34495e')
        time_container.pack()
        
        self.time_label = tk.Label(
            time_container,
            text="",
            font=('Arial', 12),
            fg='#bdc3c7',
            bg='#34495e'
        )
        self.time_label.pack(side='left')
        
        # Exit button (development only)
        if not self.is_pi:
            exit_button = tk.Button(
                time_container,
                text="Exit",
                font=('Arial', 10),
                bg='#e74c3c',
                fg='white',
                command=self.exit_app
            )
            exit_button.pack(side='right', padx=(20, 0))
        
        self._update_time()
    
    def _create_left_panel(self, parent):
        """Create the left panel with pressure display."""
        left_frame = tk.Frame(parent, bg='#2c3e50')
        left_frame.grid(row=1, column=0, sticky='nsew', padx=(0, 10))
        
        # Pressure display section
        pressure_frame = tk.LabelFrame(
            left_frame,
            text="PRESSURE",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50',
            relief='raised',
            bd=3
        )
        pressure_frame.pack(fill='x', pady=(0, 20))
        
        # Large pressure reading
        self.pressure_label = tk.Label(
            pressure_frame,
            text="0.00",
            font=('Arial', 48, 'bold'),
            fg='#3498db',  # Blue
            bg='#2c3e50'
        )
        self.pressure_label.pack(pady=20)
        
        # PSI unit
        psi_label = tk.Label(
            pressure_frame,
            text="PSI",
            font=('Arial', 20, 'bold'),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        psi_label.pack()
        
        # Test phase section
        phase_frame = tk.LabelFrame(
            left_frame,
            text="TEST PHASE",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50',
            relief='raised',
            bd=3
        )
        phase_frame.pack(fill='x', pady=(0, 20))
        
        self.phase_label = tk.Label(
            phase_frame,
            text="Ready",
            font=('Arial', 24, 'bold'),
            fg='#f39c12',  # Orange
            bg='#2c3e50'
        )
        self.phase_label.pack(pady=20)
        
        # Pressure vs Time Plot section
        plot_frame = tk.LabelFrame(
            left_frame,
            text="PRESSURE vs TIME",
            font=('Arial', 14, 'bold'),
            fg='white',
            bg='#2c3e50',
            relief='raised',
            bd=2
        )
        plot_frame.pack(fill='both', expand=True)
        
        # Create matplotlib figure and canvas
        self._create_pressure_plot(plot_frame)
    
    def _create_right_panel(self, parent):
        """Create the right panel with test controls and results."""
        right_frame = tk.Frame(parent, bg='#2c3e50')
        right_frame.grid(row=1, column=1, sticky='nsew', padx=(10, 0))
        
        # Test button section
        button_frame = tk.LabelFrame(
            right_frame,
            text="TEST CONTROL",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50',
            relief='raised',
            bd=3
        )
        button_frame.pack(fill='x', pady=(0, 20))
        
        # Main test button
        self.test_button = tk.Button(
            button_frame,
            text="START TEST",
            font=('Arial', 24, 'bold'),
            width=12,
            height=3,
            bg='#27ae60',
            fg='white',
            activebackground='#2ecc71',
            relief='raised',
            bd=5,
            command=self.on_start_test
        )
        self.test_button.pack(pady=20)
        
        # Test results section
        result_frame = tk.LabelFrame(
            right_frame,
            text="TEST RESULT",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50',
            relief='raised',
            bd=3
        )
        result_frame.pack(fill='x', pady=(0, 20))
        
        self.result_label = tk.Label(
            result_frame,
            text="—",
            font=('Arial', 36, 'bold'),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        self.result_label.pack(pady=30)
        
        # Test statistics section
        stats_frame = tk.LabelFrame(
            right_frame,
            text="TEST STATISTICS",
            font=('Arial', 14, 'bold'),
            fg='white',
            bg='#2c3e50',
            relief='raised',
            bd=2
        )
        stats_frame.pack(fill='both', expand=True)
        
        # Test timer
        self.timer_label = tk.Label(
            stats_frame,
            text="Elapsed: 00:00",
            font=('Arial', 14, 'bold'),
            fg='#3498db',
            bg='#2c3e50'
        )
        self.timer_label.pack(anchor='w', padx=10, pady=5)
        
        # Test count
        self.test_count_label = tk.Label(
            stats_frame,
            text=f"Tests run: {self.test_count}",
            font=('Arial', 12),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        self.test_count_label.pack(anchor='w', padx=10, pady=5)
        
        # Last test time
        self.last_test_label = tk.Label(
            stats_frame,
            text="Last test: —",
            font=('Arial', 12),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        self.last_test_label.pack(anchor='w', padx=10)
    

    
    def _create_pressure_plot(self, parent):
        """Create the pressure vs time matplotlib plot."""
        # Create figure with dark theme
        self.figure = Figure(figsize=(6, 4), dpi=100, facecolor='#2c3e50')
        self.ax = self.figure.add_subplot(111, facecolor='#34495e')
        
        # Set plot styling
        self.ax.set_xlabel('Time (seconds)', color='white', fontsize=10)
        self.ax.set_ylabel('Pressure (PSI)', color='white', fontsize=10)
        self.ax.tick_params(colors='white', labelsize=8)
        self.ax.grid(True, alpha=0.3, color='white')
        
        # Set fixed axes as requested
        # X-axis: 0 to test length (with buffer for phase transitions)
        test_config = self.test_runner.config
        total_test_time = (test_config.fill_time + test_config.stabilize_time + 
                          test_config.test_duration + test_config.exhaust_time)
        # Add 10% buffer to ensure full exhaust phase is visible
        total_test_time_with_buffer = total_test_time * 1.1
        self.ax.set_xlim(0, total_test_time_with_buffer)
        # Y-axis: 0 to 1 PSI as requested
        self.ax.set_ylim(0, 1.0)
        
        # Initialize empty plot
        self.pressure_line, = self.ax.plot([], [], 'cyan', linewidth=2, label='Pressure')
        self.phase_lines = {}  # Will store vertical lines for phases
        
        # Add legend
        self.ax.legend(loc='upper right', fancybox=True, framealpha=0.8)
        
        # Adjust layout to prevent label cutoff
        self.figure.tight_layout(pad=1.0)
        
        # Create canvas and add to parent
        self.canvas = FigureCanvasTkAgg(self.figure, parent)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)
        
        # Initial draw
        self.canvas.draw()
    
    def _update_pressure_plot(self):
        """Update the pressure plot with current data."""
        if not self.plot_data['test_active'] or not self.ax:
            return
        
        # Update pressure line
        self.pressure_line.set_data(self.plot_data['times'], self.plot_data['pressures'])
        
        # Update phase marker lines
        for phase_name, phase_time in self.plot_data['phase_markers'].items():
            if phase_name not in self.phase_lines:
                # Create new vertical line for this phase
                line = self.ax.axvline(x=phase_time, color='yellow', linestyle='--', 
                                     alpha=0.7, linewidth=1)
                self.phase_lines[phase_name] = line
                
                # Add text label for phase (positioned above the line)
                self.ax.text(phase_time, 0.9, phase_name, rotation=90, 
                           verticalalignment='bottom', horizontalalignment='right',
                           fontsize=8, color='yellow', alpha=0.8)
        
        # Redraw canvas
        self.canvas.draw()
    
    def _reset_pressure_plot(self):
        """Reset the pressure plot data and display."""
        self.plot_data = {
            'times': [],
            'pressures': [],
            'phase_markers': {},
            'test_active': False,
            'test_start_time': None
        }
        
        if self.ax:
            # Clear existing data
            self.pressure_line.set_data([], [])
            
            # Remove phase lines
            for line in self.phase_lines.values():
                line.remove()
            self.phase_lines.clear()
            
            # Clear text annotations
            texts = [child for child in self.ax.get_children() 
                    if hasattr(child, 'get_text')]
            for text in texts:
                if text.get_text() in ['Stabilizing', 'Testing', 'Exhausting']:
                    text.remove()
            
            # Redraw
            self.canvas.draw()
    
    def _add_pressure_data_point(self, pressure):
        """Add a new pressure data point to the plot."""
        if not self.plot_data['test_active']:
            return
        
        current_time = time.time()
        elapsed_time = current_time - self.plot_data['test_start_time']
        
        self.plot_data['times'].append(elapsed_time)
        self.plot_data['pressures'].append(pressure)
        
        # Keep only recent data to prevent memory buildup
        max_points = 1000
        if len(self.plot_data['times']) > max_points:
            self.plot_data['times'] = self.plot_data['times'][-max_points:]
            self.plot_data['pressures'] = self.plot_data['pressures'][-max_points:]
    
    def _add_phase_marker(self, phase_name):
        """Add a phase marker to the plot."""
        if not self.plot_data['test_active']:
            return
        
        current_time = time.time()
        elapsed_time = current_time - self.plot_data['test_start_time']
        self.plot_data['phase_markers'][phase_name] = elapsed_time
    
    def _update_time(self):
        """Update the time display."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self._update_time)
    
    def _start_pressure_updates(self):
        """Start the pressure reading updates."""
        if not self.pressure_update_running:
            self.pressure_update_running = True
            self._update_pressure()
    
    def _start_timer_updates(self):
        """Start the test timer updates."""
        if not self.timer_update_running:
            self.timer_update_running = True
            self._update_timer()
    
    def _stop_timer_updates(self):
        """Stop the test timer updates."""
        self.timer_update_running = False
    
    def _update_timer(self):
        """Update test timer display."""
        if self.timer_update_running and self.test_start_time:
            elapsed = time.time() - self.test_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            
            self.timer_label.config(text=f"Elapsed: {minutes:02d}:{seconds:02d}")
            
            # Schedule next update
            self.root.after(1000, self._update_timer)  # Update every second
    
    def _reset_timer(self):
        """Reset the timer display."""
        self.timer_label.config(text="Elapsed: 00:00")
    
    def _update_pressure(self):
        """Update pressure reading (runs in UI thread)."""
        if self.pressure_update_running:
            try:
                # Read pressure
                pressure = self.pressure_calibration.read_pressure_psi(num_samples=3)
                self.current_pressure = pressure
                
                # Update pressure display
                self.pressure_label.config(text=f"{pressure:.2f}")
                
                # Color based on pressure level
                if pressure < 1.0:
                    color = '#95a5a6'  # Gray - no pressure
                elif pressure < 5.0:
                    color = '#f39c12'  # Orange - low pressure
                elif pressure < 10.0:
                    color = '#3498db'  # Blue - normal pressure
                else:
                    color = '#e74c3c'  # Red - high pressure
                
                self.pressure_label.config(fg=color)
                
                # Add data point to plot if test is active
                if self.plot_data['test_active']:
                    self._add_pressure_data_point(pressure)
                    self._update_pressure_plot()
                
            except Exception as e:
                print(f"Pressure update error: {e}")
                self.pressure_label.config(text="ERROR", fg='#e74c3c')
            
            # Schedule next update
            ui_config = self.config_manager.ui
            update_ms = ui_config.update_rates.ui_refresh_ms if ui_config else 250
            self.root.after(update_ms, self._update_pressure)  # Configurable update rate
    
    def on_start_test(self):
        """Handle start test button click."""
        if self.is_testing:
            print("Test already in progress")
            return
        
        print("Test started")
        self.test_count += 1
        self.is_testing = True
        
        # Start test timer
        self.test_start_time = time.time()
        self._start_timer_updates()
        
        # Reset and prepare plot for new test
        self._reset_pressure_plot()
        
        # Update UI
        self.test_button.config(text="TESTING...", bg='#f39c12', state='disabled')
        self.result_label.config(text="—", fg='#95a5a6')
        self.test_count_label.config(text=f"Tests run: {self.test_count}")
        
        # Start test runner
        threading.Thread(target=self._run_test, daemon=True).start()
    
    def _run_test(self):
        """Run the test using the TestRunner."""
        try:
            # Execute the test
            result = self.test_runner.run_test()
            
            # Update UI with final result in main thread
            self.root.after(0, lambda: self._finish_test(result))
            
        except Exception as e:
            print(f"Test execution error: {e}")
            # Update UI with error in main thread
            self.root.after(0, lambda: self._handle_test_error(str(e)))
    
    def _on_test_phase_change(self, phase: TestPhase):
        """Handle test phase change from TestRunner."""
        # Update UI in main thread
        self.root.after(0, lambda: self._update_test_phase(phase.value))
        
        # Handle plot activation/deactivation and phase markers
        phase_name = phase.value
        
        # Start plotting when filling begins
        if phase_name == "Filling DUT" and not self.plot_data['test_active']:
            self.plot_data['test_active'] = True
            self.plot_data['test_start_time'] = time.time()
            print("Plot data collection started")
        
        # Add phase markers for key phases only
        if self.plot_data['test_active'] and phase_name in [
            "Stabilizing", "Testing", "Exhausting"
        ]:
            self.root.after(0, self._add_phase_marker, phase_name)
        
        # Stop plotting when exhausting is complete
        if phase_name == "Retracting cylinders" and self.plot_data['test_active']:
            self.plot_data['test_active'] = False
            print("Plot data collection stopped")
    
    def _update_test_phase(self, phase_name: str):
        """Update test phase display."""
        self.test_phase = phase_name
        self.phase_label.config(text=phase_name)
        
        # Color coding for phases
        if "cylinders" in phase_name.lower():
            color = '#9b59b6'  # Purple
        elif any(word in phase_name.lower() for word in ['filling', 'stabilizing']):
            color = '#3498db'  # Blue
        elif "testing" in phase_name.lower():
            color = '#e67e22'  # Orange
        elif "evaluating" in phase_name.lower():
            color = '#f39c12'  # Yellow
        elif phase_name.lower() in ['complete', 'ready']:
            color = '#95a5a6'  # Gray
        else:
            color = '#95a5a6'  # Gray
        
        self.phase_label.config(fg=color)
    
    def _finish_test(self, result: TestResult):
        """Finish test and display result."""
        self.test_result = result.value if result else "ERROR"
        self.is_testing = False
        
        # Stop test timer
        self._stop_timer_updates()
        
        # Get test data from test runner
        test_data = self.test_runner.get_test_data()
        duration = test_data.get('duration', 0)
        
        # Update UI
        self.test_button.config(text="START TEST", bg='#27ae60', state='normal')
        self.test_phase = "Complete"
        self.phase_label.config(text="Complete", fg='#95a5a6')
        
        # Update result display
        result_text = self.test_result
        if result_text == "PASS":
            result_color = '#27ae60'
        elif result_text == "FAIL":
            result_color = '#e74c3c'
        else:
            result_color = '#f39c12'  # Error/Unknown
        
        self.result_label.config(text=result_text, fg=result_color)
        
        # Update status and last test time
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.last_test_time = timestamp
        self.last_test_duration = duration
        
        # Update timer with final time
        if self.test_start_time:
            final_elapsed = time.time() - self.test_start_time
            minutes = int(final_elapsed // 60)
            seconds = int(final_elapsed % 60)
            self.timer_label.config(text=f"Completed: {minutes:02d}:{seconds:02d}")
        
        # Update statistics display
        duration_text = f" ({duration:.1f}s)" if duration > 0 else ""
        self.last_test_label.config(text=f"Last test: {timestamp}{duration_text}")
        
        print(f"Test completed: {result_text} in {duration:.1f}s")
        
        # Log test details if available
        if test_data:
            leak_rate = test_data.get('leak_rate', 0)
            start_pressure = test_data.get('start_pressure', 0)
            end_pressure = test_data.get('end_pressure', 0)
            print(f"Test details: {start_pressure:.2f} → {end_pressure:.2f} PSI, leak rate: {leak_rate:.3f} PSI/s")
    
    def _handle_test_error(self, error_msg: str):
        """Handle test execution error."""
        self.test_result = "ERROR"
        self.is_testing = False
        
        # Stop test timer
        self._stop_timer_updates()
        
        # Update UI
        self.test_button.config(text="START TEST", bg='#27ae60', state='normal')
        self.test_phase = "Error"
        self.phase_label.config(text="Error", fg='#e74c3c')
        self.result_label.config(text="ERROR", fg='#e74c3c')
        
        # Update timer with error state
        if self.test_start_time:
            final_elapsed = time.time() - self.test_start_time
            minutes = int(final_elapsed // 60)
            seconds = int(final_elapsed % 60)
            self.timer_label.config(text=f"Error: {minutes:02d}:{seconds:02d}")
        
        print(f"Test error: {error_msg}")
    
    def exit_app(self):
        """Exit the application."""
        print("Shutting down Main UI")
        self.pressure_update_running = False
        self._stop_timer_updates()
        
        # Close test runner
        if hasattr(self, 'test_runner'):
            self.test_runner.close()
        
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the main UI event loop."""
        print("Starting Main UI...")
        print("Pressure monitoring active")
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nMain UI interrupted by user")
        except Exception as e:
            print(f"Main UI error: {e}")
        finally:
            self.pressure_update_running = False
            self._stop_timer_updates()

def main():
    """Main entry point."""
    print("=== EOL Leak Tester Main UI ===")
    
    try:
        ui = MainUI()
        ui.run()
    except Exception as e:
        print(f"Failed to start Main UI: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 