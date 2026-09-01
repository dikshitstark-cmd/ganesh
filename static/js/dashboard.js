function openPaymentModal(receiptId, receiptNo, total, paid) {
  const modal = document.getElementById("paymentModal");
  const form = document.getElementById("paymentForm");
  document.getElementById("modalReceiptNo").textContent = receiptNo;
  document.getElementById("modalTotal").textContent = Number(total).toFixed(2);
  document.getElementById("paidInput").value = paid;
  document.getElementById("paidInput").max = total;
  form.action = "/receipt/" + receiptId + "/payment";
  modal.classList.remove("hidden");
}

function closePaymentModal() {
  document.getElementById("paymentModal").classList.add("hidden");
}

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") closePaymentModal();
});

// ---- Bulk selection / bulk print ----
function toggleSelectAll(checkbox) {
  document.querySelectorAll(".row-check").forEach(cb => { cb.checked = checkbox.checked; });
  updateBulkPrintState();
}

function updateBulkPrintState() {
  const all = document.querySelectorAll(".row-check");
  const checked = document.querySelectorAll(".row-check:checked").length;
  const btn = document.getElementById("bulkPrintBtn");
  if (btn) btn.disabled = checked === 0;
  const allBox = document.getElementById("selectAll");
  if (allBox) allBox.checked = all.length > 0 && checked === all.length;
}

function submitBulkPrint(e) {
  e.preventDefault();
  const ids = Array.from(document.querySelectorAll(".row-check:checked")).map(cb => cb.value);
  if (ids.length === 0) return false;
  window.open("/print/bulk?ids=" + ids.join(","), "_blank");
  return false;
}