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
        
        # Check proxy connection on startup
        self.root.after(500, self.check_proxy_connection)
        
        # Start log processor
        self.process_logs()
        
    def create_notebook(self):
        """Create the main notebook with tabs"""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.client_frame = ttk.Frame(self.notebook)
        self.server_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.client_frame, text="Client GUI (Browser Simulator)")
        self.notebook.add(self.server_frame, text="Proxy Server GUI (Control Center)")
        
    def create_client_gui(self):
        """Create the Client GUI (Browser Simulator)"""
        # Main container
        client_main = ttk.PanedWindow(self.client_frame, orient=tk.VERTICAL)
        client_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Request Panel
        request_frame = ttk.LabelFrame(client_main, text="Request Panel", padding="10")
        client_main.add(request_frame, weight=1)
        
        # URL input
        url_frame = ttk.Frame(request_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=(0, 5))
        self.client_url_entry = ttk.Entry(url_frame, width=60)
        self.client_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.client_url_entry.insert(0, "http://example.com")
        
        self.send_get_button = ttk.Button(url_frame, text="Send GET", command=self.send_client_request)
        self.send_get_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # ETag input
        etag_frame = ttk.Frame(request_frame)
        etag_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(etag_frame, text="If-None-Match / ETag:").pack(side=tk.LEFT, padx=(0, 5))
        self.etag_entry = ttk.Entry(etag_frame, width=40)
        self.etag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Response Panel
        response_frame = ttk.LabelFrame(client_main, text="Response Panel", padding="10")
        client_main.add(response_frame, weight=2)
        
        # Status line
        self.status_label = ttk.Label(response_frame, text="Status: Ready", font=('Arial', 10, 'bold'))
        self.status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Headers viewer
        headers_frame = ttk.LabelFrame(response_frame, text="Response Headers", padding="5")
        headers_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.headers_text = scrolledtext.ScrolledText(headers_frame, height=8, font=('Courier', 9))
        self.headers_text.pack(fill=tk.BOTH, expand=True)
        
        # Body viewer
        body_frame = ttk.LabelFrame(response_frame, text="Response Body", padding="5")
        body_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.body_text = scrolledtext.ScrolledText(body_frame, height=12, font=('Courier', 9))
        self.body_text.pack(fill=tk.BOTH, expand=True)
        
        # Performance and Cache Indicator
        perf_frame = ttk.Frame(response_frame)
        perf_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.timer_label = ttk.Label(perf_frame, text="Response Time: -- ms")
        self.timer_label.pack(side=tk.LEFT, padx=(0, 20))
        
        self.cache_badge = ttk.Label(perf_frame, text="Source: --", font=('Arial', 9, 'bold'))
        self.cache_badge.pack(side=tk.LEFT)
        
        # History
        history_frame = ttk.LabelFrame(client_main, text="Request History", padding="10")
        client_main.add(history_frame, weight=1)
        
        # Create treeview for history
        columns = ('URL', 'Time', 'Status', 'Cache')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            if col == 'URL':
                self.history_tree.column(col, width=300)
            else:
                self.history_tree.column(col, width=100)
        
        # Scrollbar for history
        history_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_server_gui(self):
        """Create the Server GUI (Control Center)"""
        # Main container
        server_main = ttk.PanedWindow(self.server_frame, orient=tk.VERTICAL)
        server_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Server Control
        control_frame = ttk.LabelFrame(server_main, text="Server Control", padding="10")
        server_main.add(control_frame, weight=0)
        
        control_inner = ttk.Frame(control_frame)
        control_inner.pack(fill=tk.X)
        
        self.start_server_button = ttk.Button(control_inner, text="Start Proxy Server", command=self.start_proxy_server)
        self.start_server_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_server_button = ttk.Button(control_inner, text="Stop Proxy Server", command=self.stop_proxy_server, state='disabled')
        self.stop_server_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.server_status_label = ttk.Label(control_inner, text="Server Status: Stopped", font=('Arial', 10, 'bold'))
        self.server_status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        self.server_info_label = ttk.Label(control_inner, text=f"Listening on: {self.proxy_host}:{self.proxy_port}")
        self.server_info_label.pack(side=tk.RIGHT)
        
        # Firewall Management
        firewall_frame = ttk.LabelFrame(server_main, text="Firewall (Blocked Domains)", padding="10")
        server_main.add(firewall_frame, weight=1)
        
        # Add domain controls
        add_frame = ttk.Frame(firewall_frame)
        add_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(add_frame, text="Add Domain:").pack(side=tk.LEFT, padx=(0, 5))
        self.domain_entry = ttk.Entry(add_frame, width=30)
        self.domain_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.add_domain_button = ttk.Button(add_frame, text="Add", command=self.add_blocked_domain)
        self.add_domain_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.remove_domain_button = ttk.Button(add_frame, text="Remove Selected", command=self.remove_blocked_domain)
        self.remove_domain_button.pack(side=tk.LEFT)
        
        # Blocked domains list
        columns = ('Domain', 'Added Time')
        self.blocked_tree = ttk.Treeview(firewall_frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            self.blocked_tree.heading(col, text=col)
            self.blocked_tree.column(col, width=200)
        
        blocked_scroll = ttk.Scrollbar(firewall_frame, orient=tk.VERTICAL, command=self.blocked_tree.yview)
        self.blocked_tree.configure(yscrollcommand=blocked_scroll.set)
        
        self.blocked_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        blocked_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Cache Management
        cache_frame = ttk.LabelFrame(server_main, text="Cache Management", padding="10")
        server_main.add(cache_frame, weight=1)
        
        # Cache control buttons
        cache_buttons = ttk.Frame(cache_frame)
        cache_buttons.pack(fill=tk.X, pady=(0, 10))
        
        self.clear_cache_button = ttk.Button(cache_buttons, text="Clear Cache", command=self.clear_cache)
        self.clear_cache_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.remove_cache_button = ttk.Button(cache_buttons, text="Remove Selected", command=self.remove_cache_entry)
        self.remove_cache_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_cache_button = ttk.Button(cache_buttons, text="Refresh Selected", command=self.refresh_cache_entry)
        self.refresh_cache_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_list_button = ttk.Button(cache_buttons, text="Refresh List", command=self.refresh_cache_list)
        self.refresh_list_button.pack(side=tk.LEFT)
        
        # Cache entries table
        cache_columns = ('URL', 'Stored Time', 'Expiry', 'ETag', 'Size', 'Hit Count')
        self.cache_tree = ttk.Treeview(cache_frame, columns=cache_columns, show='headings', height=6)
        
        for col in cache_columns:
            self.cache_tree.heading(col, text=col)
            if col == 'URL':
                self.cache_tree.column(col, width=250)
            elif col == 'Stored Time' or col == 'Expiry':
                self.cache_tree.column(col, width=120)
            else:
                self.cache_tree.column(col, width=80)
        
        cache_scroll = ttk.Scrollbar(cache_frame, orient=tk.VERTICAL, command=self.cache_tree.yview)
        self.cache_tree.configure(yscrollcommand=cache_scroll.set)
        
        self.cache_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cache_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Cache stats
        self.cache_stats_label = ttk.Label(cache_frame, text="Cache Stats: Total entries: 0 | Total size: 0 KB | Hits: 0 | Misses: 0 | Hit ratio: 0%")
        self.cache_stats_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Logging Console
        log_frame = ttk.LabelFrame(server_main, text="Logging Console", padding="10")
        server_main.add(log_frame, weight=2)
        
        # Log filters
        filter_frame = ttk.Frame(log_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.log_filter_var = tk.StringVar(value="ALL")
        filters = ["ALL", "Cache HIT", "Cache MISS", "Blocked", "Errors"]
        
        for filter_option in filters:
            ttk.Radiobutton(filter_frame, text=filter_option, variable=self.log_filter_var, 
                           value=filter_option, command=self.filter_logs).pack(side=tk.LEFT, padx=(0, 10))
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, font=('Courier', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log tags for colors
        self.log_text.tag_configure("HIT", foreground="green")
        self.log_text.tag_configure("MISS", foreground="blue")
        self.log_text.tag_configure("BLOCKED", foreground="red")
        self.log_text.tag_configure("ERROR", foreground="red")
        
    def send_client_request(self):
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
        thread = threading.Thread(target=self._send_client_request_thread, args=(url, etag))
        thread.daemon = True
        thread.start()
        
    def _send_client_request_thread(self, url, etag):
        """Thread function for sending client request"""
        try:
            request_start = time.time()
            
            # Get proxy configuration
            proxy_host = self.proxy_host
            proxy_port = self.proxy_port
            
            # Create socket connection to proxy
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(15)
            
            # Construct HTTP GET request
            request = f"GET {url} HTTP/1.1\r\n"
            request += f"Host: {proxy_host}\r\n"
            request += "User-Agent: IS370-GUI-Client/1.0\r\n"
            if etag:
                request += f"If-None-Match: {etag}\r\n"
            request += "Connection: close\r\n"
            request += "\r\n"
            
            client_socket.connect((proxy_host, proxy_port))
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
            total_time = time.time() - request_start
            client_socket.close()
            
            # Decode response
            response_text = response.decode('utf-8', errors='ignore')
            
            # Parse response
            headers, body = self.parse_response(response_text)
            status_code = self.extract_status_code(response_text)
            
            # Determine cache status (heuristic)
            is_cached = receive_time < 0.05 and total_time < 0.1
            
            # Update GUI in main thread
            self.root.after(0, self.update_client_response, response_text, headers, body, status_code, total_time, is_cached, url)
            
        except Exception as e:
            self.root.after(0, self.update_client_error, str(e))
            
    def parse_response(self, response_text):
        """Parse response into headers and body"""
        parts = response_text.split('\r\n\r\n', 1)
        if len(parts) >= 2:
            return parts[0], parts[1]
        return response_text, ""
        
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
        
    def update_client_response(self, response_text, headers, body, status_code, response_time, is_cached, url):
        """Update client GUI with response"""
        # Update status
        status_text = f"Status: {status_code}"
        if status_code == 200:
            status_text += " OK"
        elif status_code == 403:
            status_text += " Forbidden"
        elif status_code == 404:
            status_text += " Not Found"
        elif status_code == 502:
            status_text += " Bad Gateway"
        else:
            status_text += f" {response_text.split('\\r\\n')[0].split(' ', 2)[-1] if len(response_text.split('\\r\\n')[0].split(' ')) > 2 else ''}"
        
        self.status_label.config(text=status_text)
        
        # Update headers
        self.headers_text.delete(1.0, tk.END)
        self.headers_text.insert(1.0, headers)
        
        # Update body
        self.body_text.delete(1.0, tk.END)
        self.body_text.insert(1.0, body[:5000])  # Limit body size for display
        
        # Update performance indicators
        self.timer_label.config(text=f"Response Time: {response_time*1000:.2f} ms")
        
        if is_cached:
            self.cache_badge.config(text="Source: ✅ CACHE HIT", foreground="green")
        else:
            self.cache_badge.config(text="Source: 🌐 CACHE MISS", foreground="blue")
        
        # Add to history
        cache_status = "HIT" if is_cached else "MISS"
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.history_tree.insert('', 0, values=(url, timestamp, status_code, cache_status))
        
        # Limit history to 50 entries
        if len(self.history_tree.get_children()) > 50:
            self.history_tree.delete(self.history_tree.get_children()[-1])
        
        # Log the request
        self.log_request(url, status_code, is_cached)
        
    def update_client_error(self, error_msg):
        """Update client GUI with error"""
        self.status_label.config(text=f"Status: Error - {error_msg}")
        self.headers_text.delete(1.0, tk.END)
        self.body_text.delete(1.0, tk.END)
        self.timer_label.config(text="Response Time: -- ms")
        self.cache_badge.config(text="Source: --")
        
    def log_request(self, url, status_code, is_cached):
        """Log a request to the log queue"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        client_ip = "127.0.0.1"  # Local client
        
        if status_code == 403:
            result = "BLOCKED"
            log_type = "BLOCKED"
        elif is_cached:
            result = "HIT"
            log_type = "HIT"
        else:
            result = "MISS"
            log_type = "MISS"
            
        log_entry = {
            'timestamp': timestamp,
            'client_ip': client_ip,
            'url': url,
            'result': result,
            'status_code': status_code,
            'type': log_type,
            'exception': ''
        }
        
        self.log_queue.put(log_entry)
        
        # Update cache stats
        self.cache_stats['total_requests'] += 1
        if is_cached:
            self.cache_stats['hits'] += 1
        else:
            self.cache_stats['misses'] += 1
            
    def process_logs(self):
        """Process log entries from queue"""
        try:
            while not self.log_queue.empty():
                log_entry = self.log_queue.get_nowait()
                
                # Format log message
                message = f"[{log_entry['timestamp']}] {log_entry['client_ip']} -> {log_entry['url']} | {log_entry['result']} | {log_entry['status_code']}"
                if log_entry['exception']:
                    message += f" | {log_entry['exception']}"
                message += "\n"
                
                # Add to log display with appropriate tag
                self.log_text.insert(tk.END, message, log_entry['type'])
                self.log_text.see(tk.END)
                
        except queue.Empty:
            pass
            
        # Schedule next processing
        self.root.after(100, self.process_logs)
        
    def filter_logs(self):
        """Filter log display based on selected filter"""
        current_filter = self.log_filter_var.get()
        # This is a simplified filter - in a real implementation, 
        # you would store all logs and filter the display
        pass
        
    def check_proxy_connection(self):
        """Check if proxy server is running"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)
            result = test_socket.connect_ex((self.proxy_host, self.proxy_port))
            test_socket.close()
            
            if result == 0:
                self.server_status_label.config(text="Server Status: Running", foreground="green")
            else:
                self.server_status_label.config(text="Server Status: Stopped", foreground="red")
                
        except Exception as e:
            self.server_status_label.config(text=f"Server Status: Error - {e}", foreground="red")
            
    def start_proxy_server(self):
        """Start the proxy server"""
        try:
            # This would start the actual proxy server
            # For now, just update the GUI
            self.server_running = True
            self.start_server_button.config(state='disabled')
            self.stop_server_button.config(state='normal')
            self.server_status_label.config(text="Server Status: Running", foreground="green")
            
            # Log the start
            log_entry = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'client_ip': 'SYSTEM',
                'url': 'SERVER_START',
                'result': 'STARTED',
                'status_code': 0,
                'type': 'INFO',
                'exception': ''
            }
            self.log_queue.put(log_entry)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            
    def stop_proxy_server(self):
        """Stop the proxy server"""
        try:
            # This would stop the actual proxy server
            # For now, just update the GUI
            self.server_running = False
            self.start_server_button.config(state='normal')
            self.stop_server_button.config(state='disabled')
            self.server_status_label.config(text="Server Status: Stopped", foreground="red")
            
            # Log the stop
            log_entry = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'client_ip': 'SYSTEM',
                'url': 'SERVER_STOP',
                'result': 'STOPPED',
                'status_code': 0,
                'type': 'INFO',
                'exception': ''
            }
            self.log_queue.put(log_entry)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop server: {e}")
            
    def add_blocked_domain(self):
        """Add a domain to the blocked list"""
        domain = self.domain_entry.get().strip()
        if not domain:
            messagebox.showwarning("Invalid Input", "Please enter a domain")
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.blocked_tree.insert('', 0, values=(domain, timestamp))
        self.blocked_domains.append(domain)
        self.domain_entry.delete(0, tk.END)
        
    def remove_blocked_domain(self):
        """Remove selected domain from blocked list"""
        selection = self.blocked_tree.selection()
        if selection:
            item = self.blocked_tree.item(selection[0])
            domain = item['values'][0]
            self.blocked_tree.delete(selection[0])
            if domain in self.blocked_domains:
                self.blocked_domains.remove(domain)
                
    def clear_cache(self):
        """Clear all cache entries"""
        for item in self.cache_tree.get_children():
            self.cache_tree.delete(item)
        self.cache_entries.clear()
        self.update_cache_stats()
        
    def remove_cache_entry(self):
        """Remove selected cache entry"""
        selection = self.cache_tree.selection()
        if selection:
            self.cache_tree.delete(selection[0])
            
    def refresh_cache_entry(self):
        """Refresh selected cache entry"""
        selection = self.cache_tree.selection()
        if selection:
            # This would force a refresh of the selected entry
            messagebox.showinfo("Refresh", "Cache entry refresh requested")
            
    def refresh_cache_list(self):
        """Refresh the cache list"""
        # This would reload the cache list from the actual cache
        self.update_cache_stats()
        
    def update_cache_stats(self):
        """Update cache statistics display"""
        total_entries = len(self.cache_tree.get_children())
        total_size = 0  # This would calculate actual size
        hits = self.cache_stats['hits']
        misses = self.cache_stats['misses']
        total_requests = self.cache_stats['total_requests']
        
        hit_ratio = (hits / total_requests * 100) if total_requests > 0 else 0
        
        stats_text = f"Cache Stats: Total entries: {total_entries} | Total size: {total_size} KB | Hits: {hits} | Misses: {misses} | Hit ratio: {hit_ratio:.1f}%"
        self.cache_stats_label.config(text=stats_text)


def main():
    root = tk.Tk()
    app = ProxyGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
