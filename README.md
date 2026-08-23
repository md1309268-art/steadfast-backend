# Steadfast Backend for Order Hisab App

This small Flask API keeps the Steadfast API Key and Secret Key on the server, not inside the HTML app.

## 1. Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Configure

Copy `.env.example` to `.env` and put your Steadfast API credentials there.

Do NOT put the API key/secret in the HTML file or share them in chat.

## 3. Run

```bash
python app.py
```

The backend will listen on:
`http://127.0.0.1:5000`

Health check:
`GET /health`

Order endpoint:
`POST /steadfast/order`

## 4. Connect the HTML app

In the updated HTML app, set the Steadfast backend URL to:

`http://YOUR_SERVER_IP:5000/steadfast/order`

If the HTML is opened from a different device/network, use a public HTTPS backend URL instead.

## Order JSON accepted

```json
{
  "invoice": "ORD-1001",
  "customer_name": "Customer Name",
  "customer_phone": "01712345678",
  "delivery_address": "House/Road/Area | Thana, District",
  "cod_amount": 1200,
  "product": "Product name",
  "quantity": 1
}
```

The backend maps these to Steadfast's create-order fields and returns the consignment ID and tracking code.

## Production notes

- Use HTTPS.
- Restrict CORS to your actual app origin instead of `*`.
- Add your own authentication/rate limit before exposing this endpoint publicly.
- Keep `.env` private and never commit it to Git.
