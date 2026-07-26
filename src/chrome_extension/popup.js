const API_BASE = "http://localhost:8000/api";

// UI Elements
const stepInitial = document.getElementById("stepInitial");
const stepActive = document.getElementById("stepActive");
const infoCompany = document.getElementById("infoCompany");
const infoRole = document.getElementById("infoRole");
const statusMessage = document.getElementById("statusMessage");

// Restore state when popup opens
document.addEventListener("DOMContentLoaded", async () => {
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
      body: JSON.stringify({ markdown_text: text, url: tab ? tab.url : "" })
    });

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const data = await response.json();
    
    // Save state for the current application
    const appState = {
      company: data.company,
      role: data.role,
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
        url: tab ? tab.url : "",
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

// 5. Reset
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