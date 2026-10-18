/* Airport Operations Coordination Engine
   Gates, Staff & Resource Management
   All records below are illustrative demo data, not live airport information. */
(() => {
  "use strict";

  const gateRecords = [
    { id: "A1", terminal: "International Terminal", status: "Available", flight: "No flight assigned", route: "Ready for allocation", window: "Available now", image: "photo-1436491865332-7a61a109cc05" },
    { id: "A2", terminal: "International Terminal", status: "Occupied", flight: "AI 203", route: "Chennai → Singapore", window: "10:30 – 13:15", image: "photo-1542296332-2e4473faf563" },
    { id: "B1", terminal: "Domestic Terminal", status: "Available", flight: "No flight assigned", route: "Ready for allocation", window: "Available now", image: "photo-1521727857535-28d2047314ac" },
    { id: "B2", terminal: "Domestic Terminal", status: "Occupied", flight: "6E 412", route: "Chennai → Mumbai", window: "11:10 – 12:45", image: "photo-1517479149777-5f3b1511d5ad" },
    { id: "C3", terminal: "International Terminal", status: "Occupied", flight: "SQ 525", route: "Chennai → Singapore", window: "12:00 – 14:10", image: "photo-1515569067071-ec3b51335dd0" },
    { id: "C5", terminal: "Domestic Terminal", status: "Maintenance", flight: "No assignment", route: "Scheduled maintenance", window: "09:00 – 14:00", image: "photo-1569154941061-e231b4725ef1" },
    { id: "D1", terminal: "Domestic Terminal", status: "Available", flight: "No flight assigned", route: "Ready for allocation", window: "Available now", image: "photo-1436491865332-7a61a109cc05" },
    { id: "D2", terminal: "International Terminal", status: "Maintenance", flight: "No assignment", route: "Equipment inspection", window: "13:00 – 15:00", image: "photo-1542296332-2e4473faf563" }
  ];

  const staffRecords = [
    { id: "ST001", name: "Priya S", role: "Ground Staff", status: "On Duty", gate: "A2", shift: "06:00–14:00" },
    { id: "ST002", name: "Arjun K", role: "Ramp Agent", status: "Available", gate: "Unassigned", shift: "06:00–14:00" },
    { id: "ST003", name: "Meera N", role: "Security", status: "On Duty", gate: "B1", shift: "14:00–22:00" },
    { id: "ST004", name: "Karthik R", role: "Passenger Support", status: "On Break", gate: "Unassigned", shift: "06:00–14:00" },
    { id: "ST005", name: "Sneha P", role: "Operations", status: "Available", gate: "Unassigned", shift: "14:00–22:00" },
    { id: "ST006", name: "Dev R", role: "Ground Staff", status: "On Duty", gate: "C3", shift: "06:00–14:00" },
    { id: "ST007", name: "Nisha V", role: "Maintenance", status: "On Duty", gate: "C5", shift: "09:00–17:00" },
    { id: "ST008", name: "Omar A", role: "Security", status: "Available", gate: "Unassigned", shift: "14:00–22:00" }
  ];

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const gateGrid = $("#gateGrid");
  const staffTableBody = $("#staffTableBody");
  const modal = $("#actionModal");
  const modalFields = $("#modalFields");
  const modalForm = $("#actionForm");
  const toast = $("#toast");
  let gateFilter = "All";
  let toastTimer;
  let pendingAction = null;

  const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);

  const initials = (name) => name.split(/\s+/).map(part => part[0] || "").join("").slice(0, 2).toUpperCase();
  const gateStateClass = (status) => status === "Available" ? "status-available" : status === "Occupied" ? "status-occupied" : "status-maintenance";
  const staffStateClass = (status) => status === "Available" ? "available" : status === "On Break" ? "on-break" : "on-duty";
  const statusForFilter = (status) => status === "Maintenance" ? "Maintenance" : status;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
  }

  function getGateCounts() {
    return gateRecords.reduce((counts, gate) => {
      counts.total += 1;
      if (gate.status === "Available") counts.available += 1;
      else if (gate.status === "Occupied") counts.occupied += 1;
      else counts.unavailable += 1;
      return counts;
    }, { total: 0, available: 0, occupied: 0, unavailable: 0 });
  }

  function renderGateSummary() {
    const counts = getGateCounts();
    const percent = value => counts.total ? Math.round(value / counts.total * 100) : 0;
    $("#totalGates").textContent = counts.total;
    $("#availableGates").textContent = counts.available;
    $("#occupiedGates").textContent = counts.occupied;
    $("#unavailableGates").textContent = counts.unavailable;
    $("#availablePercent").textContent = percent(counts.available) + "%";
    $("#occupiedPercent").textContent = percent(counts.occupied) + "%";
    $("#unavailablePercent").textContent = percent(counts.unavailable) + "%";
    $("#donutTotal").textContent = counts.total;
    $("#legendAvailable").textContent = counts.available;
    $("#legendOccupied").textContent = counts.occupied;
    $("#legendUnavailable").textContent = counts.unavailable;
    $("#allGateCount").textContent = gateRecords.length;
    $("#gateDonut").style.background = `conic-gradient(var(--green) 0 ${percent(counts.available)}%, var(--amber) ${percent(counts.available)}% ${percent(counts.available) + percent(counts.occupied)}%, var(--red) ${percent(counts.available) + percent(counts.occupied)}% 100%)`;
  }

  function renderGates() {
    const query = $("#gateSearch").value.trim().toLowerCase();
    const filtered = gateRecords.filter(gate => {
      const matchesStatus = gateFilter === "All" || statusForFilter(gate.status) === gateFilter;
      const matchesQuery = [gate.id, gate.terminal, gate.flight, gate.route, gate.status].some(value => value.toLowerCase().includes(query));
      return matchesStatus && matchesQuery;
    });
    gateGrid.innerHTML = filtered.map(gate => `
      <article class="gate-card">
        <div class="gate-card-top">
          <div><div class="gate-title">Gate ${safe(gate.id)}</div><div class="gate-terminal">${safe(gate.terminal)}</div></div>
          <span class="status-badge ${gateStateClass(gate.status)}">${safe(gate.status)}</span>
        </div>
        <div class="gate-photo"><img loading="lazy" src="https://images.unsplash.com/${safe(gate.image)}?auto=format&fit=crop&w=500&q=75" alt="Airport aircraft and terminal near Gate ${safe(gate.id)}"></div>
        <div class="gate-details">
          <div class="gate-flight">${safe(gate.flight)}</div>
          <div class="gate-route">${safe(gate.route)}<br>${safe(gate.window)}</div>
          <div class="gate-card-foot"><span>Resource ID: ${safe(gate.id)}</span><button type="button" data-gate-edit="${safe(gate.id)}">Manage →</button></div>
        </div>
      </article>`).join("");
    $("#gateEmpty").classList.toggle("hidden", filtered.length !== 0);
    $("#gateResultCount").textContent = `Showing ${filtered.length} of ${gateRecords.length} sample gates`;
    renderGateSummary();
  }

  function renderStaff() {
    const query = $("#staffSearch").value.trim().toLowerCase();
    const filter = $("#staffStatusFilter").value;
    const filtered = staffRecords.filter(person => {
      const matchStatus = filter === "All" || person.status === filter;
      const matchText = [person.id, person.name, person.role, person.gate, person.status, person.shift].some(value => value.toLowerCase().includes(query));
      return matchStatus && matchText;
    });
    staffTableBody.innerHTML = filtered.map(person => `
      <tr>
        <td><div class="staff-identity"><span class="staff-avatar">${safe(initials(person.name))}</span><span><span class="staff-name">${safe(person.name)}</span><span class="staff-id">${safe(person.id)}</span></span></div></td>
        <td>${safe(person.role)}</td>
        <td><span class="table-status ${staffStateClass(person.status)}">${safe(person.status)}</span></td>
        <td>${safe(person.gate)}</td>
        <td>${safe(person.shift)}</td>
        <td><button class="row-action" type="button" data-staff-edit="${safe(person.id)}" aria-label="Edit ${safe(person.name)}">Edit</button></td>
      </tr>`).join("");
    $("#staffResultCount").textContent = `Showing ${filtered.length} of ${staffRecords.length} sample staff records`;
    const counts = staffRecords.reduce((sum, person) => { sum.total++; sum[person.status] = (sum[person.status] || 0) + 1; return sum; }, { total: 0 });
    $("#totalStaff").textContent = counts.total;
    $("#availableStaff").textContent = counts.Available || 0;
    $("#onDutyStaff").textContent = counts["On Duty"] || 0;
    $("#breakStaff").textContent = counts["On Break"] || 0;
  }

  function fieldMarkup(field) {
    const value = field.value ?? "";
    if (field.options) {
      return `<div class="field-group"><label for="${safe(field.name)}">${safe(field.label)}</label><select id="${safe(field.name)}" name="${safe(field.name)}" ${field.required === false ? "" : "required"}>${field.options.map(option => {
        const item = typeof option === "string" ? { value: option, label: option } : option;
        return `<option value="${safe(item.value)}" ${String(item.value) === String(value) ? "selected" : ""}>${safe(item.label)}</option>`;
      }).join("")}</select></div>`;
    }
    return `<div class="field-group"><label for="${safe(field.name)}">${safe(field.label)}</label><input id="${safe(field.name)}" name="${safe(field.name)}" value="${safe(value)}" placeholder="${safe(field.placeholder || "")}" type="${safe(field.type || "text")}" ${field.required === false ? "" : "required"}></div>`;
  }

  function openModal({ title, description, fields = [], action, info = false }) {
    pendingAction = action || null;
    $("#modalTitle").textContent = title;
    $("#modalDescription").textContent = description;
    modalFields.innerHTML = fields.map(fieldMarkup).join("");
    const submitButton = $(".primary-button", modalForm);
    submitButton.hidden = info;
    submitButton.textContent = action?.label || "Save demo change";
    if (!modal.open) modal.showModal();
  }

  function closeModal() {
    modal.close();
    pendingAction = null;
  }

  const gateOptions = () => gateRecords.map(gate => ({ value: gate.id, label: `Gate ${gate.id} — ${gate.status}` }));
  const staffOptions = () => staffRecords.map(person => ({ value: person.id, label: `${person.name} (${person.role})` }));

  function editGate(gateId) {
    const gate = gateRecords.find(record => record.id === gateId);
    if (!gate) return;
    openModal({
      title: `Manage Gate ${gate.id}`,
      description: "Change this illustrative gate record. No live airport system is updated.",
      fields: [
        { name: "status", label: "Gate status", value: gate.status, options: ["Available", "Occupied", "Maintenance"] },
        { name: "flight", label: "Flight / assignment", value: gate.flight },
        { name: "route", label: "Route or resource note", value: gate.route },
        { name: "window", label: "Schedule window", value: gate.window }
      ],
      action: { type: "edit-gate", gateId, label: "Save gate changes" }
    });
  }

  function editStaff(staffId) {
    const person = staffRecords.find(record => record.id === staffId);
    if (!person) return;
    openModal({
      title: `Manage ${person.name}`,
      description: "Edit staff allocation and status in the local demo.",
      fields: [
        { name: "status", label: "Staff availability", value: person.status, options: ["Available", "On Duty", "On Break"] },
        { name: "role", label: "Staff role", value: person.role, options: ["Ground Staff", "Ramp Agent", "Security", "Passenger Support", "Operations", "Maintenance", "Other"] },
        { name: "gate", label: "Current allocation", value: person.gate, options: [{ value: "Unassigned", label: "Unassigned" }, ...gateOptions()] },
        { name: "shift", label: "Shift", value: person.shift, options: ["06:00–14:00", "14:00–22:00", "22:00–06:00", "09:00–17:00"] }
      ],
      action: { type: "edit-staff", staffId, label: "Save staff changes" }
    });
  }

  function assignStaff() {
    if (!staffRecords.length) return showToast("Add a staff record before assigning.");
    openModal({
      title: "Assign staff",
      description: "Select a demo staff member and update their resource assignment.",
      fields: [
        { name: "staffId", label: "Staff member", options: staffOptions() },
        { name: "gate", label: "Assign to gate", options: [{ value: "Unassigned", label: "Unassigned" }, ...gateOptions()] },
        { name: "status", label: "Status after assignment", value: "On Duty", options: ["Available", "On Duty", "On Break"] }
      ],
      action: { type: "assign-staff", label: "Save allocation" }
    });
  }

  function addStaff() {
    openModal({
      title: "Add staff record",
      description: "Add a fictional staff record to this browser-based demo.",
      fields: [
        { name: "name", label: "Staff display name", placeholder: "e.g. Ananya R" },
        { name: "role", label: "Role", value: "Ground Staff", options: ["Ground Staff", "Ramp Agent", "Security", "Passenger Support", "Operations", "Maintenance", "Other"] },
        { name: "status", label: "Availability", value: "Available", options: ["Available", "On Duty", "On Break"] },
        { name: "gate", label: "Current allocation", value: "Unassigned", options: [{ value: "Unassigned", label: "Unassigned" }, ...gateOptions()] },
        { name: "shift", label: "Shift", value: "06:00–14:00", options: ["06:00–14:00", "14:00–22:00", "22:00–06:00", "09:00–17:00"] }
      ],
      action: { type: "add-staff", label: "Add demo staff" }
    });
  }

  function showShifts() {
    const rows = staffRecords.map(person => `<div class="shift-row"><span><strong>${safe(person.name)}</strong><small>${safe(person.role)} · ${safe(person.gate)}</small></span><span>${safe(person.shift)}</span></div>`).join("");
    openModal({ title: "Staff shift overview", description: "Illustrative shift schedule for the sample staff records.", fields: [], info: true });
    modalFields.innerHTML = rows || '<p class="section-subtitle">No staff records yet.</p>';
    modalFields.style.gap = "0";
    $$(".shift-row", modalFields).forEach(row => {
      row.style.cssText = "display:flex;justify-content:space-between;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid rgba(145,184,225,.12);color:#c3d5e9;font-size:10px";
      const sub = $("small", row); sub.style.cssText = "display:block;margin-top:4px;color:#829bb7;font-size:9px";
    });
  }

  function handleModalSubmit(event) {
    event.preventDefault();
    if (!pendingAction) return closeModal();
    const values = Object.fromEntries(new FormData(modalForm).entries());
    if (pendingAction.type === "edit-gate") {
      const gate = gateRecords.find(record => record.id === pendingAction.gateId);
      if (gate) Object.assign(gate, values);
      renderGates();
      showToast(`Gate ${pendingAction.gateId} updated in demo.`);
    } else if (pendingAction.type === "edit-staff") {
      const person = staffRecords.find(record => record.id === pendingAction.staffId);
      if (person) Object.assign(person, values);
      renderStaff();
      showToast("Staff record updated in demo.");
    } else if (pendingAction.type === "assign-staff") {
      const person = staffRecords.find(record => record.id === values.staffId);
      if (person) { person.gate = values.gate; person.status = values.status; }
      renderStaff();
      showToast(person ? `${person.name}'s demo allocation saved.` : "Staff member not found.");
    } else if (pendingAction.type === "add-staff") {
      if (!values.name.trim()) return showToast("Enter a staff display name.");
      const nextNumber = staffRecords.reduce((max, person) => Math.max(max, Number(person.id.replace("ST", "")) || 0), 0) + 1;
      staffRecords.push({ id: `ST${String(nextNumber).padStart(3, "0")}`, name: values.name.trim(), role: values.role, status: values.status, gate: values.gate, shift: values.shift });
      renderStaff();
      showToast("Demo staff record added.");
    }
    closeModal();
  }

  function exportCsv() {
    const lines = [
      ["Record Type", "ID", "Name / Flight", "Role / Route", "Status", "Allocation / Terminal", "Schedule"],
      ...gateRecords.map(gate => ["Gate", gate.id, gate.flight, gate.route, gate.status, gate.terminal, gate.window]),
      ...staffRecords.map(person => ["Staff", person.id, person.name, person.role, person.status, person.gate, person.shift])
    ];
    const csv = lines.map(row => row.map(value => `"${String(value ?? "").replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = "airport-resource-management-demo.csv";
    document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    showToast("Demo resource data exported as CSV.");
  }

  $("#gateSearch").addEventListener("input", renderGates);
  $("#staffSearch").addEventListener("input", renderStaff);
  $("#staffStatusFilter").addEventListener("change", renderStaff);
  $$(".filter-button").forEach(button => button.addEventListener("click", () => {
    gateFilter = button.dataset.gateFilter;
    $$(".filter-button").forEach(item => item.classList.toggle("selected", item === button));
    renderGates();
  }));
  gateGrid.addEventListener("click", event => {
    const button = event.target.closest("[data-gate-edit]");
    if (button) editGate(button.dataset.gateEdit);
  });
  staffTableBody.addEventListener("click", event => {
    const button = event.target.closest("[data-staff-edit]");
    if (button) editStaff(button.dataset.staffEdit);
  });

  $("#showAllGates").addEventListener("click", () => {
    gateFilter = "All"; $("#gateSearch").value = "";
    $$(".filter-button").forEach(button => button.classList.toggle("selected", button.dataset.gateFilter === "All"));
    renderGates(); $("#gates").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("#addStaffButton").addEventListener("click", addStaff);
  $("#quickAssignStaff").addEventListener("click", assignStaff);
  $("#quickGate").addEventListener("click", () => {
    const firstGate = gateRecords[0];
    if (firstGate) editGate(firstGate.id);
  });
  $("#quickSchedule").addEventListener("click", showShifts);
  $("#exportCsv").addEventListener("click", exportCsv);
  $("#closeModal").addEventListener("click", closeModal);
  $("#cancelModal").addEventListener("click", closeModal);
  modalForm.addEventListener("submit", handleModalSubmit);
  modal.addEventListener("click", event => { if (event.target === modal) closeModal(); });
  modal.addEventListener("close", () => { modalFields.style.gap = ""; pendingAction = null; });

  $("#menuButton").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  $$(".side-nav a").forEach(link => link.addEventListener("click", () => {
    $$(".side-nav a").forEach(item => item.classList.toggle("active", item === link));
    $("#sidebar").classList.remove("open");
  }));
  document.addEventListener("click", event => {
    if (window.innerWidth <= 760 && !event.target.closest("#sidebar") && !event.target.closest("#menuButton")) $("#sidebar").classList.remove("open");
  });

  renderGates();
  renderStaff();
})();