import os
import re

from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False
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
# COMMON FUNCTIONS
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


def credentials_ok():
    return bool(API_KEY and SECRET_KEY)


# =========================================================
# ORDER VALIDATION
# =========================================================

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

    missing = []

    for field in required:
        value = data.get(field)

        if value is None or clean(value) == "":
            missing.append(field)

    if missing:
        return "Missing fields: " + ", ".join(missing)

    # -----------------------------------------------------
    # PHONE
    # -----------------------------------------------------

    phone = clean_phone(data.get("customer_phone"))

    if len(phone) != 11 or not phone.startswith("01"):
        return "customer_phone must be an 11-digit Bangladesh mobile number."

    # -----------------------------------------------------
    # COD
    # -----------------------------------------------------

    try:
        cod = float(data.get("cod_amount"))

        if cod < 0:
            return "cod_amount must be >= 0."

    except (TypeError, ValueError):
        return "cod_amount must be a number."

    # -----------------------------------------------------
    # LENGTH VALIDATION
    # -----------------------------------------------------

    if len(clean(data.get("invoice"))) > 100:
        return "invoice is too long."

    if len(clean(data.get("customer_name"))) > 100:
        return "customer_name is too long."

    if len(clean(data.get("delivery_address"))) > 250:
        return "delivery_address is too long (max 250 characters)."

    if len(clean(data.get("district"))) > 100:
        return "district is too long."

    if len(clean(data.get("thana"))) > 100:
        return "thana is too long."

    return None


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def home():

    return jsonify({
        "ok": True,
        "service": "steadfast-backend",
        "message": "Steadfast backend is running."
    })


@app.get("/health")
def health():

    return jsonify({
        "ok": True,
        "service": "steadfast-backend",
        "credentials_configured": credentials_ok(),
        "base_url": STEADFAST_BASE_URL
    })


# =========================================================
# DISTRICT + THANA / POLICE STATIONS
# =========================================================

@app.get("/steadfast/police_stations")
def police_stations():

    if not credentials_ok():

        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured on the server."
        }), 500

    try:

        response = requests.get(
            f"{STEADFAST_BASE_URL}/police_stations",
            headers=steadfast_headers(),
            timeout=30
        )

        # -------------------------------------------------
        # TRY JSON
        # -------------------------------------------------

        try:
            result = response.json()

        except ValueError:

            return jsonify({
                "ok": False,
                "message": "Steadfast returned a non-JSON response.",
                "status_code": response.status_code,
                "raw": response.text[:2000]
            }), response.status_code

        # -------------------------------------------------
        # STEADFAST ERROR
        # -------------------------------------------------

        if not response.ok:

            return jsonify({
                "ok": False,
                "message": "Steadfast police station request failed.",
                "steadfast_status": response.status_code,
                "details": result
            }), response.status_code

        # -------------------------------------------------
        # NORMAL RESPONSE
        # -------------------------------------------------

        return jsonify(result), response.status_code

    except requests.RequestException as e:

        return jsonify({
            "ok": False,
            "message": "Could not reach Steadfast police station API.",
            "error": str(e)
        }), 502


# =========================================================
# CREATE STEADFAST ORDER
# =========================================================

