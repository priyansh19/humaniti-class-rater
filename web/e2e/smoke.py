"""Browser end-to-end smoke test with SYNTHETIC media only.
usage: python e2e/smoke.py <base_url> <synthetic.mp4> <synthetic.vtt> <out_dir> [--transcript-only]"""
import sys

from playwright.sync_api import expect, sync_playwright

base, mp4, vtt, out = sys.argv[1:5]
transcript_only = "--transcript-only" in sys.argv
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/google/chrome/chrome", headless=True)
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(base)
    pg.screenshot(path=f"{out}/1-home.png", full_page=True)
    if transcript_only:
        pg.get_by_role("tab", name="Transcript only").click()
        pg.locator("#tx").fill(open(vtt).read())
        pg.get_by_role("button", name="Assess class").click()
    else:
        expect(pg.get_by_text("Worker online")).to_be_visible(timeout=15000)
        pg.locator('input[type=file][accept^="video"]').set_input_files(mp4)
        pg.locator('input[type=file][accept^=".vtt"]').set_input_files(vtt)
        pg.get_by_role("button", name="Assess class").click()
        pg.wait_for_url("**/jobs/**", timeout=60000)
        pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{out}/2-progress.png", full_page=True)
    expect(pg.get_by_text("Overall rating")).to_be_visible(timeout=240000)
    expect(pg.get_by_text("Rubric scorecard")).to_be_visible()
    expect(pg.get_by_text("Evidence timeline")).to_be_visible()
    pg.wait_for_timeout(500)
    pg.screenshot(path=f"{out}/3-report.png", full_page=True)
    body = pg.inner_text("body")
    for name in ["Meera", "Arjun", "Kavya"]:
        assert name not in body, f"name leaked: {name}"
    print("E2E OK:", pg.url)
    b.close()
