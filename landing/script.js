const state = {
  year: "@",
  format: "xlsx",
};

const yearToken = document.querySelector("#year-token");
const formatToken = document.querySelector("#format-token");
const outputLines = document.querySelector("#output-lines");
const copyButton = document.querySelector("[data-copy]");
const copyStatus = document.querySelector("#copy-status");

function setActive(selector, key, value) {
  document.querySelectorAll(selector).forEach((button) => {
    button.classList.toggle("is-active", button.dataset[key] === value);
  });
}

function renderExample() {
  yearToken.textContent = state.year;
  formatToken.textContent = state.format;

  const yearText = state.year === "@"
    ? "une los ejercicios disponibles"
    : `apunta al ejercicio ${state.year}`;
  const fileName = state.format === "csv" ? "clientes.csv" : "clientes.xlsx";
  const useText = state.format === "csv"
    ? "queda listo para integraciones o procesos programados"
    : "queda listo para revisión técnica o entrega puntual";

  outputLines.innerHTML = `
    <p><strong>#clientes</strong> se resuelve contra tablas de gestión.</p>
    <p><strong>--sqlyear ${state.year}</strong> ${yearText}.</p>
    <p><strong>${fileName}</strong> ${useText}.</p>
  `;

  setActive("[data-year]", "year", state.year);
  setActive("[data-format]", "format", state.format);
}

document.querySelectorAll("[data-year]").forEach((button) => {
  button.addEventListener("click", () => {
    state.year = button.dataset.year;
    renderExample();
  });
});

document.querySelectorAll("[data-format]").forEach((button) => {
  button.addEventListener("click", () => {
    state.format = button.dataset.format;
    renderExample();
  });
});

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

copyButton?.addEventListener("click", async () => {
  try {
    await copyText(copyButton.dataset.copy);
    copyStatus.textContent = "Comando copiado.";
  } catch {
    copyStatus.textContent = "No se pudo copiar automáticamente. Seleccioná el comando del runbook.";
  }
});

renderExample();
