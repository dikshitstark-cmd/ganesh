// --- Payment modal ---
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

// --- Row selection / bulk actions ---
document.addEventListener("DOMContentLoaded", function () {
  const rowChecks = document.querySelectorAll(".row-check");
  const selectAll = document.getElementById("selectAll");
  const countLabel = document.getElementById("selectedCount");
  const printBtn = document.getElementById("printSelectedBtn");
  const deleteBtn = document.getElementById("deleteSelectedBtn");

  function selectedIds() {
    return Array.from(rowChecks).filter(c => c.checked).map(c => c.value);
  }

  function refresh() {
    const ids = selectedIds();
    countLabel.textContent = ids.length + " selected";
    printBtn.disabled = ids.length === 0;
    deleteBtn.disabled = ids.length === 0;
  }

  rowChecks.forEach(cb => cb.addEventListener("change", refresh));

  if (selectAll) {
    selectAll.addEventListener("change", function () {
      rowChecks.forEach(cb => { cb.checked = selectAll.checked; });
      refresh();
    });
  }

  if (printBtn) {
    printBtn.addEventListener("click", function () {
      const ids = selectedIds();
      if (ids.length === 0) return;
      window.open("/receipts/print-selected?ids=" + ids.join(","), "_blank");
    });
  }

  if (deleteBtn) {
    deleteBtn.addEventListener("click", function () {
      const ids = selectedIds();
      if (ids.length === 0) return;
      if (!confirm("Delete " + ids.length + " selected receipt(s)? This cannot be undone.")) return;
      const form = document.getElementById("deleteSelectedForm");
      form.innerHTML = "";
      ids.forEach(id => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "ids";
        input.value = id;
        form.appendChild(input);
      });
      form.submit();
    });
  }

  refresh();
});
