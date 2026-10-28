"""
oauth2_routes.py — Core OAuth2 endpoints.

Implements:
    GET  /authorize  — start of Authorization Code flow (shows login form)
    POST /authorize  — user submits credentials + consent decision
    POST /token      — token endpoint (authorization_code, client_credentials,
                       refresh_token grant types)

All error responses follow RFC 6749 §5.2.
"""

from __future__ import annotations

import base64
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    jsonify,
)

from models import (
    get_client,
    verify_client_secret,
    store_authorization_code,
    consume_authorization_code,
    issue_token_pair,
    validate_refresh_token,
    revoke_refresh_token
)

#Import the methods of metrics.py
from metrics import (
    auth_flows_started,
    auth_flows_success,
    auth_flows_failed,
    tokens_issued,
    user_auth_success,
    access_tokens_issued,
    refresh_tokens_issued,
    brute_force_attempts,
    user_auth_failed,
    auth_code_reuse,
    login_page_visits,
    unknown_client_attempts, 
    unique_failed_usernames
)
# In-memory set to track unique failed usernames
# Used to detect credential stuffing vs brute force
_failed_usernames: set = set()

oauth2 = Blueprint("oauth2", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_response(error: str, description: str, status: int = 400):
    """Return a JSON error per RFC 6749 §5.2."""
    return jsonify({"error": error, "error_description": description}), status


def _redirect_with_error(redirect_uri: str, error: str, description: str, state: str | None):
    """Redirect to the client with an error in the query string."""
    params = {"error": error, "error_description": description}
    if state:
        params["state"] = state
    return redirect(_append_query(redirect_uri, params))


def _append_query(url: str, params: dict) -> str:
    """Append query parameters to a URL, preserving any existing ones."""
    parts = list(urlparse(url))
    existing = parse_qs(parts[4])
    existing.update(params)
    parts[4] = urlencode(existing, doseq=True)
    return urlunparse(parts)


def _authenticate_client() -> tuple[str, None] | tuple[None, str]:
    """
    Extract client credentials from the request.

    Supports two methods (RFC 6749 §2.3):
      1. HTTP Basic authentication (preferred)
      2. client_id / client_secret in the POST body

    Returns (client_id, None) on success or (None, error_description) on failure.
    """
    # --- HTTP Basic ---
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        try:
            decoded = base64.b64decode(auth_header[6:]).decode()
            client_id, client_secret = decoded.split(":", 1)
        except Exception:
            return None, "Malformed Authorization header"
        if not verify_client_secret(client_id, client_secret):
            return None, "Invalid client credentials"
        return client_id, None

    # --- POST body ---
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    if client_id and client_secret:
        # Check if client exists before verifying secret
        # If client does not exist it is an enumeration attempt
        if get_client(client_id) is None:
            unknown_client_attempts.labels(client_id=client_id).inc()
            return None, "Invalid client credentials"
        if not verify_client_secret(client_id, client_secret):
            return None, "Invalid client credentials"
        return client_id, None

    return None, "Client authentication required"


# ═══════════════════════════════════════════════════════════════════════════
# GET /authorize — show the login / consent page
# ═══════════════════════════════════════════════════════════════════════════

@oauth2.route("/authorize", methods=["GET"])
def authorize_get():
    # --- Validate required parameters ---
    response_type = request.args.get("response_type")
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    scope = request.args.get("scope", "")
    state = request.args.get("state")

    if not response_type:
        return _error_response("invalid_request", "Missing response_type parameter")

    if response_type != "code":
        return _error_response("unsupported_response_type", "Only response_type=code is supported")

    if not client_id:
        return _error_response("invalid_request", "Missing client_id parameter")

    client = get_client(client_id)
    if client is None:
        unknown_client_attempts.inc()
        return _error_response("invalid_request", "Unknown client_id")

    if "authorization_code" not in client["grant_types"]:
        return _error_response("unauthorized_client", "Client is not authorized for authorization_code grant")

    if not redirect_uri:
        return _error_response("invalid_request", "Missing redirect_uri parameter")

    if redirect_uri not in client["redirect_uris"]:
        # Per RFC 6749 §3.1.2.4: do NOT redirect if the URI is invalid
        return _error_response("invalid_request", "redirect_uri does not match any registered URI")
    #We have a valid user, so we incremment the metric of the click simulation
    login_page_visits.labels(client_id=client_id).inc()
    # Everything valid — render the login / consent form
    return render_template(
        "login_consent.html",
        client_name=client["client_name"] or client_id,
        scope=scope,
        # Pass OAuth2 params through as hidden fields
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        state=state or "",
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST /authorize — process login + consent
# ═══════════════════════════════════════════════════════════════════════════

@oauth2.route("/authorize", methods=["POST"])
def authorize_post():
    # Recover OAuth2 parameters from the hidden form fields
    client_id = request.form.get("client_id", "")
    redirect_uri = request.form.get("redirect_uri", "")
    scope = request.form.get("scope", "")
    state = request.form.get("state", "")

    # --- Re-validate client + redirect_uri (defence in depth) ---
    client = get_client(client_id)
    if client is None or redirect_uri not in (client or {}).get("redirect_uris", []):
        return _error_response("invalid_request", "Invalid client or redirect_uri")

    # --- Check user's decision ---
    if request.form.get("action") == "deny":
        return _redirect_with_error(redirect_uri, "access_denied", "The user denied the request", state)

    # --- Authenticate the resource owner ---
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    users: dict = current_app.config["USERS"]
    if username not in users or users[username] != password:
        # Re-render the form with an error message
        # Trigger for the auth_fail bc the cliend_id with that username doesnt typed the right password 
        user_auth_failed.labels(username=username, client_id=client_id).inc()
        # Track unique failed usernames for credential stuffing detection
        _failed_usernames.add(username)
        unique_failed_usernames.set(len(_failed_usernames))
        return render_template(
            "login_consent.html",
            client_name=client["client_name"] or client_id,
            scope=scope,
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type="code",
            state=state,
            error="Invalid username or password.",
        ), 401
    #At this point we have a successful login
    user_auth_success.labels(username=username).inc()
    # --- Issue authorization code ---
    code = store_authorization_code(
        client_id=client_id,
        redirect_uri=redirect_uri,
        user_id=username,
        scope=scope,
    )

    params = {"code": code}
    if state:
        params["state"] = state
    return redirect(_append_query(redirect_uri, params))


# ═══════════════════════════════════════════════════════════════════════════
# POST /token — exchange grants for tokens
# ═══════════════════════════════════════════════════════════════════════════

@oauth2.route("/token", methods=["POST"])
def token():
    grant_type = request.form.get("grant_type")

    if not grant_type:
        return _error_response("invalid_request", "Missing grant_type parameter")

    if grant_type == "authorization_code":
        return _handle_authorization_code()
    elif grant_type == "client_credentials":
        return _handle_client_credentials()
    elif grant_type == "refresh_token":
        return _handle_refresh_token()
    else:
        return _error_response("unsupported_grant_type", f"Grant type '{grant_type}' is not supported")


# ---------------------------------------------------------------------------
# grant_type=authorization_code  (RFC 6749 §4.1.3)
# ---------------------------------------------------------------------------

def _handle_authorization_code():
    #Here we are incrementing the authorized flow of events
    auth_flows_started.labels(grant_type="authorization_code").inc()
    client_id, err = _authenticate_client()
    if err:
        #if the system cannot validate the cliend id we swap into unknown and then the trigger for the metrics
        cid_label = client_id if client_id else "unknown"
        brute_force_attempts.labels(client_id=cid_label).inc()
        auth_flows_failed.labels(grant_type="authorization_code").inc()
        return _error_response("invalid_client", err, 401)
    assert client_id is not None  # guaranteed by _authenticate_client

    #We get the code of handle_client_credentials
    code_value = request.form.get("code")
    redirect_uri = request.form.get("redirect_uri")

    if not code_value:
        #if there is any errors with the code we increment the failed counter
        auth_flows_failed.labels(grant_type="authorization_code").inc()
        return _error_response("invalid_request", "Missing code parameter")
    if not redirect_uri:
        #if there is any errors with the code we increment the failed counter
        auth_flows_failed.labels(grant_type="authorization_code").inc()
        return _error_response("invalid_request", "Missing redirect_uri parameter")

    code_data = consume_authorization_code(code_value)
    if code_data is None:
        #if there is any errors with the code we increment the failed counter
        auth_flows_failed.labels(grant_type="authorization_code").inc()
        return _error_response("invalid_grant", "Authorization code is invalid, expired, or already used")

    # The redirect_uri MUST match the one used in the authorization request
    if code_data["redirect_uri"] != redirect_uri:
        #if there is any errors with the url we increment the failed counter
        auth_flows_failed.labels(grant_type="authorization_code").inc()
        return _error_response("invalid_grant", "redirect_uri does not match the authorization request")

    # The code must have been issued to this client
    if code_data["client_id"] != client_id:
        #if there is any errors with the owner of the code we increment the failed counter
        #this mean that some client can use other client code
        auth_flows_failed.labels(grant_type="authorization_code").inc()
        return _error_response("invalid_grant", "Authorization code was issued to a different client")

    token_response = issue_token_pair(
        client_id=client_id,
        scope=code_data["scope"],
        user_id=code_data["user_id"],
        include_refresh=True,
    )
    #we increment the successful counters
    auth_flows_success.labels(grant_type="authorization_code").inc()
    tokens_issued.labels(token_type="access", grant_type="authorization_code").inc()
    tokens_issued.labels(token_type="refresh", grant_type="authorization_code").inc()
    access_tokens_issued.labels(grant_type="authorization_code").inc()
    refresh_tokens_issued.labels(grant_type="authorization_code").inc()

    return jsonify(token_response)


# ---------------------------------------------------------------------------
# grant_type=client_credentials  (RFC 6749 §4.4)
# ---------------------------------------------------------------------------

def _handle_client_credentials():
    #We increment the counter of client_credentials, we don't care if is a good one or not
    auth_flows_started.labels(grant_type="client_credentials").inc()
    #client id or an error if there is no user with that credencials
    client_id, err = _authenticate_client()
    if err:
        #if there is an error with client credentials we increment the failed login counter
        auth_flows_failed.labels(grant_type="client_credentials").inc()
        cid_label = request.form.get("client_id", "unknown")
        brute_force_attempts.labels(client_id=cid_label).inc()
        return _error_response("invalid_client", err, 401) #401=unauthorized access

    assert client_id is not None  # guaranteed by _authenticate_client

    #We get the client of the cliend_id
    client = get_client(client_id)
    if client is None or "client_credentials" not in client["grant_types"]:
        #At this point we have a valid client with no permision so is a failed login
        auth_flows_failed.labels(grant_type="client_credentials").inc()
        return _error_response("unauthorized_client", "Client is not authorized for client_credentials grant")

    scope = request.form.get("scope", "")

    # RFC 6749 §4.4.3: SHOULD NOT issue a refresh token
    # generate a valid token to store in the db bc is a valid user with the right permisions
    token_response = issue_token_pair(
        client_id=client_id,
        scope=scope,
        user_id=None,
        include_refresh=False,
    )

    auth_flows_success.labels(grant_type="client_credentials").inc() #increment the valid access count
    tokens_issued.labels(token_type="access", grant_type="client_credentials").inc() #increment the counter of generate tokens
    access_tokens_issued.labels(grant_type="client_credentials").inc() #increment the counter of access token (bc we have the distintions on our metrics.py)

    return jsonify(token_response)


# ---------------------------------------------------------------------------
# grant_type=refresh_token  (RFC 6749 §6)
# ---------------------------------------------------------------------------

def _handle_refresh_token():
    #We increment the counter of client_credentials, we don't care if is a good one or not
    auth_flows_started.labels(grant_type="refresh_token").inc()

    client_id, err = _authenticate_client()
    if err:
        #if there is any errors with the authentication of the client we increment the failed counter
        auth_flows_failed.labels(grant_type="refresh_token").inc()
        cid_label = request.form.get("client_id", "unknown")
        brute_force_attempts.labels(client_id=cid_label).inc()
        return _error_response("invalid_client", err, 401)

    assert client_id is not None  # guaranteed by _authenticate_client

    refresh_token_value = request.form.get("refresh_token")
    if not refresh_token_value:
        #if there is any errors with the refresh token that the client sent  we increment the failed counter
        auth_flows_failed.labels(grant_type="refresh_token").inc()
        return _error_response("invalid_request", "Missing refresh_token parameter")

    token_data = validate_refresh_token(refresh_token_value)
    if token_data is None:
        #if there is any errors with the validation of the token data we increment the failed counter
        auth_flows_failed.labels(grant_type="refresh_token").inc()
        return _error_response("invalid_grant", "Refresh token is invalid, expired, or revoked")

    # The refresh token must belong to this client
    if token_data["client_id"] != client_id: 
        auth_flows_failed.labels(grant_type="refresh_token").inc()
        return _error_response("invalid_grant", "Refresh token was issued to a different client")

    # Revoke the old refresh token (and its access tokens) — rotation
    revoke_refresh_token(refresh_token_value)

    # Optionally allow narrowing the scope; default to the original
    requested_scope = request.form.get("scope", token_data["scope"])

    token_response = issue_token_pair(
        client_id=client_id,
        scope=requested_scope,
        user_id=token_data["user_id"],
        include_refresh=True,
    )
    #if there is no error, we increment the counter of successful token
    auth_flows_success.labels(grant_type="refresh_token").inc()
    tokens_issued.labels(token_type="access", grant_type="refresh_token").inc()
    tokens_issued.labels(token_type="refresh", grant_type="refresh_token").inc()
    access_tokens_issued.labels(grant_type="refresh_token").inc()
    refresh_tokens_issued.labels(grant_type="refresh_token").inc()

    return jsonify(token_response)
