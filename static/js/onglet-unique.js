/**
 * Une seule page Educ_RDC active dans le navigateur.
 * Les autres onglets / fenêtres sont mis en pause (pages inutilisées).
 */
(function initOngletUnique() {
    'use strict';

    const STORAGE_KEY = 'educ_rdc_onglet_leader';
    const CHANNEL = 'educ-rdc-onglet';
    const HEARTBEAT_MS = 2000;
    const STALE_MS = 8000;

    window.__educOngletActif = true;

    function uuid() {
        try {
            if (window.crypto && typeof window.crypto.randomUUID === 'function') {
                return window.crypto.randomUUID();
            }
        } catch (_) { /* ignore */ }
        return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }

    let tabId = '';
    try {
        tabId = sessionStorage.getItem('educ_rdc_tab_id') || uuid();
        sessionStorage.setItem('educ_rdc_tab_id', tabId);
    } catch (_) {
        tabId = uuid();
    }

    let isLeader = false;
    let titreOriginal = document.title;
    let channel = null;

    function overlay() {
        return document.getElementById('overlayOngletInactif');
    }

    function lireLeader() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (_) {
            return null;
        }
    }

    function ecrireLeader() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                tabId: tabId,
                at: Date.now(),
            }));
        } catch (_) { /* ignore */ }
    }

    function effacerLeaderSiMoi() {
        const data = lireLeader();
        if (data && data.tabId === tabId) {
            try { localStorage.removeItem(STORAGE_KEY); } catch (_) { /* ignore */ }
        }
    }

    function geler() {
        if (!isLeader && window.__educOngletActif === false) return;
        isLeader = false;
        window.__educOngletActif = false;
        document.body.classList.add('onglet-inactif');
        const el = overlay();
        if (el) el.hidden = false;
        if (!document.title.startsWith('Inactive — ')) {
            titreOriginal = document.title;
            document.title = `Inactive — ${titreOriginal}`;
        }
        document.dispatchEvent(new CustomEvent('educ-onglet-change', { detail: { active: false } }));
    }

    function activer() {
        isLeader = true;
        window.__educOngletActif = true;
        document.body.classList.remove('onglet-inactif');
        const el = overlay();
        if (el) el.hidden = true;
        if (document.title.startsWith('Inactive — ')) {
            document.title = titreOriginal || document.title.replace(/^Inactive — /, '');
        }
        ecrireLeader();
        if (channel) {
            try { channel.postMessage({ type: 'claim', tabId: tabId }); } catch (_) { /* ignore */ }
        }
        document.dispatchEvent(new CustomEvent('educ-onglet-change', { detail: { active: true } }));
    }

    function onMessage(data) {
        if (!data || data.tabId === tabId) return;
        if (data.type === 'claim') geler();
        if (data.type === 'release' && !isLeader) {
            const leader = lireLeader();
            if (!leader || leader.tabId === data.tabId || (Date.now() - (leader.at || 0)) > STALE_MS) {
                activer();
            }
        }
    }

    try {
        if ('BroadcastChannel' in window) {
            channel = new BroadcastChannel(CHANNEL);
            channel.onmessage = function (ev) { onMessage(ev.data || {}); };
        }
    } catch (_) {
        channel = null;
    }

    window.addEventListener('storage', function (ev) {
        if (ev.key !== STORAGE_KEY || !ev.newValue) return;
        try {
            const data = JSON.parse(ev.newValue);
            if (data.tabId && data.tabId !== tabId) geler();
        } catch (_) { /* ignore */ }
    });

    window.addEventListener('beforeunload', function () {
        if (!isLeader) return;
        if (channel) {
            try { channel.postMessage({ type: 'release', tabId: tabId }); } catch (_) { /* ignore */ }
        }
        effacerLeaderSiMoi();
    });

    document.addEventListener('click', function (ev) {
        const btn = ev.target && ev.target.closest && ev.target.closest('#btnActiverOnglet');
        if (!btn) return;
        ev.preventDefault();
        activer();
    });

    setInterval(function () {
        if (isLeader) {
            ecrireLeader();
            return;
        }
        const leader = lireLeader();
        if (!leader || (Date.now() - (leader.at || 0)) > STALE_MS) {
            activer();
        }
    }, HEARTBEAT_MS);

    // Dernière page ouverte / rechargée devient l'unique page active
    activer();
})();
