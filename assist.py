"""Optional Playwright-assisted password change flows.

Loaded by dashlane-auditor only when `fix --assist` is used. Requires:
    pip install -r requirements-optional.txt
    playwright install chromium
"""

from __future__ import annotations

import secrets
import string
import sys
from pathlib import Path


def generate_password(length=24):
    """Strong random password satisfying typical site requirements."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        classes = sum((
            any(c.islower() for c in pw),
            any(c.isupper() for c in pw),
            any(c.isdigit() for c in pw),
            any(not c.isalnum() for c in pw),
        ))
        if classes >= 4:
            return pw


def load_recipe(domain, recipe_dirs):
    """Load the first matching YAML recipe for a domain."""
    try:
        import yaml
    except ImportError:
        return None

    for recipe_dir in recipe_dirs:
        if not recipe_dir:
            continue
        path = Path(recipe_dir) / f"{domain}.yaml"
        if path.is_file():
            with open(path) as f:
                return yaml.safe_load(f)
    return None


def _click_step(page, step):
    if step.get("selector"):
        page.locator(step["selector"]).first.click(timeout=8000)
    elif step.get("text"):
        page.get_by_role("button", name=step["text"], exact=False).first.click(timeout=8000)
    else:
        raise ValueError("click step needs selector or text")


def _fill_step(page, step, value):
    if not step.get("selector"):
        raise ValueError("fill step needs selector")
    loc = page.locator(step["selector"]).first
    loc.click(timeout=8000)
    loc.fill(value, timeout=8000)


def run_recipe(page, recipe, current_password, new_password):
    """Execute declarative recipe steps on an open Playwright page."""
    for step in recipe.get("steps", []):
        action = step.get("action")
        if action == "click":
            _click_step(page, step)
        elif action == "fill_current":
            _fill_step(page, step, current_password)
        elif action == "fill_new":
            _fill_step(page, step, new_password)
        elif action == "fill_confirm":
            _fill_step(page, step, new_password)
        elif action == "wait":
            page.wait_for_timeout(int(step.get("ms", 1000)))
        else:
            raise ValueError(f"unknown recipe action: {action}")
    return True


def find_password_fields(page):
    """Heuristic: locate current/new/confirm password inputs."""
    fields = page.locator('input[type="password"]:visible')
    count = fields.count()
    if count == 3:
        return {"current": fields.nth(0), "new": fields.nth(1), "confirm": fields.nth(2)}
    if count == 2:
        return {"current": fields.nth(0), "new": fields.nth(1), "confirm": None}
    return None


def submit_password_form(page):
    """Try common submit patterns after filling password fields."""
    for selector in (
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Save")',
        'button:has-text("Update")',
        'button:has-text("Change")',
    ):
        loc = page.locator(selector).first
        try:
            if loc.is_visible(timeout=1000):
                loc.click(timeout=5000)
                return True
        except Exception:
            continue
    return False


def run_generic(page, current_password, new_password):
    """Fill a standard change-password form when no recipe exists."""
    fields = find_password_fields(page)
    if not fields:
        return False
    fields["current"].fill(current_password, timeout=8000)
    fields["new"].fill(new_password, timeout=8000)
    if fields["confirm"]:
        fields["confirm"].fill(new_password, timeout=8000)
    return submit_password_form(page)


def pause_for_2fa(recipe):
    if recipe and recipe.get("requires_2fa"):
        input("    Complete 2FA on the page, then press Enter to continue... ")
        return
    # Heuristic: if URL or page content suggests a challenge, pause anyway.
    # Caller can pass None recipe; generic pause handled in run_assist.


def run_assist(
    *,
    url,
    domain,
    current_password,
    recipe_dirs,
    profile_dir=None,
    headless=False,
):
    """Open url and attempt an assisted password change.

    Returns (status, new_password) where status is one of:
        "ok"       — form submitted; user should confirm Dashlane saved it
        "fallback" — could not automate; caller should use manual flow
        "error"    — unexpected failure
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("    assist unavailable: install optional deps with "
              "`pip install -r requirements-optional.txt`", file=sys.stderr)
        return "fallback", None

    new_password = generate_password()
    recipe = load_recipe(domain, recipe_dirs)

    try:
        with sync_playwright() as p:
            browser = None
            if profile_dir:
                context = p.chromium.launch_persistent_context(
                    str(profile_dir),
                    headless=headless,
                    channel="chrome",
                )
                page = context.pages[0] if context.pages else context.new_page()
            else:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context()
                page = context.new_page()

            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)

            if recipe:
                run_recipe(page, recipe, current_password, new_password)
            elif not run_generic(page, current_password, new_password):
                context.close()
                if browser:
                    browser.close()
                return "fallback", None

            page.wait_for_timeout(2000)
            if recipe and recipe.get("requires_2fa"):
                pause_for_2fa(recipe)
            elif any(token in page.url.lower() for token in ("challenge", "verify", "2fa", "mfa")):
                input("    Possible 2FA/verification step — complete it, then press Enter... ")

            context.close()
            if browser:
                browser.close()
            return "ok", new_password
    except Exception as e:
        print(f"    assist error ({e.__class__.__name__}): {e}", file=sys.stderr)
        return "fallback", None
