# Discovering Coros Sleep & HRV Endpoints via Proxyman

The Coros Training Hub API is not publicly documented. The sleep and HRV endpoint
paths in `coros_api.py` are placeholder guesses — you need to capture the actual
requests using a proxy with SSL decryption.

## Why SSL Decryption Is Required

The Coros app and web frontend use TLS, so a regular proxy only sees `CONNECT` tunnels.
Proxyman with its root certificate installed can decrypt HTTPS traffic on-the-fly.

---

## Step-by-Step: Proxyman on macOS

### 1. Install Proxyman & Trust the Certificate

1. Download [Proxyman](https://proxyman.io/) and open it.
2. **Certificate → Install Certificate on this Mac**
3. Open **Keychain Access** → find "Proxyman CA" → double-click → expand "Trust"
   → set **"When using this certificate"** to **Always Trust**.

### 2. Enable SSL Proxying for Coros Domains

1. In Proxyman: **Tools → SSL Proxying List**
2. Add the following entries:
   ```
   *.coros.com
   teamapi.coros.com
   us.teamapi.coros.com
   ```
3. Restart Proxyman to apply.

### 3. Capture Sleep Data

1. Open [https://training.coros.com](https://training.coros.com) in a browser
   (with Proxyman active as system proxy).
2. Navigate to the **Sleep** section of the training hub.
3. In Proxyman, filter by host: `teamapi.coros.com` or `us.teamapi.coros.com`.
4. Look for XHR/Fetch requests that return sleep data (JSON).
5. Note the full URL path and query parameters.

### 4. Capture HRV Data

1. Navigate to the **HRV** or **Recovery** section of training.coros.com.
2. Identify the API request returning HRV metrics.
3. Note path and query parameters.

### 5. Update `coros_api.py`

Replace the placeholder values in the `ENDPOINTS` dict:

```python
ENDPOINTS = {
    "login": "/account/login",      # confirmed — do not change
    "sleep": "/sleep/query",        # TODO: replace with actual path
    "hrv": "/hrv/query",            # TODO: replace with actual path
}
```

Also update `_parse_sleep_item()` and `_parse_hrv_item()` in `coros_api.py`
to match the actual field names from the response JSON.

---

## What to Look For in the Request

| Field | Where to find it |
|-------|-----------------|
| URL path | Proxyman → request URL after the domain |
| Query params | URL bar or Proxyman "Query" tab |
| Request body | Proxyman "Body" tab (for POST requests) |
| Response fields | Proxyman "Response" → "Body" → formatted JSON |

### Expected response shape (example — actual fields may differ)

```json
{
  "result": "0000",
  "message": "OK",
  "data": {
    "list": [
      {
        "date": 20240315,
        "totalSleepMinutes": 420,
        "deepSleepMinutes": 90,
        "lightSleepMinutes": 210,
        "remSleepMinutes": 100,
        "awakeSleepMinutes": 20,
        "sleepStartTime": "23:10",
        "sleepEndTime": "06:50",
        "sleepScore": 78
      }
    ]
  }
}
```

---

## Alternative: Browser DevTools

If Proxyman is not available, you can use Safari or Chrome DevTools:

1. Open training.coros.com.
2. Open DevTools → **Network** tab → filter by **Fetch/XHR**.
3. Navigate to Sleep/HRV sections.
4. Inspect request URLs and response JSON.

> **Note:** DevTools does not require certificate installation — browser
> sessions are already decrypted from the JS engine's perspective.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Only see `CONNECT` tunnels in Proxyman | Certificate not trusted — repeat Step 1 |
| No requests from `teamapi.coros.com` | Check system proxy settings; some browsers ignore system proxy |
| Response is `{"result": "0001", ...}` | Wrong endpoint path or missing/expired auth token |
| 404 Not Found | Endpoint path is incorrect — check URL in Proxyman |
