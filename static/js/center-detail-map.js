(() => {
    const container = document.getElementById('center-detail-map');
    const featureElement = document.getElementById('center-detail-feature');
    if (!container || !featureElement || !window.L) {
        return;
    }

    const center = JSON.parse(featureElement.textContent);
    const map = window.L.map(container, { scrollWheelZoom: false }).setView(
        [center.latitude, center.longitude],
        15
    );
    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const color = center.status === 'closed'
        ? '#b93838'
        : center.status === 'full' ? '#c47b19' : '#176b58';
    const marker = window.L.circleMarker([center.latitude, center.longitude], {
        radius: 10,
        color,
        fillColor: color,
        fillOpacity: 0.85,
        weight: 2,
    }).addTo(map);
    marker.bindPopup(
        `<strong>${window.L.Util.escapeHTML(center.name)}</strong><br>` +
        `${window.L.Util.escapeHTML(center.status_label)} · Capacity ${center.capacity}`
    ).openPopup();
})();
