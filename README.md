# Steadfast Frontend Fix

This is a replacement HTML/JS frontend because the uploaded backend ZIP did not contain the original HTML/JS files.

## Fixes
- Loads Steadfast police stations through the backend proxy.
- Filters Thana/Police Station after District selection.
- Sends `district` and `thana` to `/steadfast/order`.
- Clears only the current form after a successful entry; existing saved orders are not deleted.
- Prevents double submit while an entry is being sent.

## Backend URL
`app.js` defaults to:
`https://steadfast-backend-production-1e9b.up.railway.app`

You can change it in `app.js`, or in the browser console:
`localStorage.setItem('STEADFAST_BACKEND_URL', 'YOUR_BACKEND_URL')`
then reload.

## Important
Steadfast's documented `create_order` endpoint has `recipient_address` rather than separate District/Thana order fields. The backend therefore includes the selected District/Thana in the address and note. The `/police_stations` endpoint is used for the selection list.
