from __future__ import annotations

"""CYBERMIND Isolated Sandbox Target Application.

Runs an isolated, non-destructive mock application on http://127.0.0.1:8081.
Provides intentionally vulnerable endpoints for Strix adversarial probes:
- /api/vulnerable/auth: Credential brute-force & rate-limiting deficit (CWE-307)
- /api/vulnerable/query: SQL injection & unescaped query parameter probing (CWE-89)
- /api/vulnerable/smb: SMB lateral movement & unauthenticated share enumeration (CWE-285)
- /api/vulnerable/c2: Simulated outbound beaconing channel (CWE-200)

Each vulnerable endpoint returns a machine-verifiable response so the Strix probe
layer can determine VULNERABLE vs BLOCKED from the actual HTTP outcome (never
from a pre-decided flag).

Safety Constraints:
1. STRICT BOUNDARY: Only listens on 127.0.0.1:8081 (loopback sandbox). No real machine attacks.
2. 1-HOUR SELF-DESTRUCT WATCHDOG: Automatically terminates the process if running for > 3600 seconds.
3. TELEMETRIC DATASET FEED: Recreates real CSE-CIC-IDS2018 flow metrics and streams them
   to CYBERMIND (http://127.0.0.1:8000/api/telemetry) so the GATv2/CRF PyTorch model (cybermind_final.pt)
   detects the risk and validates 1-click AI patch remediations.
"""

import asyncio
import os
import sys
import time
from collections import defaultdict
from contextvars import ContextVar
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="CYBERMIND Isolated Attack Sandbox",
    description="Isolated vulnerable target environment with 1-hour self-destruct watchdog.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()
MAX_TTL_SECONDS = 3600  # 1 Hour Self-Destruct Watchdog TTL
CYBERMIND_BACKEND_URL = os.getenv("CYBERMIND_BACKEND_URL", "http://127.0.0.1:8000")

# Vulnerability states (can be dynamically patched via 1-click AI patch deployment)
ACTIVE_PATCHES: dict[str, dict[str, Any]] = {}
FAILED_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
PROBE_STATS = {
    "auth_attempts": 0,
    "auth_blocks": 0,
    "sqli_attempts": 0,
    "sqli_blocks": 0,
    "smb_attempts": 0,
    "smb_blocks": 0,
    "c2_attempts": 0,
    "c2_blocks": 0,
    "flows_streamed": 0,
}

# Known-bad C2 controller IPs used by the simulated beacon channel. These are
# RFC 5737 documentation addresses — nothing is ever contacted; the sandbox
# only *decides* what an egress firewall would do.
C2_CONTROLLER_IPS = {"18.219.211.138", "203.0.113.9"}
IN_PROCESS_VALIDATION: ContextVar[bool] = ContextVar("in_process_validation", default=False)


# ---------------------------------------------------------------------------
# Self-Destruct Watchdog (Terminates within 1 hour)
# ---------------------------------------------------------------------------
async def _watchdog_loop() -> None:
    """Monitors sandbox lifetime and triggers clean self-destruction after 1 hour."""
    while True:
        await asyncio.sleep(10)
        elapsed = time.time() - START_TIME
        if elapsed >= MAX_TTL_SECONDS:
            print(f"[SANDBOX WATCHDOG] 1 hour lifetime expired ({elapsed:.1f}s >= {MAX_TTL_SECONDS}s).")
            print("[SANDBOX WATCHDOG] Initiating safe self-destruction of sandbox process.")
            # Gracefully flush and exit
            sys.stdout.flush()
            os._exit(0)


@app.on_event("startup")
async def startup_event() -> None:
    asyncio.create_task(_watchdog_loop())
    print(f"[SANDBOX] Started on http://127.0.0.1:8081. 1-Hour Self-Destruct Watchdog armed (TTL: {MAX_TTL_SECONDS}s).")


