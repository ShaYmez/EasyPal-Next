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
  if (!items.length) {
    gallery.innerHTML = '<p class="empty">No images yet — complete a transfer to populate the gallery.</p>';
    return;
  }
  for (const item of items) {
    const card = document.createElement("button");
    card.className = "gallery-item";
    card.type = "button";
    const direction = (item.direction || "rx").toUpperCase();
    const badgeClass = direction === "TX" ? "badge-tx" : "badge-rx";
    card.innerHTML = `
      <div class="thumb-wrap">
        <span class="direction-badge ${badgeClass}">${direction}</span>
        <img src="${item.thumb_url}" alt="${item.callsign}"
             onerror="this.onerror=null;this.src='${item.image_url}'">
      </div>
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

let refreshTimer = null;

async function refreshGallery() {
  try {
    renderGallery(await fetchGallery());
  } catch (err) {
    console.warn("gallery refresh failed", err);
  }
}

function scheduleGalleryRefresh() {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }
  refreshTimer = setTimeout(async () => {
    await refreshGallery();
    scheduleGalleryRefresh();
  }, 2500);
}

function connectEvents() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  let socket;
  try {
    socket = new WebSocket(`${protocol}://${location.host}/ws/v1/events`);
  } catch (err) {
    console.warn("live events unavailable; using poll only", err);
    return;
  }

  socket.addEventListener("message", async (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "GalleryUpdatedEvent" || data.type === "RxImageReadyEvent") {
      await refreshGallery();
    }
    if (data.type === "TransferProgressEvent") {
      const progress = document.getElementById("progress");
      progress.classList.remove("hidden");
      document.getElementById("bar-fill").style.width = `${data.pct}%`;
      document.getElementById("progress-text").textContent =
        `${data.bytes_done} / ${data.bytes_total} bytes`;
    }
  });

  // Subprocess gallery has no WebSocket; don't hammer reconnect — REST poll covers updates.
  socket.addEventListener("close", () => {
    console.warn("live events closed; gallery will refresh via poll");
  });

  socket.addEventListener("error", () => {
    socket.close();
  });
}


async function init() {
  const status = await fetchStatus();
  document.getElementById("status").textContent =
    `${status.callsign} · ${status.session_state} · ${status.modem_mode}`;
  await refreshGallery();
  scheduleGalleryRefresh();
  connectEvents();
}

init();
