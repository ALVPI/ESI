"""
test_metrics.py — Manual verification script for all Prometheus metrics.

This script tests every metric defined in metrics.py by simulating:
    - Legitimate traffic (client_credentials, authorization_code, refresh_token)
    - Brute force attacks (wrong credentials, wrong passwords)
    - Security attacks (token replay, auth code reuse)
    - Parallel requests (to trigger requests_in_progress)

Usage:
    uv run python test_metrics.py

Requirements:
    - app.py must be running on localhost:5001
    - seed.py must have been executed previously

Author: ESI Practice 2
"""

import requests
import threading
import time

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:5001"
METRICS_URL = f"{BASE_URL}/metrics"

# Credentials from seed.py
SERVICE_ACCOUNT_ID     = "service-account"
SERVICE_ACCOUNT_SECRET = "6Q6TZj_hKy4xBnZhgBuIwdJ6lSaQbF-9XWR9S_BHthk"
WEB_APP_ID             = "web-app"
WEB_APP_SECRET         = "Vh_lxCQeixB4jAraZRxcd0kmP43YOeyXAn7IVomdMmc"

# Valid test users (defined in app.py)
VALID_USERNAME = "testuser"
VALID_PASSWORD = "testpass"


# ── Helpers ──────────────────────────────────────────────────────────────────

