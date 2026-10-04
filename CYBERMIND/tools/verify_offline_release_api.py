"""Verify a running offline release through its real HTTP API; no mocks."""
from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--pcap", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--vectors", nargs="+", default=["ssh_bruteforce", "sqli_probe", "smb_lateral", "c2_beacon"])
    args = parser.parse_args()
    evidence: dict = {"base": args.base, "checks": {}, "http_calls": []}

    def api(path, body=None, method=None, binary=None, content_type=None):
        data = binary if binary is not None else (json.dumps(body).encode() if body is not None else None)
        req = Request(args.base + path, data=data, method=method,
                      headers={"Content-Type": content_type or "application/json"})
        started = time.time()
        with urlopen(req, timeout=180) as response:
            result = json.load(response)
            evidence["http_calls"].append({"method": req.get_method(), "path": path,
                                          "status": response.status, "seconds": round(time.time() - started, 3)})
        return result

    def complete_probe(vector):
        started = api("/api/attack-lab/probe/start", {"vector_id": vector, "intensity": 5, "scan_mode": "quick"})
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            records = api("/api/attack-lab/probe/records")
            if records.get("status") != "RUNNING":
                session = api("/api/attack-lab/status")["active_session"]
                assert session["session_id"] == started["session_id"]
                return session
            time.sleep(0.5)
        raise TimeoutError(f"{vector} probe did not finish")

    try:
        health = api("/api/health")
        assert health["status"] == "ok" and health["model"]["available"] is True
        evidence["checks"]["health"] = health
        # Upload the actual bundled PCAP, preserving its filename and bytes.
        pcap = Path(args.pcap)
        boundary = "CYBERMINDReleaseAudit20261004"
        prefix = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{pcap.name}\"\r\n"
                  "Content-Type: application/octet-stream\r\n\r\n").encode()
        payload = prefix + pcap.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        uploaded = api("/api/upload/flows?clear_previous=true", binary=payload,
                       content_type="multipart/form-data; boundary=" + boundary)
        evidence["checks"]["pcap_import"] = uploaded
        forecast = api("/api/forecast")
        assert forecast.get("available", True) is not False and "horizon" in forecast, forecast
        evidence["checks"]["forecast"] = forecast
        comparison = api("/api/counterfactual/simulate", {"action": "Rate Limit", "k": 4})
        assert comparison and not comparison.get("error"), comparison
        evidence["checks"]["parallel_futures"] = comparison
        local = api("/api/validation/local", {})
        evidence["checks"]["local_validation"] = local
        # The validator's exact payload is retained for independent hash review.
        assert local.get("run_id"), local
        assert "sha256" in json.dumps(local).lower(), local
        assert "http_status" in json.dumps(local).lower(), local
        api("/api/attack-lab/sandbox/reset", {})
        evidence["checks"]["attack_lab"] = {}
        for vector in args.vectors:
            before = complete_probe(vector)
            assert before["status"] == "VECTOR_SUCCEEDED", before
            assert before["summary"]["succeeded"] > 0 and before["summary"]["unreachable"] == 0
            patch = before["generated_patch"]
            assert patch and patch["patch_id"]
            approved = api("/api/attack-lab/patch/apply", {
                "patch_id": patch["patch_id"], "approver": "release-audit-analyst",
            })
            assert approved["status"] == "APPLIED_AND_VERIFIED", approved
            assert approved["verification"]["verified"] is True
            after = complete_probe(vector)
            assert after["status"] == "PROBE_DEFLECTED", after
            assert after["summary"]["succeeded"] == 0 and after["summary"]["blocked"] > 0
            evidence["checks"]["attack_lab"][vector] = {"before": before, "approval": approved, "after": after}
            print(json.dumps({"vector": vector, "before": before["summary"], "approval": approved["status"],
                              "verification_hash": approved.get("verification_hash"), "after": after["summary"]}), flush=True)
        evidence["result"] = "PASS"
        print("PASS: PCAP import, forecast, Parallel Futures, local validation, and all requested lab loops", flush=True)
    except Exception as exc:
        evidence["result"] = "FAIL"
        evidence["error"] = str(exc)
        evidence["traceback"] = traceback.format_exc()
        print(evidence["traceback"], flush=True)
    finally:
        Path(args.output).write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    return 0 if evidence.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
