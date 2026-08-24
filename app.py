// ======================================================
// STEADFAST BACKEND URL
// ======================================================

const API_BASE =
  localStorage.getItem('STEADFAST_BACKEND_URL') ||
  'https://steadfast-backend-production-1e9b.up.railway.app';


// ======================================================
// ELEMENTS
// ======================================================

const $ = (id) => document.getElementById(id);

const form = $('orderForm');
const districtEl = $('district');
const thanaEl = $('thana');
const messageEl = $('message');
const submitBtn = $('submitBtn');


// ======================================================
// MESSAGE
// ======================================================

function showMessage(text, ok = false) {

  messageEl.textContent = text;

  messageEl.className =
    'msg ' + (ok ? 'ok' : 'err');

  messageEl.style.display = 'block';
}


function hideMessage() {
  messageEl.style.display = 'none';
}


// ======================================================
// CLEAN VALUE
// ======================================================

function clean(value) {
  return String(value ?? '').trim();
}


// ======================================================
// EXTRACT POLICE STATIONS
// ======================================================
//
// Steadfast response বিভিন্নভাবে আসতে পারে।
// তাই এখানে কয়েকটি possible response format support করা হয়েছে.
// ======================================================

function extractStations(payload) {

  let raw = [];

  if (Array.isArray(payload)) {
    raw = payload;
  }

  else if (Array.isArray(payload.stations)) {
    raw = payload.stations;
  }

  else if (Array.isArray(payload.police_stations)) {
    raw = payload.police_stations;
  }

  else if (Array.isArray(payload.data)) {
    raw = payload.data;
  }

  else if (payload.data && Array.isArray(payload.data.data)) {
    raw = payload.data.data;
  }

  else if (payload.data && Array.isArray(payload.data.stations)) {
    raw = payload.data.stations;
  }

  else if (payload.data && Array.isArray(payload.data.police_stations)) {
    raw = payload.data.police_stations;
  }


  return raw
    .map(item => {

      // যদি শুধু string হয়
      if (typeof item === 'string') {

        return {
          name: clean(item),
          district: ''
        };
      }


      // যদি object হয়
      return {

        name: clean(
          item.name ??
          item.police_station ??
          item.police_station_name ??
          item.station_name ??
          item.thana ??
          item.thana_name ??
          item.upazila ??
          item.upazila_name ??
          item.title
        ),

        district: clean(
          item.district ??
          item.district_name ??
          item.city ??
          item.city_name ??
          item.division ??
          ''
        )

      };

    })

    .filter(item => item.name);
}


// ======================================================
// ALL STATIONS
// ======================================================

let stations = [];


// ======================================================
// NORMALIZE BANGLA / ENGLISH TEXT
// ======================================================

function normalizeText(value) {

  return clean(value)
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();

}


// ======================================================
// LOAD DISTRICT + THANA
// ======================================================

async function loadStations() {

  districtEl.innerHTML =
    '<option value="">জেলা নির্বাচন করুন</option>';

  thanaEl.innerHTML =
    '<option value="">আগে জেলা নির্বাচন করুন</option>';

  thanaEl.disabled = true;

  stations = [];


  try {

    const response = await fetch(
      API_BASE + '/steadfast/police_stations',
      {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      }
    );


    let payload;

    try {
      payload = await response.json();
    }

    catch (jsonError) {

      throw new Error(
        'Backend থেকে সঠিক JSON response পাওয়া যায়নি।'
      );
    }


    if (!response.ok) {

      throw new Error(
        payload.message ||
        'District/Thana API failed.'
      );
    }


    stations = extractStations(payload);


    // -----------------------------------------------
    // যদি station data না আসে
    // -----------------------------------------------

    if (!stations.length) {

      throw new Error(
        'Steadfast থেকে District/Thana data পাওয়া যায়নি।'
      );
    }


    // -----------------------------------------------
    // District তৈরি
    // -----------------------------------------------

    const districtMap = new Map();


    stations.forEach(station => {

      const district = clean(station.district);

      if (!district) return;


      const key = normalizeText(district);

      if (!districtMap.has(key)) {

        districtMap.set(key, district);
      }

    });


    const districts =
      Array.from(districtMap.values())
        .sort((a, b) =>
          a.localeCompare(b, 'bn')
        );


    // -----------------------------------------------
    // District dropdown
    // -----------------------------------------------

    districts.forEach(district => {

      districtEl.add(
        new Option(
          district,
          district
        )
      );

    });


    if (!districts.length) {

      throw new Error(
        'Station data এসেছে, কিন্তু District mapping পাওয়া যায়নি।'
      );
    }


    showMessage(
      'District ও Thana list সফলভাবে লোড হয়েছে।',
      true
    );


    // কয়েক সেকেন্ড পরে message hide
    setTimeout(() => {

      if (messageEl.textContent.includes('District')) {
        hideMessage();
      }

    }, 3000);


  }

  catch (error) {

    console.error(
      'District/Thana Load Error:',
      error
    );


    showMessage(
      'District/Thana লোড হয়নি: ' +
      error.message
    );
  }

}


