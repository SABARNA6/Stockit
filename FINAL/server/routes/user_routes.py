# routes/user_routes.py
#
# User profile endpoints backed by Supabase `profiles` table.
# Uses user's own JWT token — no service_role key needed.

from flask import Blueprint, jsonify, request
from helpers.supabase_helper import get_client_for_user, get_user_from_token

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


def ok(data):
    return jsonify({"success": True, "data": data})

def err(msg, status=400):
    return jsonify({"success": False, "message": msg}), status


def _get_token(req):
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, err("Missing Authorization header", 401)
    token = auth.split(" ", 1)[1].strip()
    user  = get_user_from_token(token)
    if not user:
        return None, err("Invalid or expired token", 401)
    return token, None


@user_bp.get("/profile")
def get_profile():
    """GET /api/user/profile"""
    token, error = _get_token(request)
    if error:
        return error

    user = get_user_from_token(token)
    try:
        sb   = get_client_for_user(token)
        resp = (
            sb.table("profiles")
            .select("id, full_name, avatar_url")
            .eq("id", user["id"])
            .single()
            .execute()
        )
        return ok(resp.data)
    except Exception as e:
        print(f"[get_profile] {e}")
        return err(str(e), 500)


@user_bp.put("/profile")
def update_profile():
    """PUT /api/user/profile  —  body: { full_name, avatar_url }"""
    token, error = _get_token(request)
    if error:
        return error

    user = get_user_from_token(token)
    body = request.get_json(silent=True)
    if not body:
        return err("Request body must be JSON")

    updates = {}
    if "full_name"  in body: updates["full_name"]  = str(body["full_name"]).strip()
    if "avatar_url" in body: updates["avatar_url"] = str(body["avatar_url"]).strip()

    if not updates:
        return err("Nothing to update. Provide 'full_name' or 'avatar_url'")

    try:
        sb   = get_client_for_user(token)
        resp = (
            sb.table("profiles")
            .update(updates)
            .eq("id", user["id"])
            .execute()
        )
        return ok(resp.data[0] if resp.data else updates)
    except Exception as e:
        print(f"[update_profile] {e}")
        return err(str(e), 500)