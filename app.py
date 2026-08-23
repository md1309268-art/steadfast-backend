import os
import re

from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}}
)

# =========================================================
# STEADFAST CONFIG
# =========================================================

STEADFAST_BASE_URL = os.getenv(
    "STEADFAST_BASE_URL",
    "https://portal.packzy.com/api/v1"
).rstrip("/")

API_KEY = os.getenv("STEADFAST_API_KEY", "")
SECRET_KEY = os.getenv("STEADFAST_SECRET_KEY", "")

PORT = int(os.getenv("PORT", "5000"))


# =========================================================
# HELPERS
# =========================================================

def clean(value):
    return str(value or "").strip()


def clean_phone(phone):
    return re.sub(r"\D", "", str(phone or ""))


def steadfast_headers():
    return {
        "Api-Key": API_KEY,
        "Secret-Key": SECRET_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# =========================================================
# VALIDATION
# =========================================================

def validate_order(data):

    # District / Thana এখানে required করছি না।
    # কারণ Steadfast create_order API-তে এগুলো আলাদা
    # required field নয়।

    required = [
        "invoice",
        "customer_name",
        "customer_phone",
        "delivery_address",
        "cod_amount",
    ]

    missing = [
        field
        for field in required
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

    if len(str(data["invoice"])) > 100:
        return "invoice is too long."

    if len(str(data["customer_name"])) > 100:
        return "customer_name is too long."

    if len(str(data["delivery_address"])) > 250:
        return "delivery_address is too long (max 250 characters)."

    return None


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return jsonify({
        "ok": True,
        "service": "steadfast-backend",
        "credentials_configured": bool(
            API_KEY and SECRET_KEY
        ),
    })


# =========================================================
# GET DISTRICT / THANA LIST
# =========================================================

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

        if not response.ok:

            return jsonify({
                "ok": False,
                "message": "Could not load Steadfast police stations.",
                "steadfast_status": response.status_code,
                "details": result,
            }), response.status_code

        return jsonify(result), 200

    except requests.RequestException as e:

        return jsonify({
            "ok": False,
            "message": f"Could not reach Steadfast: {e}"
        }), 502


# =========================================================
# CREATE STEADFAST ORDER
# =========================================================

@app.post("/steadfast/order")
def create_order():

    if not API_KEY or not SECRET_KEY:

        return jsonify({
            "ok": False,
            "message": (
                "Steadfast API credentials are not "
                "configured on the server."
            )
        }), 500

    data = request.get_json(silent=True) or {}

    # Validate normal order fields
    error = validate_order(data)

    if error:

        return jsonify({
            "ok": False,
            "message": error
        }), 400

    # -----------------------------------------------------
    # CUSTOMER DATA
    # -----------------------------------------------------

    invoice = clean(data.get("invoice"))
    customer_name = clean(data.get("customer_name"))
    customer_phone = clean_phone(
        data.get("customer_phone")
    )

    # -----------------------------------------------------
    # ADDRESS + DISTRICT + THANA
    # -----------------------------------------------------

    delivery_address = clean(
        data.get("delivery_address")
    )

    district = clean(
        data.get("district")
    )

    thana = clean(
        data.get("thana")
    )

    # Build full address
    #
    # Example:
    # Cox bazar notun bari, Ramu, Cox's Bazar
    #

    address_parts = []

    if delivery_address:
        address_parts.append(delivery_address)

    if thana:
        address_parts.append(thana)

    if district:
        address_parts.append(district)

    full_address = ", ".join(address_parts)

    # Steadfast max address length is 250 characters
    if len(full_address) > 250:

        return jsonify({
            "ok": False,
            "message": (
                "Address + Thana + District is too long "
                "(max 250 characters)."
            )
        }), 400

    # -----------------------------------------------------
    # STEADFAST PAYLOAD
    # -----------------------------------------------------

    payload = {

        "invoice": invoice,

        "recipient_name": customer_name,

        "recipient_phone": customer_phone,

        "recipient_address": full_address,

        "cod_amount": float(
            data.get("cod_amount") or 0
        ),
    }

    # -----------------------------------------------------
    # OPTIONAL FIELDS
    # -----------------------------------------------------

    optional_fields = [

        ("alternative_phone", "alternative_phone"),

        ("recipient_email", "recipient_email"),

        ("note", "note"),

        ("item_description", "item_description"),

        ("total_lot", "total_lot"),

        ("delivery_type", "delivery_type"),
    ]

    for source, destination in optional_fields:

        value = data.get(source)

        if value not in (None, ""):

            payload[destination] = value

    # -----------------------------------------------------
    # SEND TO STEADFAST
    # -----------------------------------------------------

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

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        consignment = (
            result.get("consignment")
            or {}
        )

        return jsonify({

            "ok": True,

            "message": result.get(
                "message",
                "Order created successfully."
            ),

            "consignment_id":
                consignment.get(
                    "consignment_id"
                ),

            "tracking_code":
                consignment.get(
                    "tracking_code"
                ),

            "status":
                consignment.get(
                    "status"
                ),

            "consignment":
                consignment,

        }), 200

    except requests.RequestException as e:

        return jsonify({

            "ok": False,

            "message":
                f"Could not reach Steadfast: {e}"

        }), 502


# =========================================================
# STATUS BY INVOICE
# =========================================================

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

            "message":
                f"Could not reach Steadfast: {e}"

        }), 502


# =========================================================
# STATUS BY TRACKING CODE
# =========================================================

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

            "message":
                f"Could not reach Steadfast: {e}"

        }), 502


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
