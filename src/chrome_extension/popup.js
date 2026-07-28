const API_BASE = "http://localhost:8000/api";
const HEALTH_URL = "http://localhost:8000/health";

// UI Elements
const stepInitial = document.getElementById("stepInitial");
const stepActive = document.getElementById("stepActive");
const infoCompany = document.getElementById("infoCompany");
const infoRole = document.getElementById("infoRole");
const statusMessage = document.getElementById("statusMessage");
const serverStatus = document.getElementById("serverStatus");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

/**
 * Checks server health and updates the status banner UI and action buttons.
 */
async function checkApiHealth() {
  const btnProcess = document.getElementById("btnProcess");

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000); // 2-second timeout

    const response = await fetch(HEALTH_URL, {
      method: "GET",
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (response.ok) {
      serverStatus.className = "server-status status-online";
      statusDot.className = "status-dot dot-online";
      statusText.textContent = "API Service Online";
      if (btnProcess) btnProcess.disabled = false;
    } else {
      throw new Error("Service unavailable");
    }
  } catch (error) {
    serverStatus.className = "server-status status-offline";
    statusDot.className = "status-dot dot-offline";
    statusText.textContent = "API Offline (Start FastAPI server)";
    if (btnProcess) btnProcess.disabled = true;
  }
}

// Restore active state and perform health check when popup opens
document.addEventListener("DOMContentLoaded", async () => {
  checkApiHealth();

  const state = await chrome.storage.local.get(["activeApplication"]);
  if (state.activeApplication) {
    showActiveState(state.activeApplication);
  }
});

// 1. Process resume from clipboard
document.getElementById("btnProcess").addEventListener("click", async () => {
  setStatus("Reading clipboard...");
  try {
    const text = await navigator.clipboard.readText();
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const response = await fetch(`${API_BASE}/process-resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown_text: text, source_url: tab ? tab.url : "" })
    });

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const data = await response.json();
    
    // Save state for the active application
    const appState = {
      company: data.company,
      role: data.role,
      source_url: data.source_url,
      folder_path: data.folder_path,
      pdf_path: data.pdf_path
    };
    await chrome.storage.local.set({ activeApplication: appState });

    showActiveState(appState);
    setStatus("Resume and PDF created successfully!");
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
});

// 2. Copy PDF path
document.getElementById("btnCopyPdf").addEventListener("click", async () => {
  const state = await chrome.storage.local.get(["activeApplication"]);
  if (state.activeApplication && state.activeApplication.pdf_path) {
    await navigator.clipboard.writeText(state.activeApplication.pdf_path);
    setStatus("PDF path copied! Paste it into the file upload dialog.");
  }
});

// 3. Add Cover Letter
document.getElementById("btnAddCover").addEventListener("click", async () => {
  setStatus("Reading Cover Letter...");
  try {
    const text = await navigator.clipboard.readText();
    const state = await chrome.storage.local.get(["activeApplication"]);

    const response = await fetch(`${API_BASE}/add-cover-letter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        folder_path: state.activeApplication.folder_path,
        markdown_text: text
      })
    });

    if (!response.ok) throw new Error("Failed to add Cover Letter");

    setStatus("Cover Letter saved and compiled to PDF!");
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
});

// 4. Finalize application (Applied)
document.getElementById("btnFinalize").addEventListener("click", async () => {
  try {
    const state = await chrome.storage.local.get(["activeApplication"]);
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const response = await fetch(`${API_BASE}/finalize-application`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        folder_path: state.activeApplication.folder_path,
        source_url: state.activeApplication.source_url,
        finalize_url: tab ? tab.url : "",
        company: state.activeApplication.company,
        role: state.activeApplication.role
      })
    });

    if (!response.ok) throw new Error("Failed to finalize application");

    await chrome.storage.local.remove(["activeApplication"]);
    showInitialState();
    setStatus("Application recorded and synced to Obsidian!");
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
});

// 5. Reset state
document.getElementById("btnReset").addEventListener("click", async () => {
  await chrome.storage.local.remove(["activeApplication"]);
  showInitialState();
  setStatus("State reset.");
});

function showActiveState(app) {
  infoCompany.textContent = `Company: ${app.company}`;
  infoRole.textContent = `Role: ${app.role}`;
  stepInitial.classList.add("hidden");
  stepActive.classList.remove("hidden");
}

function showInitialState() {
  stepInitial.classList.remove("hidden");
  stepActive.classList.add("hidden");
}

function setStatus(text) {
  statusMessage.textContent = text;
}