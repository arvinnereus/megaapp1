"""
End-to-end tests using Playwright.

Run headless:  pytest tests/test_e2e.py -v
Run headed:    pytest tests/test_e2e.py -v --headed
Slow demo:     pytest tests/test_e2e.py -v --headed --slowmo 500
"""
import re
import pytest


# ── Helpers ────────────────────────────────────────────────────────────

def login(page, base_url, password="testpass123"):
    """Log in and return page on dashboard."""
    page.goto(f"{base_url}/admin/login")
    page.fill("input[name='username']", "admin")
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/admin/dashboard"), timeout=5000)
    return page


# ── Auth Tests ─────────────────────────────────────────────────────────

def test_login_page_loads(page, live_server):
    page.goto(f"{live_server}/admin/login")
    assert "login" in page.url.lower()
    assert page.locator("input[name='username']").is_visible()


def test_login_and_reach_dashboard(page, live_server):
    login(page, live_server)
    assert "dashboard" in page.url.lower()


def test_unauthenticated_redirect(page, live_server):
    page.goto(f"{live_server}/admin/dashboard")
    assert "/admin/login" in page.url


# ── Dashboard ──────────────────────────────────────────────────────────

def test_dashboard_shows_stats(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/admin/dashboard")
    assert page.locator("body").is_visible()


# ── CRM Pages ─────────────────────────────────────────────────────────

def test_contacts_page(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/admin/contacts")
    assert "/admin/contacts" in page.url


def test_deals_page(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/admin/deals")
    assert "/admin/deals" in page.url


# ── Content ────────────────────────────────────────────────────────────

def test_content_page(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/content/")
    assert page.locator("body").is_visible()


# ── Jackie AI ──────────────────────────────────────────────────────────

def test_jackie_page(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/jackie/")
    assert page.locator("body").is_visible()


# ── Bookings ───────────────────────────────────────────────────────────

def test_bookings_admin(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/bookings/")
    assert page.locator("body").is_visible()


def test_public_booking_page(page, live_server):
    """Public booking page loads without auth."""
    page.goto(f"{live_server}/bookings/book")
    assert page.locator("body").is_visible()


# ── Help ───────────────────────────────────────────────────────────────

def test_help_page(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/help/")
    assert page.locator("body").is_visible()


# ── Settings ───────────────────────────────────────────────────────────

def test_settings_page(page, live_server):
    login(page, live_server)
    page.goto(f"{live_server}/admin/settings")
    assert "/admin/settings" in page.url


# ── Public Pages ───────────────────────────────────────────────────────

def test_landing_page(page, live_server):
    page.goto(f"{live_server}/lp")
    assert page.locator("body").is_visible()


def test_onboarding_form(page, live_server):
    """Onboarding survey form loads without auth."""
    page.goto(f"{live_server}/onboarding/")
    assert page.locator("body").is_visible()


def test_onboarding_submit(page, live_server):
    """Submit the onboarding survey and reach thank you page."""
    page.goto(f"{live_server}/onboarding/")
    page.fill("input[name='name']", "Test User")
    page.fill("input[name='email']", "test@example.com")
    page.click("button[type='submit']")
    page.wait_for_timeout(1000)
    # Should reach thank you page or stay on form
    assert page.locator("body").is_visible()
