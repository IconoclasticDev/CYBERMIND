"""Smoke-test the running native EXE backend and its bundled React UI."""

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


url = os.environ["CYBERMIND_TEST_URL"].rstrip("/") + "/"
out = Path(__file__).with_name("e2e_native_demo")
out.mkdir(exist_ok=True)
edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
results = {}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=edge, headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, accept_downloads=True)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.get_by_text("Model Online").first.wait_for(timeout=30000)

    page.get_by_role("button", name="Threat Forecast").click()
    page.get_by_role("heading", name="Predictive Threat Forecast").wait_for()
    page.get_by_text("Risk trajectory", exact=False).first.wait_for()
    results["forecast_visible"] = True
    page.screenshot(path=str(out / "ssh_threat_forecast.png"), full_page=True)

    page.get_by_role("button", name="Command Center", exact=True).click()
    with page.expect_response(lambda response: "/api/validation/local" in response.url and response.request.method == "POST", timeout=30000) as check_info:
        page.get_by_role("button", name="Run local check").click()
    check_response = check_info.value
    check = check_response.json()
    results["local_check"] = {
        "status": check_response.status,
        "verdict": check.get("verdict"),
        "http_statuses": [entry.get("http_status") for entry in check.get("checks", [])],
    }
    page.get_by_text("SANDBOX RESPONSES OBSERVED").first.wait_for()
    page.screenshot(path=str(out / "ssh_local_validation.png"), full_page=True)

    page.get_by_role("button", name="Benchmark (Track A)").click()
    dialog = page.get_by_role("dialog", name="CYBERMIND model benchmark")
    dialog.wait_for()
    dialog.get_by_text("Feature-matched logistic").first.wait_for(timeout=15000)
    results["benchmark_visible"] = True
    page.screenshot(path=str(out / "ssh_benchmark.png"), full_page=True)
    dialog.get_by_role("button", name="Close benchmark").click()

    page.get_by_role("button", name="Open data assistant").click()
    assistant = page.get_by_role("dialog", name="CYBERMIND data assistant")
    assistant.get_by_role("button", name="What does the model forecast?").click()
    assistant.get_by_text("Source:", exact=False).last.wait_for(timeout=15000)
    results["assistant_answered"] = True
    page.screenshot(path=str(out / "ssh_assistant.png"), full_page=True)
    assistant.get_by_role("button", name="Close assistant").click()

    page.get_by_role("button", name="Reports").click()
    page.get_by_role("heading", name="Reports & Experiment Records").wait_for()
    page.get_by_role("button", name="Export Encrypted Incident Brief (JSON)").click()
    encrypt_dialog = page.get_by_role("dialog", name="Encrypt incident brief")
    with page.expect_download(timeout=30000) as encrypted_download:
        encrypt_dialog.get_by_role("button", name="Encrypt & download").click()
    encrypted = out / "encrypted_incident_brief.json"
    encrypted_download.value.save_as(encrypted)
    key = encrypt_dialog.get_by_label("Generated report key").input_value()
    envelope = json.loads(encrypted.read_text(encoding="utf-8"))
    assert key and "executive_summary" not in envelope
    encrypt_dialog.get_by_role("button", name="Close").last.click()

    page.get_by_role("button", name="Decrypt Encrypted Incident Brief").click()
    decrypt_dialog = page.get_by_role("dialog", name="Decrypt incident brief")
    decrypt_dialog.locator('input[type="file"]').set_input_files(str(encrypted))
    decrypt_dialog.get_by_placeholder("Paste the separately shared key").fill(key)
    decrypt_dialog.get_by_role("button", name="Decrypt & view").click()
    page.get_by_role("heading", name="Decrypted incident brief").wait_for(timeout=15000)
    with page.expect_download(timeout=15000) as readable_download:
        page.get_by_role("button", name="Download readable JSON").click()
    readable = out / "readable_incident_brief.json"
    readable_download.value.save_as(readable)
    report = json.loads(readable.read_text(encoding="utf-8"))
    assert report["report_type"] == "CYBERMIND_Incident_Brief"
    results["encrypted_report_round_trip"] = True
    results["readable_report_model"] = report["environment"]["model"].get("version")
    results["browser_errors"] = errors
    (out / "workflow_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    browser.close()
