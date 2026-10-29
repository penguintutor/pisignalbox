/**
 * Shared API client with automatic CSRF token injection and silent refresh.
 */
const ApiClient = (() => {
    let refreshPromise = null;
    let csrfRefreshUrl = '/api/csrf-token';

    function setRefreshUrl(url) {
        csrfRefreshUrl = url;
    }

    function getCsrfToken() {
        const inputEl = document.getElementById('csrf_token');
        if (inputEl) return inputEl.value;

        const metaEl = document.querySelector('meta[name="csrf-token"]');
        if (metaEl) return metaEl.getAttribute('content');

        return '';
    }

    function setCsrfToken(newToken) {
        const inputEl = document.getElementById('csrf_token');
        if (inputEl) inputEl.value = newToken;

        const metaEl = document.querySelector('meta[name="csrf-token"]');
        if (metaEl) metaEl.setAttribute('content', newToken);
    }

    async function refreshCsrfToken() {
        // If a refresh is already in flight, reuse the existing promise
        if (refreshPromise) {
            return refreshPromise;
        }

        refreshPromise = (async () => {
            try {
                const response = await fetch(csrfRefreshUrl, {
                    method: 'GET',
                    headers: { 'Accept': 'application/json' }
                });
                if (!response.ok) {
                    throw new Error(`Failed to refresh CSRF token: ${response.status}`);
                }
                const data = await response.json();
                if (data.csrf_token) {
                    setCsrfToken(data.csrf_token);
                    return data.csrf_token;
                }
                throw new Error('No csrf_token in refresh response');
            } finally {
                refreshPromise = null;
            }
        })();

        return refreshPromise;
    }

    async function post(endpoint, data = {}) {
        try {
            let response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(data)
            });

            // Intercept expired CSRF token (401 with CSRF_EXPIRED)
            if (response.status === 401) {
                const cloned = response.clone();
                try {
                    const errData = await cloned.json();
                    if (errData.code === 'CSRF_EXPIRED') {
                        const newToken = await refreshCsrfToken();
                        // Retry the request once with the fresh token
                        response = await fetch(endpoint, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': newToken
                            },
                            body: JSON.stringify(data)
                        });
                    }
                } catch (refreshErr) {
                    console.error('CSRF token refresh failed:', refreshErr);
                }
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            return { error: true, message: 'Network error' };
        }
    }

    return {
        post,
        setRefreshUrl,
        getCsrfToken,
        refreshCsrfToken
    };
})();