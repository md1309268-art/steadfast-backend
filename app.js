const API_BASE =
  localStorage.getItem("STEADFAST_BACKEND_URL") ||
  "https://steadfast-backend-production-1e9b.up.railway.app";


const $ = (id) => document.getElementById(id);

const form = $("orderForm");
const districtEl = $("district");
const thanaEl = $("thana");
const messageEl = $("message");
const submitBtn = $("submitBtn");

let stations = [];


function clean(value) {
  return String(value ?? "").trim();
}


function showMessage(text, ok = false) {

  messageEl.textContent = text;

  messageEl.className =
    "msg " + (ok ? "ok" : "err");

  messageEl.style.display = "block";
}


function extractStations(payload) {

  const raw =
    payload?.stations ??
    payload?.police_stations ??
    payload?.data ??
    payload;

  if (!Array.isArray(raw)) {
    return [];
  }

  return raw
    .map((item) => {

      if (typeof item === "string") {

        return {
          name: clean(item),
          district: ""
        };
      }

      return {

        name: clean(
          item.name ??
          item.police_station ??
          item.station_name ??
          item.thana ??
          item.thana_name ??
          item.title ??
          item.area
        ),

        district: clean(
          item.district ??
          item.district_name ??
          item.city ??
          item.city_name ??
          ""
        )
      };
    })

    .filter((item) => item.name);
}


/*
---------------------------------------
Load District + Thana
---------------------------------------
*/

async function loadStations() {

  districtEl.innerHTML =
    '<option value="">জেলা নির্বাচন করুন</option>';

  thanaEl.innerHTML =
    '<option value="">আগে জেলা নির্বাচন করুন</option>';

  thanaEl.disabled = true;

  try {

    const response = await fetch(
      API_BASE + "/steadfast/police_stations",
      {
        method: "GET",
        headers: {
          Accept: "application/json"
        }
      }
    );

    const payload = await response.json();

    if (!response.ok) {

      throw new Error(
        payload.message ||
        "Police station load failed"
      );
    }

    stations = extractStations(payload);

    /*
    District list তৈরি
    */

    const districts = [
      ...new Set(
        stations
          .map((station) =>
            clean(station.district)
          )
          .filter(Boolean)
      )
    ].sort((a, b) =>
      a.localeCompare(b)
    );


    if (!districts.length) {

      showMessage(
        "Steadfast থেকে District mapping পাওয়া যায়নি। Backend police_stations response check করুন।"
      );

      return;
    }


    districts.forEach((district) => {

      districtEl.add(
        new Option(
          district,
          district
        )
      );

    });

  } catch (error) {

    showMessage(
      "জেলা/থানা লোড হয়নি: " +
      error.message
    );
  }
}


/*
---------------------------------------
District change
---------------------------------------
*/

districtEl.addEventListener(
  "change",
  () => {

    const district =
      clean(districtEl.value);

    /*
    পুরোনো Thana clear
    */

    thanaEl.innerHTML =
      '<option value="">থানা নির্বাচন করুন</option>';

    thanaEl.disabled = true;


    if (!district) {
      return;
    }


    /*
    Selected District-এর Thana
    */

    const list = stations
      .filter(
        (station) =>
          clean(station.district) === district
      )
      .map(
        (station) =>
          clean(station.name)
      )
      .filter(Boolean);


    const uniqueThanas = [
      ...new Set(list)
    ].sort((a, b) =>
      a.localeCompare(b)
    );


    if (!uniqueThanas.length) {

      thanaEl.innerHTML =
        '<option value="">এই জেলায় থানা পাওয়া যায়নি</option>';

      thanaEl.disabled = true;

      showMessage(
        "এই জেলার জন্য Steadfast-এর Thana পাওয়া যায়নি।"
      );

      return;
    }


    uniqueThanas.forEach((thana) => {

      thanaEl.add(
        new Option(
          thana,
          thana
        )
      );

    });


    thanaEl.disabled = false;

  }
);


/*
---------------------------------------
Form Data
---------------------------------------
*/

function getFormData() {

  return {

    invoice:
      clean($("invoice").value),

    customer_name:
      clean($("customer_name").value),

    customer_phone:
      clean($("customer_phone").value),

    delivery_address:
      clean($("delivery_address").value),

    district:
      clean(districtEl.value),

    thana:
      clean(thanaEl.value),

    cod_amount:
      Number(
        $("cod_amount").value || 0
      ),

    item_description:
      clean(
        $("item_description").value
      ),

    total_lot:
      Number(
        $("total_lot").value || 1
      ),

    note:
      clean($("note").value)
  };
}


/*
---------------------------------------
Clear form after successful entry
---------------------------------------
*/

function resetAfterSuccess() {

  form.reset();

  districtEl.innerHTML =
    '<option value="">জেলা নির্বাচন করুন</option>';

  thanaEl.innerHTML =
    '<option value="">আগে জেলা নির্বাচন করুন</option>';

  thanaEl.disabled = true;

  $("cod_amount").value = "0";

  $("total_lot").value = "1";

  /*
  নতুন Entry-এর জন্য আবার District load
  */

  loadStations();

  /*
  Invoice field-এ cursor
  */

  setTimeout(() => {
    $("invoice").focus();
  }, 100);
}


/*
---------------------------------------
Submit
---------------------------------------
*/

form.addEventListener(
  "submit",
  async (event) => {

    event.preventDefault();

    messageEl.style.display = "none";


    const data = getFormData();


    /*
    District validation
    */

    if (!data.district) {

      showMessage(
        "দয়া করে জেলা নির্বাচন করুন।"
      );

      districtEl.focus();

      return;
    }


    /*
    Thana validation
    */

    if (!data.thana) {

      showMessage(
        "দয়া করে থানা নির্বাচন করুন।"
      );

      thanaEl.focus();

      return;
    }


    /*
    Phone validation
    */

    if (
      !/^01\d{9}$/.test(
        data.customer_phone
      )
    ) {

      showMessage(
        "সঠিক ১১ সংখ্যার মোবাইল নম্বর দিন।"
      );

      $("customer_phone").focus();

      return;
    }


    /*
    Button loading
    */

    submitBtn.disabled = true;

    $("btnText").style.display =
      "none";

    $("spinner").style.display =
      "inline";


    try {

      const response = await fetch(
        API_BASE + "/steadfast/order",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",

            Accept:
              "application/json"
          },

          body:
            JSON.stringify(data)
        }
      );


      const result =
        await response.json();


      if (
        !response.ok ||
        !result.ok
      ) {

        throw new Error(
          result.message ||
          result.details?.message ||
          "Entry failed"
        );
      }


      /*
      --------------------------------
      SUCCESS
      --------------------------------
      */

      const tracking =
        result.tracking_code
          ? " Tracking: " +
            result.tracking_code
          : "";


      /*
      প্রথমে form clear
      */

      resetAfterSuccess();


      /*
      তারপর success message
      */

      showMessage(
        "✅ Entry সফল হয়েছে। Form clear করা হয়েছে." +
        tracking,
        true
      );


    } catch (error) {

      showMessage(
        "❌ Entry হয়নি: " +
        error.message
      );

    } finally {

      submitBtn.disabled = false;

      $("btnText").style.display =
        "inline";

      $("spinner").style.display =
        "none";
    }

  }
);


/*
---------------------------------------
Initial Load
---------------------------------------
*/

loadStations();
