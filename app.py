import os
import re

from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

STEADFAST_BASE_URL = os.getenv(
    "STEADFAST_BASE_URL",
    "https://portal.packzy.com/api/v1"
).rstrip("/")

API_KEY = os.getenv("STEADFAST_API_KEY", "")
SECRET_KEY = os.getenv("STEADFAST_SECRET_KEY", "")

PORT = int(os.getenv("PORT", "5000"))


def clean(value):
    return str(value or "").strip()


def clean_phone(phone):
    return re.sub(r"\D", "", str(phone or ""))


def validate_order(data):
    required = [
        "invoice",
        "customer_name",
        "customer_phone",
        "delivery_address",
        "district",
        "thana",
        "cod_amount",
    ]

    missing = [
        field for field in required
        if data.get(field) in (None, "")
    ]

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

    if len(clean(data["invoice"])) > 100:
        return "invoice is too long."

    if len(clean(data["customer_name"])) > 100:
        return "customer_name is too long."

    if len(clean(data["delivery_address"])) > 200:
        return "delivery_address is too long."

    if len(clean(data["district"])) > 100:
        return "district is too long."

    if len(clean(data["thana"])) > 100:
        return "thana is too long."

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
        "credentials_configured": bool(
            API_KEY and SECRET_KEY
        ),
    })


# -----------------------------------------
# GET STEADFAST POLICE STATIONS
# -----------------------------------------

@app.get("/steadfast/police_stations")
def police_stations():

    if not API_KEY or not SECRET_KEY:
        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured."
        }), 500

    try:
        response = requests.get(
            f"{STEADFAST_BASE_URL}/police_stations",
            headers=steadfast_headers(),
            timeout=30,
        )

        try:
            result = response.json()
        except ValueError:
            result = {
                "raw": response.text
            }

        return jsonify(result), response.status_code

    except requests.RequestException as e:

        return jsonify({
            "ok": False,
            "message": f"Could not reach Steadfast: {e}"
        }), 502


# -----------------------------------------
# CREATE STEADFAST ORDER
# -----------------------------------------

@app.post("/steadfast/order")
def create_order():

    if not API_KEY or not SECRET_KEY:
        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured on the server."
        }), 500

    data = request.get_json(silent=True) or {}

    error = validate_order(data)

    if error:
        return jsonify({
            "ok": False,
            "message": error
        }), 400

    invoice = clean(data["invoice"])
    customer_name = clean(data["customer_name"])
    customer_phone = clean_phone(data["customer_phone"])

    address = clean(data["delivery_address"])
    district = clean(data["district"])
    thana = clean(data["thana"])

    # -----------------------------------------
    # District + Thana address-এর সাথে যুক্ত হবে
    # -----------------------------------------

    location_parts = [
        address,
        thana,
        district
    ]

    location_parts = [
        x for x in location_parts if x
    ]

    recipient_address = ", ".join(location_parts)

    # Steadfast recipient_address max 250 chars
    recipient_address = recipient_address[:250]

    payload = {
        "invoice": invoice,
        "recipient_name": customer_name,
        "recipient_phone": customer_phone,
        "recipient_address": recipient_address,
        "cod_amount": float(data["cod_amount"]),
    }

    # -----------------------------------------
    # Optional fields
    # -----------------------------------------

    optional_fields = [
        "alternative_phone",
        "recipient_email",
        "note",
        "item_description",
        "total_lot",
        "delivery_type",
    ]

    for field in optional_fields:

        value = data.get(field)

        if value not in (None, ""):
            payload[field] = value

    try:

        response = requests.post(
            f"{STEADFAST_BASE_URL}/create_order",
            headers=steadfast_headers(),
            json=payload,
            timeout=30,
        )

        try:
            result = response.json()

        except ValueError:
            result = {
                "raw": response.text
            }

        if not response.ok:

            return jsonify({
                "ok": False,
                "message": "Steadfast API request failed.",
                "steadfast_status": response.status_code,
                "details": result,
            }), response.status_code

        consignment = result.get(
            "consignment"
        ) or {}

        return jsonify({

            "ok": True,

            "message": result.get(
                "message",
                "Order created successfully."
            ),

            "consignment_id": consignment.get(
                "consignment_id"
            ),

            "tracking_code": consignment.get(
                "tracking_code"
            ),

            "status": consignment.get(
                "status"
            ),

            "district": district,

            "thana": thana,

            "recipient_address": recipient_address,

            "consignment": consignment,
        })

    except requests.RequestException as e:

        return jsonify({
            "ok": False,
            "message": f"Could not reach Steadfast: {e}"
        }), 502


# -----------------------------------------
# STATUS BY INVOICE
# -----------------------------------------

@app.get("/steadfast/status/invoice/<path:invoice>")
def status_by_invoice(invoice):

    if not API_KEY or not SECRET_KEY:
        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured."
        }), 500

    try:

        response = requests.get(
            f"{STEADFAST_BASE_URL}/status_by_invoice/{invoice}",
            headers=steadfast_headers(),
            timeout=30,
        )

        try:
            result = response.json()

        except ValueError:
            result = {
                "raw": response.text
            }

        return jsonify(result), response.status_code

    except requests.RequestException as e:

        return jsonify({
            "ok": False,
            "message": f"Could not reach Steadfast: {e}"
        }), 502


# -----------------------------------------
# STATUS BY TRACKING
# -----------------------------------------

@app.get("/steadfast/status/tracking/<tracking_code>")
def status_by_tracking(tracking_code):

    if not API_KEY or not SECRET_KEY:
        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured."
        }), 500

    try:

        response = requests.get(
            f"{STEADFAST_BASE_URL}/status_by_trackingcode/{tracking_code}",
            headers=steadfast_headers(),
            timeout=30,
        )

        try:
            result = response.json()

        except ValueError:
            result = {
                "raw": response.text
            }

        return jsonify(result), response.status_code

    except requests.RequestException as e:

        return jsonify({
            "ok": False,
            "message": f"Could not reach Steadfast: {e}"
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
