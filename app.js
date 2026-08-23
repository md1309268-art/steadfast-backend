// Change this to your Railway backend URL if this HTML is hosted elsewhere.
const API_BASE = localStorage.getItem('STEADFAST_BACKEND_URL') || 'https://steadfast-backend-production-1e9b.up.railway.app';

const $ = (id) => document.getElementById(id);
const form = $('orderForm');
const districtEl = $('district');
const thanaEl = $('thana');
const messageEl = $('message');
const submitBtn = $('submitBtn');

function showMessage(text, ok=false) {
  messageEl.textContent = text;
  messageEl.className = 'msg ' + (ok ? 'ok' : 'err');
  messageEl.style.display = 'block';
}

function clean(v) { return String(v ?? '').trim(); }

function extractStations(payload) {
  // Supports common Steadfast response shapes: {stations:[]}, {data:[]}, {police_stations:[]}
  const raw = payload?.stations ?? payload?.police_stations ?? payload?.data ?? payload;
  if (!Array.isArray(raw)) return [];
  return raw.map(x => {
    if (typeof x === 'string') return {name:x, district:''};
    return {
      name: clean(x.name ?? x.police_station ?? x.station_name ?? x.thana ?? x.thana_name ?? x.title),
      district: clean(x.district ?? x.district_name ?? x.city ?? x.city_name ?? '')
    };
  }).filter(x => x.name);
}

let stations = [];

async function loadStations() {
  districtEl.innerHTML = '<option value="">জেলা নির্বাচন করুন</option>';
  thanaEl.innerHTML = '<option value="">জেলা নির্বাচন করুন</option>';
  thanaEl.disabled = true;
  try {
    const r = await fetch(API_BASE + '/steadfast/police_stations');
    const payload = await r.json();
    if (!r.ok) throw new Error(payload.message || 'Police station load failed');
    stations = extractStations(payload);
    const districts = [...new Set(stations.map(s => s.district).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
    if (!districts.length) {
      // If API returns stations without district metadata, keep district as manual text fallback.
      districtEl.innerHTML = '<option value="">জেলা নির্বাচন করুন</option>';
      showMessage('Steadfast police-station API-তে district mapping পাওয়া যায়নি। Backend response check করুন।');
      return;
    }
    districts.forEach(d => districtEl.add(new Option(d,d)));
  } catch (e) {
    showMessage('জেলা/থানা লোড হয়নি: ' + e.message);
  }
}

districtEl.addEventListener('change', () => {
  const district = clean(districtEl.value);
  thanaEl.innerHTML = '<option value="">থানা নির্বাচন করুন</option>';
  if (!district) { thanaEl.disabled = true; return; }
  const list = stations.filter(s => !s.district || s.district === district)
    .map(s=>s.name).filter((v,i,a)=>a.indexOf(v)===i).sort((a,b)=>a.localeCompare(b));
  list.forEach(t => thanaEl.add(new Option(t,t)));
  thanaEl.disabled = false;
});

function formData() {
  return {
    invoice: clean($('invoice').value),
    customer_name: clean($('customer_name').value),
    customer_phone: clean($('customer_phone').value),
    delivery_address: clean($('delivery_address').value),
    district: clean(districtEl.value),
    thana: clean(thanaEl.value),
    cod_amount: Number($('cod_amount').value || 0),
    item_description: clean($('item_description').value),
    total_lot: Number($('total_lot').value || 1),
    note: clean($('note').value)
  };
}

function resetAfterSuccess() {
  form.reset();
  districtEl.value = '';
  thanaEl.innerHTML = '<option value="">আগে জেলা নির্বাচন করুন</option>';
  thanaEl.disabled = true;
  $('cod_amount').value = '0';
  $('total_lot').value = '1';
  $('invoice').focus();
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  messageEl.style.display = 'none';
  const data = formData();
  if (!data.district || !data.thana) return showMessage('জেলা এবং থানা নির্বাচন করুন।');
  if (!/^01\d{9}$/.test(data.customer_phone)) return showMessage('সঠিক ১১ সংখ্যার মোবাইল নম্বর দিন।');

  submitBtn.disabled = true;
  $('btnText').style.display = 'none';
  $('spinner').style.display = 'inline';
  try {
    const r = await fetch(API_BASE + '/steadfast/order', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
    });
    const result = await r.json();
    if (!r.ok || !result.ok) {
      throw new Error(result.message || result.details?.message || 'Entry failed');
    }
    // Clear only the current form. Existing orders/history are untouched.
    resetAfterSuccess();
    const code = result.tracking_code ? ` Tracking: ${result.tracking_code}` : '';
    showMessage('Entry সফল হয়েছে। Form clear করা হয়েছে।' + code, true);
  } catch (err) {
    showMessage('Entry হয়নি: ' + err.message);
  } finally {
    submitBtn.disabled = false;
    $('btnText').style.display = 'inline';
    $('spinner').style.display = 'none';
  }
});

loadStations();
