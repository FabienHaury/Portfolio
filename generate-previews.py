import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# =========================
# CONFIGURATION
# =========================

ROOT = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT / "Images" / "previews"

JSON_FILES = [
    ROOT / "projects.json",
    ROOT / "personal-projects.json",
]

VIEWPORT = {
    "width": 1440,
    "height": 1000,
}


# =========================
# HELPERS
# =========================

def safe_filename(name):
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        name.lower()
    ).strip("-")


def load_projects():
    projects = []

    for path in JSON_FILES:

        if not path.exists():
            raise SystemExit(f"Missing JSON file: {path}")

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise SystemExit(
                f"Invalid JSON in {path}: {exc}"
            )

        def collect(sections):
            for section in sections:

                projects.extend(
                    section.get("projects", [])
                )

                collect(
                    section.get("subsections", [])
                )

        collect(data.get("sections", []))

    return projects


def valid_url(url):
    try:
        parsed = urlparse(url)

        return (
            parsed.scheme == "https"
            and bool(parsed.netloc)
        )

    except ValueError:
        return False


# =========================
# GENERATE SCREENSHOTS
# =========================

def generate_screenshots():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    projects = load_projects()

    website_projects = [
        project
        for project in projects
        if project.get("type") in (
            "website",
            "interactive"
        )
    ]

    if not website_projects:
        print("No website previews to generate.")
        return

    print(
        f"Found {len(website_projects)} websites "
        "to capture."
    )

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch()

        try:

            for project in website_projects:

                name = project.get(
                    "name",
                    "project"
                )

                url = project.get("url")

                if not url or not valid_url(url):
                    print(f"Skipping invalid URL: {name}")
                    continue

                filename = safe_filename(name) + ".png"

                screenshot_path = (
                    OUTPUT_DIR / filename
                )

                print(f"\nCapturing: {name}")

                page = browser.new_page(
                    viewport=VIEWPORT,
                    device_scale_factor=1
                )

                try:

                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=45000
                    )

                    try:
                        page.wait_for_load_state(
                            "networkidle",
                            timeout=10000
                        )

                    except PlaywrightTimeoutError:
                        print(
                            "Network still active; "
                            "continuing with screenshot."
                        )

                    # Allow charts and visual elements
                    # a little time to finish rendering.

                    page.wait_for_timeout(2000)

                    page.screenshot(
                        path=str(screenshot_path),
                        full_page=False,
                        animations="disabled"
                    )

                    print(
                        f"Screenshot saved: {filename}"
                    )

                except Exception as error:

                    print(
                        f"Failed to capture {name}: {error}"
                    )

                finally:
                    page.close()

        finally:
            browser.close()

    print("\nScreenshot generation completed.")


if __name__ == "__main__":
    generate_screenshots()
