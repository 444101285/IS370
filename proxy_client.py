import socket
import time
from datetime import datetime
import statistics

class ProxyClient:
    def __init__(self, proxy_host='127.0.0.1', proxy_port=8888):
        """
        Initialize the proxy client

        Args:
            proxy_host: Proxy server host address
            proxy_port: Proxy server port number
        """
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.request_log = []  # Track all requests

        # print(f"[INIT] Proxy Client initialized")
        # print(f"[INIT] Connecting to proxy: {self.proxy_host}:{self.proxy_port}\n")

    def send_request(self, url):
        """
        Send HTTP GET request to proxy server and measure response time

        Args:
            url: The URL to request

        Returns:
            tuple: (response_text, response_time, status_code, is_cached)
        """
        request_start = time.time()

        try:
            # Record start time for connection
            connect_start = time.time()

            # Create socket connection to proxy
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(15)

            # print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to proxy server...")
            client_socket.connect((self.proxy_host, self.proxy_port))

            connect_time = time.time() - connect_start

            # Construct HTTP GET request
            request = f"GET {url} HTTP/1.1\r\n"
            request += f"Host: {self.proxy_host}\r\n"
            request += "User-Agent: IS370-Client/1.0\r\n"
            request += "Connection: close\r\n"
            request += "\r\n"

            # print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending request for: {url}")

            # Send request
            send_start = time.time()
            client_socket.send(request.encode())
            send_time = time.time() - send_start

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

            # Determine if response came from cache
            # Cache hits are typically much faster (< 0.1 seconds)
            # and have faster receive times
            is_cached = receive_time < 0.05 and total_time < 0.1


            # Log request details
            log_entry = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'total_time': total_time,
                'connect_time': connect_time,
                'send_time': send_time,
                'receive_time': receive_time,
                'status_code': status_code,
                'is_cached': is_cached,
                'response_size': len(response)
            }
            self.request_log.append(log_entry)

            return  response_text,total_time, status_code, is_cached

        except socket.timeout:
            print(f"[ERROR] Request timeout for {url}")
            self.request_log.append({
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'error': 'timeout'
            })
            return None, 0, 0, False

        except ConnectionRefusedError:
            print(f"[ERROR] Connection refused. Is the proxy server running on {self.proxy_host}:{self.proxy_port}?")
            return None, 0, 0, False

        except socket.error as e:
            print(f"[ERROR] Socket error: {e}")
            return None, 0, 0, False

        except Exception as e:
            print(f"[ERROR] Failed to send request: {e}")
            self.request_log.append({
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            })
            return None, 0, 0, False

    def extract_status_code(self, response_text):
        """
        Extract HTTP status code from response

        Args:
            response_text: The HTTP response text

        Returns:
            int: Status code or 0 if not found
        """
        try:
            status_line = response_text.split('\r\n')[0]
            parts = status_line.split()
            if len(parts) >= 2:
                return int(parts[1])
        except:
            pass
        return 0


        #Display the HTTP response and performance metrics
    def display_response(self, response_text, response_time, status_code, is_cached, url):

        print("\n" + "="*70)
        print(f"RESPONSE FOR: {url}")
        print("="*70)

        if response_text is None:
            print("[ERROR] No response received")
            print("="*70 + "\n")
            return

        # Parse response
        parts = response_text.split('\r\n\r\n', 1)
        headers = parts[0]
        # body = parts[1] if len(parts) > 1 else ""

        # Display status
        # print("\n--- RESPONSE STATUS ---")
        # header_lines = headers.split('\r\n')
        # status_line = header_lines[0]
        # print(f"Status Line: {status_line}")
        # print(f"Status Code: {status_code}")

        # Interpret status code
        if status_code == 200:
            print("Status: ✓ OK - Request successful")
        elif status_code == 403:
            print("Status: ✗ FORBIDDEN - Request blocked by firewall")
        elif status_code == 502:
            print("Status: ✗ BAD GATEWAY - Failed to fetch from web server")
        elif status_code == 500:
            print("Status: ✗ INTERNAL SERVER ERROR")
        elif status_code == 400:
            print("Status: ✗ BAD REQUEST")

        # # Display important headers
        # print("\n--- IMPORTANT HEADERS ---")
        # for line in header_lines[1:]:
        #     if line:
        #         line_lower = line.lower()
        #         # Show cache-related headers
        #         if any(keyword in line_lower for keyword in
        #                ['cache-control', 'etag', 'last-modified', 'expires', 'content-type', 'content-length']):
        #             print(line)

        # Display body preview
        # if status_code == 200:
        #     print("\n--- RESPONSE BODY (Preview) ---")
        #     body_preview = body[:500] if len(body) > 500 else body
        #     print(body_preview)
        #     if len(body) > 500:
        #         print(f"\n... (truncated, total length: {len(body)} characters)")
        # else:
        #     print("\n--- ERROR RESPONSE ---")
        #     print(body[:500])

        # Display performance metrics
        print("\n--- PERFORMANCE METRICS ---")
        print(f"Response Time: {response_time:.4f} seconds ({response_time*1000:.2f} ms)")
        # print(f"Content Length: {len(body)} bytes ({len(body)/1024:.2f} KB)")

        # Determine cache status
        if status_code == 200:
            if is_cached:
                print(f"Cache Status: ✓ CACHE HIT")
                # print(f"Performance: FAST - Content retrieved from local cache")
            else:
                print(f"Cache Status: ✗ CACHE MISS")
                # print(f"Performance: SLOWER - Content fetched from external server")

        print("="*70 + "\n")

    def run_test(self, url, num_requests=2, delay=1):
        """
        Run test by requesting the same URL multiple times to demonstrate caching

        Args:
            url: The URL to test
            num_requests: Number of times to request the URL
            delay: Delay between requests in seconds
        """
        print(f"\n{'='*70}")
        print(f"TESTING URL: {url}")
        print(f"Number of requests: {num_requests}")
        print(f"Delay between requests: {delay} second(s)")
        print(f"{'='*70}\n")

        response_times = []
        cache_hits = 0
        cache_misses = 0

        for i in range(num_requests):
            print(f"\n{'─'*70}")
            print(f"REQUEST #{i+1} of {num_requests}")
            print(f"{'─'*70}")

            response_text, response_time, status_code, is_cached = self.send_request(url)

            if response_text:
                self.display_response(response_text, response_time, status_code, is_cached, url)

                if status_code == 200:
                    response_times.append(response_time)
                    if is_cached:
                        cache_hits += 1
                    else:
                        cache_misses += 1

            # Wait between requests
            if i < num_requests - 1:
                print(f"[INFO] Waiting {delay} second(s) before next request...\n")
                time.sleep(delay)

        # Display summary and performance analysis
        if response_times:
            self.display_test_summary(url, response_times, cache_hits, cache_misses, num_requests)

    def display_test_summary(self, url, response_times, cache_hits, cache_misses, total_requests):
        """
        Display summary and performance analysis of test

        Args:
            url: The tested URL
            response_times: List of response times
            cache_hits: Number of cache hits
            cache_misses: Number of cache misses
            total_requests: Total number of requests
        """
        print("\n" + "="*70)
        print("TEST SUMMARY & PERFORMANCE ANALYSIS")
        print("="*70)
        print(f"URL Tested: {url}")
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {len(response_times)}")

        print("\n--- CACHE STATISTICS ---")
        print(f"Cache Hits: {cache_hits}")
        print(f"Cache Misses: {cache_misses}")
        if total_requests > 0:
            hit_rate = (cache_hits / len(response_times)) * 100 if response_times else 0
            print(f"Cache Hit Rate: {hit_rate:.1f}%")

        print("\n--- RESPONSE TIME STATISTICS ---")
        avg_time = statistics.mean(response_times)
        print(f"Average Response Time: {avg_time:.4f} seconds ({avg_time*1000:.2f} ms)")
        print(f"Minimum Response Time: {min(response_times):.4f} seconds ({min(response_times)*1000:.2f} ms)")
        print(f"Maximum Response Time: {max(response_times):.4f} seconds ({max(response_times)*1000:.2f} ms)")

        if len(response_times) > 1:
            std_dev = statistics.stdev(response_times)
            print(f"Standard Deviation: {std_dev:.4f} seconds")

        # Performance comparison
        if len(response_times) > 1 and cache_misses > 0 and cache_hits > 0:
            print("\n--- CACHING PERFORMANCE BENEFIT ---")
            first_request = response_times[0]
            cached_requests = response_times[1:]
            avg_cached = statistics.mean(cached_requests)

            print(f"First Request (Cache Miss): {first_request:.4f} seconds ({first_request*1000:.2f} ms)")
            print(f"Avg Cached Requests (Cache Hit): {avg_cached:.4f} seconds ({avg_cached*1000:.2f} ms)")

            if avg_cached > 0:
                speedup = first_request / avg_cached
                time_saved = first_request - avg_cached
                percent_faster = ((first_request - avg_cached) / first_request) * 100

                print(f"\n✓ Cache Performance:")
                print(f"  • Speedup: {speedup:.2f}x faster")
                print(f"  • Time Saved: {time_saved:.4f} seconds ({time_saved*1000:.2f} ms)")
                print(f"  • Percentage Improvement: {percent_faster:.1f}% faster")

        print("="*70 + "\n")

    # def export_statistics(self, filename='client_stats.txt'):
    #     """Export request statistics to file"""
    #     try:
    #         with open(filename, 'w') as f:
    #             f.write("IS370 Proxy Client - Request Statistics\n")
    #             f.write("="*70 + "\n\n")
    #
    #             for i, log in enumerate(self.request_log, 1):
    #                 f.write(f"Request #{i}\n")
    #                 f.write(f"  URL: {log.get('url')}\n")
    #                 f.write(f"  Timestamp: {log.get('timestamp')}\n")
    #
    #                 if 'error' in log:
    #                     f.write(f"  Error: {log.get('error')}\n")
    #                 else:
    #                     f.write(f"  Total Time: {log.get('total_time', 0):.4f}s\n")
    #                     f.write(f"  Status Code: {log.get('status_code')}\n")
    #                     f.write(f"  Cached: {log.get('is_cached')}\n")
    #                     f.write(f"  Response Size: {log.get('response_size')} bytes\n")
    #
    #                 f.write("\n")
    #
    #         print(f"[INFO] Statistics exported to {filename}")
    #     except Exception as e:
    #         print(f"[ERROR] Failed to export statistics: {e}")

