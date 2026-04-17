(function () {
  function safeNumber(x) {
    const n = Number(x);
    return Number.isFinite(n) ? n : 0;
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function formatYMD(dateObj) {
    const yyyy = dateObj.getFullYear();
    const mm = pad2(dateObj.getMonth() + 1);
    const dd = pad2(dateObj.getDate());
    // Backend parser format: %Y/%m/%d
    return `${yyyy}/${mm}/${dd}`;
  }

  function normalizeDateInputToYMD(dateValue) {
    // input[type=date] -> YYYY-MM-DD, backend expects YYYY/MM/DD
    return (dateValue || "").replaceAll("-", "/");
  }

  function formatShortDateEn(dateObj) {
    return dateObj.toLocaleDateString("en-US", { month: "short", day: "2-digit" });
  }

  function formatWeekdayDateEn(dateObj) {
    return dateObj.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "2-digit" });
  }

  function buildTimeSlots() {
    return [
      { label: "09:00-10:00", start: "09:00" },
      { label: "10:00-11:00", start: "10:00" },
      { label: "11:00-12:00", start: "11:00" },
      { label: "14:00-15:00", start: "14:00" },
      { label: "15:00-16:00", start: "15:00" },
      { label: "16:00-17:00", start: "16:00" },
    ];
  }

  function initCharts() {
    const scoring = window.__SCORING__ || {};
    const dimMap = scoring.dimension_scores || {};

    // stable A-F order (fallback to Object iteration)
    const orderedKeys = ["A", "B", "C", "D", "E", "F"];
    const dims = orderedKeys.map(function (k) {
      return dimMap[k] || null;
    }).filter(Boolean);

    const labels = dims.map(function (d) { return d.dimension || ""; });
    const scores = dims.map(function (d) { return safeNumber(d.score); });
    const maxs = dims.map(function (d) { return safeNumber(d.max); });

    const totalScore = safeNumber(scoring.total_score);
    const riskLevel = scoring.risk_level || "E";

    // Interpretation: best/worst
    const interpEl = document.getElementById("riskInterpretation");
    if (interpEl) {
      if (dims.length) {
        let best = dims[0], worst = dims[0];
        dims.forEach(function (d) {
          if (safeNumber(d.score) > safeNumber(best.score)) best = d;
          if (safeNumber(d.score) < safeNumber(worst.score)) worst = d;
        });
        interpEl.innerText = `Stronger dimension: ${best.dimension} (${best.score}), weaker dimension: ${worst.dimension} (${worst.score}).`;
      } else {
        interpEl.innerText = "Current data is insufficient to generate dimension interpretation.";
      }
    }

    if (!window.Chart) return;

    // Radar chart
    const radarEl = document.getElementById("scoreRadarChart");
    if (radarEl) {
      const radarLoading = document.getElementById("radarLoading");
      if (radarLoading) radarLoading.style.display = "block";

      new Chart(radarEl, {
        type: "radar",
        data: {
          labels: labels.length ? labels : ["A", "B", "C", "D", "E", "F"],
          datasets: [{
            label: "Score",
            data: scores.length ? scores : [0, 0, 0, 0, 0, 0],
            borderColor: "rgba(13,110,253,0.95)",
            backgroundColor: "rgba(13,110,253,0.18)",
            pointBackgroundColor: "rgba(13,110,253,1)",
            pointRadius: 3,
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            r: {
              suggestedMin: 0,
              // use 20 as a safe upper bound across dimensions
              suggestedMax: 20,
              ticks: { display: false },
              grid: { color: "rgba(13,110,253,0.08)" }
            }
          }
        }
      });

      if (radarLoading) radarLoading.style.display = "none";
    }

    // Bar chart
    const barEl = document.getElementById("scoreBarChart");
    if (barEl) {
      const barLoading = document.getElementById("barLoading");
      if (barLoading) barLoading.style.display = "block";

      new Chart(barEl, {
        type: "bar",
        data: {
          labels: labels.length ? labels : ["A", "B", "C", "D", "E", "F"],
          datasets: [{
            label: "Dimension score",
            data: scores.length ? scores : [0, 0, 0, 0, 0, 0],
            backgroundColor: "rgba(13,110,253,0.18)",
            borderColor: "rgba(13,110,253,0.85)",
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: "rgba(0,0,0,0.06)" },
              suggestedMax: 20
            }
          }
        }
      });

      if (barLoading) barLoading.style.display = "none";
    }

    // Doughnut: score vs remaining
    const doughEl = document.getElementById("riskDoughnutChart");
    if (doughEl) {
      const v = Math.max(0, Math.min(100, totalScore));
      new Chart(doughEl, {
        type: "doughnut",
        data: {
          labels: ["Score", "Remaining"],
          datasets: [{
            data: [v, 100 - v],
            backgroundColor: ["rgba(13,110,253,0.88)", "rgba(0,0,0,0.08)"],
            borderWidth: 0
          }]
        },
        options: {
          responsive: false,
          cutout: "72%",
          plugins: { legend: { display: false }, tooltip: { enabled: false } }
        }
      });
    }
  }

  function initTimeSelectors() {
    const timeSlots = buildTimeSlots();
    const grids = document.querySelectorAll(".time-grid");
    const today = new Date();

    grids.forEach(function (gridEl) {
      const productId = gridEl.getAttribute("data-product-id");
      const dateStripEl = document.getElementById("dateStrip" + productId);
      const previewEl = document.getElementById("timePreview" + productId);
      const preferredDateInput = document.getElementById("preferred_date_" + productId);
      const preferredTimeInput = document.getElementById("preferred_time_" + productId);
      const submitBtn = document.getElementById("submitAppointment" + productId);
      const customDateInput = document.getElementById("customDate" + productId);
      const customTimeInput = document.getElementById("customTime" + productId);

      if (!productId) return;

      let selectedCell = null;

      // future 7 days
      const dates = [];
      for (let i = 1; i <= 7; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() + i);
        dates.push(d);
      }

      if (dateStripEl) {
        dateStripEl.innerHTML = "";
        dates.forEach(function (d) {
          const span = document.createElement("span");
          span.className = "chip chip-info me-2 mb-2";
          span.innerText = formatShortDateEn(d);
          dateStripEl.appendChild(span);
        });
      }

      // Set custom date min as today to align backend validation.
      if (customDateInput) {
        customDateInput.min = new Date().toISOString().slice(0, 10);
      }

      const table = document.createElement("table");
      const thead = document.createElement("thead");
      const trHead = document.createElement("tr");

      const thDate = document.createElement("th");
      thDate.innerText = "Date";
      trHead.appendChild(thDate);

      timeSlots.forEach(function (slot) {
        const th = document.createElement("th");
        th.innerText = slot.label;
        trHead.appendChild(th);
      });
      thead.appendChild(trHead);
      table.appendChild(thead);

      const tbody = document.createElement("tbody");
      dates.forEach(function (d) {
        const tr = document.createElement("tr");

        const tdDate = document.createElement("td");
        tdDate.style.whiteSpace = "nowrap";
        tdDate.innerText = formatWeekdayDateEn(d);
        tr.appendChild(tdDate);

        timeSlots.forEach(function (slot) {
          const td = document.createElement("td");
          const cell = document.createElement("div");
          cell.className = "time-cell";
          cell.tabIndex = 0;
          cell.setAttribute("role", "button");

          cell.dataset.date = formatYMD(d);
          cell.dataset.time = slot.start;
          cell.innerText = slot.label;

          cell.addEventListener("click", function () {
            if (cell.classList.contains("unavailable")) return;
            if (selectedCell) selectedCell.classList.remove("selected");
            selectedCell = cell;
            selectedCell.classList.add("selected");

            if (preferredDateInput) preferredDateInput.value = cell.dataset.date;
            if (preferredTimeInput) preferredTimeInput.value = slot.start;
            if (previewEl) previewEl.innerText = `${cell.dataset.date} ${slot.start}`;
            if (submitBtn) submitBtn.disabled = false;
            if (customDateInput) customDateInput.value = cell.dataset.date.replaceAll("/", "-");
            if (customTimeInput) customTimeInput.value = slot.start;
          });

          cell.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              cell.click();
            }
          });

          td.appendChild(cell);
          tr.appendChild(td);
        });

        tbody.appendChild(tr);
      });
      table.appendChild(tbody);

      gridEl.innerHTML = "";
      gridEl.appendChild(table);

      // Keep button available; validate required date/time selection at submit time.
      if (submitBtn) submitBtn.disabled = false;

      // Manual custom picker support (not limited to next 7-day table).
      function syncFromCustomInputs() {
        const d = customDateInput ? customDateInput.value : "";
        const t = customTimeInput ? customTimeInput.value : "";
        if (d && t) {
          const formattedDate = normalizeDateInputToYMD(d);
          if (preferredDateInput) preferredDateInput.value = formattedDate;
          if (preferredTimeInput) preferredTimeInput.value = t.slice(0, 5);
          if (previewEl) previewEl.innerText = `${formattedDate} ${t.slice(0, 5)}`;
          if (submitBtn) submitBtn.disabled = false;
        }
      }
      if (customDateInput) customDateInput.addEventListener("change", syncFromCustomInputs);
      if (customTimeInput) customTimeInput.addEventListener("change", syncFromCustomInputs);

      const formEl = gridEl.closest("form");
      if (formEl) {
        formEl.addEventListener("submit", function (e) {
          const selectedDate = preferredDateInput ? preferredDateInput.value : "";
          const selectedTime = preferredTimeInput ? preferredTimeInput.value : "";
          if (!selectedDate || !selectedTime) {
            e.preventDefault();
            if (previewEl) {
              previewEl.innerText = "Please choose date and time (table slot or custom picker) before submitting.";
            }
            window.alert("Please choose date and time (table slot or custom picker) before submitting.");
          }
        });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initCharts();
    initTimeSelectors();
  });
})();

