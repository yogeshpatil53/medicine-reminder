/**
 * MEDREMIND - SMART MEDICINE REMINDER
 * Client Controller, Web Audio Alarm Engine & Offline Storage Adapter
 */

// Global State
const state = {
  currentUser: null,
  patientName: "Patient",
  medicines: [],
  contacts: [],
  stats: {},
  activeTab: "tab-schedule",
  alarmActive: false,
  alarmInterval: null,
  activeAlarmMed: null,
  deferredInstallPrompt: null,
  networkInfo: null,
  contactFilter: "all",
  searchQuery: "",
  selectedRingtone: "gentle-chime",
  customRingtoneData: null,
  customRingtoneName: "",
  customAudioElement: null,
  contactToDelete: null
};

// Recommended Alarm Ringtone Presets
const RECOMMENDED_RINGTONES = [
  {
    id: "gentle-chime",
    name: "Gentle Medical Chime",
    desc: "Pleasant ascending 4-tone chime (C-E-G-C), soft and friendly.",
    badge: "Recommended",
    icon: "🔔"
  },
  {
    id: "digital-hospital",
    name: "Digital Hospital Beep",
    desc: "Crisp double-pulse medical alert monitor beep.",
    badge: "Clinical",
    icon: "🩺"
  },
  {
    id: "urgent-siren",
    name: "Urgent Wake-Up Siren",
    desc: "High-attention dual frequency warble, hard to miss.",
    badge: "Urgent",
    icon: "🚨"
  },
  {
    id: "zen-bell",
    name: "Peaceful Zen Bell",
    desc: "Warm acoustic singing bowl bell tone with harmonic decay.",
    badge: "Calm",
    icon: "🧘"
  },
  {
    id: "marimba-melody",
    name: "Cheerful Marimba",
    desc: "Upbeat wooden acoustic notes in a bouncing melody.",
    badge: "Cheerful",
    icon: "🎵"
  },
  {
    id: "radar-ping",
    name: "Sonar Radar Ping",
    desc: "High-tech rhythmic sonar ping with gentle resonance.",
    badge: "Modern",
    icon: "📡"
  },
  {
    id: "custom",
    name: "Custom Uploaded Sound",
    desc: "Upload your favorite MP3 or audio file from device.",
    badge: "Custom",
    icon: "📁"
  }
];

// Audio Engine (Web Audio API)
let audioCtx = null;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      audioCtx = new AudioContext();
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

/**
 * Play a soothing 4-tone chime for reminders
 */
function playChime() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const notes = [
      { freq: 523.25, time: 0.00, dur: 0.25 }, // C5
      { freq: 659.25, time: 0.18, dur: 0.25 }, // E5
      { freq: 783.99, time: 0.36, dur: 0.45 }, // G5
      { freq: 1046.50, time: 0.54, dur: 0.60 } // C6
    ];

    const now = ctx.currentTime;

    notes.forEach((note) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(note.freq, now + note.time);

      gain.gain.setValueAtTime(0, now + note.time);
      gain.gain.linearRampToValueAtTime(0.3, now + note.time + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, now + note.time + note.dur);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now + note.time);
      osc.stop(now + note.time + note.dur);
    });
  } catch (err) {
    console.warn("Audio playback error:", err);
  }
}

/**
 * Play any selected alarm ringtone preset or custom audio
 */
function playRingtoneSound(ringtoneId) {
  const rtId = ringtoneId || state.selectedRingtone || "gentle-chime";

  if (rtId === "custom") {
    const customData = state.customRingtoneData || localStorage.getItem("medremind_custom_ringtone");
    if (customData) {
      try {
        if (state.customAudioElement) {
          state.customAudioElement.pause();
          state.customAudioElement.currentTime = 0;
        }
        state.customAudioElement = new Audio(customData);
        state.customAudioElement.play().catch((e) => console.warn("Custom audio play error:", e));
        return;
      } catch (e) {
        console.warn("Failed to play custom audio, fallback to chime:", e);
      }
    }
  }

  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;

    if (rtId === "digital-hospital") {
      // 2 crisp clinical monitor beeps (880Hz)
      [0.0, 0.16].forEach((startTime) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, now + startTime);
        gain.gain.setValueAtTime(0, now + startTime);
        gain.gain.linearRampToValueAtTime(0.35, now + startTime + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.001, now + startTime + 0.12);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + startTime);
        osc.stop(now + startTime + 0.12);
      });
    } else if (rtId === "urgent-siren") {
      // Urgent alarm warble alternating 700Hz - 1100Hz
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(700, now);
      osc.frequency.linearRampToValueAtTime(1100, now + 0.18);
      osc.frequency.linearRampToValueAtTime(700, now + 0.36);
      osc.frequency.linearRampToValueAtTime(1100, now + 0.54);
      osc.frequency.linearRampToValueAtTime(700, now + 0.72);

      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(1600, now);

      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(0.25, now + 0.03);
      gain.gain.setValueAtTime(0.25, now + 0.70);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.85);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.85);
    } else if (rtId === "zen-bell") {
      // Deep warm Tibetan bell (329.63Hz + harmonic overtones)
      const freqs = [329.63, 659.25, 987.77];
      const amps = [0.35, 0.15, 0.08];
      freqs.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, now);
        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(amps[idx], now + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0005, now + 1.2);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 1.2);
      });
    } else if (rtId === "marimba-melody") {
      // Cheerful marimba arpeggio (C5, E5, G5, A5, C6)
      const notes = [
        { freq: 523.25, time: 0.00, dur: 0.15 },
        { freq: 659.25, time: 0.12, dur: 0.15 },
        { freq: 783.99, time: 0.24, dur: 0.15 },
        { freq: 880.00, time: 0.36, dur: 0.15 },
        { freq: 1046.50, time: 0.48, dur: 0.35 }
      ];
      notes.forEach((note) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(note.freq, now + note.time);
        gain.gain.setValueAtTime(0, now + note.time);
        gain.gain.linearRampToValueAtTime(0.3, now + note.time + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, now + note.time + note.dur);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + note.time);
        osc.stop(now + note.time + note.dur);
      });
    } else if (rtId === "radar-ping") {
      // Sonar radar pulse (1200Hz) with echo
      [0.0, 0.25].forEach((offset, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(idx === 0 ? 1200 : 1400, now + offset);
        gain.gain.setValueAtTime(0, now + offset);
        gain.gain.linearRampToValueAtTime(idx === 0 ? 0.35 : 0.18, now + offset + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.001, now + offset + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + offset);
        osc.stop(now + offset + 0.35);
      });
    } else {
      // Default: gentle-chime
      playChime();
    }
  } catch (err) {
    console.warn("Ringtone playback error:", err);
  }
}

function startAlarmSound() {
  playRingtoneSound(state.selectedRingtone);
  if (state.alarmInterval) clearInterval(state.alarmInterval);
  state.alarmInterval = setInterval(() => {
    playRingtoneSound(state.selectedRingtone);
    if ("vibrate" in navigator) {
      navigator.vibrate([300, 150, 300]);
    }
  }, 2400);
}

