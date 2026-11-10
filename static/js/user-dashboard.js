(() => {
    const updateUrl = window.evacLocateUpdatesUrl;

    const refreshUserMetrics = async () => {
        try {
            const response = await fetch(updateUrl, { cache: 'no-store' });
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            document.querySelector('[data-user-metric="flood-reports"]').textContent = data.open_flood_reports_count;
            document.querySelector('[data-user-metric="rescue-requests"]').textContent = data.open_rescue_requests_count;
            document.querySelector('[data-user-metric="centers"]').textContent = data.available_centers_count;
            document.querySelector('[data-user-metric="supplies"]').textContent = data.available_supplies_count;
        } catch (error) {
            console.error('Unable to refresh your dashboard metrics.', error);
        }
    };

    window.setInterval(refreshUserMetrics, 30000);
})();
