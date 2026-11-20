import time
import httpx

PORTS = [8001, 8002, 8003]
URL_TEMPLATE = "http://127.0.0.1:{}/health"

consecutive_failures = {port: 0 for port in PORTS}
FAILURE_THRESHOLD = 3


def check_services():
  round_results = []
  for port in PORTS:
    url = URL_TEMPLATE.format(port)
    start_time = time.time()
    try:
      response = httpx.get(url, timeout=1.5)
      response_time_ms = (time.time() - start_time) * 1000

      if response.status_code == 200:
        consecutive_failures[port] = 0
        if response_time_ms > 500:
          round_results.append(f"{port}: SLOW ({response_time_ms:.0f}ms)")
        else:
          round_results.append(f"{port}: UP ({response_time_ms:.0f}ms)")
      else:
        round_results.append(handle_failure(port))

    except (httpx.TimeoutException, httpx.ConnectError):
      round_results.append(handle_failure(port))

  print(" | ".join(round_results))


def handle_failure(port):
  consecutive_failures[port] += 1
  if consecutive_failures[port] >= FAILURE_THRESHOLD:
    return f"{port}: DOWN"
  return f"{port}: WARN ({consecutive_failures[port]}/{FAILURE_THRESHOLD})"


if __name__ == "__main__":
  try:
    while True:
      check_services()
      time.sleep(2)
  except KeyboardInterrupt:
    print("\nMonitor stopped.")
