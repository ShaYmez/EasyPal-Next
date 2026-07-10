async function fetchStatus() {
  const response = await fetch("/api/v1/status");
  return response.json();
}

async function fetchGallery() {
  const response = await fetch("/api/v1/gallery");
  return response.json();
}

function renderGallery(items) {
  const gallery = document.getElementById("gallery");
  gallery.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("button");
    card.className = "gallery-item";
    card.type = "button";
    card.innerHTML = `
      <img src="${item.thumb_url}" alt="${item.callsign}">
      <div class="meta">${item.callsign}<br>${new Date(item.created_at).toLocaleString()}</div>
    `;
    card.addEventListener("click", () => openViewer(item.image_url));
    gallery.appendChild(card);
  }
}

function openViewer(url) {
  const dialog = document.getElementById("viewer");
  const image = document.getElementById("viewer-img");
  image.src = url;
  dialog.showModal();
}

document.getElementById("viewer-close").addEventListener("click", () => {
  document.getElementById("viewer").close();
});

function connectEvents() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/v1/events`);
  socket.addEventListener("message", async (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "GalleryUpdatedEvent" || data.type === "RxImageReadyEvent") {
      renderGallery(await fetchGallery());
    }
    if (data.type === "TransferProgressEvent") {
      const progress = document.getElementById("progress");
      progress.classList.remove("hidden");
      document.getElementById("bar-fill").style.width = `${data.pct}%`;
      document.getElementById("progress-text").textContent =
        `${data.bytes_done} / ${data.bytes_total} bytes`;
    }
  });
}

async function init() {
  const status = await fetchStatus();
  document.getElementById("status").textContent =
    `${status.callsign} · ${status.session_state} · ${status.modem_mode}`;
  renderGallery(await fetchGallery());
  connectEvents();
}

init();