function stopAlarmSound() {
  if (state.alarmInterval) {
    clearInterval(state.alarmInterval);
    state.alarmInterval = null;
  }
  if (state.customAudioElement) {
    try {
      state.customAudioElement.pause();
      state.customAudioElement.currentTime = 0;
    } catch (e) {}
  }
}

// ==========================================================================
// TOAST NOTIFICATIONS
// ==========================================================================

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === "success" ? "✔️" : type === "danger" ? "⚠️" : "ℹ️"}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentNode) toast.parentNode.removeChild(toast);
  }, 3000);
}

// ==========================================================================
// OFFLINE STORAGE & DATA ADAPTER (For Standalone APK & Offline PWA)
// ==========================================================================

const isStandaloneApk = window.location.protocol === "file:";

function initLocalStorageData() {
  if (!localStorage.getItem("medremind_init_v2")) {
    const defaultMeds = [
      {
        id: 1,
        name: "Morning Medication",
        dosage: "500mg",
        reminder_time: "08:00 AM",
        start_date: new Date().toISOString().split("T")[0],
        repeat_daily: 1,
        notes: "Take after breakfast with water",
        enabled: 1,
        last_reminded_date: "",
        last_taken_date: ""
      },
      {
        id: 2,
        name: "Evening Dose",
        dosage: "1 Tablet",
        reminder_time: "08:00 PM",
        start_date: new Date().toISOString().split("T")[0],
        repeat_daily: 1,
        notes: "Take after dinner",
        enabled: 1,
        last_reminded_date: "",
        last_taken_date: ""
      }
    ];

    const defaultContacts = [
      { id: 1, name: "Emergency Ambulance", phone_number: "102", contact_type: "Ambulance", address: "National Emergency Helpline", relationship: "Emergency" },
      { id: 2, name: "Family Doctor", phone_number: "+91 98765 43210", contact_type: "Doctor", address: "City Hospital", relationship: "Physician" },
      { id: 3, name: "Nearby Pharmacy", phone_number: "+91 98765 12345", contact_type: "Nearby Medicine Store", address: "Main Road Market", relationship: "Chemist" }
    ];

    localStorage.setItem("medremind_medicines", JSON.stringify(defaultMeds));
    localStorage.setItem("medremind_contacts", JSON.stringify(defaultContacts));
    localStorage.setItem("medremind_patient_name", "yogesh");
    localStorage.setItem("medremind_init_v2", "true");
  }

  if (!localStorage.getItem("medremind_users")) {
    const defaultUsers = [
      { id: 1, username: "yogesh", name: "Yogesh", email: "yogesh@medremind.com", password: "password123" }
    ];
    localStorage.setItem("medremind_users", JSON.stringify(defaultUsers));
  }
}

initLocalStorageData();

async function apiFetch(endpoint, options = {}) {
  if (isStandaloneApk) {
    return localApiHandler(endpoint, options);
  }

  try {
    const res = await fetch(endpoint, options);
    return await res.json();
  } catch (err) {
    console.warn("Server unavailable, using local storage:", err);
    return localApiHandler(endpoint, options);
  }
}

