const API_BASE = "http://localhost:8000/api";

// Элементы UI
const stepInitial = document.getElementById("stepInitial");
const stepActive = document.getElementById("stepActive");
const infoCompany = document.getElementById("infoCompany");
const infoRole = document.getElementById("infoRole");
const statusMessage = document.getElementById("statusMessage");

// Восстановление состояния при открытии popup
document.addEventListener("DOMContentLoaded", async () => {
  const state = await chrome.storage.local.get(["activeApplication"]);
  if (state.activeApplication) {
    showActiveState(state.activeApplication);
  }
});

// 1. Создание резюме из буфера
document.getElementById("btnProcess").addEventListener("click", async () => {
  setStatus("Считываем буфер обмена...");
  try {
    const text = await navigator.clipboard.readText();
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const response = await fetch(`${API_BASE}/process-resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown_text: text, url: tab ? tab.url : "" })
    });

    if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);

    const data = await response.json();
    
    // Сохраняем стейт текущего отклика
    const appState = {
      company: data.company,
      role: data.role,
      folder_path: data.folder_path,
      pdf_path: data.pdf_path
    };
    await chrome.storage.local.set({ activeApplication: appState });

    showActiveState(appState);
    setStatus("Резюме и PDF успешно созданы!");
  } catch (err) {
    setStatus(`Ошибка: ${err.message}`);
  }
});

// 2. Копирование пути к PDF
document.getElementById("btnCopyPdf").addEventListener("click", async () => {
  const state = await chrome.storage.local.get(["activeApplication"]);
  if (state.activeApplication && state.activeApplication.pdf_path) {
    await navigator.clipboard.writeText(state.activeApplication.pdf_path);
    setStatus("Путь к PDF скопирован! Вставьте его в окно загрузки.");
  }
});

// 3. Добавление Cover Letter
document.getElementById("btnAddCover").addEventListener("click", async () => {
  setStatus("Считываем Cover Letter...");
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

    if (!response.ok) throw new Error("Не удалось добавить Cover Letter");

    setStatus("Cover Letter сохранено и скомпилировано в PDF!");
  } catch (err) {
    setStatus(`Ошибка: ${err.message}`);
  }
});

// 4. Финализация отклика (Applied)
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

    if (!response.ok) throw new Error("Не удалось зафиксировать отклик");

    await chrome.storage.local.remove(["activeApplication"]);
    showInitialState();
    setStatus("Отклик успешно зафиксирован и сохранен в Obsidian!");
  } catch (err) {
    setStatus(`Ошибка: ${err.message}`);
  }
});

// 5. Сброс
document.getElementById("btnReset").addEventListener("click", async () => {
  await chrome.storage.local.remove(["activeApplication"]);
  showInitialState();
  setStatus("Состояние сброшено.");
});

function showActiveState(app) {
  infoCompany.textContent = `Компания: ${app.company}`;
  infoRole.textContent = `Роль: ${app.role}`;
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