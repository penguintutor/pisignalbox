document.addEventListener("DOMContentLoaded", function() {

    // Configure the CSRF refresh endpoint URL from Flask
    ApiClient.setRefreshUrl(LOCO_CONFIG.csrfToken);

    // Elements
    const locoSelect = document.getElementById('locoSelect');
    const defaultOption = locoSelect.options[0];
    const acquireStatus = document.getElementById('acquireStatus');
    const controlPanel = document.getElementById('controlPanel');
    const locoDetailsCard = document.getElementById('locoDetailsCard');

    const locoImage = document.getElementById('locoImage');
    const locoTitle = document.getElementById('locoTitle');
    const locoDescription = document.getElementById('locoDescription');

    const speedSlider = document.getElementById('speedSlider');
    const speedDisplay = document.getElementById('speedDisplay');
    const dirRadios = document.getElementsByName('dirRadio');
    const dirForward = document.getElementById('dirForward');
    const btnStop = document.getElementById('btnStop');
    const btnStopAll = document.getElementById('btnStopAll');
    const funcButtons = document.querySelectorAll('.func-btn');

    // Modal initialization (Bootstrap 5)
    const acquireModalEl = document.getElementById('acquireModal');
    const acquireModal = new bootstrap.Modal(acquireModalEl);

    let currentLocoRef = null;

    // Acquire polling configuration: 6 retries * 5000ms = 30 seconds total wait
    const MAX_ACQUIRE_RETRIES = 6;
    const ACQUIRE_RETRY_DELAY_MS = 5000;
    let acquireTimer = null;

    // Status polling & interaction guards
    const STATUS_POLL_INTERVAL_MS = 2000;
    let statusTimer = null;
    let isDraggingSlider = false;
    const activeTriggers = new Set(); // Tracks currently held trigger funcIds
    let functionSyncEpoch = 0;        // Prevents stale in-flight polls overwriting fresh clicks

    function clearAcquireTimer() {
        if (acquireTimer) {
            clearTimeout(acquireTimer);
            acquireTimer = null;
        }
    }

    function clearStatusTimer() {
        if (statusTimer) {
            clearInterval(statusTimer);
            statusTimer = null;
        }
    }

    function startStatusPolling() {
        clearStatusTimer();
        statusTimer = setInterval(pollLocoStatus, STATUS_POLL_INTERVAL_MS);
    }

    // Normalize "on"/"off", 1/0, or true/false from Python into a boolean
    function normalizeStatus(val) {
        if (typeof val === 'boolean') return val;
        if (typeof val === 'number') return val === 1;
        if (typeof val === 'string') {
            const lower = val.toLowerCase();
            return lower === 'on' || lower === '1' || lower === 'true';
        }
        return false;
    }

    // Only touch the DOM when the button's visual state actually changes
    function setButtonVisualState(btn, isOn, force = false) {
        const targetState = isOn ? 'on' : 'off';
        const type = btn.dataset.funcType;

        if (!force && btn.dataset.funcState === targetState) return;

        btn.dataset.funcState = targetState;
        btn.classList.remove('btn-primary', 'btn-trigger-active', 'btn-outline-secondary');

        if (isOn && type === 'latch') {
            btn.classList.add('btn-primary');
        } else if (isOn && type === 'trigger') {
            btn.classList.add('btn-trigger-active');
        } else {
            btn.classList.add('btn-outline-secondary');
        }

        const icon = btn.querySelector('.func-type-icon');
        if (icon) {
            icon.className = 'bi func-type-icon ms-2 flex-shrink-0';
            if (type === 'latch') {
                icon.classList.add(isOn ? 'bi-toggle-on' : 'bi-toggle-off');
            } else if (type === 'trigger') {
                icon.classList.add(isOn ? 'bi-record-circle-fill' : 'bi-record-circle');
            }
        }

        btn.setAttribute('aria-pressed', String(isOn));
    }

    // Configure all 29 function buttons from Python payload:
    // { "0": ["Headlights", "latch", "on"], "2": ["Horn", "trigger", "off"], ... }
    // (Also works if Python returns a 0-indexed JSON array)
    function applyFunctionsConfig(functionsData) {
        funcButtons.forEach(btn => {
            const fId = btn.dataset.funcId;
            const descSpan = btn.querySelector('.func-desc');
            const entry = functionsData ? functionsData[fId] : null;

            // Any omitted index or entry marked "disabled" is disabled
            if (!entry || entry[1] === 'disabled') {
                descSpan.innerText = (entry && entry[0]) ? entry[0] : 'Unused';
                btn.dataset.funcType = 'disabled';
                btn.disabled = true;
                setButtonVisualState(btn, false, true);
                return;
            }

            const [label, type, rawStatus] = entry;
            descSpan.innerText = label || `Fn ${fId}`;
            btn.dataset.funcType = type; // "latch" or "trigger"
            btn.disabled = false;
            setButtonVisualState(btn, normalizeStatus(rawStatus), true);
        });
    }

    // Sync only changed button statuses during periodic polling
    function syncFunctionStates(functionsData) {
        if (!functionsData) return;

        funcButtons.forEach(btn => {
            const fId = btn.dataset.funcId;
            if (activeTriggers.has(fId)) return;

            const entry = functionsData[fId];
            if (entry === undefined || entry === null) return;

            // Handles full [label, type, status] tuples OR a compact { "0": "on" } status map
            const rawStatus = Array.isArray(entry) ? entry[2] : entry;
            const type = Array.isArray(entry) ? entry[1] : btn.dataset.funcType;

            if (type === 'disabled') {
                btn.dataset.funcType = 'disabled';
                btn.disabled = true;
                setButtonVisualState(btn, false);
            } else if (btn.dataset.funcType !== 'disabled') {
                setButtonVisualState(btn, normalizeStatus(rawStatus));
            }
        });
    }

    function sendFunctionUpdate(funcId, stateStr) {
        if (!currentLocoRef) return;
        functionSyncEpoch++;

        // Note: uses `loco_ref` if your /function route expects it
        callAPI(LOCO_CONFIG.locoFunction, {
            loco_ref: currentLocoRef,
            function_index: funcId,
            function_value: stateStr // "on" or "off"
        });
    }

    // Helper: Reset UI and state back to initial defaults
    function resetController() {
        clearAcquireTimer();
        clearStatusTimer();
        isDraggingSlider = false;
        activeTriggers.clear();
        functionSyncEpoch++;
        currentLocoRef = null;
        controlPanel.disabled = true;
        acquireStatus.innerText = "";

        // Reset locomotive details to defaults and hide card
        locoDetailsCard.classList.add('d-none');
        locoImage.src = "";
        locoTitle.innerText = "Details:";
        locoDescription.innerText = "";

        // Reset speed and direction controls
        speedSlider.value = 0;
        speedDisplay.innerText = "00";
        dirForward.checked = true;

        // Reset function buttons back to default labels and inactive state
        funcButtons.forEach(btn => {
            const fId = btn.dataset.funcId;
            const descSpan = btn.querySelector('.func-desc');
            descSpan.innerText = `Fn ${fId}`;
            btn.disabled = false;
            delete btn.dataset.funcType;
            setButtonVisualState(btn, false, true);
        });

        // Revert the first dropdown option to its initial disabled prompt
        defaultOption.textContent = "Choose a loco to acquire...";
        defaultOption.disabled = true;
        locoSelect.value = "";
    }

    // Helper: Controller-specific wrapper around shared ApiClient
    async function callAPI(endpoint, data) {
        const result = await ApiClient.post(endpoint, data);

        // Centrally handle expired/cancelled locomotive sessions
        if (result.status === 'session_cancelled') {
            resetController();
            acquireStatus.innerText = result.message || "Session cancelled.";
        }

        return result;
    }

    // Periodic status check for shared control / external updates
    function pollLocoStatus() {
        // Pause checks if no loco is active OR while any trigger button is held down
        if (!currentLocoRef || activeTriggers.size > 0) return;

        const requestEpoch = functionSyncEpoch;

        callAPI(LOCO_CONFIG.locoStatus, { loco_ref: currentLocoRef }).then(res => {
            // Ignore if controller was reset or switched while fetch was in flight
            if (!currentLocoRef || res.status !== 'valid') return;

            // Update status message (e.g., "Emergency Stop" or "" when normal)
            acquireStatus.innerText = res.message || "";

            // Update speed only if the user isn't currently dragging the slider
            if (!isDraggingSlider && res.speed !== undefined) {
                speedSlider.value = res.speed;
                speedDisplay.innerText = String(res.speed).padStart(2, '0');
            }

            // Update direction (1 = forward, 0 = reverse)
            if (res.direction === 1) {
                dirForward.checked = true;
            } else if (res.direction === 0) {
                dirRadios.forEach(radio => {
                    if (radio !== dirForward) radio.checked = true;
                });
            }

            // Update function states only if no trigger is held and no local toggle happened mid-poll
            if (res.functions && activeTriggers.size === 0 && requestEpoch === functionSyncEpoch) {
                syncFunctionStates(res.functions);
            }
        });
    }

    // Acquire or Disable Locomotive
    locoSelect.addEventListener('change', function() {
        const selectedRef = this.value;
        if (!selectedRef) {
            resetController();
            return;
        }
        attemptAcquire(selectedRef, "request", 0);
    });

    function attemptAcquire(locoRef, mode, retryCount = 0) {
        clearAcquireTimer();
        clearStatusTimer();

        if (retryCount === 0) {
            acquireStatus.innerText = "Attempting to acquire...";
            defaultOption.textContent = "Disable controller";
            defaultOption.disabled = false;
        } else {
            acquireStatus.innerText = `Waiting for locomotive... (attempt ${retryCount + 1}/${MAX_ACQUIRE_RETRIES + 1})`;
        }

        callAPI(LOCO_CONFIG.locoAcquire, { loco_ref: locoRef, mode: mode }).then(res => {
            if (locoSelect.value !== locoRef) return;

            if (res.status === 'acquired') {
                currentLocoRef = locoRef;
                acquireStatus.innerText = "";
                controlPanel.disabled = false;

                defaultOption.textContent = "Disable controller";
                defaultOption.disabled = false;

                loadLocoDetails(locoRef);

                // Reset speed/dir to safe defaults, then poll for actual current state
                speedSlider.value = 0;
                speedDisplay.innerText = "00";
                dirForward.checked = true;

                pollLocoStatus();
                startStatusPolling();

            } else if (res.status === 'acquiring') {
                if (retryCount < MAX_ACQUIRE_RETRIES) {
                    acquireTimer = setTimeout(() => {
                        attemptAcquire(locoRef, "request", retryCount + 1);
                    }, ACQUIRE_RETRY_DELAY_MS);
                } else {
                    resetController();
                    acquireStatus.innerText = "Acquire failed: Timed out waiting for locomotive.";
                }

            } else if (res.status === 'duplicate') {
                resetController();
                acquireStatus.innerText = "Unable to allocate due to a duplicate ID in use";

            } else if (res.status === 'in_use') {
                acquireModal.show();

                document.getElementById('btnSteal').onclick = () => {
                    acquireModal.hide();
                    attemptAcquire(locoRef, "steal", 0);
                };
                document.getElementById('btnShare').onclick = () => {
                    acquireModal.hide();
                    attemptAcquire(locoRef, "share", 0);
                };
                document.getElementById('btnCancelAcquire').onclick = () => {
                    resetController();
                    acquireStatus.innerText = "Acquisition cancelled.";
                };
            } else {
                resetController();
                acquireStatus.innerText = res.message || "Failed to acquire loco.";
            }
        });
    }

    // Load Locomotive Details & Initial Function Map
    function loadLocoDetails(locoRef) {
        callAPI(LOCO_CONFIG.locoDetails, { loco_ref: locoRef }).then(res => {
            if (currentLocoRef !== locoRef) return;

            const imageUrl = LOCO_CONFIG.locoImage;
            if (!res.error && res.status !== 'session_cancelled') {
                locoImage.src = `${imageUrl}?filename=${encodeURIComponent(res.image_url)}`;
                locoTitle.innerText = res.title;
                locoDescription.innerText = res.summary;
                locoDetailsCard.classList.remove('d-none');

                // Configure function labels, types (latch/trigger/disabled), and initial states
                applyFunctionsConfig(res.functions || {});
            }
        });
    }

    // Speed & Direction Updates
    function sendSpeedDir() {
        if (!currentLocoRef) return;
        const speed = Number.parseInt(speedSlider.value, 10);
        const direction = document.querySelector('input[name="dirRadio"]:checked').value;

        callAPI(LOCO_CONFIG.locoSpeedDir, {
            loco_ref: currentLocoRef,
            speed: speed,
            direction: direction
        });
    }

    speedSlider.addEventListener('pointerdown', () => { isDraggingSlider = true; });
    speedSlider.addEventListener('pointerup', () => { isDraggingSlider = false; });

    speedSlider.addEventListener('input', function() {
        isDraggingSlider = true;
        speedDisplay.innerText = this.value.padStart(2, '0');
    });

    speedSlider.addEventListener('change', function() {
        isDraggingSlider = false;
        sendSpeedDir();
    });

    dirRadios.forEach(radio => {
        radio.addEventListener('change', sendSpeedDir);
    });

    // Stop Controls
    btnStop.addEventListener('click', function() {
        speedSlider.value = 0;
        speedDisplay.innerText = "00";
        callAPI(LOCO_CONFIG.locoStop, { loco_ref: currentLocoRef });
    });

    btnStopAll.addEventListener('click', function() {
        speedSlider.value = 0;
        speedDisplay.innerText = "00";
        callAPI(LOCO_CONFIG.locoStopAll, {});
    });

    // Function Button Interactions (Latch, Trigger, Disabled)
    function releaseTrigger(btn, event) {
        const funcId = btn.dataset.funcId;
        if (!activeTriggers.has(funcId)) return;

        activeTriggers.delete(funcId);
        if (event && event.pointerId !== undefined && btn.hasPointerCapture(event.pointerId)) {
            btn.releasePointerCapture(event.pointerId);
        }

        setButtonVisualState(btn, false);
        sendFunctionUpdate(funcId, 'off');
    }

    funcButtons.forEach(btn => {
        // LATCH: toggle state on click
        btn.addEventListener('click', function() {
            if (this.disabled || this.dataset.funcType !== 'latch' || !currentLocoRef) return;

            const nextOn = this.dataset.funcState !== 'on';
            setButtonVisualState(this, nextOn);
            sendFunctionUpdate(this.dataset.funcId, nextOn ? 'on' : 'off');
        });

        // TRIGGER: "on" on press, "off" on release
        btn.addEventListener('pointerdown', function(e) {
            if (this.disabled || this.dataset.funcType !== 'trigger' || !currentLocoRef) return;
            if (e.pointerType === 'mouse' && e.button !== 0) return; // Primary button only

            const funcId = this.dataset.funcId;
            if (activeTriggers.has(funcId)) return;

            activeTriggers.add(funcId);
            this.setPointerCapture(e.pointerId);
            setButtonVisualState(this, true);
            sendFunctionUpdate(funcId, 'on');
        });

        btn.addEventListener('pointerup', function(e) {
            releaseTrigger(this, e);
        });

        btn.addEventListener('pointercancel', function(e) {
            releaseTrigger(this, e);
        });

        btn.addEventListener('lostpointercapture', function(e) {
            releaseTrigger(this, e);
        });

        // Prevent mobile long-press menu from interrupting a held trigger
        btn.addEventListener('contextmenu', function(e) {
            if (this.dataset.funcType === 'trigger') {
                e.preventDefault();
            }
        });
    });

});