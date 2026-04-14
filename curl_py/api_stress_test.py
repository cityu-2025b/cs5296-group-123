import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
TARGET_URL = "https://jsonplaceholder.typicode.com/posts/1" # Replace with your API
TOTAL_REQUESTS = 100
CONCURRENT_THREADS = 10
TIMEOUT = 5 # seconds

def send_request(request_id):
    try:
        start_time = time.perf_counter()
        response = requests.get(TARGET_URL, timeout=TIMEOUT)
        end_time = time.perf_counter()
        
        return {
            "id": request_id,
            "status": response.status_code,
            "time": end_time - start_time,
            "success": 200 <= response.status_code < 300
        }
    except Exception as e:
        return {"id": request_id, "status": "Error", "time": 0, "success": False, "error": str(e)}

def run_stress_test():
    print(f"Starting Stress Test: {TOTAL_REQUESTS} requests with {CONCURRENT_THREADS} threads...")
    
    # Run requests concurrently
    with ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        results = list(executor.map(send_request, range(TOTAL_REQUESTS)))

    # --- AGGREGATE RESULTS ---
    successes = [r['time'] for r in results if r['success']]
    failures = [r for r in results if not r['success']]
    
    print("\n" + "="*30)
    print("STRESS TEST RESULTS")
    print("="*30)
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Successes:      {len(successes)}")
    print(f"Failures:       {len(failures)}")
    
    if successes:
        print(f"Avg Latency:    {statistics.mean(successes):.4f}s")
        print(f"Min Latency:    {min(successes):.4f}s")
        print(f"Max Latency:    {max(successes):.4f}s")
        # 95th Percentile shows the response time for the slowest 5% of requests
        print(f"95th Percentile: {statistics.quantiles(successes, n=20)[18]:.4f}s")

if __name__ == "__main__":
    run_stress_test()