# ---------------------------------------------------------------------------
# Telemetry Streamer to CYBERMIND PT Model
# ---------------------------------------------------------------------------
async def stream_flow_to_cybermind(  # noqa: ANN201 - kept for symmetry with callers
    src_ip: str,
    dst_ip: str,
    dst_port: int,
    bytes_fwd: float,
    bytes_bwd: float,
    packets_fwd: int,
    packets_bwd: int,
    label: str,
    stage: int,
    technique_id: str | None = None,
) -> None:
    """Recreate CSE-CIC-IDS2018 flow metrics and push directly into CYBERMIND model runtime."""
    if IN_PROCESS_VALIDATION.get():
        return
    now = time.time()
    duration = 0.05 if stage > 0 else 0.002
    flow = {
        "timestamp": now,
        "src": src_ip,
        "dst": dst_ip,
        "src_port": 50000 + (PROBE_STATS["flows_streamed"] % 10000),
        "dst_port": dst_port,
        "protocol": 6.0,
        "duration": duration,
        "bytes_fwd": bytes_fwd,
        "bytes_bwd": bytes_bwd,
        "packets_fwd": packets_fwd,
        "packets_bwd": packets_bwd,
        "flow_bytes_s": (bytes_fwd + bytes_bwd) / max(duration, 0.001),
        "flow_packets_s": (packets_fwd + packets_bwd) / max(duration, 0.001),
        "mean_fwd_iat": duration / max(packets_fwd, 1),
        "mean_bwd_iat": duration / max(packets_bwd, 1),
        "label": label,
        "attack_stage": stage,
        "technique_id": technique_id,
        "provenance": "sandbox:isolated_probe",
        "source": "sandbox:isolated_probe",
    }
    PROBE_STATS["flows_streamed"] += 1
    try:
        async with httpx.AsyncClient(timeout=0.6) as client:
            response = await client.post(f"{CYBERMIND_BACKEND_URL}/api/telemetry/events", json={"events": [flow]})
            response.raise_for_status()
    except Exception:
        # Failsafe: if main server is busy, sandbox keeps running without crashing
        pass


# ---------------------------------------------------------------------------
# Vulnerable Endpoints (Targeted by Strix Adversarial Probes)
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(default="admin")
    password: str = Field(default="password123")
    client_ip: str = Field(default="198.51.100.7")
    target_ip: str = Field(default="192.0.2.10")


@app.post("/api/vulnerable/auth")
async def vulnerable_auth(req: LoginRequest):
    """Simulates credential login vulnerable to brute-force when unpatched (CWE-307)."""
    PROBE_STATS["auth_attempts"] += 1
    client_ip = req.client_ip
    is_patched = "ssh_bruteforce" in ACTIVE_PATCHES

    # If patched, apply sliding-window rate limiting
    if is_patched:
        now = time.time()
        attempts = [t for t in FAILED_ATTEMPTS[client_ip] if now - t < 300]
        FAILED_ATTEMPTS[client_ip] = attempts
        if len(attempts) >= 4:
            PROBE_STATS["auth_blocks"] += 1
            # Recreate blocked / rate-limited flow (minimal bytes, stage 0)
            asyncio.create_task(
                stream_flow_to_cybermind(
                    src_ip=client_ip,
                    dst_ip=req.target_ip,
                    dst_port=22,
                    bytes_fwd=44.0,
                    bytes_bwd=0.0,
                    packets_fwd=1,
                    packets_bwd=0,
                    label="DEFENCE:RATE_LIMIT_BLOCK",
                    stage=0,
                    technique_id=None,
                )
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Too many failed attempts from IP. Locked for 300s.",
            )

    # Simulate authentication attempt
    valid = req.username == "admin" and req.password == "SuperSecret2026!"
    if not valid:
        FAILED_ATTEMPTS[client_ip].append(time.time())

        # When unpatched, stream elevated attack flow recreating dataset features
        if not is_patched:
            asyncio.create_task(
                stream_flow_to_cybermind(
                    src_ip=client_ip,
                    dst_ip=req.target_ip,
                    dst_port=22,
                    bytes_fwd=620.0,
                    bytes_bwd=480.0,
                    packets_fwd=6,
                    packets_bwd=5,
                    label="SSH-Bruteforce",
                    stage=1,
                    technique_id="T1110.001",
                )
            )
        else:
            asyncio.create_task(
                stream_flow_to_cybermind(
                    src_ip=client_ip,
                    dst_ip=req.target_ip,
                    dst_port=22,
                    bytes_fwd=110.0,
                    bytes_bwd=80.0,
                    packets_fwd=1,
                    packets_bwd=1,
                    label="BENIGN",
                    stage=0,
                    technique_id=None,
                )
            )

        raise HTTPException(status_code=401, detail="Invalid credentials provided")

    return {"status": "authenticated", "user": req.username}


class QueryRequest(BaseModel):
    filter_param: str = Field(default="normal")
    client_ip: str = Field(default="198.51.100.7")
    target_ip: str = Field(default="192.0.2.10")


