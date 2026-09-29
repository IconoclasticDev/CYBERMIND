"""Exercise the already-running desktop EXE through its actual React upload UI."""

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


url = os.environ["CYBERMIND_TEST_URL"].rstrip("/") + "/"
demo_dir = Path(os.environ["CYBERMIND_DEMO_DIR"])
output_dir = Path(__file__).with_name("e2e_native_demo")
output_dir.mkdir(exist_ok=True)
edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
files = [
    ("ctu_pcap", demo_dir / "ctu_iot23_capture_9_1_only5000.pcap"),
    ("botnet_csv", demo_dir / "botnet_ares_sample.csv"),
    ("ssh_csv", demo_dir / "ssh_bruteforce_sample.csv"),
]

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=edge, headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, accept_downloads=True)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.get_by_text("Model Online").first.wait_for(timeout=30000)

    results = []
    for label, path in files:
        assert path.is_file(), path
        page.get_by_role("button", name="Upload PCAP / CSV").click()
        page.locator('input[type="file"][accept*="pcap"]').set_input_files(str(path))
        with page.expect_response(lambda response: "/api/upload/flows" in response.url and response.request.method == "POST", timeout=120000) as response_info:
            page.get_by_role("button", name="Ingest & Run World Model").click()
        response = response_info.value
        payload = response.json()
        page.screenshot(path=str(output_dir / f"{label}_upload.png"), full_page=True)
        results.append({
            "file": path.name,
            "status": response.status,
            "response": payload,
            "ui_success": page.get_by_text("Network Flows Ingested Successfully!").is_visible(),
        })
        if response.ok:
            page.get_by_role("button", name="View Live Graph").click()
            page.screenshot(path=str(output_dir / f"{label}_command_centre.png"), full_page=True)
        else:
            page.get_by_role("button", name="Close").first.click()

    results.append({"browser_errors": errors})
    (output_dir / "results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(json.dumps([{
        "file": item.get("file"),
        "status": item.get("status"),
        "ui_success": item.get("ui_success"),
        "flows_ingested": item.get("response", {}).get("flows_ingested"),
        "state_windows": item.get("response", {}).get("state_windows"),
        "forecast": bool(item.get("response", {}).get("forecast")),
    } for item in results if "file" in item], indent=2))
    print("browser_errors:", errors)
    browser.close()
