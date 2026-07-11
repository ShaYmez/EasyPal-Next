# Hybrid API v1 (EasyPal-Next client ↔ community server)

The **community server** (web gallery, accounts, SFTP, hybrid storage) lives in a
**separate repository**. EasyPal-Next implements only the **client**.

This document is the contract both sides implement.

## Goals

Mirror original EasyPal Hybrid TX:

1. Operator enables Hybrid TX and selects a file
2. Client uploads the file to the community server
3. Client transmits a **small retrieval code** over the air (HamDRM)
4. Receiving stations decode the code and download the file automatically

## Auth

| Header | Description |
|--------|-------------|
| `Authorization: Bearer <api_key>` | Operator API key (or callsign token) |
| `X-Callsign: M0VUB` | Transmitting callsign |

## Endpoints

### `POST /api/v1/hybrid/upload`

Multipart upload of the hybrid file.

**Request:** `multipart/form-data` with field `file`, optional `filename`, `callsign`.

**Response `201`:**

```json
{
  "id": "hyb_01HXYZ...",
  "retrieval_code": "A1B2C3D4",
  "download_url": "https://server.example/api/v1/hybrid/files/hyb_01HXYZ...",
  "sha256": "...",
  "size_bytes": 123456,
  "expires_at": "2026-08-01T00:00:00Z"
}
```

`retrieval_code` is what goes over the air (8–16 printable ASCII chars).

### `GET /api/v1/hybrid/files/{id}`

Authenticated download of the original file bytes.

### `GET /api/v1/hybrid/by-code/{retrieval_code}`

Resolve code → metadata (and optional redirect to download). Used by RX stations.

### `POST /api/v1/hybrid/rx-ok`

Optional notification that a station successfully received/downloaded.

```json
{
  "retrieval_code": "A1B2C3D4",
  "callsign": "G0ABC",
  "snr_db": 12.5
}
```

## Over-air payload (HamDRM)

EasyPal-Next TX after successful upload:

- Minimal text/binary stub containing `retrieval_code` (+ optional server host hint)
- Prefer Mode **E** / QAM **4** / lead-in **12** for hybrid stubs (original recommendation)

RX:

- Detect hybrid stub → `GET .../by-code/...` → download → gallery

## Legacy FTP profile (optional later)

Original vk4aes-style layout for compatibility with older servers:

- `HybridFiles/`
- `OnlineCallsigns/`
- `RxOkNotifications/`

Map via `community.upload_transport: ftp` in EasyPal-Next config.

## Client config (EasyPal-Next)

```yaml
community:
  enabled: true
  hybrid_enabled: true
  base_url: "https://community.example"
  api_key: "..."
  upload_transport: rest
```

## Out of scope for this repo

- User accounts UI, public web gallery, SFTP daemon, admin tools — **server repo**.
