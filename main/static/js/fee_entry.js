// static/js/fee_entry.js

document.addEventListener("DOMContentLoaded", function () {
  const btnLookup = document.getElementById("btn-lookup");
  const btnSubmit = document.getElementById("btn-submit-payment");
  const alertContainer = document.getElementById("alert-container");

  // Form inputs
  const inGrade = document.getElementById("grade");
  const inFname = document.getElementById("fname");
  const inLname = document.getElementById("lname");
  const inTotalFee = document.getElementById("total-fee");
  const inFeesPaid = document.getElementById("fees-paid");
  const inRemaining = document.getElementById("remaining-fee");
  const inNewPayment = document.getElementById("new-payment");
  const paymentSection = document.getElementById("payment-section");
  const studentHeader = document.getElementById("student-header");
  const paymentsTableBody = document.querySelector("#payments-table tbody");

  let currentStudentId = null;
  let isExistingStudent = false;

  function showAlert(message, type = "danger") {
    alertContainer.innerHTML = `
      <div class="alert alert-${type} alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>`;
  }

  function clearAlert() {
    alertContainer.innerHTML = "";
  }

  // Populate payment fields and table
  function populatePaymentSection(data) {
    currentStudentId = data.student_id;
    isExistingStudent = true;

    inTotalFee.value = data.total_fees.toFixed(2);
    inFeesPaid.value = data.fees_paid.toFixed(2);
    inRemaining.value = data.remaining_fee.toFixed(2);

    // Make Total Fee readonly (existing student)
    inTotalFee.readOnly = true;

    studentHeader.textContent = `Student: ${inFname.value.trim()} ${inLname.value.trim()} (Grade ${inGrade.value.trim()})`;

    // Populate payments table
    paymentsTableBody.innerHTML = "";
    data.payments.forEach((p, idx) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <th scope="row">${idx + 1}</th>
        <td>${new Date(p.date_paid).toLocaleDateString()}</td>
        <td>₹ ${p.amount_paid.toFixed(2)}</td>
      `;
      paymentsTableBody.appendChild(row);
    });

    paymentSection.style.display = "block";
  }

  // Show new-student form (allow editing total-fee)
  function showNewStudentSection() {
    isExistingStudent = false;
    currentStudentId = null;

    // Clear previous fields
    inTotalFee.value = "";
    inFeesPaid.value = "0.00";
    inRemaining.value = "";

    inTotalFee.readOnly = false;
    inFeesPaid.readOnly = true;
    inRemaining.readOnly = true;

    studentHeader.textContent = `New Student: ${inFname.value.trim()} ${inLname.value.trim()} (Grade ${inGrade.value.trim()})`;
    paymentsTableBody.innerHTML = "";
    paymentSection.style.display = "block";
  }

  // Handle "Lookup" click
  btnLookup.addEventListener("click", function () {
    clearAlert();
    const grade = inGrade.value.trim();
    const fname = inFname.value.trim();
    const lname = inLname.value.trim();

    if (!grade || !fname || !lname) {
      showAlert("Please fill Grade, First Name, and Last Name.");
      return;
    }

    fetch(`/api/student/lookup?grade=${encodeURIComponent(grade)}&fname=${encodeURIComponent(fname)}&lname=${encodeURIComponent(lname)}`)
      .then(response => response.json())
      .then((data) => {
        if (data.error) {
          showAlert(data.error);
          return;
        }
        if (data.exists) {
          populatePaymentSection(data);
        } else {
          showNewStudentSection();
        }
      })
      .catch((err) => {
        console.error(err);
        showAlert("An error occurred while looking up the student.");
      });
  });

  // Handle "Submit Payment" click
  btnSubmit.addEventListener("click", function () {
    clearAlert();
    const grade = inGrade.value.trim();
    const fname = inFname.value.trim();
    const lname = inLname.value.trim();
    const totalFeesVal = inTotalFee.value.trim();
    const paymentVal = inNewPayment.value.trim();

    if (!grade || !fname || !lname) {
      showAlert("Grade, First Name, and Last Name are required.");
      return;
    }
    if (!paymentVal) {
      showAlert("Please enter a payment amount.");
      return;
    }

    const payload = {
      grade: grade,
      fname: fname,
      lname: lname,
      payment_amount: parseFloat(paymentVal)
    };

    if (!isExistingStudent) {
      // new student: total_fees is required
      if (!totalFeesVal) {
        showAlert("Please enter Total Fee for new student.");
        return;
      }
      payload.total_fees = parseFloat(totalFeesVal);
    }

    fetch("/api/student/payment", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    })
      .then(response => response.json().then(data => ({ status: response.status, body: data })))
      .then(({ status, body }) => {
        if (status !== 200 || body.error) {
          showAlert(body.error || "An error occurred while recording payment.");
          return;
        }
        // On success, re-populate the payment section
        populatePaymentSection({
          student_id: body.student_id,
          total_fees: body.total_fees,
          fees_paid: body.fees_paid,
          remaining_fee: body.remaining_fee,
          payments: body.payments
        });
        inNewPayment.value = "";
        showAlert("Payment recorded successfully.", "success");
      })
      .catch((err) => {
        console.error(err);
        showAlert("An error occurred while recording payment.");
      });
  });
});
