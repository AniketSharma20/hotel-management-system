/**
 * admin-sos.js
 * ────────────────────────────────────────────────────────────────────────────
 * Real-Time SOS / Emergency Alert Module – Admin Dashboard
 * The Grand Aurelia Hotel Management System
 *
 * Responsibilities
 * ─────────────────
 * 1. Opens a Socket.IO connection to the Flask-SocketIO backend.
 * 2. Joins the 'admin_room' channel so this client receives broadcast alerts.
 * 3. Listens for 'emergency_alert' events and renders them live on the Admin panel.
 * 4. Shows a full-screen emergency banner with an audible cue.
 * 5. Lets admins Acknowledge / Resolve alerts via REST PATCH calls.
 * 6. Loads historical alerts from the REST API on page load.
 *
 * Usage
 * ──────
 * This script is loaded after socket.io.js (from CDN) and app.js.
 * It self-initialises via DOMContentLoaded.
 * ────────────────────────────────────────────────────────────────────────────
 */

const SOS_SERVER = 'http://127.0.0.1:5000';   // Flask-SocketIO backend

const SOSModule = (() => {

    /* ── State ────────────────────────────────────────────────────────────── */
    let socket      = null;
    let _connected  = false;
    let _alerts     = [];           // in-memory cache (newest first)
    let _bannerTimer = null;

    /* ── DOM refs (resolved lazily after page load) ──────────────────────── */
    const el = () => ({
        feed:          document.getElementById('sos-alert-feed'),
        emptyState:    document.getElementById('sos-empty-state'),
        statusBadge:   document.getElementById('sos-status-badge'),
        statusDot:     document.getElementById('sos-status-dot'),
        statusText:    document.getElementById('sos-status-text'),
        banner:        document.getElementById('sos-emergency-banner'),
        bannerMsg:     document.getElementById('sos-banner-message'),
        bannerDismiss: document.getElementById('sos-banner-dismiss'),
        testBtn:       document.getElementById('sos-test-btn'),
    });

    /* ── Audio beep (synthesised, no file needed) ────────────────────────── */
    function playAlert() {
        try {
            const ctx  = new (window.AudioContext || window.webkitAudioContext)();
            const osc  = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'square';
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.setValueAtTime(660, ctx.currentTime + 0.15);
            osc.frequency.setValueAtTime(880, ctx.currentTime + 0.30);
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.6);
        } catch (_) { /* silently ignore if audio policy blocks */ }
    }

    /* ── Status badge helper ────────────────────────────────────────────────*/
    function setStatus(type) {   // 'connected' | 'connecting' | 'disconnected'
        const { statusBadge, statusText } = el();
        if (!statusBadge) return;

        statusBadge.className = 'sos-status-badge';  // reset
        if (type === 'connected') {
            statusText.textContent = 'Live – Monitoring';
        } else if (type === 'connecting') {
            statusBadge.classList.add('connecting');
            statusText.textContent = 'Connecting…';
        } else {
            statusBadge.classList.add('disconnected');
            statusText.textContent = 'Disconnected';
        }
    }

    /* ── Banner ──────────────────────────────────────────────────────────── */
    function showBanner(alert) {
        const { banner, bannerMsg } = el();
        if (!banner) return;

        bannerMsg.textContent =
            `🚨 EMERGENCY — Room ${alert.room_number}  |  ${alert.guest_name}  |  ${_fmtTime(alert.timestamp)}`;
        banner.classList.add('active');

        // Auto-dismiss after 12 s
        clearTimeout(_bannerTimer);
        _bannerTimer = setTimeout(() => banner.classList.remove('active'), 12000);
    }

    function dismissBanner() {
        const { banner } = el();
        if (banner) banner.classList.remove('active');
    }

    /* ── Format helpers ─────────────────────────────────────────────────── */
    function _fmtTime(iso) {
        try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
        catch (_) { return iso; }
    }

    function _fmtDatetime(iso) {
        try { return new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }); }
        catch (_) { return iso; }
    }

    /* ── Render alert card ───────────────────────────────────────────────── */
    function _buildCard(alert, isNew = false) {
        const div = document.createElement('div');
        div.className = `sos-alert-card ${alert.status}${isNew ? ' new-alert' : ''}`;
        div.id = `sos-card-${alert.alert_id || alert.id}`;

        const statusLabel = {
            active:       '🔴 ACTIVE',
            acknowledged: '🟡 Acknowledged',
            resolved:     '🟢 Resolved',
        }[alert.status] || alert.status;

        const canAck     = alert.status === 'active';
        const canResolve = alert.status !== 'resolved';
        const alertId    = alert.alert_id || alert.id;

        div.innerHTML = `
            <div class="sos-room-badge">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>${alert.room_number}</span>
            </div>
            <div class="sos-alert-info">
                <div class="sos-alert-message">
                    Emergency – Room ${alert.room_number}
                </div>
                <div class="sos-alert-meta">
                    <span><i class="fa-solid fa-user"></i> ${alert.guest_name || 'Unknown Guest'}</span>
                    <span><i class="fa-regular fa-clock"></i> ${_fmtDatetime(alert.received_at || alert.timestamp)}</span>
                    <span>${statusLabel}</span>
                </div>
                ${alert.notes ? `<div style="font-size:0.78rem;color:rgba(255,255,255,0.5);margin-top:0.35rem;"><i class="fa-solid fa-note-sticky"></i> ${alert.notes}</div>` : ''}
            </div>
            <div class="sos-alert-actions">
                ${canAck     ? `<button class="sos-btn-ack"     onclick="SOSModule.acknowledge(${alertId}, this)"><i class="fa-solid fa-check"></i> Ack</button>` : ''}
                ${canResolve ? `<button class="sos-btn-resolve" onclick="SOSModule.resolve(${alertId}, this)"><i class="fa-solid fa-circle-check"></i> Resolve</button>` : ''}
            </div>
        `;

        // Remove 'new-alert' glow after 5 s
        if (isNew) setTimeout(() => div.classList.remove('new-alert'), 5000);

        return div;
    }

    /* ── Refresh the feed from the in-memory array ───────────────────────── */
    function _render() {
        const { feed, emptyState } = el();
        if (!feed) return;

        feed.innerHTML = '';

        if (_alerts.length === 0) {
            if (emptyState) emptyState.style.display = 'flex';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';

        _alerts.forEach(a => feed.appendChild(_buildCard(a)));
    }

    /* ── Prepend a new alert (called when socket event fires) ────────────── */
    function _prependAlert(alert, isNew = true) {
        // Remove any existing card for this ID to avoid duplicates
        const existing = document.getElementById(`sos-card-${alert.alert_id || alert.id}`);
        if (existing) existing.remove();

        const { feed, emptyState } = el();
        if (!feed) return;
        if (emptyState) emptyState.style.display = 'none';

        // Add to state array at front
        _alerts = [alert, ..._alerts.filter(a => (a.id || a.alert_id) !== (alert.id || alert.alert_id))];

        const card = _buildCard(alert, isNew);
        feed.prepend(card);
    }

    /* ── Update an existing card in the feed after ACK / Resolve ─────────── */
    function _updateCard(alertData) {
        const alertId = alertData.alert_id || alertData.id;
        // Update memory
        _alerts = _alerts.map(a =>
            (a.id === alertId || a.alert_id === alertId) ? { ...a, ...alertData } : a
        );
        // Replace card DOM
        const existing = document.getElementById(`sos-card-${alertId}`);
        if (existing) {
            const updated = _buildCard({ ..._alerts.find(a => (a.id || a.alert_id) === alertId) });
            existing.replaceWith(updated);
        }
    }

    /* ── Load historical alerts from REST API ────────────────────────────── */
    async function loadHistory() {
        try {
            const resp = await fetch(`${SOS_SERVER}/api/sos/alerts`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            _alerts = data.alerts || [];
            _render();
        } catch (err) {
            console.warn('[SOS] Could not load history:', err.message);
        }
    }

    /* ── Acknowledge alert ───────────────────────────────────────────────── */
    async function acknowledge(alertId, btn) {
        try {
            btn.disabled = true;
            const resp = await fetch(`${SOS_SERVER}/api/sos/alerts/${alertId}/acknowledge`, {
                method:  'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ notes: 'Staff notified via dashboard.' }),
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            _updateCard(data.alert);
            if (window.app?.ui?.showToast) {
                app.ui.showToast(`Alert for Room ${data.alert.room_number} acknowledged.`, 'success');
            }
        } catch (err) {
            console.error('[SOS] Acknowledge failed:', err);
            if (btn) btn.disabled = false;
        }
    }

    /* ── Resolve alert ───────────────────────────────────────────────────── */
    async function resolve(alertId, btn) {
        try {
            btn.disabled = true;
            const resp = await fetch(`${SOS_SERVER}/api/sos/alerts/${alertId}/resolve`, {
                method:  'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ notes: 'Situation resolved by staff.' }),
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            _updateCard(data.alert);
            if (window.app?.ui?.showToast) {
                app.ui.showToast(`Alert for Room ${data.alert.room_number} resolved.`, 'success');
            }
        } catch (err) {
            console.error('[SOS] Resolve failed:', err);
            if (btn) btn.disabled = false;
        }
    }

    /* ── Fire a test SOS (dev helper) ────────────────────────────────────── */
    async function fireTest() {
        const rooms = ['101', '204', '310', '512', '701'];
        const names = ['Priya Sharma', 'Rahul Mehta', 'Anjali Singh', 'Vikram Patel', 'Neha Gupta'];
        const room  = rooms[Math.floor(Math.random() * rooms.length)];
        const name  = names[Math.floor(Math.random() * names.length)];

        try {
            const resp = await fetch(`${SOS_SERVER}/api/sos/test`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    room_number: room,
                    guest_name:  name,
                    timestamp:   new Date().toISOString(),
                }),
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            // The backend will emit 'emergency_alert' → socket handler below will pick it up
        } catch (err) {
            console.warn('[SOS] Test fire failed (backend offline?)', err.message);
            // Simulate locally when backend is down
            const fakeAlert = {
                alert_id:    Date.now(),
                id:          Date.now(),
                room_number: room,
                guest_name:  name,
                timestamp:   new Date().toISOString(),
                received_at: new Date().toISOString(),
                status:      'active',
                notes:       '',
                message:     `🚨 EMERGENCY in Room ${room}! Immediate assistance required.`,
            };
            _onEmergencyAlert(fakeAlert);
        }
    }

    /* ── Socket event handler (separated for reuse) ───────────────────────── */
    function _onEmergencyAlert(alert) {
        console.log('[SOS] emergency_alert received:', alert);
        playAlert();
        showBanner(alert);
        _prependAlert(alert, true);

        // Switch admin to SOS section if they're on another section
        const adminSection = document.getElementById('admin');
        if (adminSection?.classList.contains('active-view')) {
            // Already on admin, just scroll to SOS panel
            document.getElementById('sos-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    /* ── Connect to SocketIO ─────────────────────────────────────────────── */
    function connect() {
        if (typeof io === 'undefined') {
            console.warn('[SOS] socket.io.js not loaded yet.');
            setStatus('disconnected');
            return;
        }

        setStatus('connecting');

        socket = io(SOS_SERVER, {
            transports:        ['websocket', 'polling'],
            reconnectionDelay: 2000,
            reconnectionAttempts: 10,
        });

        socket.on('connect', () => {
            _connected = true;
            setStatus('connected');
            socket.emit('join_admin', { role: 'admin' });
            console.log('[SOS] Connected and joined admin_room.');
        });

        socket.on('admin_joined', (data) => {
            console.log('[SOS] Server confirmed:', data.message);
        });

        socket.on('emergency_alert', _onEmergencyAlert);

        socket.on('disconnect', (reason) => {
            _connected = false;
            setStatus('disconnected');
            console.warn('[SOS] Disconnected:', reason);
        });

        socket.on('connect_error', (err) => {
            setStatus('disconnected');
            console.warn('[SOS] Connection error:', err.message);
        });
    }

    /* ── Public API ──────────────────────────────────────────────────────── */
    function init() {
        connect();
        loadHistory();

        // Wire dismiss banner button
        const { bannerDismiss, testBtn } = el();
        if (bannerDismiss) bannerDismiss.addEventListener('click', dismissBanner);
        if (testBtn)       testBtn.addEventListener('click', fireTest);

        console.log('[SOS] Module initialised.');
    }

    return { init, acknowledge, resolve, fireTest };

})();

/* ── Boot on DOM ready ──────────────────────────────────────────────────────*/
document.addEventListener('DOMContentLoaded', () => SOSModule.init());

// Expose to global scope so onclick attributes can reach it
window.SOSModule = SOSModule;