function localApiHandler(endpoint, options) {
  const method = (options.method || "GET").toUpperCase();
  const body = options.body ? JSON.parse(options.body) : {};
  const today = new Date().toISOString().split("T")[0];
  const now = new Date();
  let hours = now.getHours();
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;
  const now12 = `${String(hours).padStart(2, "0")}:${minutes} ${ampm}`;

  let meds = JSON.parse(localStorage.getItem("medremind_medicines") || "[]");
  let contacts = JSON.parse(localStorage.getItem("medremind_contacts") || "[]");
  let patient = localStorage.getItem("medremind_patient_name") || "yogesh";

  // Auth endpoints (Local / Offline APK)
  if (endpoint === "/api/auth/login" && method === "POST") {
    const users = JSON.parse(localStorage.getItem("medremind_users") || "[]");
    const identifier = (body.username || body.identifier || "").trim().toLowerCase();
    const pwd = (body.password || "").trim();
    const found = users.find(u => 
      (u.username.toLowerCase() === identifier || u.email.toLowerCase() === identifier) && 
      u.password === pwd
    );
    if (found) {
      const userObj = { id: found.id, username: found.username, name: found.name, email: found.email };
      localStorage.setItem("medremind_current_user", JSON.stringify(userObj));
      localStorage.setItem("medremind_patient_name", userObj.name);
      return { success: true, message: `Welcome back, ${userObj.name}!`, user: userObj };
    }
    return { success: false, error: "Invalid username or password. Please try again." };
  }

  if (endpoint === "/api/auth/register" && method === "POST") {
    const users = JSON.parse(localStorage.getItem("medremind_users") || "[]");
    const username = (body.username || "").trim().toLowerCase();
    const name = (body.name || "").trim();
    const email = (body.email || `${username}@example.com`).trim().toLowerCase();
    const pwd = (body.password || "").trim();

    if (!username || !pwd || !name) {
      return { success: false, error: "Full name, username, and password are required." };
    }
    if (users.some(u => u.username.toLowerCase() === username)) {
      return { success: false, error: "Username is already taken. Please choose another." };
    }
    const newUser = { id: Date.now(), username, name, email, password: pwd };
    users.push(newUser);
    localStorage.setItem("medremind_users", JSON.stringify(users));
    const userObj = { id: newUser.id, username: newUser.username, name: newUser.name, email: newUser.email };
    localStorage.setItem("medremind_current_user", JSON.stringify(userObj));
    localStorage.setItem("medremind_patient_name", userObj.name);
    return { success: true, message: `Welcome, ${userObj.name}! Account created successfully.`, user: userObj };
  }

  if (endpoint === "/api/auth/me" && method === "GET") {
    const cur = localStorage.getItem("medremind_current_user");
    if (cur) {
      try {
        return { success: true, authenticated: true, user: JSON.parse(cur) };
      } catch (e) {}
    }
    return { success: true, authenticated: false, user: null };
  }

  if (endpoint === "/api/auth/logout" && method === "POST") {
    localStorage.removeItem("medremind_current_user");
    return { success: true, message: "Logged out successfully." };
  }

  if (endpoint === "/api/status") {
    const todayMeds = meds.filter((m) => m.repeat_daily === 1 || m.start_date === today);
    const taken = todayMeds.filter((m) => m.last_taken_date === today).length;
    return {
      success: true,
      patient_name: patient,
      current_date: today,
      current_time: now12,
      stats: {
        all_medicines: meds.length,
        today_total: todayMeds.length,
        today_taken: taken,
        today_pending: Math.max(0, todayMeds.length - taken),
        contacts_count: contacts.length
      }
    };
  }

  if (endpoint === "/api/medicines" && method === "GET") {
    const list = meds.map((m) => ({
      ...m,
      is_today: Boolean(m.repeat_daily === 1 || m.start_date === today),
      is_taken_today: Boolean(m.last_taken_date === today)
    }));
    return { success: true, medicines: list };
  }

  if (endpoint === "/api/medicines" && method === "POST") {
    const newMed = {
      id: Date.now(),
      name: body.name,
      dosage: body.dosage,
      reminder_time: body.reminder_time,
      start_date: body.start_date || today,
      repeat_daily: body.repeat_daily ? 1 : 0,
      notes: body.notes || "",
      enabled: 1,
      last_reminded_date: "",
      last_taken_date: ""
    };
    meds.push(newMed);
    localStorage.setItem("medremind_medicines", JSON.stringify(meds));
    return { success: true, message: "Medicine saved", id: newMed.id };
  }

  if (endpoint.startsWith("/api/medicines/") && method === "DELETE") {
    const id = parseInt(endpoint.split("/")[3], 10);
    meds = meds.filter((m) => m.id !== id);
    localStorage.setItem("medremind_medicines", JSON.stringify(meds));
    return { success: true };
  }

  if (endpoint.includes("/taken") && method === "POST") {
    const id = parseInt(endpoint.split("/")[3], 10);
    const m = meds.find((x) => x.id === id);
    if (m) {
      m.last_taken_date = body.taken ? today : "";
      localStorage.setItem("medremind_medicines", JSON.stringify(meds));
    }
    return { success: true, taken: body.taken };
  }

  if (endpoint === "/api/medicines/due" && method === "GET") {
    const due = meds.filter((m) => {
      const isToday = m.repeat_daily === 1 || m.start_date === today;
      return m.enabled === 1 && isToday && m.reminder_time === now12 && m.last_reminded_date !== today;
    });
    return { success: true, due_medicines: due };
  }

  if (endpoint.includes("/ack-reminder") && method === "POST") {
    const id = parseInt(endpoint.split("/")[3], 10);
    const m = meds.find((x) => x.id === id);
    if (m) {
      m.last_reminded_date = today;
      localStorage.setItem("medremind_medicines", JSON.stringify(meds));
    }
    return { success: true };
  }

  if (endpoint === "/api/contacts" && method === "GET") {
    return { success: true, contacts };
  }

  if (endpoint === "/api/contacts" && method === "POST") {
    const newContact = {
      id: Date.now(),
      name: body.name,
      phone_number: body.phone_number,
      contact_type: body.contact_type || "Emergency Contact",
      relationship: body.relationship || "",
      address: body.address || ""
    };
    contacts.push(newContact);
    localStorage.setItem("medremind_contacts", JSON.stringify(contacts));
    return { success: true, id: newContact.id };
  }

  if (endpoint.startsWith("/api/contacts/") && (method === "PUT" || method === "POST") && !endpoint.includes("/delete")) {
    const id = parseInt(endpoint.split("/")[3], 10);
    const c = contacts.find((x) => x.id === id);
    if (c) {
      c.name = body.name !== undefined ? body.name : c.name;
      c.phone_number = body.phone_number !== undefined ? body.phone_number : c.phone_number;
      c.contact_type = body.contact_type !== undefined ? body.contact_type : c.contact_type;
      c.relationship = body.relationship !== undefined ? body.relationship : c.relationship;
      c.address = body.address !== undefined ? body.address : c.address;
      localStorage.setItem("medremind_contacts", JSON.stringify(contacts));
      return { success: true, message: "Contact updated successfully", contact: c };
    }
    return { success: false, error: "Contact not found" };
  }

  if (endpoint.startsWith("/api/contacts/") && method === "DELETE") {
    const id = parseInt(endpoint.split("/")[3], 10);
    contacts = contacts.filter((c) => c.id !== id);
    localStorage.setItem("medremind_contacts", JSON.stringify(contacts));
    return { success: true };
  }

  if (endpoint === "/api/settings/ringtone" && method === "GET") {
    const rt = localStorage.getItem("medremind_ringtone") || "gentle-chime";
    return { success: true, ringtone: rt };
  }

  if (endpoint === "/api/settings/ringtone" && method === "POST") {
    const rt = body.ringtone || "gentle-chime";
    localStorage.setItem("medremind_ringtone", rt);
    return { success: true, ringtone: rt };
  }

  if (endpoint.includes("/patient-name") && method === "POST") {
    localStorage.setItem("medremind_patient_name", body.name);
    return { success: true, patient_name: body.name };
  }

  if (endpoint === "/api/network-info") {
    return {
      success: true,
      lan_ip: "Android APK",
      mobile_url: "Offline Native Android App",
      localhost_url: "file:///android_asset/index.html"
    };
  }

  return { success: true };
}

// ==========================================================================
// DATA FETCHING & SYNCHRONIZATION
// ==========================================================================

async function fetchStatus() {
  try {
    const data = await apiFetch("/api/status");
    if (data.success) {
      state.patientName = data.patient_name || "Patient";
      state.stats = data.stats || {};
      renderStatus();
    }
  } catch (err) {
    console.error("Failed to load status:", err);
  }
}

async function fetchMedicines() {
  try {
    const data = await apiFetch("/api/medicines");
    if (data.success) {
      state.medicines = data.medicines || [];
      renderSchedule();
      renderAllMedicines();
    }
  } catch (err) {
    console.error("Failed to load medicines:", err);
  }
}

async function fetchContacts() {
  try {
    const data = await apiFetch("/api/contacts");
    if (data.success) {
      state.contacts = data.contacts || [];
      renderContacts();
    }
  } catch (err) {
    console.error("Failed to load contacts:", err);
  }
}

async function fetchNetworkInfo() {
  try {
    const data = await apiFetch("/api/network-info");
    if (data.success) {
      state.networkInfo = data;
      const input = document.getElementById("phone-url-input");
      if (input) input.value = data.mobile_url;
      renderQrCode(data.mobile_url);
    }
  } catch (err) {
    console.error("Failed to load network info:", err);
  }
}

// ==========================================================================
// DUE MEDICINES & ALARM CONTROLLER
// ==========================================================================

async function checkDueMedicines() {
  try {
    const data = await apiFetch("/api/medicines/due");
    if (data.success && data.due_medicines && data.due_medicines.length > 0) {
      triggerAlarm(data.due_medicines[0]);
    }
  } catch (err) {
    console.error("Due check error:", err);
  }
}

function triggerAlarm(medicine) {
  if (state.alarmActive) return;
  state.alarmActive = true;
  state.activeAlarmMed = medicine;

  document.getElementById("alarm-med-name").textContent = medicine.name;
  document.getElementById("alarm-med-dosage").textContent = medicine.dosage;
  document.getElementById("alarm-med-notes").textContent = medicine.notes || "Time to take your scheduled dose.";
  document.getElementById("alarm-med-time").textContent = `Scheduled: ${medicine.reminder_time}`;

  const modal = document.getElementById("alarm-modal");
  if (modal) modal.style.display = "flex";

  startAlarmSound();

  // Browser Notification if granted
  if (window.Notification && Notification.permission === "granted") {
    new Notification(`Medicine Due: ${medicine.name}`, {
      body: `Dosage: ${medicine.dosage} (${medicine.reminder_time})\n${medicine.notes || ""}`,
      icon: "/icon-192.png",
      vibrate: [300, 150, 300]
    });
  }
}

