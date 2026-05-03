from locust import HttpUser, task, between

class OAuth2LoadTest(HttpUser):
    wait_time = between(1, 3)

    VALID_CLIENT_ID = "service-account"
    VALID_CLIENT_SECRET = "6Q6TZj_hKy4xBnZhgBuIwdJ6lSaQbF-9XWR9S_BHthk"

    @task(4)
    def valid_client_credentials(self):
        """
        Legitimate traffic: requests a token correctly.
        Probability: 40% (4 of 10)
        """
        self.client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
            "scope": "read"
        })

    @task(2)
    def brute_force_api(self):
        """
        M2M attack: tries to guess the secret.
        Fires brute_force_attempts metric.
        Probability: 20% (2 of 10)
        """
        with self.client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": "clave_falsa_inventada"
        }, catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Expected 401 but got {response.status_code}")

    @task(2)
    def brute_force_user_login(self):
        """
        Web attack: tries to login with wrong password.
        Fires user_auth_failed metric.
        Probability: 20% (2 of 10)
        """
        with self.client.post("/authorize", data={
            "client_id": "web-app",
            "redirect_uri": "http://localhost:8080/callback",
            "response_type": "code",
            "scope": "read",
            "state": "test123",
            "username": "usuario_victima",
            "password": "password_incorrecta",
            "action": "approve"
        }, catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Expected 401 but got {response.status_code}")

    @task(1)
    def valid_user_login(self):
        """
        Legitimate traffic: user logs in correctly.
        Fires auth_flows_success for authorization_code.
        Probability: 10% (1 of 10)
        """
        with self.client.post("/authorize", data={
            "client_id": "web-app",
            "redirect_uri": "http://localhost:8080/callback",
            "response_type": "code",
            "scope": "read",
            "state": "test123",
            "username": "testuser",
            "password": "testpass",
            "action": "approve"
        }, catch_response=True) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Expected 302 but got {response.status_code}")

    @task(1)
    def replay_attack(self):
        """
        Replay attack: uses an access token as a refresh token.
        Fires revoked_token_usage metric.
        Probability: 10% (1 of 10)
        """
        # Step 1: get a valid access token
        response = self.client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
        })

        if response.status_code != 200:
            return

        # Step 2: try to use it as a refresh token (invalid)
        token = response.json().get("access_token")
        with self.client.post("/token", data={
            "grant_type": "refresh_token",
            "refresh_token": token,
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
        }, catch_response=True) as response:
            if response.status_code == 400:
                response.success()
            else:
                response.failure(f"Expected 400 but got {response.status_code}")
