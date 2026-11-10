(() => {
    const container = document.getElementById('response-map');
    const featuresElement = document.getElementById('map-features');
    if (!container || !featuresElement || !window.L) {
        return;
    }

    const features = JSON.parse(featuresElement.textContent);
    if (!features.length) {
        return;
    }

    const map = window.L.map(container, { scrollWheelZoom: false });
    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const markers = features.map((feature) => {
        const color = feature.condition === 'critical'
            ? '#b93838'
            : feature.condition === 'watch' ? '#c47b19' : '#176b58';
        const marker = window.L.circleMarker([feature.latitude, feature.longitude], {
            radius: 9,
            color,
            fillColor: color,
            fillOpacity: 0.85,
            weight: 2,
        }).addTo(map);
        marker.bindPopup(
            `<strong>${window.L.Util.escapeHTML(feature.name)}</strong><br>` +
            `${window.L.Util.escapeHTML(feature.condition_label)} · ${feature.rescue_percentage}% rescued`
        );
        return marker;
    });

    map.fitBounds(window.L.featureGroup(markers).getBounds().pad(0.2), { maxZoom: 14 });
})();
