import os
import re
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

STEADFAST_BASE_URL = os.getenv("STEADFAST_BASE_URL", "https://portal.packzy.com/api/v1").rstrip("/")
API_KEY = os.getenv("STEADFAST_API_KEY", "")
SECRET_KEY = os.getenv("STEADFAST_SECRET_KEY", "")
PORT = int(os.getenv("PORT", "5000"))

def clean_phone(phone):
    return re.sub(r"\D", "", str(phone or ""))

def validate_order(data):
    required = ["invoice", "customer_name", "customer_phone", "delivery_address", "cod_amount"]
    missing = [x for x in required if data.get(x) in (None, "")]
    if missing:
        return f"Missing fields: {', '.join(missing)}"

    phone = clean_phone(data["customer_phone"])
    if len(phone) != 11 or not phone.startswith("01"):
        return "customer_phone must be an 11-digit Bangladesh mobile number."

    try:
        cod = float(data["cod_amount"])
        if cod < 0:
            return "cod_amount must be >= 0."
    except (TypeError, ValueError):
        return "cod_amount must be a number."

    if len(str(data["invoice"])) > 100:
        return "invoice is too long."
    if len(str(data["customer_name"])) > 100:
        return "customer_name is too long."
    if len(str(data["delivery_address"])) > 250:
        return "delivery_address is too long (max 250 characters)."

    return None

def steadfast_headers():
    return {
        "Api-Key": API_KEY,
        "Secret-Key": SECRET_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "steadfast-backend",
        "credentials_configured": bool(API_KEY and SECRET_KEY),
    })

@app.post("/steadfast/order")
def create_order():
    if not API_KEY or not SECRET_KEY:
        return jsonify({"ok": False, "message": "Steadfast API credentials are not configured on the server."}), 500

    data = request.get_json(silent=True) or {}
    error = validate_order(data)
    if error:
        return jsonify({"ok": False, "message": error}), 400

    payload = {
        "invoice": str(data["invoice"]),
        "recipient_name": str(data["customer_name"]),
        "recipient_phone": clean_phone(data["customer_phone"]),
        "recipient_address": str(data["delivery_address"]),
        "cod_amount": float(data["cod_amount"]),
    }

    # Optional Steadfast fields.
    for src, dst in [
        ("alternative_phone", "alternative_phone"),
        ("recipient_email", "recipient_email"),
        ("note", "note"),
        ("item_description", "item_description"),
        ("total_lot", "total_lot"),
        ("delivery_type", "delivery_type"),
    ]:
        if data.get(src) not in (None, ""):
            payload[dst] = data[src]

    try:
        r = requests.post(
            f"{STEADFAST_BASE_URL}/create_order",
            headers=steadfast_headers(),
            json=payload,
            timeout=30,
        )
        try:
            result = r.json()
        except ValueError:
            result = {"raw": r.text}

        if not r.ok:
            return jsonify({
                "ok": False,
                "message": "Steadfast API request failed.",
                "steadfast_status": r.status_code,
                "details": result,
            }), r.status_code

        consignment = result.get("consignment") or {}
        return jsonify({
            "ok": True,
            "message": result.get("message", "Order created successfully."),
            "consignment_id": consignment.get("consignment_id"),
            "tracking_code": consignment.get("tracking_code"),
            "status": consignment.get("status"),
            "consignment": consignment,
        })

    except requests.RequestException as e:
        return jsonify({"ok": False, "message": f"Could not reach Steadfast: {e}"}), 502

@app.get("/steadfast/status/invoice/<path:invoice>")
def status_by_invoice(invoice):
    if not API_KEY or not SECRET_KEY:
        return jsonify({"ok": False, "message": "Steadfast API credentials are not configured on the server."}), 500
    try:
        r = requests.get(
            f"{STEADFAST_BASE_URL}/status_by_invoice/{invoice}",
            headers=steadfast_headers(),
            timeout=30,
        )
        try:
            result = r.json()
        except ValueError:
            result = {"raw": r.text}
        return jsonify(result), r.status_code
    except requests.RequestException as e:
        return jsonify({"ok": False, "message": f"Could not reach Steadfast: {e}"}), 502

@app.get("/steadfast/status/tracking/<tracking_code>")
def status_by_tracking(tracking_code):
    if not API_KEY or not SECRET_KEY:
        return jsonify({"ok": False, "message": "Steadfast API credentials are not configured on the server."}), 500
    try:
        r = requests.get(
            f"{STEADFAST_BASE_URL}/status_by_trackingcode/{tracking_code}",
            headers=steadfast_headers(),
            timeout=30,
        )
        try:
            result = r.json()
        except ValueError:
            result = {"raw": r.text}
        return jsonify(result), r.status_code
    except requests.RequestException as e:
        return jsonify({"ok": False, "message": f"Could not reach Steadfast: {e}"}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
