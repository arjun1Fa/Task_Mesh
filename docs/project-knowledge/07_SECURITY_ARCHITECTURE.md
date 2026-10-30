# TaskMesh — Security Architecture

## 1. Security Philosophy & Threat Model

TaskMesh was engineered primarily for deployment across **trusted local networks** (LAN / private Wi-Fi). However, unmanaged local networks are frequently exposed to accidental misconfiguration, rogue devices, replay attempts, and packet inspection. 

To address these risks without requiring complex Public Key Infrastructure (PKI) or external certificate authorities, TaskMesh implements an embedded, message-level security architecture built on **HMAC-SHA256 message signing, strict sequence monotonicity, timestamp skew verification, and replay cache tracking**.

---

## 2. Implemented Security Controls

### 2.1 Canonical Serialization & HMAC-SHA256 Signing
- **Module**: [`taskmesh/security/hmac_auth.py`](file:///C:/Malenia/TASK_MESH/taskmesh/security/hmac_auth.py)
- **Functions**: `serialize_for_signature()`, `compute_hmac_signature()`, `verify_hmac_signature()`
- **Mechanism**:
  Every message exchanged over WebSockets can be cryptographically signed. To ensure that formatting differences (whitespace, dictionary key order) do not invalidate signatures, TaskMesh produces a deterministic canonical byte string:
  ```python
  components = [
      str(msg.protocol_version),
      str(msg.message_id),
      str(msg.message_type.value),
      str(msg.node_id or ""),
      msg.timestamp.isoformat(),
      str(msg.sequence_number or 0),
      json.dumps(msg.payload, sort_keys=True, separators=(",", ":")),
  ]
  canonical_bytes = "|".join(components).encode("utf-8")
  ```
  The signature is computed using HMAC-SHA256:
  $$\text{Signature} = \text{HMAC-SHA256}(K_{\text{secret}}, \text{canonical\_bytes})$$
  Verification uses constant-time comparison (`hmac.compare_digest`), preventing timing side-channel attacks.

### 2.2 Replay Protection Engine
The `SecurityManager` enforces three distinct layers of protection against replay attacks:

1. **Timestamp Freshness (Skew Check)**:
   The orchestrator checks $|t_{\text{now}} - t_{\text{msg}}| \le \text{max\_skew\_seconds}$ (default: 60.0s). Stale messages captured by an eavesdropper and re-injected later are rejected:
   `Message timestamp expired (skew: 75.2s > 60.0s)`.
2. **Message ID Uniqueness Cache**:
   Every message possesses a unique UUID `message_id`. Processed IDs are recorded in an in-memory sliding set `_seen_message_ids`. Duplicate message IDs are immediately dropped:
   `Replay attack detected: duplicate message_id '...'`.
3. **Monotonic Sequence Numbers**:
   Node sessions maintain an incrementing `sequence_number`. The orchestrator tracks `_last_sequence[node_id]`. If an incoming message has $\text{seq} \le \text{last\_seq}$, it is discarded as an out-of-order or duplicate injection:
   `Replay attack detected: non-monotonic sequence 4 <= 4`.

### 2.3 Join Token Authentication
When a worker node connects, it must provide a valid `token` inside its `RegisterNodePayload`. If `token != orchestrator.join_token`, registration is rejected, the connection is closed with WebSocket code `1008` (Policy Violation), and no task offers or telemetry are exchanged.

### 2.4 Payload Size Boundaries & Checksum Integrity
- **Size Enforcements**: `BinaryPayloadStore` and `ChunkAssembler` enforce a hard ceiling (`max_payload_size_bytes = 50 MB`). Oversized frames immediately raise `PayloadSizeLimitExceededError` and discard buffered bytes, preventing memory exhaustion (OOM DoS attacks).
- **SHA-256 Checksums**: Assembled binary frames are verified against pre-computed SHA-256 hashes using constant-time comparison before passing to worker handlers.

### 2.5 Dual Operational Modes
TaskMesh supports two distinct operational modes:
1. **Secure Mode (`--secure`)**:
   Enforced via CLI flag `--secure` or `TASKMESH_SECURE_MODE=true`. All incoming WebSocket messages must carry valid HMAC signatures and pass timestamp, ID, and sequence checks. Unsigned or corrupted messages are rejected.
2. **Insecure Development Mode (Default)**:
   Permissive mode allowing rapid local testing without managing shared secrets. Skips cryptographic validation for ease of local debugging.

---

## 3. Security Limitations & Gaps (Architectural Honesty)

While TaskMesh implements strong message-level authentication and replay prevention, a distributed systems engineer should be aware of several real-world security limitations in the current implementation:

1. **Lack of Transport Layer Security (Plain HTTP & WS)**:
   By default, TaskMesh binds to unencrypted `http://` and `ws://` sockets. While payload integrity is protected by HMAC, network traffic (including binary image pixels and task JSON payloads) is transmitted in plaintext, vulnerable to passive Wi-Fi eavesdropping unless deployed behind a reverse proxy (e.g. Caddy/Nginx with TLS) or over an encrypted VPN (WireGuard, Tailscale).
2. **Shared Symmetric Secret**:
   Authentication relies on a single cluster-wide shared secret (`join_token`). All nodes share the same key. If one worker laptop is compromised, the attacker possesses the key and can sign valid messages. There is currently no per-node asymmetric public/private key infrastructure.
3. **Unauthenticated REST API**:
   The HTTP management endpoints (`/v1/tasks`, `/v1/nodes`, `/v1/cluster/health`) do not currently enforce HTTP Bearer tokens or API keys. Any device with network connectivity to port 8000 can submit tasks or cancel existing jobs.
4. **Arbitrary Code Execution in Handlers**:
   Workers execute Python functions directly in-process or via thread pools. There is no sandboxing (no seccomp, gVisor, or Docker container isolation). A custom handler containing malicious code has full OS access on the host node.

---

## 4. Threat Model & Recommended Hardening

| Threat | Risk Level | Implemented Mitigation | Recommended Production Hardening |
|---|---|---|---|
| **Eavesdropping on Wi-Fi** | High | None (Plaintext HTTP/WS) | Terminate TLS via Nginx / Traefik; use `wss://` |
| **Message Tampering** | High | HMAC-SHA256 signature verification | Enable `--secure` mode in all deployments |
| **Replay Attacks** | High | Timestamp skew + unique UUID + sequence checks | Fully mitigated by `SecurityManager` |
| **Memory Exhaustion (DoS)** | Medium | 50MB ceiling in `ChunkAssembler` | Add per-IP rate limiting on `/v1/tasks/binary` |
| **Rogue Node Joining Cluster** | High | Cluster join token verification on handshake | Upgrade to per-node mTLS certificates |
| **REST API Abuse** | Medium | None | Add API key middleware to FastAPI endpoints |

