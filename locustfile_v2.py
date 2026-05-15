from locust import HttpUser, task, between


class OAuth2LoadTest(HttpUser):
    """
    Virtual Locust user for testing the OAuth2 server.

    This user simulates both legitimate traffic and controlled malicious
    traffic to observe the application behavior and its Prometheus metrics.

    Metrics covered:
        - auth_flows_started / auth_flows_success / auth_flows_failed
        - tokens_issued / access_tokens_issued / refresh_tokens_issued
        - http_requests / http_requests_token / http_requests_authorize / http_requests_admin
        - requests_in_progress / request_duration
        - active_tokens / tokens_revoked
        - pending_auth_codes
        - auth_code_reuse
        - revoked_token_usage
        - expired_token_usage (indirectly via invalid refresh token)
        - brute_force_attempts
        - user_auth_failed
        - active_clients

    Traffic distribution:
        Legitimate:  6+3+2 = 11/19 = 58% of traffic
        Malicious:   2+2+1+1+1 = 7/19 = 37% of traffic
        Monitoring:  1/19 = 5% of traffic
    """

    # Each virtual user waits between 3 and 7 seconds before the next task
    # This simulates real user think time between actions
    wait_time = between(3, 7)

    # ── Client credentials (M2M flow) ─────────────────────────────────────
    VALID_CLIENT_ID     = "service-account"
    VALID_CLIENT_SECRET = "6Q6TZj_hKy4xBnZhgBuIwdJ6lSaQbF-9XWR9S_BHthk"

    # ── Web application client (authorization_code flow) ──────────────────
    WEB_CLIENT_ID     = "web-app"
    WEB_CLIENT_SECRET = "Vh_lxCQeixB4jAraZRxcd0kmP43YOeyXAn7IVomdMmc"
    WEB_REDIRECT_URI  = "http://localhost:8080/callback"

    # ── Valid test users defined in app.py ────────────────────────────────
    VALID_USERNAME = "testuser"
    VALID_PASSWORD = "testpass"

    # =========================================================================
    # LEGITIMATE TRAFFIC
    # =========================================================================
    @task(6)
    def valid_client_credentials(self):
        with self.client.post("/token", data={
            "grant_type":    "client_credentials",
            "client_id":     self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
            "scope":         "read"
        }, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Valid client_credentials failed with {response.status_code}")

    @task(3)
    def valid_authorization_code_flow(self):
        """
        Complete authorization_code flow: load login page -> login -> get code -> exchange for tokens.
        Without this task, pending_auth_codes would grow indefinitely during
        load tests because codes would be issued but never consumed.

        Metrics fired:
            - auth_flows_started / auth_flows_success {grant_type="authorization_code"}
            - tokens_issued{token_type="access"/"refresh", grant_type="authorization_code"}
            - access_tokens_issued / refresh_tokens_issued {grant_type="authorization_code"}
            - active_tokens{token_type="access"} / active_tokens{token_type="refresh"}
            - pending_auth_codes (incremented then decremented)
            - http_requests / http_requests_authorize / http_requests_token with status 200

        Probability: 16% (3 of 19)
        """
        # Step 1: GET /authorize to simulate a real user loading the login HTML page
        with self.client.get("/authorize", params={
            "client_id":     self.WEB_CLIENT_ID,
            "redirect_uri":  self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope":         "read",
            "state":         "locust-test"
        }, catch_response=True) as get_response:

            if get_response.status_code != 200:
                get_response.failure(f"GET /authorize failed with {get_response.status_code}")
                return
            get_response.success()

        # Step 2: POST /authorize with valid credentials -> get the auth code
        with self.client.post("/authorize", data={
            "client_id":     self.WEB_CLIENT_ID,
            "redirect_uri":  self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope":         "read",
            "state":         "locust-test",
            "action":        "approve",
            "username":      self.VALID_USERNAME,
            "password":      self.VALID_PASSWORD
        }, catch_response=True, allow_redirects=False) as auth_response:

            # Server returns 302 with the code in the redirect URL
            if auth_response.status_code not in (200, 302):
                auth_response.failure(
                    f"Valid authorize failed with {auth_response.status_code}"
                )
                return
            # Extract the code from the Location header
            code = None
            location = auth_response.headers.get("Location", "")
            if "code=" in location:
                code = location.split("code=")[1].split("&")[0]

            if not code:
                auth_response.success()
                return
            auth_response.success()
        # Step 3: POST /token exchanging the code -> get access + refresh token
        with self.client.post("/token", data={
            "grant_type":   "authorization_code",
            "client_id":     self.WEB_CLIENT_ID,
            "client_secret": self.WEB_CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  self.WEB_REDIRECT_URI
        }, catch_response=True) as token_response:
            if token_response.status_code != 200:
                token_response.failure(
                    f"Code exchange failed with {token_response.status_code}"
                )
                return
            token_response.success()
    @task(2)
    def valid_refresh_token_flow(self):
        """
        Complete refresh_token flow: get tokens via authorization_code,
        then renew them using the refresh token.
        Without this task, tokens_revoked and refresh_tokens_issued
        would always be zero during load tests.

        Metrics fired:
            - auth_flows_started / auth_flows_success {grant_type="refresh_token"}
            - tokens_issued / access_tokens_issued / refresh_tokens_issued
            - active_tokens (new tokens activated)
            - tokens_revoked (old refresh token revoked via token rotation)
            - http_requests_token with status 200

        Probability: 11% (2 of 19)
        """
        # Step 1: Get a valid pair of tokens via authorization_code
        code = self._get_authorization_code()
        if not code:
            return

        with self.client.post("/token", data={
            "grant_type":   "authorization_code",
            "client_id":     self.WEB_CLIENT_ID,
            "client_secret": self.WEB_CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  self.WEB_REDIRECT_URI
        }, catch_response=True) as token_response:

            if token_response.status_code != 200:
                token_response.failure(
                    f"Token acquisition for refresh failed with {token_response.status_code}"
                )
                return

            try:
                tokens        = token_response.json()
                refresh_token = tokens.get("refresh_token")
            except Exception:
                token_response.failure("Could not parse token response")
                return

            token_response.success()

        if not refresh_token:
            return

        # Step 2: Renew tokens using the refresh token
        with self.client.post("/token", data={
            "grant_type":    "refresh_token",
            "client_id":      self.WEB_CLIENT_ID,
            "client_secret":  self.WEB_CLIENT_SECRET,
            "refresh_token":  refresh_token
        }, catch_response=True) as refresh_response:

            if refresh_response.status_code != 200:
                refresh_response.failure(
                    f"Valid refresh_token failed with {refresh_response.status_code}"
                )
                return

            refresh_response.success()

    # =========================================================================
    # MALICIOUS TRAFFIC / ATTACK SIMULATION
    # =========================================================================

    @task(2)
    def brute_force_api(self):
        """
        M2M brute force attack: tries to guess the client secret.
        The server should defend correctly returning 401.

        Metrics fired:
            - auth_flows_started / auth_flows_failed {grant_type="client_credentials"}
            - brute_force_attempts{client_id="service-account"}
            - http_requests / http_requests_token with status 401

        Probability: 11% (2 of 19)
        """
        with self.client.post("/token", data={
            "grant_type":    "client_credentials",
            "client_id":     self.VALID_CLIENT_ID,
            "client_secret": "wrong_secret_attempt"
        }, catch_response=True) as response:

            # 401 is the expected behavior, server defended correctly
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Expected 401 but got {response.status_code}")

    @task(2)
    def brute_force_user_login(self):
        """
        Web brute force attack: tries to guess a user password.
        The action field is required for the app to reach the credential
        check. Without it the app fails before checking the password
        and user_auth_failed would never be incremented.

        Metrics fired:
            - user_auth_failed{username=..., client_id="web-app"}
            - http_requests / http_requests_authorize with status 401

        Probability: 11% (2 of 19)
        """
        with self.client.post("/authorize", data={
            "client_id":     self.WEB_CLIENT_ID,
            "redirect_uri":  self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope":         "read",
            "state":         "locust-test",
            "action":        "approve",   # required for app to reach login check
            "username":      self.VALID_USERNAME,
            "password":      "wrong_password_attempt"
        }, catch_response=True) as response:

            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Expected 401 but got {response.status_code}")

    @task(1)
    def auth_code_replay_attack(self):
        """
        Authorization code replay attack: tries to use the same auth code twice.
        The first exchange should succeed (200), the second should fail (400)
        because the code is already marked as used in the database.
        This is more realistic than using an access token as refresh token.

        Metrics fired:
            - pending_auth_codes (incremented then decremented on first exchange)
            - auth_code_reuse (incremented on second exchange attempt)
            - http_requests_token with status 200 then 400

        Probability: 5% (1 of 19)
        """
        # Get a valid auth code
        code = self._get_authorization_code()
        if not code:
            return

        # First exchange: should succeed (200)
        with self.client.post("/token", data={
            "grant_type":   "authorization_code",
            "client_id":     self.WEB_CLIENT_ID,
            "client_secret": self.WEB_CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  self.WEB_REDIRECT_URI
        }, catch_response=True) as first_response:

            if first_response.status_code != 200:
                first_response.failure(
                    f"First exchange failed unexpectedly with {first_response.status_code}"
                )
                return

            first_response.success()

        # Second exchange of the same code: should fail (400)
        # This fires auth_code_reuse in models.py -> consume_authorization_code()
        with self.client.post("/token", data={
            "grant_type":   "authorization_code",
            "client_id":     self.WEB_CLIENT_ID,
            "client_secret": self.WEB_CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  self.WEB_REDIRECT_URI
        }, catch_response=True) as second_response:

            if second_response.status_code in (400, 401):
                second_response.success()
            else:
                second_response.failure(
                    f"Expected 400/401 on code replay but got {second_response.status_code}"
                )

    @task(1)
    def revoked_token_replay_attack(self):
        """
        Token replay attack: gets a valid refresh token, rotates it
        (which revokes the old one) and then tries to use the revoked token.
        This is more realistic than using an access token as refresh token
        because it simulates a real token theft scenario.

        Metrics fired:
            - tokens_revoked{token_type="refresh"} / tokens_revoked{token_type="access"}
            - active_tokens (decremented on revocation)
            - revoked_token_usage (on attempt to use the revoked token)
            - http_requests_token with status 400

        Probability: 5% (1 of 19)
        """
        # Step 1: Get valid tokens
        code = self._get_authorization_code()
        if not code:
            return

        refresh_token = None
        with self.client.post("/token", data={
            "grant_type":   "authorization_code",
            "client_id":     self.WEB_CLIENT_ID,
            "client_secret": self.WEB_CLIENT_SECRET,
            "code":          code,
            "redirect_uri":  self.WEB_REDIRECT_URI
        }, catch_response=True) as token_response:

            if token_response.status_code != 200:
                token_response.failure(
                    f"Token acquisition failed with {token_response.status_code}"
                )
                return

            try:
                tokens        = token_response.json()
                refresh_token = tokens.get("refresh_token")
            except Exception:
                token_response.failure("Could not parse token response")
                return

            token_response.success()

        if not refresh_token:
            return

        # Step 2: Rotate the token (this revokes the old refresh token)
        with self.client.post("/token", data={
            "grant_type":    "refresh_token",
            "client_id":      self.WEB_CLIENT_ID,
            "client_secret":  self.WEB_CLIENT_SECRET,
            "refresh_token":  refresh_token
        }, catch_response=True) as rotate_response:

            if rotate_response.status_code != 200:
                rotate_response.success()
                return

            rotate_response.success()

        # Step 3: Try to use the ORIGINAL refresh token (now revoked)
        # This fires revoked_token_usage in models.py -> validate_refresh_token()
        with self.client.post("/token", data={
            "grant_type":    "refresh_token",
            "client_id":      self.WEB_CLIENT_ID,
            "client_secret":  self.WEB_CLIENT_SECRET,
            "refresh_token":  refresh_token
        }, catch_response=True) as revoked_response:

            if revoked_response.status_code in (400, 401):
                revoked_response.success()
            else:
                revoked_response.failure(
                    f"Expected 400/401 on revoked token but got {revoked_response.status_code}"
                )

    @task(1)
    def invalid_refresh_token(self):
        """
        Tries to use a completely fake refresh token.
        Tests the expired/invalid token error path.

        Metrics fired:
            - auth_flows_started / auth_flows_failed {grant_type="refresh_token"}
            - http_requests / http_requests_token with status 400

        Probability: 5% (1 of 19)
        """
        with self.client.post("/token", data={
            "grant_type":    "refresh_token",
            "client_id":      self.WEB_CLIENT_ID,
            "client_secret":  self.WEB_CLIENT_SECRET,
            "refresh_token":  "completely_fake_refresh_token_xyz123"
        }, catch_response=True) as response:

            if response.status_code == 400:
                response.success()
            else:
                response.failure(
                    f"Expected 400 for fake refresh token but got {response.status_code}"
                )

    # =========================================================================
    # MONITORING ENDPOINTS
    # =========================================================================

    @task(1)
    def list_admin_clients(self):
        """
        Queries the list of registered clients.
        Generates traffic on the admin endpoint metrics.

        Metrics fired:
            - http_requests / http_requests_admin with status 200
            - requests_in_progress / request_duration for /admin/clients

        Probability: 5% (1 of 19)
        """
        with self.client.get("/admin/clients", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"/admin/clients GET failed with {response.status_code}")

    # =========================================================================
    # PRIVATE HELPER METHOD
    # =========================================================================

    def _get_authorization_code(self) -> str | None:
        """
        Performs the authorization step (POST /authorize) with valid credentials
        and returns the auth code extracted from the Location header.
        Returns None if the code could not be obtained.

        This helper is used by multiple tasks to avoid repeating the login
        logic in each one (DRY principle).

        Note: the action field is required for the app to reach the
        credential check. Without it the app fails before authenticating
        the user and no auth code is issued.
        """
        with self.client.post("/authorize", data={
            "client_id":     self.WEB_CLIENT_ID,
            "redirect_uri":  self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope":         "read",
            "state":         "locust-internal",
            "action":        "approve",   # required field
            "username":      self.VALID_USERNAME,
            "password":      self.VALID_PASSWORD
        }, catch_response=True, allow_redirects=False) as response:

            if response.status_code not in (200, 302):
                response.failure(
                    f"_get_authorization_code failed with {response.status_code}"
                )
                return None

            # Extract the code from the Location header (302 redirect)
            code     = None
            location = response.headers.get("Location", "")
            if "code=" in location:
                code = location.split("code=")[1].split("&")[0]

            response.success()
            return code


    @task(1)
    def client_enumeration_attack(self):
        """
        Client enumeration attack: tries to access with unknown client_ids.
        Fires: unknown_client_attempts
        Probability: ~5% (1 of 20)
        """
        import random
        fake_clients = [
            "admin", "root", "test", "app", "api",
            "mobile", "backend", "service", "user", "guest"
        ]
        fake_client = random.choice(fake_clients)

        with self.client.post("/token", data={
            "grant_type":    "client_credentials",
            "client_id":     fake_client,
            "client_secret": "any_secret"
        }, catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Expected 401 but got {response.status_code}")
    @task(1)
    def credential_stuffing_attack(self):
        """
        Credential stuffing attack: tries many different usernames
        with common passwords. Different from brute force which
        attacks one user with many passwords.
        Fires: user_auth_failed, unique_failed_usernames
        Probability: ~5% (1 of 20)
        """
        import random
        # Simulates a list of leaked credentials from other sites
        leaked_credentials = [
            ("john.doe", "password123"),
            ("jane.smith", "qwerty"),
            ("carlos.garcia", "123456"),
            ("maria.lopez", "letmein"),
            ("pedro.martinez", "welcome"),
            ("ana.rodriguez", "monkey"),
            ("luis.hernandez", "dragon"),
            ("sofia.gonzalez", "master"),
        ]
        username, password = random.choice(leaked_credentials)

        with self.client.post("/authorize", data={
            "client_id":     self.WEB_CLIENT_ID,
            "redirect_uri":  self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope":         "read",
            "state":         "locust-test",
            "action":        "approve",
            "username":      username,
            "password":      password
        }, catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Expected 401 but got {response.status_code}")

    @task(1)
    def token_harvesting_attack(self):
        """
        Token harvesting: requests valid tokens but never uses or
        revokes them. active_tokens gauge will keep growing.
        Fires: active_tokens (keeps incrementing without decrementing)
        Probability: ~5% (1 of 20)
        """
        # Just request tokens without ever refreshing or revoking them
        # This simulates an attacker accumulating valid tokens
        with self.client.post("/token", data={
            "grant_type":    "client_credentials",
            "client_id":     self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
            "scope":         "read"
        }, catch_response=True) as response:
            if response.status_code == 200:
                # Intentionally do nothing with the token
                # In a real attack the attacker would store it
                response.success()
            else:
                response.failure(f"Expected 200 but got {response.status_code}")