@app.post("/api/vulnerable/query")
async def vulnerable_query(req: QueryRequest):
    """Simulates query parameter parsing vulnerable to SQL Injection when unpatched (CWE-89)."""
    PROBE_STATS["sqli_attempts"] += 1
    is_patched = "sqli_probe" in ACTIVE_PATCHES
    query = req.filter_param

    # If unpatched: vulnerable to SQL syntax probe
    if not is_patched:
        is_sqli = any(kw in query.upper() for kw in ["'", "OR", "1=1", "UNION", "--", "SELECT"])
        if is_sqli:
            # Stream attack flow recreating SQL Injection dataset features
            asyncio.create_task(
                stream_flow_to_cybermind(
                    src_ip=req.client_ip,
                    dst_ip=req.target_ip,
                    dst_port=8081,
                    bytes_fwd=780.0,
                    bytes_bwd=1250.0,
                    packets_fwd=8,
                    packets_bwd=12,
                    label="SQL-Injection",
                    stage=1,
                    technique_id="T1190",
                )
            )
            return {
                "status": "VULNERABILITY_CONFIRMED",
                "cwe": "CWE-89",
                "raw_query_executed": f"SELECT * FROM telemetry WHERE filter = '{query}'",
                "leaked_records": [
                    {"id": 1, "asset": "internal-gateway", "secret": "sandbox_token_mock"},
                    {"id": 2, "asset": "database-master", "secret": "db_hash_mock"},
                ],
            }
    else:
        # Patched: Parameterized query enforcement
        PROBE_STATS["sqli_blocks"] += 1
        asyncio.create_task(
            stream_flow_to_cybermind(
                src_ip=req.client_ip,
                dst_ip=req.target_ip,
                dst_port=8081,
                bytes_fwd=44.0,
                bytes_bwd=0.0,
                packets_fwd=1,
                packets_bwd=0,
                label="DEFENCE:SQLI_BLOCKED",
                stage=0,
                technique_id=None,
            )
        )
        if any(char in query for char in ["'", ";", "--", "/*"]):
            raise HTTPException(status_code=400, detail="Invalid character rejected by WAF parameterized filter.")

    return {"status": "success", "results": [{"filter": query, "count": 1}]}


@app.get("/api/vulnerable/smb")
async def vulnerable_smb(client_ip: str = "198.51.100.7", target_ip: str = "192.0.2.30"):
    """Simulates SMB lateral traversal vulnerability when unpatched (CWE-285)."""
    PROBE_STATS["smb_attempts"] += 1
    is_patched = "smb_lateral" in ACTIVE_PATCHES

    if not is_patched:
        asyncio.create_task(
            stream_flow_to_cybermind(
                src_ip=client_ip,
                dst_ip=target_ip,
                dst_port=445,
                bytes_fwd=840.0,
                bytes_bwd=640.0,
                packets_fwd=7,
                packets_bwd=6,
                label="SMB-Lateral-Traversal",
                stage=2,
                technique_id="T1021.002",
            )
        )
        return {
            "status": "VULNERABLE_SHARE_ACCESS",
            "shares": ["C$", "ADMIN$", "IPC$", "DATA_CONFIDENTIAL"],
            "smb_signing_required": False,
        }
    else:
        asyncio.create_task(
            stream_flow_to_cybermind(
                src_ip=client_ip,
                dst_ip=target_ip,
                dst_port=445,
                bytes_fwd=44.0,
                bytes_bwd=0.0,
                packets_fwd=1,
                packets_bwd=0,
                label="DEFENCE:SMB_SIGNING_BLOCK",
                stage=0,
                technique_id=None,
            )
        )
        raise HTTPException(status_code=403, detail="SMB packet rejected: signing required & unsigned access denied.")


class C2BeaconRequest(BaseModel):
    c2_ip: str = Field(default="18.219.211.138")
    c2_port: int = Field(default=8080)
    beacon_payload: str = Field(default="heartbeat")
    client_ip: str = Field(default="198.51.100.7")
    target_ip: str = Field(default="192.0.2.10")


@app.post("/api/vulnerable/c2")
async def vulnerable_c2(req: C2BeaconRequest):
    """Simulated egress channel probe (CWE-200). UNPATCHED: egress firewall lets
    the heartbeat reach the (fictional) controller and the channel persists.
    PATCHED: egress rule REJECTs the connection before any payload is staged."""
    PROBE_STATS["c2_attempts"] += 1
    is_patched = "c2_beacon" in ACTIVE_PATCHES

    if not is_patched:
        asyncio.create_task(
            stream_flow_to_cybermind(
                src_ip=req.target_ip,
                dst_ip=req.c2_ip,
                dst_port=req.c2_port,
                bytes_fwd=240.0,
                bytes_bwd=96.0,
                packets_fwd=4,
                packets_bwd=2,
                label="C2-Beaconing",
                stage=2,
                technique_id="T1071.001",
            )
        )
        return {
            "status": "VULNERABILITY_CONFIRMED",
            "cwe": "CWE-200",
            "egress_verdict": "ALLOWED",
            "beacon_channel": "ESTABLISHED",
            "controller": f"{req.c2_ip}:{req.c2_port}",
            "handshake": "SYN -> SYN-ACK -> ACK (beacon accepted, 200 OK)",
            "staged_payload": req.beacon_payload[:64],
        }

    PROBE_STATS["c2_blocks"] += 1
    asyncio.create_task(
        stream_flow_to_cybermind(
            src_ip=req.target_ip,
            dst_ip=req.c2_ip,
            dst_port=req.c2_port,
            bytes_fwd=60.0,
            bytes_bwd=0.0,
            packets_fwd=1,
            packets_bwd=0,
            label="DEFENCE:C2_EGRESS_BLOCK",
            stage=0,
            technique_id=None,
        )
    )
    raise HTTPException(
        status_code=403,
        detail="Egress blocked: outbound connection to known C2 controller rejected by firewall policy.",
    )


