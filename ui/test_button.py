#!/usr/bin/env python3
"""
Test Button Widget

Simple GUI button for testing touchscreen interaction.
Displays a button and prints "Test started" when clicked.
"""

import tkinter as tk
from tkinter import ttk
import platform
import time
from datetime import datetime

def is_raspberry_pi():
    """Detect if running on a Raspberry Pi."""
    machine = platform.machine().lower()
    release = platform.release().lower()
    platform_str = platform.platform().lower()
    
    is_arm = machine.startswith('arm') or machine.startswith('aarch64')
    is_rpi_kernel = 'rpi' in release or 'raspberrypi' in platform_str
    
    return platform.system() == "Linux" and (is_arm or is_rpi_kernel)

class TestButton:
    """
    Simple test button widget for verifying GUI and touch functionality.
    
    Creates a large, touch-friendly button that responds to clicks.
    Designed for industrial touchscreen interfaces.
    """
    
    def __init__(self, master=None):
        """
        Initialize the test button.
        
        Args:
            master: Parent tkinter widget, or None to create root window
        """
        # Create root window if no master provided
        if master is None:
            self.root = tk.Tk()
            self.own_root = True
        else:
            self.root = master
            self.own_root = False
        
        self.is_pi = is_raspberry_pi()
        self.click_count = 0
        
        self._setup_window()
        self._create_widgets()
        
        print("TestButton initialized")
        print(f"Platform: {'Raspberry Pi' if self.is_pi else 'Development'}")
    
    def _setup_window(self):
        """Configure the main window."""
        if self.own_root:
            self.root.title("EOL Leak Tester - Test Button")
            
            # Set window size
            if self.is_pi:
                self.root.geometry("800x480")  # Common Pi touchscreen resolution
                self.root.attributes('-fullscreen', True)
                self.root.configure(cursor='none')  # Hide cursor for touchscreen
            else:
                self.root.geometry("600x400")  # Smaller for development
        
        # Set background color
        self.root.configure(bg='#2c3e50')
    
    def _create_widgets(self):
        """Create and layout the GUI widgets."""
        # Title
        title_label = tk.Label(
            self.root,
            text="Test Button Demo",
            font=('Arial', 24, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(pady=30)
        
        # Instruction
        instruction_label = tk.Label(
            self.root,
            text="Click the button to start a test",
            font=('Arial', 14),
            fg='#bdc3c7',
            bg='#2c3e50'
        )
        instruction_label.pack(pady=10)
        
        # Main test button
        self.test_button = tk.Button(
            self.root,
            text="START TEST",
            font=('Arial', 28, 'bold'),
            width=15,
            height=3,
            bg='#27ae60',  # Green
            fg='white',
            activebackground='#2ecc71',
            activeforeground='white',
            relief='raised',
            bd=5,
            command=self.on_test_button_click
        )
        self.test_button.pack(pady=40)
        
        # Status display
        self.status_label = tk.Label(
            self.root,
            text="Ready to test",
            font=('Arial', 16),
            fg='#f39c12',  # Orange
            bg='#2c3e50'
        )
        self.status_label.pack(pady=20)
        
        # Click counter
        self.counter_label = tk.Label(
            self.root,
            text=f"Button clicks: {self.click_count}",
            font=('Arial', 12),
            fg='#95a5a6',
            bg='#2c3e50'
        )
        self.counter_label.pack(pady=10)
        
        # Exit button (for testing)
        if not self.is_pi:  # Only show on development systems
            exit_button = tk.Button(
                self.root,
                text="Exit",
                font=('Arial', 12),
                width=8,
                height=1,
                bg='#e74c3c',
                fg='white',
                command=self.exit_app
            )
            exit_button.pack(side='bottom', pady=10)
        
        # Bind ESC key to exit
        self.root.bind('<Escape>', lambda e: self.exit_app())
        
        # Bind spacebar for keyboard testing
        self.root.bind('<space>', lambda e: self.on_test_button_click())
        self.root.focus_set()  # Allow keyboard input
    
    def on_test_button_click(self):
        """Handle test button click."""
        self.click_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Print to console (as required by task)
        print("Test started")
        print(f"  Time: {timestamp}")
        print(f"  Click count: {self.click_count}")
        
        # Update GUI
        self.status_label.config(
            text=f"Test started at {timestamp}",
            fg='#27ae60'  # Green
        )
        
        self.counter_label.config(text=f"Button clicks: {self.click_count}")
        
        # Visual feedback - button color change
        self.test_button.config(bg='#f39c12')  # Orange during click
        self.root.after(500, self._reset_button_color)
    
    def _reset_button_color(self):
        """Reset button color after click animation."""
        self.test_button.config(bg='#27ae60')  # Back to green
    
    def exit_app(self):
        """Exit the application."""
        print(f"Test button demo completed. Total clicks: {self.click_count}")
        if self.own_root:
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """Start the GUI event loop."""
        if self.own_root:
            print("Starting test button GUI...")
            print("Instructions:")
            print("- Click the green 'START TEST' button")
            print("- Press spacebar for keyboard testing")
            print("- Press ESC to exit")
            
            try:
                self.root.mainloop()
            except KeyboardInterrupt:
                print("\nTest interrupted by user")
            except Exception as e:
                print(f"GUI error: {e}")
        else:
            print("TestButton widget ready (embedded mode)")

def main():
    """Main entry point for standalone testing."""
    print("=== Test Button Demo ===")
    
    try:
        # Create and run test button
        test_button = TestButton()
        test_button.run()
        
    except ImportError as e:
        print(f"GUI libraries not available: {e}")
        print("Ensure tkinter is installed")
        return 1
    except Exception as e:
        print(f"Test button failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 