// ======================================================
// DISTRICT CHANGE
// ======================================================

districtEl.addEventListener(
  'change',
  function () {

    const selectedDistrict =
      clean(this.value);


    // -----------------------------------------------
    // Thana reset
    // -----------------------------------------------

    thanaEl.innerHTML =
      '<option value="">থানা নির্বাচন করুন</option>';

    thanaEl.disabled = true;


    if (!selectedDistrict) {
      return;
    }


    const selectedDistrictKey =
      normalizeText(selectedDistrict);


    // -----------------------------------------------
    // Selected district-এর Thana বের করা
    // -----------------------------------------------

    const thanaMap = new Map();


    stations.forEach(station => {

      const stationDistrict =
        normalizeText(station.district);


      if (
        stationDistrict === selectedDistrictKey
      ) {

        const thana =
          clean(station.name);


        if (!thana) return;


        const key =
          normalizeText(thana);


        if (!thanaMap.has(key)) {

          thanaMap.set(key, thana);
        }

      }

    });


    const thanas =
      Array.from(thanaMap.values())
        .sort((a, b) =>
          a.localeCompare(b, 'bn')
        );


    // -----------------------------------------------
    // Thana dropdown
    // -----------------------------------------------

    thanas.forEach(thana => {

      thanaEl.add(
        new Option(
          thana,
          thana
        )
      );

    });


    if (thanas.length) {

      thanaEl.disabled = false;

    }

    else {

      thanaEl.innerHTML =
        '<option value="">এই জেলার থানা পাওয়া যায়নি</option>';

      thanaEl.disabled = true;

    }

  }
);


// ======================================================
// FORM DATA
// ======================================================

function getFormData() {

  return {

    invoice:
      clean($('invoice').value),

    customer_name:
      clean($('customer_name').value),

    customer_phone:
      clean($('customer_phone').value),

    delivery_address:
      clean($('delivery_address').value),

    district:
      clean(districtEl.value),

    thana:
      clean(thanaEl.value),

    cod_amount:
      Number(
        $('cod_amount').value || 0
      ),

    item_description:
      clean($('item_description').value),

    total_lot:
      Number(
        $('total_lot').value || 1
      ),

    note:
      clean($('note').value)

  };

}


// ======================================================
// RESET FORM AFTER SUCCESS
// ======================================================

function resetAfterSuccess() {

  // পুরো form clear
  form.reset();


  // District আবার প্রথম option
  districtEl.value = '';


  // Thana reset
  thanaEl.innerHTML =
    '<option value="">আগে জেলা নির্বাচন করুন</option>';

  thanaEl.disabled = true;


  // Default values
  $('cod_amount').value = '0';

  $('total_lot').value = '1';


  // Invoice field-এ cursor
  setTimeout(() => {

    $('invoice').focus();

  }, 100);

}


// ======================================================
// SUBMIT ORDER
// ======================================================