@app.post("/steadfast/order")
def create_order():

    if not credentials_ok():

        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured on the server."
        }), 500

    data = request.get_json(silent=True) or {}

    # -----------------------------------------------------
    # VALIDATE
    # -----------------------------------------------------

    error = validate_order(data)

    if error:

        return jsonify({
            "ok": False,
            "message": error
        }), 400

    # -----------------------------------------------------
    # ADDRESS
    #
    # Steadfast's create_order API requires one
    # recipient_address field.
    #
    # We combine:
    # District + Thana + user's address
    #
    # Example:
    # Cox's Bazar, Ramu, Notun Bari
    # -----------------------------------------------------

    district = clean(data.get("district"))
    thana = clean(data.get("thana"))
    address = clean(data.get("delivery_address"))

    full_address = f"{address} | {thana}, {district}"

    # Steadfast max address length is 250 characters.
    if len(full_address) > 250:

        return jsonify({
            "ok": False,
            "message": "Combined delivery address is longer than 250 characters."
        }), 400

    # -----------------------------------------------------
    # MAIN PAYLOAD
    # -----------------------------------------------------

    payload = {
        "invoice": clean(data.get("invoice")),

        "recipient_name": clean(
            data.get("customer_name")
        ),

        "recipient_phone": clean_phone(
            data.get("customer_phone")
        ),

        "recipient_address": full_address,

        "cod_amount": float(
            data.get("cod_amount") or 0
        ),
    }

    # -----------------------------------------------------
    # OPTIONAL FIELDS
    # -----------------------------------------------------

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

            if field == "alternative_phone":

                payload[field] = clean_phone(value)

            else:

                payload[field] = value

    # -----------------------------------------------------
    # SEND TO STEADFAST
    # -----------------------------------------------------

    try:

        response = requests.post(
            f"{STEADFAST_BASE_URL}/create_order",
            headers=steadfast_headers(),
            json=payload,
            timeout=30
        )

        # -------------------------------------------------
        # JSON RESPONSE
        # -------------------------------------------------

        try:
            result = response.json()

        except ValueError:

            return jsonify({
                "ok": False,
                "message": "Steadfast returned a non-JSON response.",
                "steadfast_status": response.status_code,
                "raw": response.text[:3000]
            }), response.status_code

        # -------------------------------------------------
        # STEADFAST ERROR
        # -------------------------------------------------

        if not response.ok:

            return jsonify({
                "ok": False,
                "message": "Steadfast API request failed.",
                "steadfast_status": response.status_code,
                "details": result
            }), response.status_code

        # -------------------------------------------------
        # CONSIGNMENT
        # -------------------------------------------------

        consignment = result.get("consignment") or {}

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

            "consignment": consignment,

            # Keep these so frontend can confirm
            # what was actually sent.
            "district": district,

            "thana": thana,

            "recipient_address": full_address

        }), response.status_code

    except requests.RequestException as e:

        return jsonify({
            "ok": False,
            "message": "Could not reach Steadfast.",
            "error": str(e)
        }), 502


# =========================================================
# STATUS BY INVOICE
# =========================================================

@app.get("/steadfast/status/invoice/<path:invoice>")
def status_by_invoice(invoice):

    if not credentials_ok():

        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured on the server."
        }), 500

    try:

        response = requests.get(
            f"{STEADFAST_BASE_URL}/status_by_invoice/{invoice}",
            headers=steadfast_headers(),
            timeout=30
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
            "message": "Could not reach Steadfast.",
            "error": str(e)
        }), 502


# =========================================================
# STATUS BY TRACKING CODE
# =========================================================

@app.get("/steadfast/status/tracking/<tracking_code>")
def status_by_tracking(tracking_code):

    if not credentials_ok():

        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured on the server."
        }), 500

    try:

        response = requests.get(
            f"{STEADFAST_BASE_URL}/status_by_trackingcode/{tracking_code}",
            headers=steadfast_headers(),
            timeout=30
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
            "message": "Could not reach Steadfast.",
            "error": str(e)
        }), 502


# =========================================================
# STATUS BY CONSIGNMENT ID
# =========================================================

@app.get("/steadfast/status/cid/<int:consignment_id>")
def status_by_cid(consignment_id):

    if not credentials_ok():

        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured on the server."
        }), 500

    try:

        response = requests.get(
            f"{STEADFAST_BASE_URL}/status_by_cid/{consignment_id}",
            headers=steadfast_headers(),
            timeout=30
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
            "message": "Could not reach Steadfast.",
            "error": str(e)
        }), 502


# =========================================================
# BALANCE
# =========================================================

@app.get("/steadfast/balance")
def balance():

    if not credentials_ok():

        return jsonify({
            "ok": False,
            "message": "Steadfast API credentials are not configured on the server."
        }), 500

    try:

        response = requests.get(
            f"{STEADFAST_BASE_URL}/get_balance",
            headers=steadfast_headers(),
            timeout=30
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
            "message": "Could not reach Steadfast.",
            "error": str(e)
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
