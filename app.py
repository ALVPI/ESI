"""
app.py — Flask application entry point.

Wires together the database, blueprints, and configuration.
Run with:  uv run python app.py
"""
#DISCLAIMER we've commented in english to mantain the consistence of the code

from flask import Flask, request, g
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import time

from database import close_db, init_db
from oauth2_routes import oauth2
from admin_routes import admin
from metrics import http_requests

# ---------------------------------------------------------------------------
# Hardcoded test users (resource owners for the authorization code flow).
# In production these would live in a proper user store.
# ---------------------------------------------------------------------------
USERS = {
    "testuser": "testpass",
    "admin": "adminpass",
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "dev-secret-key-change-in-production"

    # Store users in app config so routes can access them
    app.config["USERS"] = USERS

    # Register blueprints
    app.register_blueprint(oauth2)
    app.register_blueprint(admin)

    # Database lifecycle
    app.teardown_appcontext(close_db)

    # Ensure tables exist on first launch
    with app.app_context():
        init_db()

    #Registro automatico de métricas HTTP
    #Automatic HTTP metrics log
    @app.before_request
    def antes_de_peticion():
        # Guardamos el momento en que llega la peticion
        # Store the moment of the request arrives
        g.start_time = time.time()

    @app.after_request
    def despues_de_peticion(response):
        # get the request endopoint
        endpoint = request.path

        # we increment the general counter 
        http_requests.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code)
        ).inc()

        # We increment the specific counter for each endpoint
        if "/token" in endpoint:
            from metrics import http_requests_token
            http_requests_token.labels(
                method=request.method,
                status_code=str(response.status_code)
            ).inc()
        elif "/authorize" in endpoint:
            from metrics import http_requests_authorize
            http_requests_authorize.labels(
                method=request.method,
                status_code=str(response.status_code)
            ).inc()
        elif "/admin" in endpoint:
            from metrics import http_requests_admin
            http_requests_admin.labels(
                method=request.method,
                status_code=str(response.status_code)
            ).inc()

        return response

    return app


if __name__ == "__main__":
    # Cretaion of the Flask's app
    flask_app = create_app()

    # Merge Flask with the /metrics (Prometheus) endpoint 
    application = DispatcherMiddleware(flask_app, {
        "/metrics": make_wsgi_app()
    })

    print("OAuth2 server running on http://localhost:5001")
    print("Metrics available on http://localhost:5001/metrics")
    print("Endpoints:")
    print("  GET    /authorize            — Authorization Code flow (browser)")
    print("  POST   /token                — Token endpoint")
    print("  GET    /admin/clients         — List all clients")
    print("  POST   /admin/clients         — Register a new client")
    print("  DELETE /admin/clients/<id>    — Delete a client")
    print()

    from werkzeug.serving import run_simple
    run_simple("0.0.0.0", 5001, application, use_reloader=True, use_debugger=True)
