from locust import HttpUser, task, between

class OAuth2LoadTest(HttpUser):
    # Simulamos que cada usuario "piensa" entre 1 y 3 segundos antes de hacer el siguiente clic
    wait_time = between(1, 3) 

    # Credenciales extraídas de tu script seed.py
    VALID_CLIENT_ID = "service-account"
    VALID_CLIENT_SECRET = "6Q6TZj_hKy4xBnZhgBuIwdJ6lSaQbF-9XWR9S_BHthk"

    @task(4)
    def valid_client_credentials(self):
        """
        Tráfico Legítimo: Pide un token correctamente.
        La probabilidad de que se ejecute esta tarea es del 50% (4 de 8).
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
        Ataque M2M: Intenta adivinar el secret (Dispara la métrica 'brute_force_attempts').
        La probabilidad es del 25% (2 de 8).
        """
        # IMPORTANTE: catch_response=True nos permite decirle a Locust que un error 401 
        # en realidad es un "éxito" para nuestro test, porque el servidor actuó bien bloqueándolo.
        with self.client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.VALID_CLIENT_ID,
            "client_secret": "clave_falsa_inventada"
        }, catch_response=True) as response:
            
            if response.status_code == 401:
                response.success()  # El servidor se defendió, el test es exitoso
            else:
                response.failure(f"¡Peligro! El atacante recibió un código {response.status_code}")

    @task(2)
    def brute_force_user_login(self):
        """
        Ataque Web: Intenta loguearse con mala contraseña (Dispara la métrica 'user_auth_failed').
        La probabilidad es del 25% (2 de 8).
        """
        with self.client.post("/authorize", data={
            "client_id": "web-app", # El otro cliente de tu seed.py
            "redirect_uri": "http://localhost:8080/callback",
            "response_type": "code",
            "username": "usuario_victima",
            "password": "password123"
        }, catch_response=True) as response:
            
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f"Error de seguridad, esperábamos un 401 pero dio {response.status_code}")
