(() => {
    const updateUrl = window.evacLocateUpdatesUrl;
    let dataVersion = window.evacLocateDataVersion || '';
    const lastUpdated = document.getElementById('last-updated');

    const checkForUpdates = async () => {
        try {
            const response = await fetch(updateUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                cache: 'no-store',
            });
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            if (data.data_version !== dataVersion && (data.data_version || dataVersion)) {
                window.location.reload();
                return;
            }
            dataVersion = data.data_version || dataVersion;

            document.querySelector('[data-metric="active-incidents"]').textContent = data.active_incidents_count;
            document.querySelector('[data-metric="units-deployed"]').textContent = data.units_deployed;
            document.querySelector('[data-metric="personnel-online"]').textContent = data.personnel_online;
            document.querySelector('[data-metric="average-response"]').textContent =
                data.average_response === null ? '—' : `${data.average_response} min`;
            document.querySelector('[data-metric="registered-users"]').textContent = data.registered_users_count;
            document.querySelector('[data-metric="evacuation-centers"]').textContent = data.evacuation_centers_count;
            document.querySelector('[data-metric="pending-rescue-requests"]').textContent = data.pending_rescue_requests_count;
            document.querySelector('[data-metric="reported-flood-incidents"]').textContent = data.reported_flood_incidents_count;
            if (lastUpdated) {
                lastUpdated.textContent = data.data_version ? new Date(data.data_version).toLocaleString() : 'No updates yet';
            }
        } catch (error) {
            console.error('Unable to refresh dashboard data.', error);
        }
    };

    window.setInterval(checkForUpdates, 30000);
})();
