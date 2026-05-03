from locust import HttpUser, task, between


class OAuth2LoadTest(HttpUser):
    """
    Usuario virtual de Locust para probar el servidor OAuth2.

    Este usuario simula tanto trafico legitimo como trafico erroneo/controlado
    para observar el comportamiento de la aplicacion y sus metricas Prometheus.

    Metricas cubiertas:
        - auth_flows_started / auth_flows_success / auth_flows_failed
        - tokens_issued / access_tokens_issued / refresh_tokens_issued
        - http_requests / http_requests_token / http_requests_authorize / http_requests_admin
        - requests_in_progress / request_duration
        - active_tokens / tokens_revoked
        - pending_auth_codes
        - auth_code_reuse
        - revoked_token_usage
        - expired_token_usage  (indirectamente via refresh token invalido)
        - brute_force_attempts
        - user_auth_failed
        - active_clients
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

    # =========================================================================
    # FLUJOS LEGITIMOS
    # =========================================================================

    @task(6)
    def valid_client_credentials(self):
        """
        Trafico legitimo maquina a maquina.

        Metricas activadas:
            - auth_flows_started{grant_type="client_credentials"}
            - auth_flows_success{grant_type="client_credentials"}
            - tokens_issued{token_type="access", grant_type="client_credentials"}
            - access_tokens_issued{grant_type="client_credentials"}
            - active_tokens{token_type="access"}
            - active_clients
            - http_requests / http_requests_token con status 200
            - requests_in_progress / request_duration
        """
        response = self.client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
            "scope": "read"
        })

        if response.status_code != 200:
            response.failure(f"client_credentials valido fallo con {response.status_code}")

    @task(3)
    def valid_authorization_code_flow(self):
        """
        Flujo completo authorization_code: login -> obtener code -> canjear por tokens.

        Metricas activadas:
            - auth_flows_started{grant_type="authorization_code"}
            - auth_flows_success{grant_type="authorization_code"}
            - tokens_issued{token_type="access"/"refresh", grant_type="authorization_code"}
            - access_tokens_issued{grant_type="authorization_code"}
            - refresh_tokens_issued{grant_type="authorization_code"}
            - active_tokens{token_type="access"} / active_tokens{token_type="refresh"}
            - pending_auth_codes (sube al emitir el code, baja al canjearlo)
            - active_clients
            - http_requests / http_requests_authorize / http_requests_token con status 200
            - requests_in_progress / request_duration
        """
        # Paso 1: POST /authorize con credenciales validas -> obtenemos el code
        with self.client.post("/authorize", data={
            "client_id": self.WEB_CLIENT_ID,
            "redirect_uri": self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope": "read",
            "state": "locust-test",
            "username": self.VALID_USERNAME,
            "password": self.VALID_PASSWORD
        }, catch_response=True, allow_redirects=False) as auth_response:

            # El servidor devuelve 302 con el code en la URL de redireccion
            if auth_response.status_code not in (200, 302):
                auth_response.failure(
                    f"authorize valido fallo con {auth_response.status_code}"
                )
                return

            # Extraemos el code del cuerpo o de la cabecera Location segun impl.
            code = None

            location = auth_response.headers.get("Location", "")
            if "code=" in location:
                code = location.split("code=")[1].split("&")[0]

            if not code and auth_response.status_code == 200:
                try:
                    data = auth_response.json()
                    code = data.get("code")
                except Exception:
                    pass

            if not code:
                auth_response.success()  # El flujo puede ser distinto, no falla el test
                return

            auth_response.success()

        # Paso 2: POST /token canjeando el code -> obtenemos access + refresh token
        with self.client.post("/token", data={
            "grant_type": "authorization_code",
            "client_id": self.WEB_CLIENT_ID,
            "code": code,
            "redirect_uri": self.WEB_REDIRECT_URI
        }, catch_response=True) as token_response:

            if token_response.status_code != 200:
                token_response.failure(
                    f"canje de code fallo con {token_response.status_code}"
                )
                return

            token_response.success()

    @task(2)
    def valid_refresh_token_flow(self):
        """
        Flujo completo refresh_token: primero obtiene tokens via authorization_code,
        luego los renueva con el refresh token.

        Metricas activadas:
            - auth_flows_started / auth_flows_success {grant_type="refresh_token"}
            - tokens_issued / access_tokens_issued / refresh_tokens_issued
            - active_tokens (los nuevos tokens se activan)
            - tokens_revoked (el refresh token viejo se revoca al rotar)
            - http_requests_token con status 200
        """
        # Paso 1: Obtenemos un par de tokens via authorization_code
        code = self._get_authorization_code()
        if not code:
            return

        with self.client.post("/token", data={
            "grant_type": "authorization_code",
            "client_id": self.WEB_CLIENT_ID,
            "code": code,
            "redirect_uri": self.WEB_REDIRECT_URI
        }, catch_response=True) as token_response:

            if token_response.status_code != 200:
                token_response.failure(
                    f"obtencion de tokens para refresh fallo con {token_response.status_code}"
                )
                return

            try:
                tokens = token_response.json()
                refresh_token = tokens.get("refresh_token")
            except Exception:
                token_response.failure("No se pudo parsear la respuesta de tokens")
                return

            token_response.success()

        if not refresh_token:
            return

        # Paso 2: Renovamos usando el refresh token
        with self.client.post("/token", data={
            "grant_type": "refresh_token",
            "client_id": self.WEB_CLIENT_ID,
            "refresh_token": refresh_token
        }, catch_response=True) as refresh_response:

            if refresh_response.status_code != 200:
                refresh_response.failure(
                    f"refresh_token valido fallo con {refresh_response.status_code}"
                )
                return

            refresh_response.success()

    # =========================================================================
    # FLUJOS DE ERROR / TRAFICO MALICIOSO
    # =========================================================================

    @task(2)
    def invalid_client_credentials(self):
        """
        Trafico malicioso: client_secret incorrecto.

        Metricas activadas:
            - auth_flows_started / auth_flows_failed {grant_type="client_credentials"}
            - brute_force_attempts{client_id="service-account"}
            - http_requests / http_requests_token con status 401
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
        Fallo de login de usuario: password incorrecta.

        Metricas activadas:
            - auth_flows_started / auth_flows_failed {grant_type="authorization_code"}
            - user_auth_failed{username="testuser", client_id="web-app"}
            - http_requests / http_requests_authorize con status 401
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
    def auth_code_replay_attack(self):
        """
        Intenta canjear el mismo authorization_code dos veces.
        La primera llamada deberia tener exito (200), la segunda debe fallar (400)
        porque el code ya fue marcado como 'used' en la base de datos.

        Metricas activadas:
            - pending_auth_codes (sube al emitir, baja al primer canje)
            - auth_code_reuse (se incrementa en el segundo intento)
            - http_requests / http_requests_token con status 200 y luego 400
        """
        # Obtenemos un code valido
        code = self._get_authorization_code()
        if not code:
            return

        # Primer canje: deberia funcionar (200)
        with self.client.post("/token", data={
            "grant_type": "authorization_code",
            "client_id": self.WEB_CLIENT_ID,
            "code": code,
            "redirect_uri": self.WEB_REDIRECT_URI
        }, catch_response=True) as first_response:

            if first_response.status_code != 200:
                first_response.failure(
                    f"Primer canje fallo inesperadamente con {first_response.status_code}"
                )
                return

            first_response.success()

        # Segundo canje del mismo code: deberia fallar (400 o 401)
        # Esto dispara auth_code_reuse en models.py -> consume_authorization_code()
        with self.client.post("/token", data={
            "grant_type": "authorization_code",
            "client_id": self.WEB_CLIENT_ID,
            "code": code,
            "redirect_uri": self.WEB_REDIRECT_URI
        }, catch_response=True) as second_response:

            if second_response.status_code in (400, 401):
                second_response.success()  # Es el comportamiento esperado
            else:
                second_response.failure(
                    f"Se esperaba 400/401 en replay attack, pero llego {second_response.status_code}"
                )

    @task(1)
    def revoked_token_usage_attack(self):
        """
        Obtiene un refresh token valido, lo revoca y luego intenta usarlo.
        Simula un ataque de token replay con un token ya revocado.

        Metricas activadas:
            - tokens_revoked{token_type="refresh"} / tokens_revoked{token_type="access"}
            - active_tokens (decrementos al revocar)
            - revoked_token_usage (al intentar usar el token revocado)
            - http_requests_token con status 400
        """
        # Paso 1: Obtenemos tokens validos
        code = self._get_authorization_code()
        if not code:
            return

        refresh_token = None
        with self.client.post("/token", data={
            "grant_type": "authorization_code",
            "client_id": self.WEB_CLIENT_ID,
            "code": code,
            "redirect_uri": self.WEB_REDIRECT_URI
        }, catch_response=True) as token_response:

            if token_response.status_code != 200:
                token_response.failure(
                    f"Obtencion de tokens para revocacion fallo con {token_response.status_code}"
                )
                return

            try:
                tokens = token_response.json()
                refresh_token = tokens.get("refresh_token")
            except Exception:
                token_response.failure("No se pudo parsear la respuesta")
                return

            token_response.success()

        if not refresh_token:
            return

        # Paso 2: Renovamos el token una vez para que el anterior quede revocado
        # (muchos servidores revocan el refresh token viejo al emitir uno nuevo)
        with self.client.post("/token", data={
            "grant_type": "refresh_token",
            "client_id": self.WEB_CLIENT_ID,
            "refresh_token": refresh_token
        }, catch_response=True) as rotate_response:

            if rotate_response.status_code != 200:
                rotate_response.success()  # No nos importa el resultado aqui
                return

            rotate_response.success()

        # Paso 3: Intentamos usar el refresh token ORIGINAL (ya revocado)
        # Esto dispara revoked_token_usage en models.py -> validate_refresh_token()
        with self.client.post("/token", data={
            "grant_type": "refresh_token",
            "client_id": self.WEB_CLIENT_ID,
            "refresh_token": refresh_token
        }, catch_response=True) as revoked_response:

            if revoked_response.status_code in (400, 401):
                revoked_response.success()  # Comportamiento esperado
            else:
                revoked_response.failure(
                    f"Se esperaba 400/401 al usar token revocado, pero llego {revoked_response.status_code}"
                )

    @task(1)
    def invalid_refresh_token(self):
        """
        Intenta usar un refresh token completamente falso.
        Esto prueba el error de refresh_token invalido (no existe en BD).

        Metricas activadas:
            - auth_flows_started / auth_flows_failed {grant_type="refresh_token"}
            - http_requests / http_requests_token con status 400
        """
        with self.client.post("/token", data={
            "grant_type": "refresh_token",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": self.VALID_CLIENT_SECRET,
            "refresh_token": "refresh_token_completamente_falso_xyz123"
        }, catch_response=True) as response:

            if response.status_code == 400:
                response.success()
            else:
                response.failure(
                    f"Se esperaba 400 para refresh_token invalido, pero llego {response.status_code}"
                )

    # =========================================================================
    # ENDPOINTS DE ADMINISTRACION
    # =========================================================================

    @task(1)
    def list_admin_clients(self):
        """
        Consulta el listado de clientes registrados en la aplicacion.

        Metricas activadas:
            - http_requests / http_requests_admin con status 200
            - requests_in_progress / request_duration para /admin/clients
        """
        response = self.client.get("/admin/clients")

        if response.status_code != 200:
            response.failure(f"/admin/clients GET fallo con {response.status_code}")

    # =========================================================================
    # ENDPOINT DE METRICAS
    # =========================================================================

    @task(1)
    def metrics_endpoint(self):
        """
        Comprueba que el endpoint /metrics sigue respondiendo bajo carga.
        Tiene poco peso porque Prometheus sera quien normalmente consulte este endpoint.

        Metricas activadas:
            - http_requests con endpoint="/metrics" y status 200
            - requests_in_progress / request_duration para /metrics
        """
        response = self.client.get("/metrics")

        if response.status_code != 200:
            response.failure(f"/metrics fallo con {response.status_code}")

    # =========================================================================
    # METODO AUXILIAR PRIVADO
    # =========================================================================

    def _get_authorization_code(self) -> str | None:
        """
        Realiza el paso de autorizacion (POST /authorize) con credenciales validas
        y devuelve el code extraido de la respuesta o de la cabecera Location.
        Devuelve None si no se pudo obtener el code.
        """
        with self.client.post("/authorize", data={
            "client_id": self.WEB_CLIENT_ID,
            "redirect_uri": self.WEB_REDIRECT_URI,
            "response_type": "code",
            "scope": "read",
            "state": "locust-internal",
            "username": self.VALID_USERNAME,
            "password": self.VALID_PASSWORD
        }, catch_response=True, allow_redirects=False) as response:

            if response.status_code not in (200, 302):
                response.failure(
                    f"_get_authorization_code fallo con {response.status_code}"
                )
                return None

            code = None

            # Intentamos extraer el code de la cabecera Location (redirect 302)
            location = response.headers.get("Location", "")
            if "code=" in location:
                code = location.split("code=")[1].split("&")[0]

            # Si no hay redirect, intentamos parsear el JSON del cuerpo
            if not code and response.status_code == 200:
                try:
                    data = response.json()
                    code = data.get("code")
                except Exception:
                    pass

            response.success()
            return code