def separator(title: str) -> None:
    """Print a section separator."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_metric(metric_name: str) -> None:
    """Query /metrics and print the value of a specific metric."""
    response = requests.get(METRICS_URL)
    lines = [
        line for line in response.text.splitlines()
        if metric_name in line and not line.startswith("#")
    ]
    if lines:
        print(f"  ✓ {metric_name}:")
        for line in lines:
            print(f"      {line}")
    else:
        print(f"  ✗ {metric_name}: no value yet (metric not incremented)")


def wait_for_prometheus(seconds: int = 2) -> None:
    """Wait for Prometheus to scrape the latest metrics."""
    print(f"  ⏳ Waiting {seconds}s for Prometheus to scrape...")
    time.sleep(seconds)


# ── Test blocks ──────────────────────────────────────────────────────────────

def test_client_credentials_valid() -> str | None:
    """
    Tests a valid client_credentials request.
    Expected metrics incremented:
        - auth_flows_started{grant_type="client_credentials"}
        - auth_flows_success{grant_type="client_credentials"}
        - access_tokens_issued{grant_type="client_credentials"}
        - tokens_issued{token_type="access", grant_type="client_credentials"}
        - active_tokens{token_type="access"}
        - http_requests{method="POST", endpoint="/token", status_code="200"}
    Returns the access_token for later use.
    """
    separator("TEST 1 — Valid client_credentials request")
    print("  Sending correct credentials to /token...")

    response = requests.post(f"{BASE_URL}/token", data={
        "grant_type":    "client_credentials",
        "client_id":     SERVICE_ACCOUNT_ID,
        "client_secret": SERVICE_ACCOUNT_SECRET,
        "scope":         "read"
    })

    print(f"  Response status: {response.status_code}")
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"  Access token received: {token[:20]}...")
        print("  Expected metrics incremented: auth_flows_started, auth_flows_success,")
        print("  access_tokens_issued, tokens_issued, active_tokens, http_requests (200)")
        wait_for_prometheus()
        check_metric("oauth2_auth_flows_started_total")
        check_metric("oauth2_auth_flows_success_total")
        check_metric("oauth2_active_tokens")
        return token
    else:
        print(f"  ERROR: expected 200 but got {response.status_code}")
        return None


def test_client_credentials_invalid() -> None:
    """
    Tests a client_credentials request with wrong secret.
    Expected metrics incremented:
        - auth_flows_started{grant_type="client_credentials"}
        - auth_flows_failed{grant_type="client_credentials"}
        - brute_force_attempts{client_id="service-account"}
        - http_requests{method="POST", endpoint="/token", status_code="401"}
    """
    separator("TEST 2 — Brute force M2M attack (wrong secret)")
    print("  Sending wrong secret to /token 5 times...")

    for i in range(5):
        response = requests.post(f"{BASE_URL}/token", data={
            "grant_type":    "client_credentials",
            "client_id":     SERVICE_ACCOUNT_ID,
            "client_secret": f"wrong_secret_{i}"
        })
        print(f"  Attempt {i+1}: status {response.status_code} (expected 401)")

    print("  Expected metrics incremented: auth_flows_failed x5, brute_force_attempts x5")
    wait_for_prometheus()
    check_metric("oauth2_auth_flows_failed_total")
    check_metric("oauth2_brute_force_attempts_total")
    check_metric("oauth2_http_requests_total")


def test_user_login_invalid() -> None:
    """
    Tests failed user login attempts via /authorize.
    Expected metrics incremented:
        - user_auth_failed{username="attacker", client_id="web-app"}
        - http_requests{method="POST", endpoint="/authorize", status_code="401"}
    """
    separator("TEST 3 — Brute force web attack (wrong password)")
    print("  Sending wrong passwords to /authorize 5 times...")

    for i in range(5):
        response = requests.post(f"{BASE_URL}/authorize", data={
            "client_id":     WEB_APP_ID,
            "redirect_uri":  "http://localhost:8080/callback",
            "response_type": "code",
            "scope":         "read",
            "state":         "test123",
            "action":        "approve",
            "username":      "attacker",
            "password":      f"wrong_password_{i}"
        })
        print(f"  Attempt {i+1}: status {response.status_code} (expected 401)")

    print("  Expected metrics incremented: user_auth_failed x5")
    wait_for_prometheus()
    check_metric("oauth2_user_auth_failed_total")


def test_authorization_code_flow() -> tuple[str | None, str | None]:
    """
    Tests the complete authorization_code flow.
    Step 1: Login with correct credentials to get an auth code.
    Step 2: Exchange the auth code for tokens.
    Expected metrics incremented:
        - auth_flows_success{grant_type="authorization_code"}
        - access_tokens_issued{grant_type="authorization_code"}
        - refresh_tokens_issued{grant_type="authorization_code"}
        - pending_auth_codes (inc then dec)
        - active_tokens{token_type="access"}
        - active_tokens{token_type="refresh"}
    Returns (access_token, refresh_token) for later use.
    """
    separator("TEST 4 — Valid authorization_code flow")

    # Step 1: Login to get the auth code
    print("  Step 1: Logging in to get authorization code...")
    response = requests.post(f"{BASE_URL}/authorize",
        data={
            "client_id":     WEB_APP_ID,
            "redirect_uri":  "http://localhost:8080/callback",
            "response_type": "code",
            "scope":         "read",
            "state":         "test123",
            "action":        "approve",
            "username":      VALID_USERNAME,
            "password":      VALID_PASSWORD
        },
        allow_redirects=False  # we need to capture the redirect to extract the code
    )

    print(f"  Step 1 status: {response.status_code} (expected 302)")

    if response.status_code != 302:
        print(f"  ERROR: expected 302 but got {response.status_code}")
        return None, None

    # Extract the auth code from the redirect URL
    location = response.headers.get("Location", "")
    print(f"  Redirect URL: {location}")

    if "code=" not in location:
        print("  ERROR: no code found in redirect URL")
        return None, None

    auth_code = location.split("code=")[1].split("&")[0]
    print(f"  Authorization code obtained: {auth_code[:20]}...")

    # Step 2: Exchange the auth code for tokens
    print("  Step 2: Exchanging auth code for tokens...")
    response = requests.post(f"{BASE_URL}/token", data={
        "grant_type":   "authorization_code",
        "code":          auth_code,
        "redirect_uri":  "http://localhost:8080/callback",
        "client_id":     WEB_APP_ID,
        "client_secret": WEB_APP_SECRET
    })

    print(f"  Step 2 status: {response.status_code} (expected 200)")

    if response.status_code == 200:
        data = response.json()
        access_token  = data.get("access_token")
        refresh_token = data.get("refresh_token")
        print(f"  Access token:  {access_token[:20]}...")
        print(f"  Refresh token: {refresh_token[:20]}...")
        print("  Expected metrics: auth_flows_success, access_tokens_issued,")
        print("  refresh_tokens_issued, active_tokens (access + refresh)")
        wait_for_prometheus()
        check_metric("oauth2_auth_flows_success_total")
        check_metric("oauth2_refresh_tokens_issued_total")
        check_metric("oauth2_pending_auth_codes")
        return access_token, refresh_token
    else:
        print(f"  ERROR: {response.status_code} — {response.text}")
        return None, None


def test_refresh_token_flow(refresh_token: str) -> str | None:
    """
    Tests the refresh_token flow.
    Expected metrics incremented:
        - auth_flows_success{grant_type="refresh_token"}
        - tokens_revoked{token_type="refresh"} (old token revoked)
        - tokens_revoked{token_type="access"} (old access token revoked)
        - active_tokens decremented then incremented
    Returns the new refresh_token for later use.
    """
    separator("TEST 5 — Valid refresh_token flow")
    print(f"  Using refresh token: {refresh_token[:20]}...")

    response = requests.post(f"{BASE_URL}/token", data={
        "grant_type":    "refresh_token",
        "refresh_token":  refresh_token,
        "client_id":      WEB_APP_ID,
        "client_secret":  WEB_APP_SECRET
    })

    print(f"  Response status: {response.status_code} (expected 200)")

    if response.status_code == 200:
        data = response.json()
        new_refresh = data.get("refresh_token")
        print(f"  New refresh token: {new_refresh[:20]}...")
        print("  Old tokens should be revoked (token rotation)")
        print("  Expected metrics: tokens_revoked x2, active_tokens dec+inc")
        wait_for_prometheus()
        check_metric("oauth2_tokens_revoked_total")
        check_metric("oauth2_auth_flows_success_total")
        return new_refresh
    else:
        print(f"  ERROR: {response.status_code} — {response.text}")
        return None


def test_revoked_token_replay(refresh_token: str) -> None:
    """
    Tests using a revoked refresh token (token replay attack).
    The token passed here should already be revoked from test 5.
    Expected metrics incremented:
        - revoked_token_usage
        - auth_flows_failed{grant_type="refresh_token"}
    """
    separator("TEST 6 — Token replay attack (revoked token reuse)")
    print(f"  Trying to reuse already-revoked token: {refresh_token[:20]}...")

    response = requests.post(f"{BASE_URL}/token", data={
        "grant_type":    "refresh_token",
        "refresh_token":  refresh_token,
        "client_id":      WEB_APP_ID,
        "client_secret":  WEB_APP_SECRET
    })

    print(f"  Response status: {response.status_code} (expected 400)")
    if response.status_code == 400:
        print("  Server correctly rejected the revoked token")
        print("  Expected metrics: revoked_token_usage incremented")
    else:
        print(f"  Unexpected status: {response.status_code}")

    wait_for_prometheus()
    check_metric("oauth2_revoked_token_usage_total")


def test_auth_code_reuse(auth_code: str) -> None:
    """
    Tests reusing an already-consumed authorization code.
    Expected metrics incremented:
        - auth_code_reuse
        - auth_flows_failed{grant_type="authorization_code"}
    """
    separator("TEST 7 — Auth code replay attack (code reuse)")
    print(f"  Trying to reuse already-used auth code: {auth_code[:20]}...")

    response = requests.post(f"{BASE_URL}/token", data={
        "grant_type":   "authorization_code",
        "code":          auth_code,
        "redirect_uri":  "http://localhost:8080/callback",
        "client_id":     WEB_APP_ID,
        "client_secret": WEB_APP_SECRET
    })

    print(f"  Response status: {response.status_code} (expected 400)")
    if response.status_code == 400:
        print("  Server correctly rejected the reused code")
        print("  Expected metrics: auth_code_reuse incremented")
    else:
        print(f"  Unexpected status: {response.status_code}")

    wait_for_prometheus()
    check_metric("oauth2_auth_code_reuse_total")


def test_parallel_requests() -> None:
    """
    Sends 20 parallel requests to trigger requests_in_progress > 0.
    Expected metrics visible during execution:
        - requests_in_progress{endpoint="/token"} > 0
    Note: this gauge goes up and down so fast it may still show 0
    after the requests complete. Check Grafana for the spike.
    """
    separator("TEST 8 — Parallel requests (requests_in_progress)")
    print("  Launching 20 parallel requests to /token...")

    results = []

    def make_request():
        response = requests.post(f"{BASE_URL}/token", data={
            "grant_type":    "client_credentials",
            "client_id":     SERVICE_ACCOUNT_ID,
            "client_secret": SERVICE_ACCOUNT_SECRET,
        })
        results.append(response.status_code)

    # Launch all threads simultaneously
    threads = [threading.Thread(target=make_request) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    success = results.count(200)
    failed  = len(results) - success
    print(f"  Completed: {success} successful, {failed} failed")
    print("  Check Grafana for requests_in_progress spike during execution")
    print("  Check request_duration histogram for response time distribution")
    wait_for_prometheus()
    check_metric("oauth2_requests_in_progress")
    check_metric("oauth2_request_duration_seconds_count")


def test_expired_token() -> None:
    """
    Tests using a completely fake/non-existent refresh token.
    This simulates what happens when someone tries an expired or
    completely fabricated token.
    Expected metrics incremented:
        - auth_flows_failed{grant_type="refresh_token"}
        - expired_token_usage (if the token exists but is expired)
        Note: for a fake token the server returns None from validate_refresh_token
        so expired_token_usage may not increment (token not found vs expired)
    """
    separator("TEST 9 — Expired/fake token usage")
    print("  Trying to use a completely fake refresh token...")

    response = requests.post(f"{BASE_URL}/token", data={
        "grant_type":    "refresh_token",
        "refresh_token": "this_is_a_completely_fake_token_that_does_not_exist",
        "client_id":     WEB_APP_ID,
        "client_secret": WEB_APP_SECRET
    })

    print(f"  Response status: {response.status_code} (expected 400)")
    wait_for_prometheus()
    check_metric("oauth2_expired_token_usage_total")
    check_metric("oauth2_auth_flows_failed_total")


def print_full_metrics_summary() -> None:
    """Print all oauth2 metrics with their current values."""
    separator("FULL METRICS SUMMARY")
    print("  All oauth2 metrics current values:\n")

    response = requests.get(METRICS_URL)
    lines = [
        line for line in response.text.splitlines()
        if "oauth2" in line and not line.startswith("#")
    ]

    if lines:
        for line in lines:
            print(f"  {line}")
    else:
        print("  No oauth2 metrics found. Is the app running?")

def test_client_enumeration() -> None:
    separator("TEST 10 — Client enumeration attack")
    print("  Trying to access with unknown client_ids...")

    fake_clients = [
        "admin", "root", "test", "app", "api",
        "mobile", "backend", "service", "user", "guest"
    ]

    for fake_client in fake_clients:
        response = requests.post(f"{BASE_URL}/token", data={
            "grant_type":    "client_credentials",
            "client_id":     fake_client,
            "client_secret": "any_secret"
        })
        print(f"  client_id={fake_client}: status {response.status_code} (expected 401)")

    print("\n  Expected: unknown_client_attempts incremented 10 times")
    wait_for_prometheus()
    check_metric("oauth2_unknown_client_attempts_total")

def test_credential_stuffing() -> None:
    separator("TEST 11 — Credential stuffing attack")
    print("  Trying leaked credentials with different usernames...\n")

    leaked_credentials = [
        ("john.doe",       "password123"),
        ("jane.smith",     "qwerty"),
        ("carlos.garcia",  "123456"),
        ("maria.lopez",    "letmein"),
        ("pedro.martinez", "welcome"),
        ("ana.rodriguez",  "monkey"),
        ("luis.hernandez", "dragon"),
        ("sofia.gonzalez", "master"),
        ]

    for username, password in leaked_credentials:
        response = requests.post(f"{BASE_URL}/authorize", data={
            "client_id":     WEB_APP_ID,
            "redirect_uri":  "http://localhost:8080/callback",
            "response_type": "code",
            "scope":         "read",
            "state":         "test123",
            "action":        "approve",
            "username":      username,
            "password":      password
        })
    print(f"  username={username}: status {response.status_code} (expected 401)")

    print("\n  Expected: user_auth_failed x8 con usernames distintos")
    print("  Expected: unique_failed_usernames_active sube a 8+")
    wait_for_prometheus()
    check_metric("oauth2_user_auth_failed_total")
    check_metric("oauth2_unique_failed_usernames_active")

def test_token_harvesting() -> None:
    separator("TEST 12 — Token harvesting attack")
    print("  Requesting 10 tokens without revoking any...\n")

    print("  active_tokens BEFORE harvesting:")
    check_metric("oauth2_active_tokens")
    print()

    for i in range(10):
        response = requests.post(f"{BASE_URL}/token", data={
            "grant_type":    "client_credentials",
            "client_id":     SERVICE_ACCOUNT_ID,
            "client_secret": SERVICE_ACCOUNT_SECRET,
            "scope":         "read"
        })
        if response.status_code == 200:
            print(f"  Token {i+1} acquired and stored (not revoked)")
        else:
            print(f"  Token {i+1} FAILED: {response.status_code}")

    print("\n  active_tokens AFTER harvesting:")
    wait_for_prometheus()
    check_metric("oauth2_active_tokens")
    check_metric("oauth2_tokens_revoked_total")
# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  OAuth2 Metrics Verification Script")
    print("  Make sure app.py is running on localhost:5001")
    print("="*60)

    # Verify the app is reachable before starting
    try:
        requests.get(METRICS_URL, timeout=3)
        print("\n  ✓ App is reachable at localhost:5001")
    except requests.exceptions.ConnectionError:
        print("\n  ✗ ERROR: Cannot connect to localhost:5001")
        print("  Make sure app.py is running with: uv run python app.py")
        return

    # Run all tests in order
    # Test 1 — valid client_credentials
    test_client_credentials_valid()

    # Test 2 — brute force M2M
    test_client_credentials_invalid()

    # Test 3 — brute force web login
    test_user_login_invalid()

    # Test 4 — full authorization_code flow
    # We need to save the auth code before it gets consumed
    # so we run the login step manually here to save it
    separator("TEST 4 — Valid authorization_code flow")
    print("  Step 1: Logging in to get authorization code...")
    response = requests.post(f"{BASE_URL}/authorize",
        data={
            "client_id":     WEB_APP_ID,
            "redirect_uri":  "http://localhost:8080/callback",
            "response_type": "code",
            "scope":         "read",
            "state":         "test123",
            "action":        "approve",
            "username":      VALID_USERNAME,
            "password":      VALID_PASSWORD
        },
        allow_redirects=False
    )

    auth_code     = None
    access_token  = None
    refresh_token = None

    if response.status_code == 302:
        location  = response.headers.get("Location", "")
        auth_code = location.split("code=")[1].split("&")[0]
        print(f"  Authorization code obtained: {auth_code[:20]}...")

        # Exchange the code for tokens
        print("  Step 2: Exchanging auth code for tokens...")
        response2 = requests.post(f"{BASE_URL}/token", data={
            "grant_type":   "authorization_code",
            "code":          auth_code,
            "redirect_uri":  "http://localhost:8080/callback",
            "client_id":     WEB_APP_ID,
            "client_secret": WEB_APP_SECRET
        })

        if response2.status_code == 200:
            data          = response2.json()
            access_token  = data.get("access_token")
            refresh_token = data.get("refresh_token")
            print(f"  Access token:  {access_token[:20]}...")
            print(f"  Refresh token: {refresh_token[:20]}...")
            wait_for_prometheus()
            check_metric("oauth2_auth_flows_success_total")
            check_metric("oauth2_refresh_tokens_issued_total")
            check_metric("oauth2_pending_auth_codes")

    # Test 5 — refresh_token flow (uses the refresh_token from test 4)
    new_refresh_token = None
    if refresh_token:
        new_refresh_token = test_refresh_token_flow(refresh_token)

    # Test 6 — token replay with the OLD refresh_token (now revoked)
    if refresh_token:
        test_revoked_token_replay(refresh_token)

    # Test 7 — auth code reuse with the code from test 4 (now consumed)
    if auth_code:
        test_auth_code_reuse(auth_code)

    # Test 8 — parallel requests
    test_parallel_requests()

    # Test 9 — fake token
    test_expired_token()

    # Test 10 - usuarios this_is_a_completely_fake_token_that_does_not_exist
    test_client_enumeration()
    test_credential_stuffing()
    test_token_harvesting()
    # Final summary
    print_full_metrics_summary()

    print("\n" + "="*60)
    print("  All tests completed.")
    print("  Check Grafana at http://YOUR-VM-IP:3000 for visual results")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