function dismissAlarm(markTaken = false) {
  stopAlarmSound();
  state.alarmActive = false;

  const modal = document.getElementById("alarm-modal");
  if (modal) modal.style.display = "none";

  if (state.activeAlarmMed) {
    const medId = state.activeAlarmMed.id;
    apiFetch(`/api/medicines/${medId}/ack-reminder`, { method: "POST" });

    if (markTaken) {
      apiFetch(`/api/medicines/${medId}/taken`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taken: true })
      }).then(() => {
        showToast("Dose recorded as taken!", "success");
        fetchMedicines();
        fetchStatus();
      });
    }
    state.activeAlarmMed = null;
  }
}

// ==========================================================================
// RENDERING & AUTHENTICATION
// ==========================================================================

function renderUserProfile() {
  const headerInitial = document.getElementById("header-avatar-initial");
  const headerName = document.getElementById("header-user-name");
  const settingsAvatar = document.getElementById("settings-user-avatar");
  const settingsName = document.getElementById("settings-account-name");
  const settingsEmail = document.getElementById("settings-account-email");
  const patientDisplay = document.getElementById("patient-name-display");

  if (state.currentUser) {
    const initial = (state.currentUser.name || state.currentUser.username || "U").charAt(0).toUpperCase();
    if (headerInitial) headerInitial.textContent = initial;
    if (headerName) headerName.textContent = state.currentUser.name || state.currentUser.username;
    if (settingsAvatar) settingsAvatar.textContent = initial;
    if (settingsName) settingsName.textContent = `${state.currentUser.name} (@${state.currentUser.username})`;
    if (settingsEmail) settingsEmail.textContent = state.currentUser.email || "Active User Account";
    if (patientDisplay) patientDisplay.textContent = state.currentUser.name;
    state.patientName = state.currentUser.name;
  } else {
    if (headerInitial) headerInitial.textContent = "👤";
    if (headerName) headerName.textContent = "Sign In";
    if (settingsAvatar) settingsAvatar.textContent = "👤";
    if (settingsName) settingsName.textContent = "Guest User";
    if (settingsEmail) settingsEmail.textContent = "Not signed in - Tap to Sign In";
  }
}

function openAuthModal(defaultPane = "login-pane") {
  const modal = document.getElementById("auth-modal");
  const app = document.getElementById("app");
  if (app) app.style.display = "none";
  if (modal) modal.style.display = "flex";

  const tabs = document.querySelectorAll(".auth-tab-btn");
  tabs.forEach(tab => {
    if (tab.getAttribute("data-auth-tab") === defaultPane) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });

  const panes = document.querySelectorAll(".auth-pane");
  panes.forEach(pane => {
    if (pane.id === defaultPane) {
      pane.classList.add("active");
    } else {
      pane.classList.remove("active");
    }
  });

  clearAuthAlert();
}

function closeAuthModal() {
  const modal = document.getElementById("auth-modal");
  const app = document.getElementById("app");
  if (modal) modal.style.display = "none";
  if (app) app.style.display = "flex";
}

function showAuthAlert(message, type = "error") {
  const alert = document.getElementById("auth-alert");
  if (!alert) return;
  alert.className = `auth-alert ${type}`;
  alert.innerHTML = `<span>${type === "error" ? "⚠️" : "✔️"}</span> <span>${message}</span>`;
  alert.style.display = "flex";
}

function clearAuthAlert() {
  const alert = document.getElementById("auth-alert");
  if (alert) {
    alert.style.display = "none";
    alert.innerHTML = "";
  }
}

async function handleLogin(identifier, password) {
  clearAuthAlert();
  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: identifier, password: password })
    });

    if (data && data.success && data.user) {
      state.currentUser = data.user;
      localStorage.setItem("medremind_current_user", JSON.stringify(data.user));
      localStorage.setItem("medremind_patient_name", data.user.name);
      state.patientName = data.user.name;
      renderUserProfile();
      fetchStatus();
      fetchMedicines();
      fetchContacts();
      fetchRingtoneSetting();
      closeAuthModal();
      showToast(data.message || `Welcome back, ${data.user.name}!`, "success");
    } else {
      showAuthAlert(data && data.error || "Invalid username or password. Please try again.", "error");
    }
  } catch (err) {
    showAuthAlert("Login failed. Please check your credentials.", "error");
  }
}

async function handleRegister(name, username, email, password, confirmPassword) {
  clearAuthAlert();
  if (password !== confirmPassword) {
    showAuthAlert("Passwords do not match. Please verify.", "error");
    return;
  }
  if (password.length < 6) {
    showAuthAlert("Password must be at least 6 characters long.", "error");
    return;
  }

  try {
    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, username, email, password })
    });

    if (data && data.success && data.user) {
      state.currentUser = data.user;
      localStorage.setItem("medremind_current_user", JSON.stringify(data.user));
      localStorage.setItem("medremind_patient_name", data.user.name);
      state.patientName = data.user.name;
      renderUserProfile();
      fetchStatus();
      fetchMedicines();
      fetchContacts();
      fetchRingtoneSetting();
      closeAuthModal();
      showToast(data.message || `Welcome, ${data.user.name}! Account created.`, "success");
    } else {
      showAuthAlert(data && data.error || "Registration failed. Please try again.", "error");
    }
  } catch (err) {
    showAuthAlert("Registration failed. Please check your connection.", "error");
  }
}

async function handleLogout() {
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } catch (e) {}

  state.currentUser = null;
  localStorage.removeItem("medremind_current_user");
  renderUserProfile();
  const settingsModal = document.getElementById("account-settings-modal");
  if (settingsModal) settingsModal.style.display = "none";
  showToast("Signed out successfully.", "info");
  openAuthModal("login-pane");
}

async function checkAuthStatus() {
  const localUser = localStorage.getItem("medremind_current_user");
  if (localUser) {
    try {
      state.currentUser = JSON.parse(localUser);
    } catch (e) {
      state.currentUser = null;
    }
  }

  if (state.currentUser) {
    // Direct entry in app (2nd time access)
    closeAuthModal();
    renderUserProfile();
    fetchStatus();
    fetchMedicines();
    fetchContacts();
    fetchRingtoneSetting();

    // Verify session with server in background
    apiFetch("/api/auth/me").then((data) => {
      if (data && data.success && data.user) {
        state.currentUser = data.user;
        localStorage.setItem("medremind_current_user", JSON.stringify(data.user));
        renderUserProfile();
      }
    }).catch(() => {});
  } else {
    // First time / not logged in -> show login screen first
    openAuthModal("login-pane");
  }
}

function renderStatus() {
  const patientDisplay = document.getElementById("patient-name-display");
  if (patientDisplay && !state.currentUser) patientDisplay.textContent = state.patientName;
  if (patientDisplay) patientDisplay.textContent = state.patientName;

  const settingsPatientInput = document.getElementById("settings-patient-name");
  if (settingsPatientInput) settingsPatientInput.value = state.patientName;

  const totalEl = document.getElementById("stat-today-total");
  const takenEl = document.getElementById("stat-today-taken");
  const pendingEl = document.getElementById("stat-today-pending");

  if (totalEl) totalEl.textContent = state.stats.today_total ?? 0;
  if (takenEl) takenEl.textContent = state.stats.today_taken ?? 0;
  if (pendingEl) pendingEl.textContent = state.stats.today_pending ?? 0;
}

