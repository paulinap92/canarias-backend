const $ = (id) => document.getElementById(id);

const state = {
  items: [],
  selected: null,
  isNew: false,
  mediaUploadEnabled: false,
};

const fields = [
  "slug","name","category","order","short_description","description",
  "latitude","longitude","image_url","image_credit","image_license",
  "image_origin","image_source_url","image_license_url","source_url"
];

function token() {
  return $("token").value.trim() || localStorage.getItem("canarias-editor-token") || "";
}

async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(url, {...options, headers});
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}

function setStatus(message, error = false) {
  $("status").textContent = message || "";
  $("status").classList.toggle("error", error);
}

function currentScope() {
  return {
    island: $("island").value,
    section: $("section").value,
  };
}

function qs(scope = currentScope()) {
  return new URLSearchParams(scope).toString();
}

function renderList() {
  const root = $("items");
  root.innerHTML = "";
  state.items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "item" + (state.selected?.slug === item.slug && !state.isNew ? " active" : "");
    button.innerHTML = `<strong>${escapeHtml(item.name || item.title || item.slug)}</strong><small>${escapeHtml(item.slug || "")}</small>`;
    button.addEventListener("click", () => editItem(item));
    root.appendChild(button);
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  })[char]);
}

function setValue(id, value) {
  const element = $(id);
  if (!element) return;
  element.value = value ?? "";
}

function editItem(item) {
  state.selected = structuredClone(item);
  state.isNew = false;
  $("empty").classList.add("hidden");
  $("form").classList.remove("hidden");
  $("mode").textContent = "EDITAR";
  $("form-title").textContent = item.name || item.title || item.slug;
  $("slug").disabled = true;
  $("delete").classList.remove("hidden");

  fields.forEach((field) => setValue(field, item[field]));
  $("featured").checked = item.featured === true;
  $("tags").value = Array.isArray(item.tags) ? item.tags.join(", ") : "";
  $("raw-json").value = JSON.stringify(item, null, 2);
  updateImagePreview();
  renderList();
  setStatus("");
}

function newItem() {
  state.selected = {};
  state.isNew = true;
  $("empty").classList.add("hidden");
  $("form").classList.remove("hidden");
  $("mode").textContent = "NUEVO";
  $("form-title").textContent = "Nuevo contenido";
  $("slug").disabled = false;
  $("delete").classList.add("hidden");
  $("form").reset();
  $("raw-json").value = "{}";
  updateImagePreview();
  renderList();
  setStatus("");
}

function slugify(value) {
  return String(value || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function buildItem() {
  let base = {};
  const raw = $("raw-json").value.trim();
  if (raw) {
    try {
      base = JSON.parse(raw);
    } catch (error) {
      throw new Error("JSON avanzado no es válido.");
    }
  }

  const assign = (key, value) => {
    if (value === "" || value == null) delete base[key];
    else base[key] = value;
  };

  assign("slug", $("slug").value.trim());
  assign("name", $("name").value.trim());
  assign("category", $("category").value.trim());
  assign("short_description", $("short_description").value.trim());
  assign("description", $("description").value.trim());
  assign("source_url", $("source_url").value.trim());
  assign("image_url", $("image_url").value.trim());
  assign("image_credit", $("image_credit").value.trim());
  assign("image_license", $("image_license").value.trim());
  assign("image_origin", $("image_origin").value.trim());
  assign("image_source_url", $("image_source_url").value.trim());
  assign("image_license_url", $("image_license_url").value.trim());

  const order = $("order").value.trim();
  if (order) base.order = Number(order); else delete base.order;

  const latitude = $("latitude").value.trim();
  if (latitude) base.latitude = Number(latitude); else delete base.latitude;
  const longitude = $("longitude").value.trim();
  if (longitude) base.longitude = Number(longitude); else delete base.longitude;

  const tags = $("tags").value.split(",").map((value) => value.trim()).filter(Boolean);
  if (tags.length) base.tags = tags; else delete base.tags;

  base.featured = $("featured").checked;
  return base;
}

function updateImagePreview() {
  const url = $("image_url").value.trim();
  const root = $("image-preview");
  root.innerHTML = "";
  if (!url) {
    root.textContent = "Sin imagen";
    return;
  }
  const img = document.createElement("img");
  img.src = url;
  img.alt = "";
  img.onerror = () => { root.textContent = "No se pudo cargar la imagen"; };
  root.appendChild(img);
}

async function loadContent() {
  setStatus("Cargando…");
  try {
    const data = await api(`/api/editor/content?${qs()}`);
    state.items = data.items || [];
    state.selected = null;
    state.isNew = false;
    $("form").classList.add("hidden");
    $("empty").classList.remove("hidden");
    renderList();
    setStatus(`${state.items.length} elementos`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function save(event) {
  event.preventDefault();
  setStatus("Guardando…");
  try {
    const item = buildItem();
    if (!item.slug) throw new Error("Falta slug.");
    if (!item.name && !item.title) throw new Error("Falta nombre.");

    const url = state.isNew
      ? `/api/editor/content?${qs()}`
      : `/api/editor/content/${encodeURIComponent(state.selected.slug)}?${qs()}`;
    const method = state.isNew ? "POST" : "PUT";
    await api(url, {method, body: JSON.stringify(item)});
    await loadContent();
    const saved = state.items.find((value) => value.slug === item.slug);
    if (saved) editItem(saved);
    setStatus("Guardado ✓");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function removeItem() {
  if (!state.selected?.slug || state.isNew) return;
  if (!confirm(`¿Eliminar "${state.selected.name || state.selected.slug}"?`)) return;
  setStatus("Eliminando…");
  try {
    await api(`/api/editor/content/${encodeURIComponent(state.selected.slug)}?${qs()}`, {method:"DELETE"});
    await loadContent();
    setStatus("Eliminado.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function init() {
  const savedToken = localStorage.getItem("canarias-editor-token") || "";
  $("token").value = savedToken;

  try {
    const options = await api("/api/editor/options");
    options.islands.forEach((value) => $("island").add(new Option(value, value)));
    options.sections.forEach((value) => $("section").add(new Option(value, value)));
    $("island").value = "tenerife";
    $("section").value = "food";
    state.mediaUploadEnabled = Boolean(options.media_upload_enabled);
    if (state.mediaUploadEnabled) {
      $("upload-status").textContent = "R2 configurado; endpoint de upload będzie dodany w następnym kroku.";
    }
    await loadContent();
  } catch (error) {
    $("empty").innerHTML = `<h2>No se pudo abrir el editor</h2><p>${escapeHtml(error.message)}</p>`;
  }
}

$("token").addEventListener("change", () => {
  localStorage.setItem("canarias-editor-token", $("token").value.trim());
  loadContent();
});
$("reload").addEventListener("click", loadContent);
$("island").addEventListener("change", loadContent);
$("section").addEventListener("change", loadContent);
$("new-item").addEventListener("click", newItem);
$("delete").addEventListener("click", removeItem);
$("form").addEventListener("submit", save);
$("image_url").addEventListener("input", updateImagePreview);
$("name").addEventListener("input", () => {
  if (state.isNew && !$("slug").value.trim()) $("slug").value = slugify($("name").value);
});

init();
