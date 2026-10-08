# SolarAI Device Telemetry Protocol v1

SolarAI gateways authenticate with a per-device API key and can sign each telemetry request with HMAC-SHA256. Production deployments require signed requests.

## Endpoint

`POST /device-telemetry/`

## Required authentication header

`X-Device-API-Key: tambo_dev_...`

The raw API key is shown only when a device is registered or the key is rotated. The backend stores only its SHA-256 lookup hash.

## Signed request headers

Production gateways send:

- `X-Device-Timestamp` — current Unix time in seconds.
- `X-Device-Nonce` — a unique random value for this HTTP request.
- `X-Device-Signature` — lowercase HMAC-SHA256 hexadecimal digest.

Requests older/newer than the configured time window are rejected. Reusing the same nonce for the same device is rejected as a replay.

## Signature algorithm

1. Serialize the JSON payload with keys sorted, no extra whitespace, UTF-8 and JSON `null` values preserved.
2. Calculate `payload_hash = SHA256(canonical_json)` as lowercase hexadecimal.
3. Build the message: `v1.<timestamp>.<nonce>.<payload_hash>`.
4. Calculate `HMAC-SHA256(api_key, message)` and send the lowercase hexadecimal digest as `X-Device-Signature`.

The included `simulator/simulator.py` implements the reference client.

## Event idempotency

Gateways should include an `event_id` in every telemetry body. If delivery fails after the server has stored the event, the gateway may retry using the same `event_id` but a new timestamp, nonce and signature. SolarAI returns the already-stored telemetry record instead of creating a duplicate.

Example payload:

```json
{
  "event_id": "01HZX2M5G8R7J9K2M3N4P5Q6RS",
  "pv_voltage": 125.0,
  "pv_current": 9.5,
  "pv_power": 1187.5,
  "battery_voltage": 51.4,
  "battery_current": 7.5,
  "battery_soc": 82.0,
  "load_power": 650.0,
  "temperature": 31.0,
  "error_code": null
}
```

## Operational controls

- Payload numeric fields have conservative bounds to reject obviously invalid input.
- Per-device telemetry rate limiting is applied using recent persisted telemetry.
- Device request nonces are retained for a configurable period.
- Production traffic must use HTTPS. Request signing is an additional integrity/replay layer; it does not replace TLS.
