const btnCargar = document.getElementById("btn-cargar");
const btnCruzar = document.getElementById("btn-cruzar");
const resultadoCargar = document.getElementById("resultado-cargar");
const resultadoCruzar = document.getElementById("resultado-cruzar");
const selectorClave = document.getElementById("selector-clave");
const keyColumnSelect = document.getElementById("key-column");
const badge1 = document.getElementById("badge-1");
const badge2 = document.getElementById("badge-2");
const step2 = document.querySelector('.step[data-step="2"]');
const subidaArchivo = document.getElementById("subida-archivo");
const archivoInput = document.getElementById("archivo-input");
const btnSubir = document.getElementById("btn-subir");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function renderTable(rows) {
  if (!rows.length) {
    return '<p class="step-desc">No hay filas en esta categoría.</p>';
  }
  const columns = Object.keys(rows[0]);
  const head = columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${columns.map((c) => `<td>${escapeHtml(row[c])}</td>`).join("")}</tr>`
    )
    .join("");
  return `<div class="table-wrap"><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

async function postJson(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json();
  return { ok: resp.ok && data.ok, data };
}

async function postForm(url, formData) {
  const resp = await fetch(url, { method: "POST", body: formData });
  const data = await resp.json();
  return { ok: resp.ok && data.ok, data };
}

function renderCargarExito(data) {
  let html = `<div class="info-line ok">✅ Hoy: <span class="filename">${escapeHtml(data.hoy.filename)}</span> — ${data.hoy.rows} filas</div>`;

  if (data.ayer) {
    html += `<div class="info-line ok">✅ Anterior: <span class="filename">${escapeHtml(data.ayer.filename)}</span> — ${data.ayer.rows} filas</div>`;
    if (data.warning) {
      html += `<div class="info-line warn">ℹ️ ${escapeHtml(data.warning)}</div>`;
    }
  } else {
    html += `<div class="info-line err">⚠️ ${escapeHtml(data.warning)}</div>`;
  }

  resultadoCargar.hidden = false;
  resultadoCargar.innerHTML = html;
  badge1.classList.add("is-done");
  badge1.textContent = "✓";
  subidaArchivo.hidden = true;

  if (data.ayer) {
    keyColumnSelect.innerHTML = data.columnas
      .map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`)
      .join("");
    selectorClave.hidden = false;
    btnCruzar.disabled = false;
    step2.classList.remove("is-disabled");
    badge2.classList.add("is-active");
  } else {
    btnCruzar.disabled = true;
    selectorClave.hidden = true;
  }

  resultadoCruzar.hidden = true;
  resultadoCruzar.innerHTML = "";
}

btnCargar.addEventListener("click", async () => {
  btnCargar.disabled = true;
  btnCargar.textContent = "Cargando...";
  resultadoCargar.hidden = false;
  resultadoCargar.innerHTML = '<p class="step-desc">Buscando archivos en el servidor...</p>';
  subidaArchivo.hidden = true;

  const { ok, data } = await postJson("/api/cargar");

  btnCargar.disabled = false;
  btnCargar.textContent = "Cargar";

  if (!ok) {
    resultadoCargar.innerHTML = `<div class="info-line err">⚠️ ${escapeHtml(data.error)}</div>`;
    if (data.necesita_subida) {
      subidaArchivo.hidden = false;
    }
    return;
  }

  renderCargarExito(data);
});

btnSubir.addEventListener("click", async () => {
  const file = archivoInput.files[0];
  if (!file) {
    resultadoCargar.innerHTML = `<div class="info-line err">⚠️ Selecciona un archivo primero.</div>`;
    return;
  }

  btnSubir.disabled = true;
  btnSubir.textContent = "Subiendo...";
  resultadoCargar.hidden = false;
  resultadoCargar.innerHTML = '<p class="step-desc">Subiendo y cargando archivo...</p>';

  const formData = new FormData();
  formData.append("archivo", file);
  const { ok, data } = await postForm("/api/subir", formData);

  btnSubir.disabled = false;
  btnSubir.textContent = "Subir y cargar";

  if (!ok) {
    resultadoCargar.innerHTML = `<div class="info-line err">⚠️ ${escapeHtml(data.error)}</div>`;
    return;
  }

  renderCargarExito(data);
});

btnCruzar.addEventListener("click", async () => {
  const keyColumn = keyColumnSelect.value;
  if (!keyColumn) return;

  btnCruzar.disabled = true;
  btnCruzar.textContent = "Cruzando...";
  resultadoCruzar.hidden = false;
  resultadoCruzar.innerHTML = '<p class="step-desc">Comparando reportes...</p>';

  const { ok, data } = await postJson("/api/cruzar", { key_column: keyColumn });

  btnCruzar.disabled = false;
  btnCruzar.textContent = "Cruzar";

  if (!ok) {
    resultadoCruzar.innerHTML = `<div class="info-line err">⚠️ ${escapeHtml(data.error)}</div>`;
    return;
  }

  badge2.classList.remove("is-active");
  badge2.classList.add("is-done");
  badge2.textContent = "✓";

  resultadoCruzar.innerHTML = `
    <div class="summary-cards">
      <div class="summary-card ok">
        <span class="count">${data.total_procesado_ayer}</span>
        <span class="label">Ya procesado ayer (columna "${escapeHtml(data.key_column)}")</span>
      </div>
      <div class="summary-card new">
        <span class="count">${data.total_nuevo_hoy}</span>
        <span class="label">Nuevo hoy</span>
      </div>
    </div>
    <p class="section-title">📋 Información que ya existía ayer</p>
    ${renderTable(data.procesado_ayer)}
    <p class="section-title">✨ Información nueva de hoy</p>
    ${renderTable(data.nuevo_hoy)}
  `;
});