def print_menu():
    """Display menu options"""
    print("\n" + "="*70)
    print("HTTP PROXY CLIENT - MAIN MENU")
    print("="*70)
    print("1. Test single URL (one request)")
    print("2. Test caching performance (multiple requests to same URL)")
    print("3. Test firewall blocking")
    print("4. Run comprehensive test suite")
    # print("5. View request statistics")
    # print("6. Export statistics to file")
    print("7. Exit")
    print("="*70)

def main():
    """Main function to run the proxy client"""
    client = ProxyClient(proxy_host='127.0.0.1', proxy_port=8888)

    while True:
        print_menu()
        choice = input("\nEnter your choice (1-7): ").strip()

        if choice == '1':
            url = input("Enter URL (e.g., http://example.com): ").strip()
            if url:
                client.run_test(url, num_requests=1)
            else:
                print("[ERROR] Invalid URL")

        elif choice == '2':
            url = input("Enter URL to test caching (e.g., http://example.com): ").strip()
            if url:
                num_requests = input("Number of requests (default 3): ").strip()
                num_requests = int(num_requests) if num_requests.isdigit() else 3
                delay = input("Delay between requests in seconds (default 1): ").strip()
                delay = int(delay) if delay.isdigit() else 1
                client.run_test(url, num_requests=num_requests, delay=delay)
            else:
                print("[ERROR] Invalid URL")

        elif choice == '3':
            print("\n" + "="*70)
            print("FIREWALL TEST")
            print("="*70)
            print("Testing with blocked domains...")
            print("Blocked domains include: facebook.com, twitter.com, instagram.com")
            print()

            blocked_url = input("Enter blocked URL to test (e.g., http://facebook.com): ").strip()
            if not blocked_url:
                blocked_url = "http://facebook.com"

            client.run_test(blocked_url, num_requests=1)

        elif choice == '4':
            print("\n" + "="*70)
            print("COMPREHENSIVE TEST SUITE")
            print("="*70)
            print("This will run multiple tests to demonstrate all features.\n")

            # Test 1: Normal request (Cache Miss)
            '''
            print("\n[TEST 1/4] Testing initial request (Cache Miss)...")
            time.sleep(1)
            client.run_test("http://example.com", num_requests=1)
            time.sleep(2)
            '''
            # Test 2: Caching (Cache Hit)
            print("\n[TEST 2/4] Testing caching performance (multiple requests)...")
            time.sleep(1)
            client.run_test("http://example.com", num_requests=3, delay=1)
            time.sleep(2)

            # Test 3: Different URL
            print("\n[TEST 3/4] Testing different URL...")
            time.sleep(1)
            client.run_test("http://www.example.org", num_requests=2, delay=1)
            time.sleep(2)

            # Test 4: Firewall blocking
            print("\n[TEST 4/4] Testing firewall (blocked domain)...")
            time.sleep(1)
            client.run_test("http://facebook.com", num_requests=1)

            # print("\n[INFO] Comprehensive test suite completed!")

        #
        # elif choice == '5':
        #     print("\n" + "="*70)
        #     print("REQUEST STATISTICS")
        #     print("="*70)
        #
        #     if not client.request_log:
        #         print("No requests logged yet.")
        #     else:
        #         print(f"Total Requests: {len(client.request_log)}\n")
        #
        #         successful = [log for log in client.request_log if 'error' not in log]
        #         errors = [log for log in client.request_log if 'error' in log]
        #
        #         print(f"Successful: {len(successful)}")
        #         print(f"Errors: {len(errors)}")
        #
        #         if successful:
        #             times = [log['total_time'] for log in successful]
        #             cached = [log for log in successful if log.get('is_cached')]
        #
        #             print(f"\nAverage Response Time: {statistics.mean(times):.4f}s")
        #             print(f"Cache Hit Rate: {len(cached)/len(successful)*100:.1f}%")
        #
        #     print("="*70)
        #
        #
        # elif choice == '6':
        #     filename = input("Enter filename (default: client_stats.txt): ").strip()
        #     if not filename:
        #         filename = "client_stats.txt"
        #     client.export_statistics(filename)

        elif choice == '7':
            print("\n[EXIT] Goodbye!")
            print("Thank you for using IS370 Proxy Client\n")
            break

        else:
            print("\n[ERROR] Invalid choice. Please select 1-7.")

if __name__ == "__main__":
    # print("""
    # ╔═══════════════════════════════════════════════════════════════╗
    # ║         IS370 HTTP Proxy Client with Performance Analysis    ║
    # ║              King Saud University - Fall 2025                 ║
    # ╚═══════════════════════════════════════════════════════════════╝
    # """)

    # print("[INFO] Ensure the proxy server is running before using the client!")
    # print("[INFO] Start the server: python proxy_server.py")
    # print("[INFO] Then run this client in a separate terminal.\n")

    # input("Press Enter to continue...")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Client terminated by user. Goodbye!")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")