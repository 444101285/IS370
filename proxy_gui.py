"""
IS370 HTTP Proxy - Tkinter GUI
King Saud University - Fall 2025

This GUI provides a desktop interface for controlling the HTTP proxy server
and testing requests through the proxy client.

Usage:
    python proxy_gui.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import time
from proxy_server import ProxyServer
from proxy_client import ProxyClient


class ProxyApp:
    """Main GUI application for IS370 HTTP Proxy"""
    
    def __init__(self, root):
        """
        Initialize the GUI application
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("IS370 HTTP Proxy - Server & Client")
        self.root.geometry("900x800")
        
        # Server state
        self.proxy_server = None
        self.server_thread = None
        self.server_running = False
        
        # Client instance (reused)
        self.proxy_client = None
        
        # Log file state for tailing
        self.log_file_position = 0
        self.log_file_path = None
        
        # Create the GUI
        self.create_gui()
        
        # Start log polling
        self.poll_log_file()
    
    def create_gui(self):
        """Build the complete GUI interface"""
        # Create main container with padding
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        
        # Create server section
        self.create_server_section(main_container)
        
        # Separator
        ttk.Separator(main_container, orient='horizontal').grid(
            row=1, column=0, sticky=(tk.W, tk.E), pady=10
        )
        
        # Create client section
        self.create_client_section(main_container)
    
    def create_server_section(self, parent):
        """
        Create the server control section of the GUI
        
        Args:
            parent: Parent widget
        """
        # Server frame
        server_frame = ttk.LabelFrame(parent, text="Proxy Server Control", padding="10")
        server_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        parent.rowconfigure(0, weight=1)
        server_frame.columnconfigure(1, weight=1)
        
        # Server configuration inputs
        ttk.Label(server_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.server_host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(server_frame, textvariable=self.server_host_var, width=20).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=2
        )
        
        ttk.Label(server_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.server_port_var = tk.StringVar(value="8888")
        ttk.Entry(server_frame, textvariable=self.server_port_var, width=20).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=2
        )
        
        # Server control buttons
        button_frame = ttk.Frame(server_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        self.start_button = ttk.Button(
            button_frame, text="Start Server", command=self.start_server
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(
            button_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # Server status
        self.server_status_var = tk.StringVar(value="Server stopped")
        self.server_status_label = ttk.Label(
            server_frame, textvariable=self.server_status_var, 
            foreground="red", font=("TkDefaultFont", 9, "bold")
        )
        self.server_status_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Blocked domains display
        ttk.Label(server_frame, text="Blocked Domains (Firewall):").grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 2)
        )
        self.blocked_domains_text = tk.Text(
            server_frame, height=3, width=60, state=tk.DISABLED,
            wrap=tk.WORD, background="#f0f0f0"
        )
        self.blocked_domains_text.grid(
            row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2
        )
        
        # Log viewer
        ttk.Label(server_frame, text="Server Log (Live):").grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 2)
        )
        
        self.log_text = scrolledtext.ScrolledText(
            server_frame, height=12, width=80, state=tk.DISABLED,
            wrap=tk.WORD, background="#1e1e1e", foreground="#00ff00",
            font=("Courier", 9)
        )
        self.log_text.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        server_frame.rowconfigure(7, weight=1)
    
    def create_client_section(self, parent):
        """
        Create the client testing section of the GUI
        
        Args:
            parent: Parent widget
        """
        # Client frame
        client_frame = ttk.LabelFrame(parent, text="Proxy Client Tester", padding="10")
        client_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        parent.rowconfigure(2, weight=1)
        client_frame.columnconfigure(1, weight=1)
        
        # Client configuration
        ttk.Label(client_frame, text="Proxy Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.client_host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(client_frame, textvariable=self.client_host_var, width=20).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=2
        )
        
        ttk.Label(client_frame, text="Proxy Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.client_port_var = tk.StringVar(value="8888")
        ttk.Entry(client_frame, textvariable=self.client_port_var, width=20).grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=2
        )
        
        ttk.Label(client_frame, text="Target URL:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.url_var = tk.StringVar(value="http://example.com")
        ttk.Entry(client_frame, textvariable=self.url_var, width=50).grid(
            row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=2
        )
        
        # Client control buttons
        button_frame = ttk.Frame(client_frame)
        button_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        ttk.Button(
            button_frame, text="Send Request", command=self.send_request
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame, text="Clear Output", command=self.clear_output
        ).grid(row=0, column=1, padx=5)
        
        # Response information frame
        info_frame = ttk.Frame(client_frame)
        info_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Status code
        ttk.Label(info_frame, text="Status Code:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.status_code_var = tk.StringVar(value="---")
        ttk.Label(info_frame, textvariable=self.status_code_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=1, sticky=tk.W, padx=5
        )
        
        # Cache status
        ttk.Label(info_frame, text="Cache Status:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.cache_status_var = tk.StringVar(value="---")
        ttk.Label(info_frame, textvariable=self.cache_status_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=3, sticky=tk.W, padx=5
        )
        
        # Response time
        ttk.Label(info_frame, text="Response Time:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.response_time_var = tk.StringVar(value="---")
        ttk.Label(info_frame, textvariable=self.response_time_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=1, column=1, sticky=tk.W, padx=5
        )
        
        # Response preview
        ttk.Label(client_frame, text="Response (Headers + Body Preview):").grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=(10, 2)
        )
        
        self.response_text = scrolledtext.ScrolledText(
            client_frame, height=15, width=80, wrap=tk.WORD,
            background="#f5f5f5", font=("Courier", 9)
        )
        self.response_text.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        client_frame.rowconfigure(6, weight=1)
    
    def start_server(self):
        """Start the proxy server in a background thread"""
        try:
            host = self.server_host_var.get().strip()
            port_str = self.server_port_var.get().strip()
            
            # Validate inputs
            if not host:
                messagebox.showerror("Error", "Please enter a valid host address")
                return
            
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid port number (1-65535)")
                return
            
            # Ensure cache and log files live in the project directory
            project_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(project_dir, 'cache')

            # Create proxy server instance with cache_dir forced to project cache
            self.proxy_server = ProxyServer(host=host, port=port, cache_dir=cache_dir)

            # GUI will tail the proxy.log inside that cache directory
            self.log_file_path = os.path.join(cache_dir, 'proxy.log')
            
            # Display blocked domains
            self.update_blocked_domains()
            
            # Start server in background thread
            self.server_thread = threading.Thread(
                target=self.run_server, 
                daemon=True
            )
            self.server_thread.start()
            
            # Update UI
            self.server_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.server_status_var.set(f"Server running on {host}:{port}")
            self.server_status_label.config(foreground="green")
            
        except Exception as e:
            messagebox.showerror("Server Start Error", f"Failed to start server:\n{str(e)}")
            self.server_running = False
    
    def run_server(self):
        """
        Run the server (called in background thread)
        This wraps proxy.start() and handles any exceptions
        """
        try:
            self.proxy_server.start()
        except Exception as e:
            # Update UI on main thread
            self.root.after(0, lambda: self.handle_server_error(str(e)))
    
    def handle_server_error(self, error_msg):
        """
        Handle server errors (called on main thread)
        
        Args:
            error_msg: Error message to display
        """
        messagebox.showerror("Server Error", f"Server error:\n{error_msg}")
        self.server_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.server_status_var.set("Server stopped (error)")
        self.server_status_label.config(foreground="red")
    
    def stop_server(self):
        """Stop the proxy server"""
        if self.proxy_server and self.server_running:
            # Try common stop/shutdown methods on ProxyServer in a safe order
            stopped = False
            for name in ('stop', 'shutdown', 'stop_server', 'close', 'server_close'):
                method = getattr(self.proxy_server, name, None)
                if callable(method):
                    try:
                        method()
                        stopped = True
                        break
                    except Exception:
                        # If calling one method fails, try the next
                        continue

            # If no callable method was found, try flipping common flags
            if not stopped:
                for attr, val in (('running', False), ('should_stop', True), ('_running', False)):
                    if hasattr(self.proxy_server, attr):
                        try:
                            setattr(self.proxy_server, attr, val)
                            stopped = True
                            break
                        except Exception:
                            pass

            # As a last resort, try closing an exposed socket attribute
            if not stopped and hasattr(self.proxy_server, 'server_socket'):
                try:
                    sock = getattr(self.proxy_server, 'server_socket')
                    try:
                        sock.close()
                        stopped = True
                    except Exception:
                        pass
                except Exception:
                    pass

            
            # Update UI to reflect server stopped (best-effort)
            self.server_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.server_status_var.set("Server stopped")
            self.server_status_label.config(foreground="red")
    
    def update_blocked_domains(self):
        """Update the blocked domains display"""
        if self.proxy_server:
            domains = ", ".join(self.proxy_server.blocked_domains)
            self.blocked_domains_text.config(state=tk.NORMAL)
            self.blocked_domains_text.delete(1.0, tk.END)
            self.blocked_domains_text.insert(1.0, domains)
            self.blocked_domains_text.config(state=tk.DISABLED)
    
    def poll_log_file(self):
        """
        Poll the log file for new content and update the log viewer
        This is called periodically using root.after()
        """
        if self.log_file_path and os.path.exists(self.log_file_path):
            try:
                # Open file and seek to last position
                with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self.log_file_position)
                    new_lines = f.read()
                    
                    if new_lines:
                        # Update text widget
                        self.log_text.config(state=tk.NORMAL)
                        self.log_text.insert(tk.END, new_lines)
                        self.log_text.see(tk.END)  # Auto-scroll to bottom
                        self.log_text.config(state=tk.DISABLED)
                        
                        # Update position
                        self.log_file_position = f.tell()
            except Exception as e:
                # Silently ignore errors (file might be locked, etc.)
                pass
        
        # Schedule next poll (every 500ms)
        self.root.after(500, self.poll_log_file)
    
    def send_request(self):
        """Send a request through the proxy client"""
        try:
            # Get parameters
            proxy_host = self.client_host_var.get().strip()
            proxy_port_str = self.client_port_var.get().strip()
            url = self.url_var.get().strip()
            
            # Validate inputs
            if not url:
                messagebox.showerror("Error", "Please enter a target URL")
                return
            
            if not url.startswith('http://') and not url.startswith('https://'):
                messagebox.showerror("Error", "URL must start with http:// or https://")
                return
            
            try:
                proxy_port = int(proxy_port_str)
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid proxy port number")
                return
            
            # Create or reuse client
            if not self.proxy_client or \
               self.proxy_client.proxy_host != proxy_host or \
               self.proxy_client.proxy_port != proxy_port:
                self.proxy_client = ProxyClient(proxy_host=proxy_host, proxy_port=proxy_port)
            
            # Send request
            response_text, response_time, status_code, is_cached = self.proxy_client.send_request(url)
            
            # Handle response
            if response_text is None:
                messagebox.showerror(
                    "Request Failed", 
                    "Failed to get response from proxy.\n\n"
                    "Make sure the proxy server is running and accessible."
                )
                self.status_code_var.set("ERROR")
                self.cache_status_var.set("---")
                self.response_time_var.set("---")
                return
            
            # Update status displays
            self.update_response_display(response_text, response_time, status_code, is_cached)
            
        except ConnectionRefusedError:
            messagebox.showerror(
                "Connection Refused",
                f"Could not connect to proxy at {proxy_host}:{proxy_port}\n\n"
                "Make sure the proxy server is running."
            )
        except Exception as e:
            messagebox.showerror("Request Error", f"Error sending request:\n{str(e)}")
    
    def update_response_display(self, response_text, response_time, status_code, is_cached):
        """
        Update the GUI with response information
        
        Args:
            response_text: Full HTTP response text
            response_time: Response time in seconds
            status_code: HTTP status code
            is_cached: Whether response came from cache
        """
        # Update status code (keep original formatting for display)
        self.status_code_var.set(f"{status_code}")

        # Normalize status_code to integer when possible for logic
        sc_int = None
        try:
            sc_int = int(status_code)
        except Exception:
            sc_int = None

        # Update cache status: only display hit/miss for successful (200) responses.
        # If `is_cached` is provided, use it but only for 200 responses; otherwise
        # show '---' for non-200 responses (e.g., 403 should not show cache info).
        if sc_int == 200:
            if is_cached is True:
                self.cache_status_var.set("✓ CACHE HIT")
            elif is_cached is False:
                self.cache_status_var.set("✗ CACHE MISS")
            else:
                # Unknown cache flag but 200 response — assume miss by default
                self.cache_status_var.set("✗ CACHE MISS")
        else:
            # Non-200 responses should not report cache hit/miss
            self.cache_status_var.set("---")
        
        # Update response time
        self.response_time_var.set(f"{response_time*1000:.2f} ms")
        
        # Parse and display response
        try:
            parts = response_text.split('\r\n\r\n', 1)
            headers = parts[0]
            body = parts[1] if len(parts) > 1 else ""
            
            # Limit body preview
            body_preview = body[:1000]
            if len(body) > 1000:
                body_preview += f"\n\n... (truncated, total length: {len(body)} characters)"
            
            # Build display text
            display_text = "=== HEADERS ===\n"
            display_text += headers
            display_text += "\n\n=== BODY PREVIEW ===\n"
            display_text += body_preview
            
            # Update text widget
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(1.0, display_text)
            
        except Exception as e:
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(1.0, f"Error displaying response: {str(e)}\n\n{response_text[:500]}")
    
    def clear_output(self):
        """Clear all client output displays"""
        self.status_code_var.set("---")
        self.cache_status_var.set("---")
        self.response_time_var.set("---")
        self.response_text.delete(1.0, tk.END)


def main():
    """Main entry point for the GUI application"""
    root = tk.Tk()
    app = ProxyApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()