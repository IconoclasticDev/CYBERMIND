"""End-to-end checks for the local API using an unlabeled packet capture."""
from pathlib import Path
from fastapi.testclient import TestClient
from scapy.all import IP, TCP, Raw, wrpcap
from cybermind.analyst.api import app


def test_capture_authentication_and_four_step_forecast(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERMIND_HOME", str(tmp_path))
    client = TestClient(app)
    assert client.get("/api/status").json()["checkpoint_ready"]
    assert client.get("/api/capture/forecast").status_code == 401
    token = client.post("/api/auth/setup", json={"password": "correct-horse-battery-staple"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    packets = []
    for index in range(22):
        packet = IP(src="10.0.0.10", dst="10.0.0.20") / TCP(
            sport=40000 + index, dport=80 + index % 4, flags="PA") / Raw(load=b"X" * 40)
        packet.time = 1700000000 + index * 30
        packets.append(packet)
    path = Path(tmp_path) / "sample.pcap"
    wrpcap(str(path), packets)
    with path.open("rb") as source:
        response = client.post("/api/capture", files={"file": ("sample.pcap", source)}, headers=headers)
    assert response.status_code == 200, response.text
    loaded = response.json()
    assert loaded["packet_feature_coverage"] == 1.0
    assert loaded["sequences"] > 1
    forecast = client.get("/api/capture/forecast?position=0", headers=headers)
    assert forecast.status_code == 200, forecast.text
    result = forecast.json()
    assert result["position"] == 0
    assert [row["step"] for row in result["forecast"]] == [0, 1, 2, 3, 4]
    assert result["lineage"]["split"] == "live_upload_unlabeled"
    assert result["flows"]
    assert client.post("/api/capture/ask", json={"question": "what is the risk?"}, headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/capture/forecast", headers=headers).status_code == 401



def test_bundled_synthetic_demos_load_through_real_parser(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERMIND_HOME", str(tmp_path))
    client = TestClient(app)
    token = client.post("/api/auth/setup", json={"password": "correct-horse-battery-staple"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    demos = client.get("/api/demos", headers=headers)
    assert demos.status_code == 200
    entries = demos.json()
    assert {item["id"] for item in entries} == {"web_like", "sequential_ports"}
    assert all(item["synthetic"] and len(item["sha256"]) == 64 for item in entries)
    for item in entries:
        loaded = client.post(f"/api/demos/{item['id']}/load", headers=headers)
        assert loaded.status_code == 200, loaded.text
        assert loaded.json()["input_sha256"] == item["sha256"]
        assert loaded.json()["packet_feature_coverage"] == 1.0
        assert loaded.json()["sequences"] > 0
        result = client.get("/api/capture/forecast", headers=headers)
        assert result.status_code == 200, result.text
        assert len(result.json()["forecast"]) == 5
        assert result.json()["lineage"]["demo_synthetic"] is True
        downloaded = client.get(f"/api/demos/{item['id']}/file", headers=headers)
        assert downloaded.status_code == 200
        assert len(downloaded.content) == item["bytes"]
    assert client.post("/api/demos/does-not-exist/load", headers=headers).status_code == 404