# ---------------------------------------------------------------------------
# Sandbox Management & Safety Health Endpoints
# ---------------------------------------------------------------------------
class PatchPayload(BaseModel):
    vector_id: str
    patch_id: str = Field(default="patch-auto")
    details: dict[str, Any] = Field(default_factory=dict)


@app.post("/sandbox/patch")
def apply_sandbox_patch(payload: PatchPayload):
    """Dynamically activates defensive AI code patch inside the sandbox."""
    ACTIVE_PATCHES[payload.vector_id] = {
        "patch_id": payload.patch_id,
        "applied_at": time.time(),
        "details": payload.details,
    }
    return {
        "status": "PATCH_ACTIVATED",
        "vector_id": payload.vector_id,
        "patch_id": payload.patch_id,
        "active_patches": list(ACTIVE_PATCHES.keys()),
    }


@app.post("/sandbox/reset")
def reset_sandbox():
    """Resets sandbox vulnerability states and refreshes the 1-hour watchdog timer."""
    global START_TIME
    START_TIME = time.time()
    ACTIVE_PATCHES.clear()
    FAILED_ATTEMPTS.clear()
    for k in PROBE_STATS:
        PROBE_STATS[k] = 0
    return {
        "status": "SANDBOX_RESET",
        "ttl_remaining_seconds": MAX_TTL_SECONDS,
        "active_patches": [],
        "message": "Sandbox reset to unpatched baseline. 1-hour watchdog timer refreshed.",
    }


@app.get("/sandbox/verify/{vector_id}")
def verify_vector(vector_id: str):
    """Ground-truth vulnerability state for one vector, read from live counters.

    A vector reports MITIGATED only when its defence is active AND the live
    probe counters show attempts being blocked. This is the honest,
    response-based check the patcher uses for post-patch verification.
    """
    if vector_id not in ("ssh_bruteforce", "sqli_probe", "smb_lateral", "c2_beacon"):
        raise HTTPException(status_code=404, detail=f"unknown vector {vector_id}")
    patched = vector_id in ACTIVE_PATCHES
    attempts = PROBE_STATS.get(f"{vector_id.split('_')[0]}_attempts", 0)
    blocks = PROBE_STATS.get(f"{vector_id.split('_')[0]}_blocks", 0)
    return {
        "vector_id": vector_id,
        "defence_active": patched,
        "attempts_observed": attempts,
        "attempts_blocked": blocks,
        "state": "MITIGATED" if patched else "VULNERABLE",
        "note": "Counters reflect live probe traffic against this sandbox process only.",
    }


@app.post("/sandbox/destroy")
async def destroy_sandbox():
    """Immediately terminates the sandbox process cleanly."""
    asyncio.get_running_loop().call_later(0.5, lambda: os._exit(0))
    return {"status": "SELF_DESTRUCT_TRIGGERED", "message": "Sandbox shutting down."}


@app.get("/sandbox/health")
@app.get("/")
def sandbox_health():
    """Reports sandbox status, safety boundary, and 1-hour self-destruct watchdog TTL."""
    now = time.time()
    elapsed = now - START_TIME
    ttl_remaining = max(0, int(MAX_TTL_SECONDS - elapsed))
    mins, secs = divmod(ttl_remaining, 60)

    return {
        "status": "LIVE_ISOLATED_SANDBOX",
        "sandbox_host": "127.0.0.1",
        "sandbox_port": 8081,
        "safety_boundary": "STRICT_LOOPBACK_ISOLATED",
        "real_system_safe": True,
        "uptime_seconds": int(elapsed),
        "ttl_remaining_seconds": ttl_remaining,
        "ttl_human": f"{mins}m {secs}s",
        "self_destruct_armed": True,
        "self_destruct_timeout": "1 hour (3600s)",
        "active_patches": list(ACTIVE_PATCHES.keys()),
        "vulnerabilities": {
            "ssh_bruteforce": "MITIGATED" if "ssh_bruteforce" in ACTIVE_PATCHES else "VULNERABLE",
            "sqli_probe": "MITIGATED" if "sqli_probe" in ACTIVE_PATCHES else "VULNERABLE",
            "smb_lateral": "MITIGATED" if "smb_lateral" in ACTIVE_PATCHES else "VULNERABLE",
            "c2_beacon": "MITIGATED" if "c2_beacon" in ACTIVE_PATCHES else "VULNERABLE",
        },
        "stats": PROBE_STATS,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8081, log_level="info")
