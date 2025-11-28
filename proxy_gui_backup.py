import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import time
from datetime import datetime
import threading
import statistics
import json
import os
import subprocess
import queue
from proxy_client import ProxyClient
from proxy_server import ProxyServer


class ProxyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IS370 HTTP Proxy System - King Saud University")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        
        # Proxy configuration
        self.proxy_host = '127.0.0.1'
        self.proxy_port = 8888
        
        # Components
        self.proxy_client = ProxyClient(self.proxy_host, self.proxy_port)
        self.proxy_server = None
        self.server_process = None
        self.server_running = False
        
        # Data storage
        self.request_log = []
        self.cache_entries = []
        self.blocked_domains = []
        self.log_queue = queue.Queue()
        self.cache_stats = {'hits': 0, 'misses': 0, 'total_requests': 0}
        
        # Create GUI
        self.create_notebook()
        self.create_client_gui()
        self.create_server_gui()
        
        self.root.after(500, self.check_proxy_connection)
        
        # Start log processor
        self.process_logs()
        
        # Create a new frame for the proxy configuration
        config_frame = ttk.Frame(main_frame)
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Create a label frame for the proxy configuration
        proxy_config_frame = ttk.LabelFrame(config_frame, text="Proxy Configuration", padding="10")
        proxy_config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))

        ttk.Label(proxy_config_frame, text="Proxy Host:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.host_entry = ttk.Entry(proxy_config_frame, width=20)
        self.host_entry.insert(0, self.proxy_host)
        self.host_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(config_frame, text="Proxy Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.port_entry = ttk.Entry(config_frame, width=10)
        self.port_entry.insert(0, str(self.proxy_port))
        self.port_entry.grid(row=0, column=3, sticky=tk.W)
        
        # ========== REQUEST SECTION ========== REMOVED
        # request_frame = ttk.LabelFrame(main_frame, text="Send Request", padding="10")
        # request_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        # request_frame.columnconfigure(1, weight=1)
        
        ttk.Label(main_frame, text="URL:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.url_entry = ttk.Entry(main_frame, width=60)
        ttk.Label(request_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.url_entry = ttk.Entry(request_frame, width=60)
        self.url_entry.insert(0, "http://example.com")
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.send_button = ttk.Button(request_frame, text="Send Request", 
                                      command=self.send_single_request)
        self.send_button.grid(row=0, column=2, padx=(0, 5))
        
        # ========== TESTING OPTIONS ==========
        test_frame = ttk.LabelFrame(main_frame, text="Testing Options", padding="10")
        test_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(test_frame, text="Number of Requests:").grid(row=0, column=0, 
                                                                sticky=tk.W, padx=(0, 5))
        self.num_requests_spinbox = ttk.Spinbox(test_frame, from_=1, to=10, width=5)
        self.num_requests_spinbox.set(3)
        self.num_requests_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(test_frame, text="Delay (seconds):").grid(row=0, column=2, 
                                                             sticky=tk.W, padx=(0, 5))
        self.delay_spinbox = ttk.Spinbox(test_frame, from_=0, to=10, width=5)
        self.delay_spinbox.set(1)
        self.delay_spinbox.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        self.test_cache_button = ttk.Button(test_frame, text="Test Caching", 
                                           command=self.test_caching)
        self.test_cache_button.grid(row=0, column=4, padx=(0, 5))
        
        self.test_firewall_button = ttk.Button(test_frame, text="Test Firewall", 
                                              command=self.test_firewall)
        self.test_firewall_button.grid(row=0, column=5, padx=(0, 5))
        
        self.comprehensive_button = ttk.Button(test_frame, text="Comprehensive Test", 
                                              command=self.comprehensive_test)
        self.comprehensive_button.grid(row=0, column=6)
        
        # ========== OUTPUT SECTION ==========
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="10")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # Output text area with scrollbar
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, 
                                                     height=20, font=('Courier', 9))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ========== CONTROL BUTTONS ==========
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.clear_button = ttk.Button(control_frame, text="Clear Output", 
                                       command=self.clear_output)
        self.clear_button.grid(row=0, column=0, padx=(0, 5))
        
        self.stats_button = ttk.Button(control_frame, text="View Statistics", 
                                       command=self.show_statistics)
        self.stats_button.grid(row=0, column=1, padx=(0, 5))
        
        # Status bar
        self.status_label = ttk.Label(control_frame, text="Ready", 
                                      relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(20, 0))
        control_frame.columnconfigure(2, weight=1)
        
    def log_output(self, message, tag=None):
        """Add message to output text area"""
        self.output_text.insert(tk.END, message + "\n")
        if tag:
            # You can configure tags for different colors
            pass
        self.output_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_output(self):
        """Clear the output text area"""
        self.output_text.delete(1.0, tk.END)
        
    def check_proxy_connection(self):
        """Check if proxy server is running"""
        try:
            proxy_host = self.host_entry.get()
            proxy_port = int(self.port_entry.get())
            
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)
            result = test_socket.connect_ex((proxy_host, proxy_port))
            test_socket.close()
            
            if result == 0:
                self.update_status(f"✓ Connected to proxy server at {proxy_host}:{proxy_port}")
                self.log_output(f"[SUCCESS] Proxy server is running on {proxy_host}:{proxy_port}\n")
            else:
                self.update_status(f"✗ Proxy server not responding")
                self.log_output(f"[WARNING] Cannot connect to proxy server at {proxy_host}:{proxy_port}")
                self.log_output(f"[INFO] Please start the proxy server first:")
                self.log_output(f"       python proxy_server.py\n")
                messagebox.showwarning(
                    "Proxy Server Not Running",
                    f"Cannot connect to proxy server at {proxy_host}:{proxy_port}\n\n"
                    f"Please start the proxy server first:\n"
                    f"python proxy_server.py"
                )
        except Exception as e:
            self.update_status("✗ Connection check failed")
            self.log_output(f"[ERROR] Connection check failed: {e}\n")
        
    def update_status(self, message):
        """Update status bar"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
        
    def disable_buttons(self):
        """Disable all action buttons"""
        self.send_button.config(state='disabled')
        self.test_cache_button.config(state='disabled')
        self.test_firewall_button.config(state='disabled')
        self.comprehensive_button.config(state='disabled')
        
    def enable_buttons(self):
        """Enable all action buttons"""
        self.send_button.config(state='normal')
        self.test_cache_button.config(state='normal')
        self.test_firewall_button.config(state='normal')
        self.comprehensive_button.config(state='normal')
        
    def send_request(self, url):
        """Send HTTP GET request to proxy server"""
        request_start = time.time()
        
        try:
            # Get proxy configuration
            proxy_host = self.host_entry.get()
            proxy_port = int(self.port_entry.get())
            
            # Create socket connection to proxy
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(15)
            
            self.log_output(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to proxy server...")
            client_socket.connect((proxy_host, proxy_port))
            
            # Construct HTTP GET request
            request = f"GET {url} HTTP/1.1\r\n"
            request += f"Host: {proxy_host}\r\n"
            request += "User-Agent: IS370-GUI-Client/1.0\r\n"
            request += "Connection: close\r\n"
            request += "\r\n"
            
            self.log_output(f"[{datetime.now().strftime('%H:%M:%S')}] Sending request for: {url}")
            
            # Send request
            client_socket.send(request.encode())
            
            # Receive response
            receive_start = time.time()
            response = b''
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                response += data
            
            receive_time = time.time() - receive_start
            client_socket.close()
            
            # Calculate total response time
            total_time = time.time() - request_start
            
            # Decode response
            response_text = response.decode('utf-8', errors='ignore')
            
            # Extract status code
            status_code = self.extract_status_code(response_text)
            
            # Determine if response came from cache (heuristic)
            is_cached = receive_time < 0.05 and total_time < 0.1
            
            # Log request details
            log_entry = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'total_time': total_time,
                'receive_time': receive_time,
                'status_code': status_code,
                'is_cached': is_cached,
                'response_size': len(response)
            }
            self.request_log.append(log_entry)
            
            return response_text, total_time, status_code, is_cached
            
        except ConnectionRefusedError:
            error_msg = f"Connection refused. Is the proxy server running on {proxy_host}:{proxy_port}?"
            self.log_output(f"[ERROR] {error_msg}")
            messagebox.showerror("Connection Error", error_msg)
            return None, 0, 0, False
            
        except socket.timeout:
            self.log_output(f"[ERROR] Request timeout for {url}")
            messagebox.showerror("Timeout Error", f"Request timeout for {url}")
            return None, 0, 0, False
            
        except Exception as e:
            self.log_output(f"[ERROR] {str(e)}")
            messagebox.showerror("Error", str(e))
            return None, 0, 0, False
            
    def extract_status_code(self, response_text):
        """Extract HTTP status code from response"""
        try:
            status_line = response_text.split('\r\n')[0]
            parts = status_line.split()
            if len(parts) >= 2:
                return int(parts[1])
        except:
            pass
        return 0
        
    def display_response(self, response_text, response_time, status_code, is_cached, url):
        """Display response details"""
        self.log_output("\n" + "="*70)
        self.log_output(f"RESPONSE FOR: {url}")
        self.log_output("="*70)
        
        if response_text is None:
            self.log_output("[ERROR] No response received")
            self.log_output("="*70 + "\n")
            return
            
        # Display status
        if status_code == 200:
            self.log_output("Status: ✓ OK - Request successful")
        elif status_code == 403:
            self.log_output("Status: ✗ FORBIDDEN - Request blocked by firewall")
        elif status_code == 502:
            self.log_output("Status: ✗ BAD GATEWAY - Failed to fetch from web server")
        elif status_code == 500:
            self.log_output("Status: ✗ INTERNAL SERVER ERROR")
        elif status_code == 400:
            self.log_output("Status: ✗ BAD REQUEST")
            
        # Display performance metrics
        self.log_output("\n--- PERFORMANCE METRICS ---")
        self.log_output(f"Response Time: {response_time:.4f} seconds ({response_time*1000:.2f} ms)")
        
        # Determine cache status
        if status_code == 200:
            if is_cached:
                self.log_output(f"Cache Status: ✓ CACHE HIT")
            else:
                self.log_output(f"Cache Status: ✗ CACHE MISS")
                
        self.log_output("="*70 + "\n")
        
    def send_single_request(self):
        """Send a single request"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Invalid Input", "Please enter a URL")
            return
            
        if not url.startswith('http://') and not url.startswith('https://'):
            messagebox.showwarning("Invalid URL", "URL must start with http:// or https://")
            return
            
        # Run in separate thread to prevent GUI freezing
        thread = threading.Thread(target=self._send_single_request_thread, args=(url,))
        thread.daemon = True
        thread.start()
        
    def create_client_gui(self):
        """Create the Client GUI (Browser Simulator)"""
        # Main container
        client_main = ttk.PanedWindow(self.client_frame, orient=tk.VERTICAL)
        client_main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top panel for request
        top_frame = ttk.Frame(client_main)
        client_main.add(top_frame, weight=1)
        
        # Request Panel
        request_frame = ttk.LabelFrame(top_frame, text="Request Panel", padding="10")
        request_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # URL input
        ttk.Label(request_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.client_url_entry = ttk.Entry(request_frame, width=80)
        self.client_url_entry.insert(0, "http://example.com")
        self.client_url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.client_send_button = ttk.Button(request_frame, text="Send GET", 
                                           command=self.client_send_request)
        self.client_send_button.grid(row=0, column=2, padx=(0, 5))
        
        # ETag input for validation testing
        ttk.Label(request_frame, text="If-None-Match:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.etag_entry = ttk.Entry(request_frame, width=40)
        self.etag_entry.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        
        request_frame.columnconfigure(1, weight=1)
        
        # Response Panel
        response_frame = ttk.LabelFrame(top_frame, text="Response Panel", padding="10")
        response_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status line
        self.status_line = ttk.Label(response_frame, text="Status: Ready", 
                                    font=('Arial', 10, 'bold'), foreground='blue')
        self.status_line.pack(anchor=tk.W, pady=(0, 5))
        
        # Performance and cache indicator
        perf_frame = ttk.Frame(response_frame)
        perf_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.timer_label = ttk.Label(perf_frame, text="Response Time: -- ms")
        self.timer_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.cache_badge = ttk.Label(perf_frame, text="Source: --", 
                                     font=('Arial', 9, 'bold'))
        self.cache_badge.pack(side=tk.LEFT)
        
        # Notebook for headers and body
        response_notebook = ttk.Notebook(response_frame)
        response_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Headers tab
        headers_frame = ttk.Frame(response_notebook)
        response_notebook.add(headers_frame, text="Response Headers")
        
        self.headers_text = scrolledtext.ScrolledText(headers_frame, height=10, 
                                                     font=('Courier', 9))
        self.headers_text.pack(fill=tk.BOTH, expand=True)
        
        # Body tab
        body_frame = ttk.Frame(response_notebook)
        response_notebook.add(body_frame, text="Response Body")
        
        self.body_text = scrolledtext.ScrolledText(body_frame, height=15, 
                                                  font=('Courier', 9))
        self.body_text.pack(fill=tk.BOTH, expand=True)
        
        # Bottom panel for history
        bottom_frame = ttk.Frame(client_main)
        client_main.add(bottom_frame, weight=1)
        
        # History Panel
        history_frame = ttk.LabelFrame(bottom_frame, text="Request History", padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for history
        columns = ('URL', 'Time', 'Status', 'Hit/Miss')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            if col == 'URL':
                self.history_tree.column(col, width=300)
            elif col == 'Time':
                self.history_tree.column(col, width=150)
            else:
                self.history_tree.column(col, width=100)
        
        # Scrollbar for treeview
        history_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, 
                                          command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to view details
        self.history_tree.bind('<Double-1>', self.view_history_details)
        
    def create_server_gui(self):
        """Create the Proxy Server GUI (Control Center)"""
        # Main container
        server_main = ttk.PanedWindow(self.server_frame, orient=tk.VERTICAL)
        server_main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Top section for server control and firewall
        top_section = ttk.Frame(server_main)
        server_main.add(top_section, weight=1)
        
        # Server Control
        server_control_frame = ttk.LabelFrame(top_section, text="Server Control", padding="10")
        server_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        control_buttons = ttk.Frame(server_control_frame)
        control_buttons.pack(fill=tk.X)
        
        self.start_server_button = ttk.Button(control_buttons, text="Start Proxy", 
                                             command=self.start_proxy_server)
        self.start_server_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_server_button = ttk.Button(control_buttons, text="Stop Proxy", 
                                            command=self.stop_proxy_server, state='disabled')
        self.stop_server_button.pack(side=tk.LEFT, padx=(0, 20))
        
        self.server_status_label = ttk.Label(control_buttons, text="Server: Stopped", 
                                            font=('Arial', 10, 'bold'), foreground='red')
        self.server_status_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.server_info_label = ttk.Label(control_buttons, text="Listening: --")
        self.server_info_label.pack(side=tk.LEFT)
        
        # Firewall Management
        firewall_frame = ttk.LabelFrame(top_section, text="Firewall (Blocked Domains)", padding="10")
        firewall_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add domain controls
        add_domain_frame = ttk.Frame(firewall_frame)
        add_domain_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(add_domain_frame, text="Add Domain:").pack(side=tk.LEFT, padx=(0, 5))
        self.domain_entry = ttk.Entry(add_domain_frame, width=30)
        self.domain_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.add_domain_button = ttk.Button(add_domain_frame, text="Add", 
                                           command=self.add_blocked_domain)
        self.add_domain_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.remove_domain_button = ttk.Button(add_domain_frame, text="Remove Selected", 
                                              command=self.remove_blocked_domain)
        self.remove_domain_button.pack(side=tk.LEFT)
        
        # Blocked domains list
        self.blocked_tree = ttk.Treeview(firewall_frame, columns=('Domain',), show='headings', height=6)
        self.blocked_tree.heading('Domain', text='Blocked Domain')
        self.blocked_tree.column('Domain', width=200)
        
        blocked_scrollbar = ttk.Scrollbar(firewall_frame, orient=tk.VERTICAL, 
                                         command=self.blocked_tree.yview)
        self.blocked_tree.configure(yscrollcommand=blocked_scrollbar.set)
        
        self.blocked_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5, 0))
        blocked_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(5, 0))
        
        # Load initial blocked domains
        self.load_blocked_domains()
        
        # Middle section for cache management
        middle_section = ttk.Frame(server_main)
        server_main.add(middle_section, weight=1)
        
        cache_frame = ttk.LabelFrame(middle_section, text="Cache Management", padding="10")
        cache_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cache control buttons
        cache_buttons = ttk.Frame(cache_frame)
        cache_buttons.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(cache_buttons, text="Clear Cache", 
                  command=self.clear_cache).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cache_buttons, text="Remove Selected", 
                  command=self.remove_cache_entry).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cache_buttons, text="Refresh Selected", 
                  command=self.refresh_cache_entry).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cache_buttons, text="Refresh List", 
                  command=self.refresh_cache_list).pack(side=tk.LEFT)
        
        # Cache entries table
        cache_columns = ('URL', 'Stored Time', 'Expiry', 'ETag', 'Size', 'Hit Count')
        self.cache_tree = ttk.Treeview(cache_frame, columns=cache_columns, show='headings', height=8)
        
        for col in cache_columns:
            self.cache_tree.heading(col, text=col)
            if col == 'URL':
                self.cache_tree.column(col, width=250)
            elif col in ['Stored Time', 'Expiry']:
                self.cache_tree.column(col, width=150)
            elif col == 'Size':
                self.cache_tree.column(col, width=80)
            else:
                self.cache_tree.column(col, width=100)
        
        cache_scrollbar = ttk.Scrollbar(cache_frame, orient=tk.VERTICAL, 
                                        command=self.cache_tree.yview)
        self.cache_tree.configure(yscrollcommand=cache_scrollbar.set)
        
        self.cache_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5, 0))
        cache_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(5, 0))
        
        # Cache statistics
        cache_stats_frame = ttk.Frame(cache_frame)
        cache_stats_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.cache_stats_label = ttk.Label(cache_stats_frame, 
                                         text="Total: 0 | Size: 0 KB | Hits: 0 | Misses: 0 | Hit Rate: 0%")
        self.cache_stats_label.pack(anchor=tk.W)
        
        # Bottom section for logging
        bottom_section = ttk.Frame(server_main)
        server_main.add(bottom_section, weight=2)
        
        log_frame = ttk.LabelFrame(bottom_section, text="Logging Console", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log filters
        log_filters = ttk.Frame(log_frame)
        log_filters.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(log_filters, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_filter_var = tk.StringVar(value="ALL")
        filters = ["ALL", "Cache HIT", "Cache MISS", "Blocked", "Errors"]
        for filter_option in filters:
            ttk.Radiobutton(log_filters, text=filter_option, variable=self.log_filter_var, 
                           value=filter_option, command=self.filter_logs).pack(side=tk.LEFT, padx=(0, 10))
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, font=('Courier', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for colored logging
        self.log_text.tag_configure("HIT", foreground="green")
        self.log_text.tag_configure("MISS", foreground="orange")
        self.log_text.tag_configure("BLOCKED", foreground="red")
        self.log_text.tag_configure("ERROR", foreground="red", font=('Courier', 9, 'bold'))
        
    def client_send_request(self):
        """Send request from client GUI"""
        url = self.client_url_entry.get().strip()
        etag = self.etag_entry.get().strip()
        
        if not url:
            messagebox.showwarning("Invalid Input", "Please enter a URL")
            return
            
        if not url.startswith('http://') and not url.startswith('https://'):
            messagebox.showwarning("Invalid URL", "URL must start with http:// or https://")
            return
            
        # Run in separate thread
        thread = threading.Thread(target=self._client_send_request_thread, args=(url, etag))
        thread.daemon = True
        thread.start()
        
    def _client_send_request_thread(self, url, etag):
        """Thread worker for client request"""
        try:
            start_time = time.time()
            
            # Send request using proxy client
            response_text, response_time, status_code, is_cached = self.proxy_client.send_request(url)
            
            # Update GUI in main thread
            self.root.after(0, self.update_client_response, url, response_text, response_time, status_code, is_cached)
            
        except Exception as e:
            self.root.after(0, self.update_client_error, str(e))
            
    def update_client_response(self, url, response_text, response_time, status_code, is_cached):
        """Update client GUI with response"""
        # Update status line
        status_text = f"Status: {status_code}"
        if status_code == 200:
            status_text += " OK"
            self.status_line.config(text=status_text, foreground="green")
        elif status_code == 403:
            status_text += " Forbidden"
            self.status_line.config(text=status_text, foreground="red")
        elif status_code == 404:
            status_text += " Not Found"
            self.status_line.config(text=status_text, foreground="orange")
        else:
            status_text += f" {status_code}"
            self.status_line.config(text=status_text, foreground="black")
            
        # Update performance metrics
        self.timer_label.config(text=f"Response Time: {response_time*1000:.2f} ms")
        
        # Update cache badge
        if is_cached:
            self.cache_badge.config(text="Source: Cache HIT ✅", foreground="green")
        else:
            self.cache_badge.config(text="Source: Cache MISS 🌐", foreground="blue")
            
        # Parse and display response
        if response_text:
            parts = response_text.split('\r\n\r\n', 1)
            headers = parts[0] if parts else ""
            body = parts[1] if len(parts) > 1 else ""
            
            # Update headers
            self.headers_text.delete(1.0, tk.END)
            self.headers_text.insert(1.0, headers)
            
            # Update body
            self.body_text.delete(1.0, tk.END)
            self.body_text.insert(1.0, body)
            
        # Add to history
        timestamp = datetime.now().strftime('%H:%M:%S')
        hit_miss = "HIT" if is_cached else "MISS"
        self.history_tree.insert('', 0, values=(url, timestamp, status_code, hit_miss))
        
        # Limit history to 50 entries
        if len(self.history_tree.get_children()) > 50:
            self.history_tree.delete(self.history_tree.get_children()[-1])
            
    def update_client_error(self, error_msg):
        """Update client GUI with error"""
        self.status_line.config(text=f"Error: {error_msg}", foreground="red")
        self.timer_label.config(text="Response Time: -- ms")
        self.cache_badge.config(text="Source: --", foreground="black")
        
    def view_history_details(self, event):
        """View details of selected history item"""
        selection = self.history_tree.selection()
        if not selection:
            return
            
        item = self.history_tree.item(selection[0])
        values = item['values']
        
        # Create details window
        details_window = tk.Toplevel(self.root)
        details_window.title("Request Details")
        details_window.geometry("500x300")
        
        text = scrolledtext.ScrolledText(details_window, wrap=tk.WORD, font=('Courier', 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text.insert(tk.END, f"URL: {values[0]}\n")
        text.insert(tk.END, f"Time: {values[1]}\n")
        text.insert(tk.END, f"Status Code: {values[2]}\n")
        text.insert(tk.END, f"Cache: {values[3]}\n")
        
        text.config(state='disabled')
        
    def start_proxy_server(self):
        """Start the proxy server"""
        try:
            # Start server in separate thread
            self.proxy_server = ProxyServer(host=self.proxy_host, port=self.proxy_port)
            server_thread = threading.Thread(target=self._run_server_thread)
            server_thread.daemon = True
            server_thread.start()
            
            # Update GUI
            self.server_running = True
            self.start_server_button.config(state='disabled')
            self.stop_server_button.config(state='normal')
            self.server_status_label.config(text="Server: Running", foreground="green")
            self.server_info_label.config(text=f"Listening: {self.proxy_host}:{self.proxy_port}")
            
            # Add log entry
            self.add_log_entry("INFO", "Server started", f"{self.proxy_host}:{self.proxy_port}", "STARTED", 200, "")
            
            # Refresh cache list periodically
            self.refresh_cache_list()
            self.root.after(5000, self.periodic_cache_refresh)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            
    def _run_server_thread(self):
        """Run server in thread"""
        try:
            self.proxy_server.start()
        except Exception as e:
            self.root.after(0, self.add_log_entry, "ERROR", "Server", "CRASH", 500, str(e))
            
    def stop_proxy_server(self):
        """Stop the proxy server"""
        try:
            if self.proxy_server:
                # Note: The server doesn't have a clean stop method, 
                # but we'll update the GUI state
                self.server_running = False
                
                # Update GUI
                self.start_server_button.config(state='normal')
                self.stop_server_button.config(state='disabled')
                self.server_status_label.config(text="Server: Stopped", foreground="red")
                self.server_info_label.config(text="Listening: --")
                
                # Add log entry
                self.add_log_entry("INFO", "Server stopped", f"{self.proxy_host}:{self.proxy_port}", "STOPPED", 200, "")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop server: {e}")
            
    def add_blocked_domain(self):
        """Add domain to blocked list"""
        domain = self.domain_entry.get().strip().lower()
        if not domain:
            return
            
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Check if already exists
        for item in self.blocked_tree.get_children():
            if self.blocked_tree.item(item)['values'][0] == domain:
                messagebox.showwarning("Duplicate", f"Domain {domain} is already blocked")
                return
                
        # Add to tree
        self.blocked_tree.insert('', 0, values=(domain,))
        self.blocked_domains.append(domain)
        
        # Update server if running
        if self.proxy_server:
            self.proxy_server.blocked_domains.append(domain)
            
        # Clear entry
        self.domain_entry.delete(0, tk.END)
        
        # Add log entry
        self.add_log_entry("INFO", "Firewall", domain, "BLOCKED", 403, "Domain added to blocklist")
        
    def remove_blocked_domain(self):
        """Remove selected domain from blocked list"""
        selection = self.blocked_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a domain to remove")
            return
            
        item = self.blocked_tree.item(selection[0])
        domain = item['values'][0]
        
        # Remove from tree
        self.blocked_tree.delete(selection[0])
        
        # Remove from list
        if domain in self.blocked_domains:
            self.blocked_domains.remove(domain)
            
        # Update server if running
        if self.proxy_server and domain in self.proxy_server.blocked_domains:
            self.proxy_server.blocked_domains.remove(domain)
            
        # Add log entry
        self.add_log_entry("INFO", "Firewall", domain, "UNBLOCKED", 200, "Domain removed from blocklist")
        
    def load_blocked_domains(self):
        """Load initial blocked domains from server"""
        if self.proxy_server:
            self.blocked_domains = self.proxy_server.blocked_domains.copy()
        else:
            # Default blocked domains
            self.blocked_domains = ['facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com']
            
        # Populate tree
        for domain in self.blocked_domains:
            self.blocked_tree.insert('', 0, values=(domain,))
            
    def clear_cache(self):
        """Clear all cache entries"""
        try:
            cache_dir = 'cache'
            if os.path.exists(cache_dir):
                for filename in os.listdir(cache_dir):
                    if filename.endswith('.cache'):
                        os.remove(os.path.join(cache_dir, filename))
                        
            # Clear metadata
            metadata_file = os.path.join(cache_dir, 'metadata.json')
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
                
            # Refresh list
            self.refresh_cache_list()
            
            # Add log entry
            self.add_log_entry("INFO", "Cache", "ALL", "CLEARED", 200, "All cache entries cleared")
            
            messagebox.showinfo("Success", "Cache cleared successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear cache: {e}")
            
    def remove_cache_entry(self):
        """Remove selected cache entry"""
        selection = self.cache_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a cache entry to remove")
            return
            
        item = self.cache_tree.item(selection[0])
        url = item['values'][0]
        
        try:
            # Get cache filename
            if self.proxy_server:
                cache_file = self.proxy_server.get_cache_filename(url)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    
            # Remove from metadata
            if self.proxy_server and url in self.proxy_server.cache_metadata:
                del self.proxy_server.cache_metadata[url]
                self.proxy_server.save_cache_metadata()
                
            # Refresh list
            self.refresh_cache_list()
            
            # Add log entry
            self.add_log_entry("INFO", "Cache", url, "REMOVED", 200, "Cache entry removed")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove cache entry: {e}")
            
    def refresh_cache_entry(self):
        """Force refresh selected cache entry"""
        selection = self.cache_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a cache entry to refresh")
            return
            
        item = self.cache_tree.item(selection[0])
        url = item['values'][0]
        
        # Remove cache entry (will be re-fetched on next request)
        self.remove_cache_entry()
        
        # Add log entry
        self.add_log_entry("INFO", "Cache", url, "REFRESH", 200, "Cache entry marked for refresh")
        
    def refresh_cache_list(self):
        """Refresh the cache entries list"""
        # Clear existing items
        for item in self.cache_tree.get_children():
            self.cache_tree.delete(item)
            
        self.cache_entries = []
        
        try:
            if self.proxy_server:
                # Load from metadata
                metadata = self.proxy_server.cache_metadata
                
                total_size = 0
                for url, data in metadata.items():
                    cache_file = self.proxy_server.get_cache_filename(url)
                    size = os.path.getsize(cache_file) if os.path.exists(cache_file) else 0
                    total_size += size
                    
                    stored_time = data.get('cached_at', 'Unknown')
                    expiry = data.get('expiry', 'Unknown')
                    etag = data.get('etag', 'N/A')
                    hit_count = data.get('hit_count', 0)
                    
                    # Format times
                    if stored_time != 'Unknown':
                        try:
                            dt = datetime.fromisoformat(stored_time.replace('Z', '+00:00'))
                            stored_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                            
                    if expiry != 'Unknown':
                        try:
                            dt = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                            expiry = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                            
                    values = (url, stored_time, expiry, etag or 'N/A', f"{size}B", hit_count)
                    self.cache_tree.insert('', 0, values=values)
                    self.cache_entries.append(values)
                    
                # Update statistics
                self.update_cache_statistics(total_size)
                
        except Exception as e:
            print(f"Error refreshing cache list: {e}")
            
    def update_cache_statistics(self, total_size_bytes):
        """Update cache statistics display"""
        total_entries = len(self.cache_entries)
        total_size_kb = total_size_bytes / 1024
        
        hits = self.cache_stats.get('hits', 0)
        misses = self.cache_stats.get('misses', 0)
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        
        stats_text = f"Total: {total_entries} | Size: {total_size_kb:.1f} KB | Hits: {hits} | Misses: {misses} | Hit Rate: {hit_rate:.1f}%"
        self.cache_stats_label.config(text=stats_text)
        
    def periodic_cache_refresh(self):
        """Periodically refresh cache list if server is running"""
        if self.server_running:
            self.refresh_cache_list()
            self.root.after(10000, self.periodic_cache_refresh)  # Refresh every 10 seconds
            
    def add_log_entry(self, log_type, client_ip, url, result, status_code, error_msg=""):
        """Add entry to log console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Format log line
        log_line = f"[{timestamp}] {client_ip} {url} {result} {status_code}"
        if error_msg:
            log_line += f" {error_msg}"
            
        # Add to queue for thread-safe processing
        self.log_queue.put((log_type, log_line))
        
    def process_logs(self):
        """Process log entries from queue"""
        try:
            while not self.log_queue.empty():
                log_type, log_line = self.log_queue.get_nowait()
                
                # Apply filter
                filter_value = self.log_filter_var.get()
                if filter_value != "ALL":
                    if filter_value == "Cache HIT" and "HIT" not in log_line:
                        continue
                    elif filter_value == "Cache MISS" and "MISS" not in log_line:
                        continue
                    elif filter_value == "Blocked" and "BLOCKED" not in log_line:
                        continue
                    elif filter_value == "Errors" and "ERROR" not in log_line:
                        continue
                        
                # Add to log text with appropriate tag
                self.log_text.insert(tk.END, log_line + "\n", log_type)
                self.log_text.see(tk.END)
                
                # Limit log size
                lines = int(self.log_text.index('end-1c').split('.')[0])
                if lines > 1000:
                    self.log_text.delete(1.0, "100.0")
                    
        except queue.Empty:
            pass
            
        # Schedule next processing
        self.root.after(100, self.process_logs)
        
    def filter_logs(self):
        """Filter log display"""
        # Clear and re-display logs with new filter
        self.log_text.delete(1.0, tk.END)
        
    def check_proxy_connection(self):
        """Check if proxy server is running"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)
            result = test_socket.connect_ex((self.proxy_host, self.proxy_port))
            test_socket.close()
            
            if result == 0:
                self.server_running = True
                self.start_server_button.config(state='disabled')
                self.stop_server_button.config(state='normal')
                self.server_status_label.config(text="Server: Running", foreground="green")
                self.server_info_label.config(text=f"Listening: {self.proxy_host}:{self.proxy_port}")
            else:
                self.server_running = False
                self.start_server_button.config(state='normal')
                self.stop_server_button.config(state='disabled')
                self.server_status_label.config(text="Server: Stopped", foreground="red")
                self.server_info_label.config(text="Listening: --")
                
        except Exception as e:
            print(f"Error checking connection: {e}")
        
def main():
    root = tk.Tk()
    app = ProxyGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()