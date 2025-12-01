import socket
import os
import hashlib
# import time
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse

class ProxyServer:
    def __init__(self, host='127.0.0.1', port=8888, cache_dir='cache'):
        """
        Initialize the proxy server

        Args:
            host: Server host address
            port: Server port number
            cache_dir: Directory to store cached files
        """
        self.host = host
        self.port = port
        self.cache_dir = cache_dir

        # Firewall: List of blocked domains
        self.blocked_domains = ['facebook.com', 'twitter.com', 'instagram.com',
                                'tiktok.com', 'example-blocked.com']

        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        # Initialize cache metadata storage (includes ETag, Last-Modified, etc.)
        self.cache_metadata_file = os.path.join(self.cache_dir, 'metadata.json')
        self.cache_metadata = self.load_cache_metadata()

        # Log file for tracking cache hits/misses
        self.log_file = os.path.join(self.cache_dir, 'proxy.log')

        self.log_event("SERVER_START", f"Proxy server started on {self.host}:{self.port}")

    def log_event(self, event_type, message):
        """Log events to file with timestamp"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] [{event_type}] {message}\n"
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[ERROR] Failed to write to log: {e}")

    def load_cache_metadata(self):
        """Load cache metadata from file"""
        if os.path.exists(self.cache_metadata_file):
            try:
                with open(self.cache_metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to load cache metadata: {e}")
                return {}
        return {}

    def save_cache_metadata(self):
        """Save cache metadata to file"""
        try:
            with open(self.cache_metadata_file, 'w') as f:
                json.dump(self.cache_metadata, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save cache metadata: {e}")

    def get_cache_filename(self, url):
        """Generate a unique filename for cached content based on URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.cache")

    def is_domain_blocked(self, url):
        """
        Check if the domain is in the blocked list (Firewall functionality)

        Args:
            url: The URL to check

        Returns:
            bool: True if domain is blocked, False otherwise
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

            # Remove www. prefix for comparison
            if domain.startswith('www.'):
                domain = domain[4:]
            # Check if domain matches any blocked domain
            for blocked in self.blocked_domains:
                if blocked in domain :
                    return True
            return False
        except Exception as e:
            print(f"[ERROR] Error checking blocked domain: {e}")
            return False

    def parse_http_headers(self, response):
        """
        Parse HTTP response headers

        Args:
            response: Raw HTTP response bytes

        Returns:
            dict: Dictionary of headers
        """
        headers = {}
        try:
            # Split response into headers and body
            parts = response.split(b'\r\n\r\n', 1)
            header_section = parts[0].decode('utf-8', errors='ignore')

            # Parse each header line
            lines = header_section.split('\r\n')
            for line in lines[1:]:  # Skip status line
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
        except Exception as e:
            print(f"[ERROR] Error parsing headers: {e}")

        return headers

    def extract_header_value(self, response, header_name):
        """
        Extract specific header value from HTTP response

        Args:
            response: Raw HTTP response bytes
            header_name: Name of header to extract

        Returns:
            str: Header value or None
        """
        try:
            headers = self.parse_http_headers(response)
            return headers.get(header_name.lower())
        except:
            return None

    def is_cache_valid(self, url):
        """
        Check if cached content is still valid based on:
        1. Cache-Control max-age
        2. Expiration time
        3. ETag presence for validation

        Args:
            url: The URL to check

        Returns:
            bool: True if cache is valid, False otherwise
        """
        cache_file = self.get_cache_filename(url)

        # Check if cache file exists
        if not os.path.exists(cache_file):
            return False

        # Check metadata for expiration
        if url in self.cache_metadata:
            metadata = self.cache_metadata[url]

            # Check if cache has expired based on max-age
            expiry_time = metadata.get('expiry')
            if expiry_time:
                expiry_dt = datetime.fromisoformat(expiry_time)
                if datetime.now() > expiry_dt:
                    print(f"[CACHE] Cache expired for {url}")
                    self.log_event("CACHE_EXPIRED", url)
                    return False

            return True

        return False

    def get_from_cache(self, url):
        """
        Retrieve content from cache

        Args:
            url: The URL to retrieve

        Returns:
            bytes: Cached content or None
        """
        cache_file = self.get_cache_filename(url)

        try:
            with open(cache_file, 'rb') as f:
                content = f.read()

            print(f"[CACHE HIT] Serving from cache: {url}")
            self.log_event("CACHE_HIT", url)

            # Log metadata info
            if url in self.cache_metadata:
                metadata = self.cache_metadata[url]
                print(f"[CACHE] Cached at: {metadata.get('cached_at')}")
                if 'etag' in metadata:
                    print(f"[CACHE] ETag: {metadata.get('etag')}")

            return content
        except Exception as e:
            print(f"[ERROR] Failed to read from cache: {e}")
            return None

    def parse_cache_control(self, headers):
        """
        Parse Cache-Control header to get max-age and other directives

        Args:
            headers: Dictionary of HTTP headers

        Returns:
            dict: Dictionary with cache control directives
        """
        cache_control = {
            'max_age': 3600,  # Default 1 hour
            'no_cache': False,
            'no_store': False
        }

        try:
            if 'cache-control' in headers:
                cc_header = headers['cache-control']

                # Check for no-cache or no-store
                if 'no-cache' in cc_header.lower():
                    cache_control['no_cache'] = True
                ##I don't know if we should keep it????   ###################################
                if 'no-store' in cc_header.lower():
                    cache_control['no_store'] = True
                    ##I don't know if we should keep it????  ################################

                # Extract max-age
                for directive in cc_header.split(','):
                    directive = directive.strip()
                    if directive.startswith('max-age='):
                        try:
                            max_age = int(directive.split('=')[1])
                            cache_control['max_age'] = max_age
                        except:
                            pass
        except Exception as e:
            print(f"[ERROR] Error parsing Cache-Control: {e}")

        return cache_control

    def save_to_cache(self, url, response):
        """
        Save content to cache with metadata (ETag, Cache-Control, expiration)

        Args:
            url: The URL being cached
            response: The HTTP response to cache
        """
        cache_file = self.get_cache_filename(url)

        try:
            # Parse headers from response
            headers = self.parse_http_headers(response)

            # Get cache control directives
            cache_control = self.parse_cache_control(headers)

            ##I don't know if we should keep it????   ###################################
            # Don't cache if no-store is set
            if cache_control['no_store']:
                print(f"[CACHE] Not caching (no-store directive): {url}")
                return
            ##I don't know if we should keep it????   ###################################

            # Save response to cache file
            with open(cache_file, 'wb') as f:
                f.write(response)

            # Extract ETag if present
            etag = headers.get('etag', None)
            last_modified = headers.get('last-modified', None)

            # Calculate expiry time based on max-age
            max_age = cache_control['max_age']
            expiry_time = datetime.now() + timedelta(seconds=max_age)

            # Save metadata
            self.cache_metadata[url] = {
                'cached_at': datetime.now().isoformat(),
                'expiry': expiry_time.isoformat(),
                'max_age': max_age,
                'etag': etag,
                'last_modified': last_modified,
                'no_cache': cache_control['no_cache']
            }
            self.save_cache_metadata()

            print(f"[CACHE] Cached content for {url}")
            print(f"[CACHE] Max-age: {max_age}s, Expires: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if etag:
                print(f"[CACHE] ETag: {etag}")

            self.log_event("CACHE_SAVE", f"{url} (max-age={max_age}s)")

        except Exception as e:
            print(f"[ERROR] Failed to save to cache: {e}")
            self.log_event("CACHE_ERROR", f"Failed to cache {url}: {str(e)}")

    def fetch_from_web(self, url):
        """
        Fetch content from the external web server

        Args:
            url: The URL to fetch

        Returns:
            bytes: HTTP response or None
        """
        try:
            parsed_url = urlparse(url)
            host = parsed_url.netloc
            path = parsed_url.path if parsed_url.path else '/'

            # Add query string if present
            if parsed_url.query:
                path += '?' + parsed_url.query

            print(f"[WEB] Connecting to {host}...")

            # Create socket connection to web server
            web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            web_socket.settimeout(10)

            # Connect to port 80 (HTTP)
            port = 80
            web_socket.connect((host, port))

            # Construct HTTP GET request
            request = f"GET {path} HTTP/1.1\r\n"
            request += f"Host: {host}\r\n"
            request += "User-Agent: IS370-Proxy-Server/1.0\r\n"
            request += "Accept: */*\r\n"
            request += "Connection: close\r\n"
            request += "\r\n"

            web_socket.send(request.encode())

            # Receive response
            response = b''
            while True:
                data = web_socket.recv(4096)
                if not data:
                    break
                response += data

            web_socket.close()

            print(f"[CACHE MISS] Fetched from web: {url}")
            self.log_event("CACHE_MISS", url)

            # Save to cache
            self.save_to_cache(url, response)

            return response

        except socket.timeout:
            error_msg = f"Timeout while connecting to {url}"
            print(f"[ERROR] {error_msg}")
            self.log_event("ERROR", error_msg)
            return None
        except socket.gaierror:
            error_msg = f"Failed to resolve hostname for {url}"
            print(f"[ERROR] {error_msg}")
            self.log_event("ERROR", error_msg)
            return None
        except ConnectionRefusedError:
            error_msg = f"Connection refused by {url}"
            print(f"[ERROR] {error_msg}")
            self.log_event("ERROR", error_msg)
            return None
        except Exception as e:
            error_msg = f"Failed to fetch from web: {e}"
            print(f"[ERROR] {error_msg}")
            self.log_event("ERROR", f"{url} - {str(e)}")
            return None

    def handle_client_request(self, client_socket, address):
        """
        Handle incoming client request with proper exception handling

        Args:
            client_socket: Socket connection to client
            address: Client address tuple
        """
        try:
            # Receive request from client
            request = client_socket.recv(4096).decode('utf-8', errors='ignore')

            if not request:
                print(f"[WARNING] Empty request from {address}")
                return

            print(f"\n[REQUEST] Received from {address}")
            self.log_event("REQUEST", f"From {address}")

            # Parse the request to get the URL
            lines = request.split('\r\n')
            first_line = lines[0]

            print(f"[REQUEST] {first_line}")

            # Extract URL from request
            parts = first_line.split()
            if len(parts) < 2:
                print(f"[ERROR] Malformed request from {address}")
                self.send_error_response(client_socket, 400, "Bad Request")
                self.log_event("ERROR", f"Bad request from {address}")
                return

            # Check if it's a GET request
            method = parts[0].upper()
            if method != 'GET':
                print(f"[ERROR] Unsupported method: {method}")
                self.send_error_response(client_socket, 405, "Method Not Allowed")
                self.log_event("ERROR", f"Method {method} not allowed")
                return

            url = parts[1]
            print(f"[REQUEST] URL: {url}")

            # Validate URL format
            if not url.startswith('http://') and not url.startswith('https://'):
                print(f"[ERROR] Invalid URL format: {url}")
                self.send_error_response(client_socket, 400, "Bad Request - Invalid URL")
                self.log_event("ERROR", f"Invalid URL: {url}")
                return

            # Check if domain is blocked (Firewall functionality)
            if self.is_domain_blocked(url):
                print(f"[FIREWALL] Blocked request to {url}")
                self.send_error_response(client_socket, 403,
                    "Forbidden - Domain Blocked by Firewall")
                self.log_event("FIREWALL_BLOCK", url)
                return

            # Check cache first
            if self.is_cache_valid(url):
                response = self.get_from_cache(url)
                if response:
                    client_socket.send(response)
                    return

            # Fetch from web if not in cache or cache invalid
            response = self.fetch_from_web(url)

            if response:
                client_socket.send(response)
            else:
                self.send_error_response(client_socket, 502,
                    "Bad Gateway - Failed to fetch from web server")

        except socket.error as e:
            error_msg = f"Socket error handling request: {e}"
            print(f"[ERROR] {error_msg}")
            self.log_event("ERROR", error_msg)
            try:
                self.send_error_response(client_socket, 500, "Internal Server Error")
            except:
                pass

        except Exception as e:
            error_msg = f"Exception handling request: {e}"
            print(f"[ERROR] {error_msg}")
            self.log_event("ERROR", error_msg)
            try:
                self.send_error_response(client_socket, 500, "Internal Server Error")
            except:
                pass

        finally:
            try:
                client_socket.close()
            except:
                pass

    def send_error_response(self, client_socket, status_code, message):
        """
        Send HTTP error response to client

        Args:
            client_socket: Socket connection to client
            status_code: HTTP status code
            message: Error message
        """
        try:
            response = f"HTTP/1.1 {status_code} {message}\r\n"
            response += "Content-Type: text/html; charset=utf-8\r\n"
            response += "Connection: close\r\n"
            response += "\r\n"
            response += f"<html><head><title>{status_code} {message}</title></head>"
            response += f"<body><h1>{status_code} {message}</h1>"
            response += f"<p>IS370 Proxy Server</p></body></html>"
            client_socket.send(response.encode())
        except Exception as e:
            print(f"[ERROR] Failed to send error response: {e}")

    def start(self):
        """Start the proxy server"""
        server_socket = None
        try:
            # Create server socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)

            print(f"\n{'='*70}")
            print(f"[SERVER] Proxy server listening on {self.host}:{self.port}")
            print(f"[SERVER] Cache directory: {self.cache_dir}")
            print(f"[SERVER] Log file: {self.log_file}")
            print(f"[SERVER] Waiting for connections...")
            print(f"{'='*70}\n")

            while True:
                try:
                    # Accept client connection
                    client_socket, address = server_socket.accept()
                    print(f"[CONNECTION] Accepted connection from {address}")

                    # Handle the request
                    self.handle_client_request(client_socket, address)

                except KeyboardInterrupt:
                    print("\n[SERVER] Shutting down proxy server...")
                    self.log_event("SERVER_STOP", "Server shutdown by user")
                    break
                except Exception as e:
                    print(f"[ERROR] Error accepting connection: {e}")
                    self.log_event("ERROR", f"Connection error: {str(e)}")
                    continue

        except OSError as e:
            print(f"[ERROR] Failed to start server (port may be in use): {e}")
            self.log_event("ERROR", f"Server start failed: {str(e)}")
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}")
            self.log_event("ERROR", f"Server error: {str(e)}")

        finally:
            if server_socket:
                try:
                    server_socket.close()
                    print("[SERVER] Server socket closed")
                except:
                    pass

# Main execution
if __name__ == "__main__":
    # print("""
    # ╔═══════════════════════════════════════════════════════════════╗
    # ║      IS370 HTTP Proxy Server with Caching & Firewall         ║
    # ║              King Saud University - Fall 2025                 ║
    # ╚═══════════════════════════════════════════════════════════════╝
    # """)

    # Create and start proxy server
    proxy = ProxyServer(host='127.0.0.1', port=8888)
    proxy.start()