function renderSchedule() {
  const container = document.getElementById("today-medicines-list");
  if (!container) return;

  const todayMeds = state.medicines.filter((m) => m.is_today);

  if (todayMeds.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🎉</div>
        <h4>No Medications Scheduled for Today</h4>
        <p class="subtext">Add a daily medicine or a scheduled dose to see it here.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = todayMeds.map((med) => `
    <div class="medicine-card ${med.is_taken_today ? 'taken' : ''}" data-id="${med.id}">
      <div class="med-left">
        <div class="med-time-pill">${med.reminder_time}</div>
        <div class="med-details">
          <h4>${escapeHtml(med.name)}</h4>
          <div class="med-meta">
            <span class="dosage-tag">${escapeHtml(med.dosage)}</span>
            <span>${med.repeat_daily ? 'Daily' : 'One-time'}</span>
          </div>
          ${med.notes ? `<div class="med-notes">📝 ${escapeHtml(med.notes)}</div>` : ''}
        </div>
      </div>
      <button class="take-check-btn ${med.is_taken_today ? 'checked' : ''}" 
              data-id="${med.id}" 
              data-taken="${med.is_taken_today ? 'true' : 'false'}"
              title="${med.is_taken_today ? 'Mark as Pending' : 'Mark as Taken'}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      </button>
    </div>
  `).join("");

  container.querySelectorAll(".take-check-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = btn.getAttribute("data-id");
      const currentTaken = btn.getAttribute("data-taken") === "true";
      const newTaken = !currentTaken;

      btn.classList.toggle("checked", newTaken);
      const card = btn.closest(".medicine-card");
      if (card) card.classList.toggle("taken", newTaken);

      try {
        await apiFetch(`/api/medicines/${id}/taken`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ taken: newTaken })
        });
        showToast(newTaken ? "Marked as Taken ✔️" : "Marked as Pending ⏳", "success");
        fetchStatus();
        fetchMedicines();
      } catch (err) {
        showToast("Failed to update status", "danger");
      }
    });
  });
}

function renderAllMedicines() {
  const container = document.getElementById("all-medicines-list");
  if (!container) return;

  const q = state.searchQuery.toLowerCase();
  const filtered = state.medicines.filter((m) => {
    return m.name.toLowerCase().includes(q) || m.dosage.toLowerCase().includes(q);
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">💊</div>
        <h4>No Medications Found</h4>
        <p class="subtext">${q ? "No medicines matching your search." : "Tap '+ Add Medicine' to create your first reminder."}</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map((med) => `
    <div class="medicine-card" data-id="${med.id}">
      <div class="med-left">
        <div class="med-time-pill">${med.reminder_time}</div>
        <div class="med-details">
          <h4>${escapeHtml(med.name)}</h4>
          <div class="med-meta">
            <span class="dosage-tag">${escapeHtml(med.dosage)}</span>
            <span>${med.repeat_daily ? '🔁 Daily Repeat' : '📅 ' + (med.start_date || 'Once')}</span>
          </div>
          ${med.notes ? `<div class="med-notes">📝 ${escapeHtml(med.notes)}</div>` : ''}
        </div>
      </div>
      <div class="med-actions">
        <button class="btn-delete" data-id="${med.id}" data-name="${escapeHtml(med.name)}" title="Delete Medicine">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    </div>
  `).join("");

  container.querySelectorAll(".btn-delete").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-id");
      const name = btn.getAttribute("data-name");
      if (confirm(`Are you sure you want to delete ${name}?`)) {
        await apiFetch(`/api/medicines/${id}`, { method: "DELETE" });
        showToast(`Deleted ${name}`, "danger");
        fetchMedicines();
        fetchStatus();
      }
    });
  });
}

