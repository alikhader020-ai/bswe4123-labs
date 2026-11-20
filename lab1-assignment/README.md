# Lab Assignment 1: Is the Service Up, Slow or Down?

## Student Info
- **Name:** Ali Khader
- **Student ID:** 120220101
- **Course:** BSWE4123

---

## Step 3: Experiment Output & Explanation
During the one-minute runtime, the following changes were observed:
1. **Stopping a Service (Ctrl+C):** When stopping the service on port `8002`, the monitor initially registered warnings/timeouts, and after reaching the failure threshold, it reported `DOWN`. Once restarted, it immediately recovered to `UP`.
2. **Making a Service Slow:** By modifying one service to sleep for `0.8` seconds before responding, the monitor accurately captured its response time exceeding 500 ms and changed its status from `UP` to `SLOW`.

### Sample Monitor Output:
```text
Port 8001: UP (1.25 ms) - Response: {'status': 'ok', 'uptime_seconds': 15}
Port 8002: UP (1.40 ms) - Response: {'status': 'ok', 'uptime_seconds': 15}
Port 8003: SLOW (820.15 ms) - Response: {'status': 'ok', 'uptime_seconds': 15}
Port 8002: DOWN (Failed 3 times in a row - Reason: Connection Timeout or Refused)
