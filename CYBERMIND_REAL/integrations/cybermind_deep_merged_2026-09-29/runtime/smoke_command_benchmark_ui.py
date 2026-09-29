import os
from pathlib import Path

from playwright.sync_api import sync_playwright


URL = os.environ["CYBERMIND_TEST_URL"].rstrip("/") + "/"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SCREENSHOT = Path(__file__).with_name("smoke_command_benchmark_ui.png")
MENU_SCREENSHOT = Path(__file__).with_name("smoke_command_scenario_menu.png")


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=EDGE, headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL, wait_until="domcontentloaded")
    selector = page.get_by_role("button", name="Select scenario")
    selector.wait_for(timeout=30000)
    selector.click()
    menu = page.get_by_role("listbox", name="Scenarios")
    menu.wait_for()
    assert menu.is_visible(), "Scenario menu did not open"
    assert page.locator("select[aria-label='Select scenario']").count() == 0
    bounds = menu.bounding_box()
    assert bounds and bounds["width"] < 500, f"Scenario menu bounds look wrong: {bounds}"
    card_bounds = selector.locator("xpath=../..").bounding_box()
    assert card_bounds and bounds["y"] >= card_bounds["y"] and bounds["y"] + bounds["height"] <= card_bounds["y"] + card_bounds["height"], (
        f"Scenario menu leaves its card: menu={bounds}, card={card_bounds}"
    )
    page.screenshot(path=str(MENU_SCREENSHOT))
    first = menu.get_by_role("option").first
    first_name = first.inner_text()
    first.click()
    assert not menu.is_visible(), "Scenario menu did not close after selection"
    page.wait_for_function(
        "name => document.querySelector('button[aria-label=\"Select scenario\"]')?.textContent?.includes(name)",
        arg=first_name,
        timeout=10000,
    )
    page.get_by_role("button", name="Benchmark (Track A)").click()
    dialog = page.get_by_role("dialog", name="CYBERMIND model benchmark")
    dialog.wait_for()
    filter_value = dialog.evaluate("node => getComputedStyle(node).backdropFilter")
    assert filter_value == "none", f"Benchmark still uses backdrop blur: {filter_value}"
    page.screenshot(path=str(SCREENSHOT))
    assert not errors, f"Browser errors: {errors}"
    page.request.post(f"{URL}api/scenarios/stop", data={"scenario_id": "current"})
    page.request.post(f"{URL}api/scenarios/reset", data={})
    print(f"PASS: scenario selected ({first_name}); benchmark overlay has no backdrop blur; screenshot={SCREENSHOT}")
    browser.close()