form.addEventListener(
  'submit',
  async function (event) {

    event.preventDefault();

    hideMessage();


    const data =
      getFormData();


    // -----------------------------------------------
    // District validation
    // -----------------------------------------------

    if (!data.district) {

      showMessage(
        'দয়া করে জেলা নির্বাচন করুন।'
      );

      districtEl.focus();

      return;
    }


    // -----------------------------------------------
    // Thana validation
    // -----------------------------------------------

    if (!data.thana) {

      showMessage(
        'দয়া করে থানা নির্বাচন করুন।'
      );

      thanaEl.focus();

      return;
    }


    // -----------------------------------------------
    // Phone validation
    // -----------------------------------------------

    if (
      !/^01\d{9}$/.test(
        data.customer_phone
      )
    ) {

      showMessage(
        'সঠিক ১১ সংখ্যার মোবাইল নম্বর দিন।'
      );

      $('customer_phone').focus();

      return;
    }


    // -----------------------------------------------
    // COD validation
    // -----------------------------------------------

    if (
      Number.isNaN(data.cod_amount) ||
      data.cod_amount < 0
    ) {

      showMessage(
        'সঠিক COD Amount দিন।'
      );

      $('cod_amount').focus();

      return;
    }


    // -----------------------------------------------
    // Address validation
    // -----------------------------------------------

    if (!data.delivery_address) {

      showMessage(
        'সম্পূর্ণ ঠিকানা দিন।'
      );

      $('delivery_address').focus();

      return;
    }


    // -----------------------------------------------
    // Disable button
    // -----------------------------------------------

    submitBtn.disabled = true;


    const btnText =
      $('btnText');

    const spinner =
      $('spinner');


    if (btnText) {
      btnText.style.display = 'none';
    }


    if (spinner) {
      spinner.style.display = 'inline';
    }


    try {

      // ---------------------------------------------
      // Send order
      // ---------------------------------------------

      const response =
        await fetch(
          API_BASE + '/steadfast/order',
          {

            method: 'POST',

            headers: {
              'Content-Type':
                'application/json',

              'Accept':
                'application/json'
            },

            body:
              JSON.stringify(data)

          }
        );


      // ---------------------------------------------
      // Response JSON
      // ---------------------------------------------

      let result;

      try {

        result =
          await response.json();

      }

      catch (jsonError) {

        throw new Error(
          'Backend থেকে সঠিক response পাওয়া যায়নি।'
        );
      }


      // ---------------------------------------------
      // Error response
      // ---------------------------------------------

      if (
        !response.ok ||
        !result.ok
      ) {

        let errorMessage =
          result.message ||
          result.details?.message ||
          'Steadfast Entry failed.';


        // Steadfast API error থাকলে
        if (
          result.details &&
          typeof result.details === 'object'
        ) {

          const details =
            result.details;


          if (details.message) {

            errorMessage =
              details.message;

          }

          else if (details.errors) {

            errorMessage =
              JSON.stringify(
                details.errors
              );

          }

        }


        throw new Error(
          errorMessage
        );
      }


      // ---------------------------------------------
      // SUCCESS
      // ---------------------------------------------

      const tracking =
        result.tracking_code
          ? ' Tracking: ' +
            result.tracking_code
          : '';


      const consignmentId =
        result.consignment_id
          ? ' Consignment ID: ' +
            result.consignment_id
          : '';


      // ---------------------------------------------
      // প্রথমে success message
      // ---------------------------------------------

      showMessage(
        '✅ Steadfast Entry সফল হয়েছে।' +
        tracking +
        consignmentId,
        true
      );


      // ---------------------------------------------
      // তারপর form clear
      // ---------------------------------------------

      resetAfterSuccess();


    }

    catch (error) {

      console.error(
        'Steadfast Entry Error:',
        error
      );


      // ---------------------------------------------
      // Failed to fetch
      // ---------------------------------------------

      if (
        error.message ===
        'Failed to fetch'
      ) {

        showMessage(
          '❌ Backend-এর সাথে connection হচ্ছে না। ' +
          'Railway URL, Deployment এবং CORS check করুন।'
        );

      }

      else {

        showMessage(
          '❌ Steadfast Entry হয়নি: ' +
          error.message
        );

      }

    }

    finally {

      // ---------------------------------------------
      // Enable button
      // ---------------------------------------------

      submitBtn.disabled = false;


      if (btnText) {
        btnText.style.display = 'inline';
      }


      if (spinner) {
        spinner.style.display = 'none';
      }

    }

  }
);


// ======================================================
// BACKEND CONNECTION CHECK
// ======================================================

async function checkBackend() {

  try {

    const response =
      await fetch(
        API_BASE + '/health',
        {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        }
      );


    const result =
      await response.json();


    console.log(
      'Steadfast Backend:',
      result
    );


    if (!response.ok || !result.ok) {

      showMessage(
        'Backend connection ঠিক নেই।'
      );

      return false;
    }


    return true;

  }

  catch (error) {

    console.error(
      'Backend Check Error:',
      error
    );

    showMessage(
      'Backend-এর সাথে connection হচ্ছে না।'
    );

    return false;
  }

}


// ======================================================
// START
// ======================================================

(async function () {

  const connected =
    await checkBackend();


  if (connected) {

    await loadStations();

  }

})();
