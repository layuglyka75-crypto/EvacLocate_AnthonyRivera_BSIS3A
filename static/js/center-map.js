(() => {
    const container = document.getElementById('center-map');
    const featureElement = document.getElementById('center-map-features');
    if (!container || !featureElement || !window.L) {
        return;
    }

    const centers = JSON.parse(featureElement.textContent);
    if (!centers.length) {
        return;
    }

    const map = window.L.map(container, { scrollWheelZoom: false });
    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const markers = centers.map((center) => {
        const color = center.status === 'closed'
            ? '#b93838'
            : center.status === 'full' ? '#c47b19' : '#176b58';
        const marker = window.L.circleMarker([center.latitude, center.longitude], {
            radius: 9,
            color,
            fillColor: color,
            fillOpacity: 0.85,
            weight: 2,
        }).addTo(map);

        const popup = document.createElement('div');
        const title = document.createElement('strong');
        const address = document.createElement('p');
        const status = document.createElement('p');
        const link = document.createElement('a');
        title.textContent = center.name;
        address.textContent = center.address;
        status.textContent = `${center.status_label} · Capacity ${center.capacity}`;
        link.textContent = 'View center details';
        link.href = center.detail_url;
        popup.append(title, address, status, link);
        marker.bindPopup(popup);
        return marker;
    });

    map.fitBounds(window.L.featureGroup(markers).getBounds().pad(0.2), { maxZoom: 14 });
})();
