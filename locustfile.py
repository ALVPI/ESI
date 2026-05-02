from locust import HttpUser, task, between


class OAuth2LoadTest(HttpUser):
    """
    Usuario virtual de Locust para probar el servidor OAuth2.

    Este usuario simula tanto trafico legitimo como trafico erroneo/controlado
    para observar el comportamiento de la aplicacion y sus metricas Prometheus.
    """

    wait_time = between(1, 3)

    # Cliente valido para el flujo client_credentials
    VALID_CLIENT_ID = "service-account"
    VALID_CLIENT_SECRET = "6Q6TZj_hKy4xBnZhgBuIwdJ6lSaQbF-9XWR9S_BHthk"

    # Cliente web para el flujo authorization_code
    WEB_CLIENT_ID = "web-app"
    WEB_REDIRECT_URI = "http://localhost:8080/callback"

    # Usuario valido definido en app.py
    VALID_USERNAME = "testuser"
    VALID_PASSWORD = "testpass"

    @task(6)
    def valid_client_credentials(self):
        """
        Trafico legitimo maquina a maquina.

        Simula un cliente valido pidiendo un access token mediante
        el flujo client_credentials.
        """
        response = self.client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
            "scope": "read"
        })

        if response.status_code != 200:
            response.failure(f"client_credentials valido fallo con {response.status_code}")

    @task(2)
    def invalid_client_credentials(self):
        """
        Trafico malicioso o erroneo.

        Simula intentos de autenticacion con client_secret incorrecto.
        El servidor deberia responder con 401.
        """
        with self.client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": "secret_incorrecto",
            "scope": "read"
        }, catch_response=True) as response:

            if response.status_code == 401:
                response.success()
            else:
                response.failure(
                    f"Se esperaba 401 para credenciales incorrectas, pero llego {response.status_code}"
                )

    @task(2)
    def invalid_user_login(self):
        """
        Simula un fallo de login de usuario.

        Esto deberia incrementar la metrica user_auth_failed,
        porque el usuario existe pero la contraseña es incorrecta.
        """
        with self.client.post("/authorize", data={
            "client_id": self.WEB_CLIENT_ID,
            "redirect_uri": self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope": "read",
            "state": "locust-test",
            "username": self.VALID_USERNAME,
            "password": "password_incorrecta"
        }, catch_response=True) as response:

            if response.status_code == 401:
                response.success()
            else:
                response.failure(
                    f"Se esperaba 401 en login incorrecto, pero llego {response.status_code}"
                )

    @task(1)
    def invalid_refresh_token(self):
        """
        Simula un intento de usar un refresh token invalido.

        Esto prueba el flujo refresh_token en caso de error.
        """
        with self.client.post("/token", data={
            "grant_type": "refresh_token",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
            "refresh_token": "refresh_token_falso"
        }, catch_response=True) as response:

            if response.status_code == 400:
                response.success()
            else:
                response.failure(
                    f"Se esperaba 400 para refresh_token invalido, pero llego {response.status_code}"
                )

    @task(1)
    def metrics_endpoint(self):
        """
        Comprueba que el endpoint /metrics sigue respondiendo bajo carga.

        Tiene poco peso porque Prometheus sera quien normalmente consulte este endpoint.
        """
        response = self.client.get("/metrics")

        if response.status_code != 200:
            response.failure(f"/metrics fallo con {response.status_code}")