function renderContacts() {
  const container = document.getElementById("contacts-list");
  if (!container) return;

  const filtered = state.contacts.filter((c) => {
    if (state.contactFilter === "all") return true;
    return c.contact_type === state.contactFilter;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📞</div>
        <h4>No Emergency Contacts</h4>
        <p class="subtext">Add your doctor, ambulance, or family contact details.</p>
      </div>
    `;
    return;
  }

  const categoryEmojis = {
    Doctor: "🩺",
    Ambulance: "🚑",
    "Nearby Medicine Store": "💊",
    "Emergency Contact": "👤"
  };

  container.innerHTML = filtered.map((c) => {
    const emoji = categoryEmojis[c.contact_type] || "👤";
    const phoneClean = (c.phone_number || "").replace(/[^0-9+]/g, "");

    return `
      <div class="contact-card" data-id="${c.id}">
        <div class="contact-left">
          <div class="contact-avatar">${emoji}</div>
          <div class="contact-details">
            <span class="contact-type-tag">${escapeHtml(c.contact_type)}</span>
            <h4>${escapeHtml(c.name)}</h4>
            <div class="contact-phone-sub">${escapeHtml(c.phone_number)}</div>
            ${c.relationship ? `<div class="contact-address" style="margin-top:2px; font-weight:500; color:#475569;">💼 ${escapeHtml(c.relationship)}</div>` : ''}
            ${c.address ? `<div class="contact-address">📍 ${escapeHtml(c.address)}</div>` : ''}
          </div>
        </div>
        <div class="contact-actions">
          <a href="tel:${phoneClean}" class="call-btn" title="Call ${escapeHtml(c.name)}">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
            </svg>
            <span>Call</span>
          </a>
          <button class="btn-edit-contact" data-id="${c.id}" title="Edit Doctor / Contact">
            ✏️ <span>Edit</span>
          </button>
          <button class="btn-delete-contact" data-id="${c.id}" data-name="${escapeHtml(c.name)}" title="Delete Contact">
            🗑️ <span>Delete</span>
          </button>
        </div>
      </div>
    `;
  }).join("");

  // Attach Edit and Delete listeners
  container.querySelectorAll(".btn-edit-contact").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = parseInt(btn.getAttribute("data-id"), 10);
      openEditContactModal(id);
    });
  });

  container.querySelectorAll(".btn-delete-contact").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = parseInt(btn.getAttribute("data-id"), 10);
      const name = btn.getAttribute("data-name");
      openDeleteContactModal(id, name);
    });
  });
}

function openEditContactModal(id) {
  const contact = state.contacts.find((c) => c.id === id);
  if (!contact) {
    showToast("Contact not found", "danger");
    return;
  }
  document.getElementById("edit-contact-id").value = contact.id;
  document.getElementById("edit-contact-name").value = contact.name || "";
  document.getElementById("edit-contact-phone").value = contact.phone_number || "";
  document.getElementById("edit-contact-type").value = contact.contact_type || "Doctor";
  document.getElementById("edit-contact-relation").value = contact.relationship || "";
  document.getElementById("edit-contact-address").value = contact.address || "";

  const modal = document.getElementById("edit-contact-modal");
  if (modal) modal.style.display = "flex";
}

function openDeleteContactModal(id, name) {
  state.contactToDelete = { id, name };
  const label = document.getElementById("delete-contact-name-display");
  if (label) label.textContent = `"${name}"`;

  const modal = document.getElementById("delete-contact-modal");
  if (modal) modal.style.display = "flex";
}

async function handleConfirmDeleteContact() {
  if (!state.contactToDelete) return;
  const { id, name } = state.contactToDelete;

  try {
    const data = await apiFetch(`/api/contacts/${id}`, { method: "DELETE" });
    if (data && data.success) {
      showToast(`Deleted ${name} 🗑️`, "success");
      const modal = document.getElementById("delete-contact-modal");
      if (modal) modal.style.display = "none";
      state.contactToDelete = null;
      fetchContacts();
      fetchStatus();
    } else {
      showToast(data && data.error ? data.error : "Failed to delete contact", "danger");
    }
  } catch (err) {
    showToast("Error deleting contact", "danger");
  }
}

// Ringtone Settings Helpers
function getRingtoneDisplayName(id) {
  const match = RECOMMENDED_RINGTONES.find((r) => r.id === id);
  if (match) {
    if (id === "custom" && state.customRingtoneName) {
      return `Custom (${state.customRingtoneName})`;
    }
    return match.name;
  }
  return "Gentle Medical Chime";
}

function updateRingtoneBadge() {
  const badge = document.getElementById("active-ringtone-badge");
  if (badge) {
    badge.textContent = getRingtoneDisplayName(state.selectedRingtone);
  }
}

async function fetchRingtoneSetting() {
  try {
    const data = await apiFetch("/api/settings/ringtone");
    if (data && data.success && data.ringtone) {
      state.selectedRingtone = data.ringtone;
    } else {
      state.selectedRingtone = localStorage.getItem("medremind_ringtone") || "gentle-chime";
    }
  } catch (e) {
    state.selectedRingtone = localStorage.getItem("medremind_ringtone") || "gentle-chime";
  }

  // Load custom sound info from storage if present
  const savedCustom = localStorage.getItem("medremind_custom_ringtone");
  const savedCustomName = localStorage.getItem("medremind_custom_ringtone_name");
  if (savedCustom) {
    state.customRingtoneData = savedCustom;
    state.customRingtoneName = savedCustomName || "custom-audio.mp3";
    const tag = document.getElementById("custom-audio-filename");
    const testBtn = document.getElementById("btn-test-custom-audio");
    if (tag) {
      tag.textContent = state.customRingtoneName;
      tag.style.display = "inline-block";
    }
    if (testBtn) testBtn.style.display = "inline-block";
  }

  updateRingtoneBadge();
  renderRingtonePresets();
}

function renderRingtonePresets() {
  const container = document.getElementById("ringtone-presets-container");
  if (!container) return;

  container.innerHTML = RECOMMENDED_RINGTONES.map((rt) => {
    const isSelected = state.selectedRingtone === rt.id;
    return `
      <div class="ringtone-preset-item ${isSelected ? 'selected' : ''}" data-id="${rt.id}">
        <div class="ringtone-radio-dot"></div>
        <div class="ringtone-preset-icon">${rt.icon}</div>
        <div class="ringtone-preset-info">
          <div class="ringtone-preset-header">
            <span class="ringtone-preset-name">${escapeHtml(rt.name)}</span>
            <span class="badge-ringtone" style="font-size:0.7rem; padding:2px 7px;">${rt.badge}</span>
          </div>
          <div class="ringtone-preset-desc">${escapeHtml(rt.desc)}</div>
        </div>
        <button class="btn-play-ringtone" data-id="${rt.id}" title="Preview Sound" type="button">
          ▶️
        </button>
      </div>
    `;
  }).join("");

  // Attach card selection
  container.querySelectorAll(".ringtone-preset-item").forEach((card) => {
    card.addEventListener("click", () => {
      const id = card.getAttribute("data-id");
      state.selectedRingtone = id;
      renderRingtonePresets();
      playRingtoneSound(id);
    });
  });

  // Attach preview button click
  container.querySelectorAll(".btn-play-ringtone").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.getAttribute("data-id");
      playRingtoneSound(id);
      showToast(`Playing "${getRingtoneDisplayName(id)}" preview 🎵`, "info");
    });
  });
}

async function saveRingtoneChoice() {
  try {
    localStorage.setItem("medremind_ringtone", state.selectedRingtone);
    await apiFetch("/api/settings/ringtone", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ringtone: state.selectedRingtone })
    });
    updateRingtoneBadge();
    const modal = document.getElementById("ringtone-modal");
    if (modal) modal.style.display = "none";
    showToast(`Active alarm tone updated to: "${getRingtoneDisplayName(state.selectedRingtone)}" 🎵`, "success");
  } catch (err) {
    showToast("Saved ringtone preference!", "success");
    const modal = document.getElementById("ringtone-modal");
    if (modal) modal.style.display = "none";
  }
}

// ==========================================================================
// QR CODE GENERATOR (Standalone SVG Renderer)
// ==========================================================================

function renderQrCode(url) {
  const box = document.getElementById("qr-code-box");
  if (!box || !url) return;

  const encodedUrl = encodeURIComponent(url);
  const qrImg = document.createElement("img");
  qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodedUrl}`;
  qrImg.alt = "Scan to Open on Phone";
  qrImg.style.width = "100%";
  qrImg.style.height = "100%";
  qrImg.style.borderRadius = "4px";

  qrImg.onerror = () => {
    box.innerHTML = `
      <div style="font-size:0.75rem; text-align:center; padding:10px; color:#1E293B;">
        <strong>Type on Phone:</strong><br>
        <code style="word-break:break-all; font-size:0.8rem; color:#2563EB;">${url}</code>
      </div>
    `;
  };

  box.innerHTML = "";
  box.appendChild(qrImg);
}

// ==========================================================================
// EVENT LISTENERS & INITIALIZATION
// ==========================================================================

function switchTab(tabId) {
  state.activeTab = tabId;

  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.remove("active");
  });
  const target = document.getElementById(tabId);
  if (target) target.classList.add("active");

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.getAttribute("data-tab") === tabId);
  });

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateClock() {
  const now = new Date();
  let hours = now.getHours();
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;

  const clockEl = document.getElementById("live-clock");
  if (clockEl) clockEl.textContent = `${hours}:${minutes} ${ampm}`;

  const dateEl = document.getElementById("live-date");
  if (dateEl) {
    const options = { weekday: "short", month: "short", day: "numeric" };
    dateEl.textContent = now.toLocaleDateString(undefined, options);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  // Service Worker Registration (Web only)
  if ("serviceWorker" in navigator && !isStandaloneApk) {
    navigator.serviceWorker.register("/sw.js").then(() => {
      console.log("PWA Service Worker registered.");
    }).catch((err) => {
      console.warn("Service Worker registration failed:", err);
    });
  }

  // PWA Install Prompt Listener
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    state.deferredInstallPrompt = e;
    const banner = document.getElementById("pwa-install-banner");
    if (banner) banner.style.display = "flex";
  });

  const installBtn = document.getElementById("pwa-install-btn");
  if (installBtn) {
    installBtn.addEventListener("click", async () => {
      if (state.deferredInstallPrompt) {
        state.deferredInstallPrompt.prompt();
        const choice = await state.deferredInstallPrompt.userChoice;
        if (choice.outcome === "accepted") {
          showToast("App installing to your device!", "success");
        }
        state.deferredInstallPrompt = null;
        document.getElementById("pwa-install-banner").style.display = "none";
      }
    });
  }

  const dismissInstallBtn = document.getElementById("pwa-dismiss-btn");
  if (dismissInstallBtn) {
    dismissInstallBtn.addEventListener("click", () => {
      document.getElementById("pwa-install-banner").style.display = "none";
    });
  }

  // Navigation Tabs
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      switchTab(tab);
    });
  });

  // Header Settings Button
  const headerSettingsBtn = document.getElementById("header-settings-btn");
  if (headerSettingsBtn) {
    headerSettingsBtn.addEventListener("click", () => {
      openModal("account-settings-modal");
    });
  }

  // Sound Chime Test
  document.getElementById("header-sound-btn").addEventListener("click", () => {
    playChime();
    showToast("Audio chime tested 🔔", "info");
  });

  document.getElementById("test-alarm-btn").addEventListener("click", () => {
    playChime();
    showToast("Playing medicine chime...", "info");
  });

  // Notifications Permission
  document.getElementById("enable-notifications-btn").addEventListener("click", async () => {
    if ("Notification" in window) {
      const perm = await Notification.requestPermission();
      if (perm === "granted") {
        showToast("Notifications enabled!", "success");
        new Notification("MedRemind Active", {
          body: "You will receive reminders when medications are due.",
          icon: "/icon-192.png"
        });
      } else {
        showToast("Notification permission denied", "danger");
      }
    } else {
      showToast("Notifications not supported in this browser", "info");
    }
  });

  // Edit Patient Name -> Open Account & Settings Modal
  document.getElementById("edit-patient-btn").addEventListener("click", () => {
    openModal("account-settings-modal");
    const input = document.getElementById("settings-patient-name");
    if (input) input.focus();
  });

  document.getElementById("save-patient-name-btn").addEventListener("click", async () => {
    const input = document.getElementById("settings-patient-name");
    const name = input ? input.value.trim() : "";
    if (!name) return;

    await apiFetch("/api/settings/patient-name", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    state.patientName = name;
    renderStatus();
    showToast("Patient name saved!", "success");
  });

  // Copy URL Button (if present)
  const copyUrlBtn = document.getElementById("copy-url-btn");
  if (copyUrlBtn) {
    copyUrlBtn.addEventListener("click", () => {
      const input = document.getElementById("phone-url-input");
      if (input) {
        input.select();
        navigator.clipboard.writeText(input.value).then(() => {
          showToast("Link copied to clipboard! 📋", "success");
        });
      }
    });
  }

  // Search Filter
  const searchInput = document.getElementById("med-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value;
      renderAllMedicines();
    });
  }

  // Contact Filter Chips
  document.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".filter-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.contactFilter = chip.getAttribute("data-filter");
      renderContacts();
    });
  });

  // Quick Dial Buttons
  document.querySelectorAll(".quick-dial-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const type = btn.getAttribute("data-type");
      const contact = state.contacts.find((c) => c.contact_type === type);
      if (contact && contact.phone_number) {
        const clean = contact.phone_number.replace(/[^0-9+]/g, "");
        window.location.href = `tel:${clean}`;
      } else {
        showToast(`No ${type} contact found. Add one in Emergency tab.`, "info");
        switchTab("tab-contacts");
      }
    });
  });

  // Alarm Modal Buttons
  document.getElementById("alarm-take-btn").addEventListener("click", () => {
    dismissAlarm(true);
  });

  document.getElementById("alarm-snooze-btn").addEventListener("click", () => {
    dismissAlarm(false);
    showToast("Alarm snoozed for 5 minutes ⏰", "info");
  });

  // Modals Open/Close
  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = "flex";
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = "none";
  }

  document.getElementById("open-add-med-modal").addEventListener("click", () => openModal("add-med-modal"));
  document.getElementById("quick-add-med-btn").addEventListener("click", () => openModal("add-med-modal"));
  document.getElementById("open-add-contact-modal").addEventListener("click", () => openModal("add-contact-modal"));

  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.getAttribute("data-close");
      closeModal(modalId);
    });
  });

  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.style.display = "none";
      }
    });
  });

  // Add Medicine Form Submit
  const addMedForm = document.getElementById("add-med-form");
  if (addMedForm) {
    document.getElementById("med-start-date").value = new Date().toISOString().split("T")[0];

    addMedForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("med-name").value.trim();
      const dosage = document.getElementById("med-dosage").value.trim();
      const timeVal = document.getElementById("med-time").value.trim();
      const startDate = document.getElementById("med-start-date").value.trim();
      const daily = document.getElementById("med-daily").checked;
      const notes = document.getElementById("med-notes").value.trim();

      if (!name || !dosage || !timeVal) {
        showToast("Please fill in required fields", "danger");
        return;
      }

      const [hStr, mStr] = timeVal.split(":");
      let h = parseInt(hStr, 10);
      const ampm = h >= 12 ? "PM" : "AM";
      h = h % 12 || 12;
      const reminder_time = `${String(h).padStart(2, "0")}:${mStr} ${ampm}`;

      try {
        const data = await apiFetch("/api/medicines", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            dosage,
            reminder_time,
            start_date: startDate,
            repeat_daily: daily,
            notes
          })
        });
        if (data.success) {
          showToast(`Medicine '${name}' scheduled!`, "success");
          addMedForm.reset();
          document.getElementById("med-start-date").value = new Date().toISOString().split("T")[0];
          closeModal("add-med-modal");
          fetchMedicines();
          fetchStatus();
        } else {
          showToast(data.error || "Failed to add medicine", "danger");
        }
      } catch (err) {
        showToast("Error saving medicine", "danger");
      }
    });
  }

  // Add Contact Form Submit
  const addContactForm = document.getElementById("add-contact-form");
  if (addContactForm) {
    addContactForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("contact-name").value.trim();
      const phone_number = document.getElementById("contact-phone").value.trim();
      const contact_type = document.getElementById("contact-type").value;
      const relationship = document.getElementById("contact-relation").value.trim();
      const address = document.getElementById("contact-address").value.trim();

      if (!name || !phone_number) {
        showToast("Name and phone number required", "danger");
        return;
      }

      try {
        const data = await apiFetch("/api/contacts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            phone_number,
            contact_type,
            relationship,
            address
          })
        });
        if (data.success) {
          showToast(`Contact '${name}' added!`, "success");
          addContactForm.reset();
          closeModal("add-contact-modal");
          fetchContacts();
          fetchStatus();
        } else {
          showToast(data.error || "Failed to add contact", "danger");
        }
      } catch (err) {
        showToast("Error saving contact", "danger");
      }
    });
  }

  // Edit Contact Form Submit
  const editContactForm = document.getElementById("edit-contact-form");
  if (editContactForm) {
    editContactForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = document.getElementById("edit-contact-id").value;
      const name = document.getElementById("edit-contact-name").value.trim();
      const phone_number = document.getElementById("edit-contact-phone").value.trim();
      const contact_type = document.getElementById("edit-contact-type").value;
      const relationship = document.getElementById("edit-contact-relation").value.trim();
      const address = document.getElementById("edit-contact-address").value.trim();

      if (!name || !phone_number) {
        showToast("Name and phone number required", "danger");
        return;
      }

      try {
        const data = await apiFetch(`/api/contacts/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name,
            phone_number,
            contact_type,
            relationship,
            address
          })
        });
        if (data && data.success) {
          showToast(`Contact '${name}' updated! ✔️`, "success");
          closeModal("edit-contact-modal");
          fetchContacts();
          fetchStatus();
        } else {
          showToast(data && data.error ? data.error : "Failed to update contact", "danger");
        }
      } catch (err) {
        showToast("Error updating contact", "danger");
      }
    });
  }

  // Confirm Delete Contact Button
  const confirmDeleteContactBtn = document.getElementById("confirm-delete-contact-btn");
  if (confirmDeleteContactBtn) {
    confirmDeleteContactBtn.addEventListener("click", () => {
      handleConfirmDeleteContact();
    });
  }

  // Ringtone Modal Controls
  const openRingtoneModalBtn = document.getElementById("open-ringtone-modal-btn");
  if (openRingtoneModalBtn) {
    openRingtoneModalBtn.addEventListener("click", () => {
      renderRingtonePresets();
      openModal("ringtone-modal");
    });
  }

  const saveRingtoneChoiceBtn = document.getElementById("btn-save-ringtone-choice");
  if (saveRingtoneChoiceBtn) {
    saveRingtoneChoiceBtn.addEventListener("click", () => {
      saveRingtoneChoice();
    });
  }

  // Custom Ringtone File Upload Controls
  const btnPickCustomAudio = document.getElementById("btn-pick-custom-audio");
  const customRingtoneFileInput = document.getElementById("custom-ringtone-file");
  const btnTestCustomAudio = document.getElementById("btn-test-custom-audio");
  const customAudioFilenameTag = document.getElementById("custom-audio-filename");

  if (btnPickCustomAudio && customRingtoneFileInput) {
    btnPickCustomAudio.addEventListener("click", () => {
      customRingtoneFileInput.click();
    });

    customRingtoneFileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (uploadEvent) => {
        const base64Data = uploadEvent.target.result;
        state.customRingtoneData = base64Data;
        state.customRingtoneName = file.name;
        state.selectedRingtone = "custom";

        localStorage.setItem("medremind_custom_ringtone", base64Data);
        localStorage.setItem("medremind_custom_ringtone_name", file.name);
        localStorage.setItem("medremind_ringtone", "custom");

        if (customAudioFilenameTag) {
          customAudioFilenameTag.textContent = file.name;
          customAudioFilenameTag.style.display = "inline-block";
        }
        if (btnTestCustomAudio) {
          btnTestCustomAudio.style.display = "inline-block";
        }

        renderRingtonePresets();
        updateRingtoneBadge();
        playRingtoneSound("custom");
        showToast(`Loaded "${file.name}" as custom alarm ringtone! 🎵`, "success");
      };
      reader.readAsDataURL(file);
    });
  }

  if (btnTestCustomAudio) {
    btnTestCustomAudio.addEventListener("click", () => {
      playRingtoneSound("custom");
      showToast("Testing your custom ringtone... 🎵", "info");
    });
  }

  // Auth Modal & Settings Controls
  const headerUserBtn = document.getElementById("header-user-btn");
  if (headerUserBtn) {
    headerUserBtn.addEventListener("click", () => {
      if (state.currentUser) {
        openModal("account-settings-modal");
      } else {
        openAuthModal("login-pane");
      }
    });
  }

  const authCloseBtn = document.getElementById("auth-close-btn");
  if (authCloseBtn) {
    authCloseBtn.addEventListener("click", () => {
      if (state.currentUser) {
        closeAuthModal();
      }
    });
  }

  // Auth Tab Switchers
  const authTabBtns = document.querySelectorAll(".auth-tab-btn");
  authTabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetPane = btn.getAttribute("data-auth-tab");
      openAuthModal(targetPane);
    });
  });

  // Switch to Login from Register pane link
  const switchToLoginBtn = document.getElementById("btn-switch-to-login");
  if (switchToLoginBtn) {
    switchToLoginBtn.addEventListener("click", () => {
      openAuthModal("login-pane");
    });
  }

  // One-Click Demo Login
  const demoLoginBtn = document.getElementById("btn-demo-login");
  if (demoLoginBtn) {
    demoLoginBtn.addEventListener("click", () => {
      const uField = document.getElementById("login-username");
      const pField = document.getElementById("login-password");
      if (uField) uField.value = "yogesh";
      if (pField) pField.value = "password123";
      handleLogin("yogesh", "password123");
    });
  }

  // Form Login Submit
  const formLogin = document.getElementById("form-login");
  if (formLogin) {
    formLogin.addEventListener("submit", (e) => {
      e.preventDefault();
      const identifier = document.getElementById("login-username").value.trim();
      const password = document.getElementById("login-password").value.trim();
      if (!identifier || !password) {
        showAuthAlert("Please enter your username and password.", "error");
        return;
      }
      handleLogin(identifier, password);
    });
  }

  // Form Register Submit
  const formRegister = document.getElementById("form-register");
  if (formRegister) {
    formRegister.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = document.getElementById("reg-name").value.trim();
      const username = document.getElementById("reg-username").value.trim();
      const email = document.getElementById("reg-email").value.trim();
      const password = document.getElementById("reg-password").value.trim();
      const confirmPassword = document.getElementById("reg-confirm-password").value.trim();

      if (!name || !username || !password) {
        showAuthAlert("Name, username, and password are required.", "error");
        return;
      }
      handleRegister(name, username, email, password, confirmPassword);
    });
  }

  // Password Visibility Toggles
  const pwdToggles = document.querySelectorAll(".pwd-toggle-btn");
  pwdToggles.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const input = document.getElementById(targetId);
      if (input) {
        if (input.type === "password") {
          input.type = "text";
          btn.textContent = "🙈";
        } else {
          input.type = "password";
          btn.textContent = "👁️";
        }
      }
    });
  });

  // Settings Modal Auth Actions
  const btnSwitchAccount = document.getElementById("btn-switch-account");
  if (btnSwitchAccount) {
    btnSwitchAccount.addEventListener("click", () => {
      const settingsModal = document.getElementById("account-settings-modal");
      if (settingsModal) settingsModal.style.display = "none";
      openAuthModal("login-pane");
    });
  }

  const btnLogout = document.getElementById("btn-logout");
  if (btnLogout) {
    btnLogout.addEventListener("click", () => {
      handleLogout();
    });
  }

  // Initial Data Load
  updateClock();
  setInterval(updateClock, 1000);

  checkAuthStatus();

  // Due medicines check loop (every 10 seconds)
  setInterval(checkDueMedicines, 10000);
});
