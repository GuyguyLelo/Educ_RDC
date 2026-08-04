/**
 * Educ_RDC — Frontend JavaScript (Fetch API)
 * Gestion formulaires, validation, notifications, pagination
 */
const EducRDC = (() => {
    'use strict';

    const API = '/api';

    function getCookie(name) {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? decodeURIComponent(match[2]) : null;
    }

    function toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return alert(message);
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    async function api(url, options = {}) {
        const headers = options.headers || {};
        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = headers['Content-Type'] || 'application/json';
        }
        const csrf = getCookie('csrftoken');
        if (csrf) headers['X-CSRFToken'] = csrf;

        const response = await fetch(url, {
            credentials: 'same-origin',
            ...options,
            headers,
        });

        if (response.status === 204) return null;

        const contentType = response.headers.get('content-type') || '';
        const data = contentType.includes('application/json')
            ? await response.json()
            : await response.text();

        if (!response.ok) {
            let msg = 'Une erreur est survenue.';
            if (typeof data === 'object' && data) {
                msg = data.detail || data.error || JSON.stringify(data);
            } else if (typeof data === 'string' && data) {
                msg = data.slice(0, 200);
            }
            throw new Error(msg);
        }
        return data;
    }

    function openModal(id) {
        const modal = document.getElementById(id);
        if (modal) modal.hidden = false;
    }

    function closeModal(id) {
        const modal = document.getElementById(id);
        if (modal) modal.hidden = true;
    }

    function bindModalClosers() {
        document.querySelectorAll('.modal').forEach((modal) => {
            modal.querySelectorAll('[data-close]').forEach((btn) => {
                btn.addEventListener('click', () => { modal.hidden = true; });
            });
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.hidden = true;
            });
        });
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function initials(text) {
        const parts = String(text || '').trim().split(/\s+/).filter(Boolean);
        if (!parts.length) return '—';
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }

    function setCount(id, count, label = 'résultat') {
        const el = document.getElementById(id);
        if (!el) return;
        const n = Number(count) || 0;
        const word = n > 1 ? label + 's' : label;
        el.textContent = `${n} ${word}`;
    }

    function emptyRow(colspan, title, subtitle) {
        return `<tr><td class="cell-empty" colspan="${colspan}" data-label="Info">
            <div class="empty-state">
                <strong>${escapeHtml(title)}</strong>
                <span>${escapeHtml(subtitle)}</span>
            </div>
        </td></tr>`;
    }

    function renderPagination(containerId, page, totalPages, onPage) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = '';
        if (totalPages <= 1) return;
        const maxButtons = window.innerWidth <= 560 ? 5 : 9;
        let start = Math.max(1, page - Math.floor(maxButtons / 2));
        let end = Math.min(totalPages, start + maxButtons - 1);
        start = Math.max(1, end - maxButtons + 1);

        const addBtn = (label, target, disabled = false, active = false) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = label;
            if (active) btn.classList.add('active');
            btn.disabled = disabled;
            if (!disabled) btn.addEventListener('click', () => onPage(target));
            el.appendChild(btn);
        };

        addBtn('‹', Math.max(1, page - 1), page === 1);
        for (let i = start; i <= end; i++) addBtn(String(i), i, false, i === page);
        addBtn('›', Math.min(totalPages, page + 1), page === totalPages);
    }

    function bindFileDropPreview(inputId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        const drop = input.closest('.file-drop');
        if (!drop) return;
        const title = drop.querySelector('.file-drop-title');
        input.addEventListener('change', () => {
            if (input.files && input.files[0] && title) {
                title.textContent = input.files[0].name;
            }
        });
    }

    function sizeChartCanvas(canvas) {
        const parent = canvas.parentElement;
        const cssWidth = Math.max(280, parent ? parent.clientWidth : 800);
        const cssHeight = window.innerWidth <= 560 ? 220 : window.innerWidth <= 1024 ? 280 : 320;
        const dpr = window.devicePixelRatio || 1;
        canvas.style.width = cssWidth + 'px';
        canvas.style.height = cssHeight + 'px';
        canvas.width = Math.floor(cssWidth * dpr);
        canvas.height = Math.floor(cssHeight * dpr);
        const ctx = canvas.getContext('2d');
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        return { width: cssWidth, height: cssHeight, ctx };
    }

    function drawBarChart(canvasId, labels, values) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const sized = sizeChartCanvas(canvas);
        const ctx = sized.ctx;
        const w = sized.width;
        const h = sized.height;
        ctx.clearRect(0, 0, w, h);

        if (!labels.length) {
            ctx.fillStyle = '#6b7a8d';
            ctx.font = '500 15px Figtree, sans-serif';
            ctx.fillText('Aucune donnée disponible', 40, h / 2);
            return;
        }

        const max = Math.max(...values, 1);
        const pad = 48;
        const gap = (w - pad * 2) / labels.length;
        const barW = Math.min(42, gap * 0.55);

        // Grille horizontale
        ctx.strokeStyle = '#e8eef5';
        ctx.lineWidth = 1;
        for (let g = 0; g < 4; g++) {
            const gy = 28 + ((h - 78) / 3) * g;
            ctx.beginPath();
            ctx.moveTo(pad, gy);
            ctx.lineTo(w - 16, gy);
            ctx.stroke();
        }

        labels.forEach((label, i) => {
            const val = values[i] || 0;
            const barH = ((h - 78) * val) / max;
            const x = pad + gap * i + (gap - barW) / 2;
            const y = h - 48 - barH;

            const grad = ctx.createLinearGradient(0, y, 0, h - 48);
            grad.addColorStop(0, '#007FFF');
            grad.addColorStop(1, '#0a3d7a');
            ctx.fillStyle = grad;
            // Barres arrondies (approximation)
            const r = 4;
            ctx.beginPath();
            ctx.moveTo(x, y + barH);
            ctx.lineTo(x, y + r);
            ctx.quadraticCurveTo(x, y, x + r, y);
            ctx.lineTo(x + barW - r, y);
            ctx.quadraticCurveTo(x + barW, y, x + barW, y + r);
            ctx.lineTo(x + barW, y + barH);
            ctx.closePath();
            ctx.fill();

            // Accent jaune en haut de barre
            ctx.fillStyle = '#FCD116';
            ctx.fillRect(x, y, barW, 3);

            ctx.fillStyle = '#142033';
            ctx.font = '600 12px Sora, sans-serif';
            ctx.fillText(String(val), x + Math.max(0, (barW - 8) / 2), y - 8);

            ctx.fillStyle = '#6b7a8d';
            ctx.font = '500 11px Figtree, sans-serif';
            const short = label.length > 10 ? label.slice(0, 9) + '…' : label;
            ctx.fillText(short, x + gap * 0.05 - 8, h - 24);
        });
    }

    /* ---------- Dashboard ---------- */
    async function chargerDashboard() {
        try {
            const stats = await api(`${API}/stats/`);
            setText('statEleves', stats.nb_eleves);
            setText('statEcoles', stats.nb_ecoles);
            setText('statCartes', stats.nb_cartes);
            setText('statAttente', stats.enrolements_en_attente);

            const labels = (stats.par_province || []).map((p) => p.nom);
            const values = (stats.par_province || []).map((p) => p.nb_eleves);
            drawBarChart('chartProvinces', labels, values);
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    /* ---------- Écoles ---------- */
    let pageEcoles = 1;

    async function chargerProvincesAntennes() {
        const [provinces, antennes] = await Promise.all([
            api(`${API}/provinces/?page_size=100`),
            api(`${API}/antennes/?page_size=100`),
        ]);
        const selP = document.getElementById('selectProvince');
        const selA = document.getElementById('selectAntenne');
        if (!selP || !selA) return;

        const provList = provinces.results || provinces;
        const antList = antennes.results || antennes;

        selP.innerHTML = provList.map((p) => `<option value="${p.id}">${p.nom}</option>`).join('');
        const fillAntennes = () => {
            const pid = selP.value;
            selA.innerHTML = antList
                .filter((a) => String(a.province) === String(pid))
                .map((a) => `<option value="${a.id}">${a.nom}</option>`)
                .join('');
        };
        selP.addEventListener('change', fillAntennes);
        fillAntennes();
    }

    async function chargerEcoles(page = 1) {
        pageEcoles = page;
        const q = document.getElementById('searchEcoles')?.value || '';
        let url = `${API}/ecoles/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        const data = await api(url);
        const rows = data.results || data;
        const tbody = document.querySelector('#tableEcoles tbody');
        const count = data.count ?? rows.length;
        setCount('countEcoles', count);

        tbody.innerHTML = rows.length ? rows.map((e) => `
            <tr>
                <td data-label="École">
                    <div class="entity-cell">
                        <div class="entity-avatar school">${escapeHtml(initials(e.nom))}</div>
                        <div class="entity-meta">
                            <strong title="${escapeHtml(e.nom)}">${escapeHtml(e.nom)}</strong>
                            <span>${escapeHtml(e.directeur || 'Directeur non renseigné')}</span>
                        </div>
                    </div>
                </td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(e.code)}</span></td>
                <td data-label="Type"><span class="badge badge-neutral">${escapeHtml(e.type_display || e.type_ecole)}</span></td>
                <td data-label="Niveau">${escapeHtml(e.niveau_display || e.niveau)}</td>
                <td data-label="Localisation">
                    <div class="entity-meta">
                        <strong>${escapeHtml(e.province_nom || '—')}</strong>
                        <span>${escapeHtml(e.antenne_nom || '')}</span>
                    </div>
                </td>
                <td data-label="Élèves"><strong>${e.nombre_eleves ?? 0}</strong></td>
                <td data-label="Statut"><span class="badge ${e.active ? 'badge-success' : 'badge-danger'}">${e.active ? 'Active' : 'Inactive'}</span></td>
            </tr>
        `).join('') : emptyRow(7, 'Aucune école trouvée', 'Modifiez la recherche ou créez une nouvelle école.');

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationEcoles', pageEcoles, totalPages, chargerEcoles);
        return count;
    }

    function initEcoles() {
        bindModalClosers();
        chargerProvincesAntennes().catch((e) => toast(e.message, 'error'));
        chargerEcoles().catch((e) => toast(e.message, 'error'));

        document.getElementById('btnNouvelleEcole')?.addEventListener('click', () => openModal('modalEcole'));
        document.getElementById('btnSearchEcoles')?.addEventListener('click', () => chargerEcoles(1));
        document.getElementById('searchEcoles')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerEcoles(1);
        });

        document.getElementById('formEcole')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            const payload = Object.fromEntries(new FormData(form).entries());
            payload.province = Number(payload.province);
            payload.antenne = Number(payload.antenne);
            try {
                await api(`${API}/ecoles/`, { method: 'POST', body: JSON.stringify(payload) });
                toast('École créée avec succès.', 'success');
                form.reset();
                closeModal('modalEcole');
                await chargerProvincesAntennes();
                await chargerEcoles(1);
            } catch (err) {
                toast(err.message, 'error');
            }
        });
    }

    /* ---------- Élèves ---------- */
    let pageEleves = 1;

    async function chargerSelectEcoles(selectId) {
        const data = await api(`${API}/ecoles/?page_size=200`);
        const list = data.results || data;
        const sel = document.getElementById(selectId);
        if (!sel) return;
        sel.innerHTML = list.map((e) => `<option value="${e.id}">${e.nom} (${e.code})</option>`).join('');
    }

    async function chargerEleves(page = 1) {
        pageEleves = page;
        const q = document.getElementById('searchEleves')?.value || '';
        let url = `${API}/eleves/?page=${page}`;
        if (q) url += `&q=${encodeURIComponent(q)}`;
        const data = await api(url);
        const rows = data.results || data;
        const tbody = document.querySelector('#tableEleves tbody');
        setCount('countEleves', data.count ?? rows.length);

        tbody.innerHTML = rows.length ? rows.map((e) => {
            const avatar = e.photo_url
                ? `<div class="entity-avatar has-photo"><img src="${escapeHtml(e.photo_url)}" alt="${escapeHtml(e.nom_complet)}"></div>`
                : `<div class="entity-avatar">${escapeHtml(initials(e.nom_complet))}</div>`;
            return `
            <tr>
                <td data-label="Élève">
                    <a class="entity-cell" href="/eleves/${e.id}/" style="color:inherit">
                        ${avatar}
                        <div class="entity-meta">
                            <strong title="${escapeHtml(e.nom_complet)}">${escapeHtml(e.nom_complet)}</strong>
                            <span>${escapeHtml(e.lieu_naissance || 'Lieu de naissance non renseigné')}</span>
                        </div>
                    </a>
                </td>
                <td data-label="Matricule"><span class="code-chip">${escapeHtml(e.matricule)}</span></td>
                <td data-label="Sexe">${escapeHtml(e.sexe_display || e.sexe)}</td>
                <td data-label="Naissance">${escapeHtml(e.date_naissance)}</td>
                <td data-label="École / Classe">
                    <div class="entity-meta">
                        <strong title="${escapeHtml(e.ecole_nom || '')}">${escapeHtml(e.ecole_nom || '—')}</strong>
                        <span>${escapeHtml(e.classe || '')}</span>
                    </div>
                </td>
                <td data-label="Statut"><span class="badge ${e.actif ? 'badge-success' : 'badge-danger'}">${e.actif ? 'Actif' : 'Inactif'}</span></td>
                <td data-label="Actions">
                    <a class="btn btn-secondary btn-sm" href="/eleves/${e.id}/">Détail</a>
                </td>
            </tr>`;
        }).join('') : emptyRow(7, 'Aucun élève trouvé', 'Ajoutez un élève ou affinez votre recherche.');

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationEleves', pageEleves, totalPages, chargerEleves);
    }

    function initEleves() {
        bindModalClosers();
        bindFileDropPreview('elevePhoto');
        chargerSelectEcoles('selectEcoleEleve').catch((e) => toast(e.message, 'error'));
        chargerEleves().catch((e) => toast(e.message, 'error'));

        document.getElementById('btnNouvelEleve')?.addEventListener('click', () => openModal('modalEleve'));
        document.getElementById('btnSearchEleves')?.addEventListener('click', () => chargerEleves(1));
        document.getElementById('searchEleves')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerEleves(1);
        });

        document.getElementById('formEleve')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            const fd = new FormData(form);
            // Retirer photo vide pour éviter erreur API
            const photo = fd.get('photo');
            if (photo instanceof File && !photo.size) fd.delete('photo');
            try {
                await api(`${API}/eleves/`, { method: 'POST', body: fd, headers: {} });
                toast('Élève enregistré.', 'success');
                form.reset();
                const title = form.querySelector('.file-drop-title');
                if (title) title.textContent = 'Déposer une photo ou cliquer pour parcourir';
                closeModal('modalEleve');
                await chargerSelectEcoles('selectEcoleEleve');
                await chargerEleves(1);
            } catch (err) {
                toast(err.message, 'error');
            }
        });
    }

    /* ---------- Détail élève ---------- */
    function fillDetailList(containerId, items) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = items.map(([label, value]) => `
            <div class="detail-item">
                <dt>${escapeHtml(label)}</dt>
                <dd>${escapeHtml(value || '—')}</dd>
            </div>
        `).join('');
    }

    function renderDetailPhoto(eleve) {
        const img = document.getElementById('detailPhoto');
        const fallback = document.getElementById('detailPhotoFallback');
        const badge = document.getElementById('detailBadgePhoto');
        if (!img || !fallback) return;

        if (eleve.photo_url) {
            img.src = eleve.photo_url;
            img.alt = `Photo de ${eleve.nom_complet}`;
            img.hidden = false;
            fallback.hidden = true;
            if (badge) {
                badge.textContent = 'Photo disponible';
                badge.className = 'badge badge-success';
            }
        } else {
            img.hidden = true;
            img.removeAttribute('src');
            fallback.hidden = false;
            fallback.textContent = initials(eleve.nom_complet);
            if (badge) {
                badge.textContent = 'Sans photo';
                badge.className = 'badge badge-warning';
            }
        }
    }

    async function chargerEleveDetail() {
        const root = document.getElementById('eleveDetail');
        if (!root) return;
        const id = root.dataset.eleveId;
        const eleve = await api(`${API}/eleves/${id}/`);

        document.getElementById('detailMatricule').textContent = eleve.matricule;
        document.getElementById('detailNom').textContent = eleve.nom_complet;
        document.getElementById('detailSousTitre').textContent =
            `${eleve.ecole_nom || '—'} · ${eleve.classe || '—'}`;
        document.getElementById('detailSexe').textContent = eleve.sexe_display || eleve.sexe;
        document.getElementById('detailClasse').textContent = eleve.classe || '—';
        const statut = document.getElementById('detailStatut');
        statut.textContent = eleve.actif ? 'Actif' : 'Inactif';
        statut.className = `badge ${eleve.actif ? 'badge-success' : 'badge-danger'}`;

        renderDetailPhoto(eleve);

        fillDetailList('blocIdentite', [
            ['Nom', eleve.nom],
            ['Postnom', eleve.postnom],
            ['Prénom', eleve.prenom],
            ['Date de naissance', eleve.date_naissance],
            ['Lieu de naissance', eleve.lieu_naissance],
            ['Sexe', eleve.sexe_display || eleve.sexe],
        ]);

        fillDetailList('blocScolarite', [
            ['École', eleve.ecole_nom],
            ['Code école', eleve.ecole_code],
            ['Classe', eleve.classe],
            ['Province', eleve.province_nom],
            ['Antenne', eleve.antenne_nom],
            ['Inscription', (eleve.date_inscription || '').slice(0, 10)],
        ]);

        fillDetailList('blocTuteur', [
            ['Nom du tuteur', eleve.nom_tuteur],
            ['Téléphone', eleve.telephone_tuteur],
            ['Adresse', eleve.adresse],
        ]);

        const bio = eleve.biometrie;
        fillDetailList('blocBiometrie', bio ? [
            ['Statut', bio.validee ? 'Validée' : 'En attente'],
            ['Date capture', (bio.date_capture || '').slice(0, 10)],
            ['Empreinte', bio.empreinte_hash ? `${bio.empreinte_hash.slice(0, 16)}…` : '—'],
            ['Observations', bio.observations],
        ] : [
            ['Statut', 'Aucune biométrie non créée'],
            ['Info', 'Ajoutez une photo pour initialiser la biométrie'],
        ]);

        const tEnr = document.querySelector('#tableDetailEnrolements tbody');
        const enrs = eleve.enrolements || [];
        tEnr.innerHTML = enrs.length ? enrs.map((r) => {
            const badge = r.statut === 'valide' ? 'badge-success' : r.statut === 'rejete' ? 'badge-danger' : 'badge-warning';
            return `<tr>
                <td data-label="Année">${escapeHtml(r.annee_scolaire)}</td>
                <td data-label="Statut"><span class="badge ${badge}">${escapeHtml(r.statut_display)}</span></td>
                <td data-label="Date">${escapeHtml((r.date_enrolement || '').slice(0, 10))}</td>
            </tr>`;
        }).join('') : emptyRow(3, 'Aucun enrôlement', 'Cet élève n\'a pas encore de dossier.');

        const tCartes = document.querySelector('#tableDetailCartes tbody');
        const cartes = eleve.cartes || [];
        tCartes.innerHTML = cartes.length ? cartes.map((c) => `
            <tr>
                <td data-label="N° Carte"><span class="code-chip">${escapeHtml(c.numero_carte)}</span></td>
                <td data-label="Statut"><span class="badge badge-info">${escapeHtml(c.statut_display)}</span></td>
                <td data-label="Expiration">${escapeHtml(c.date_expiration)}</td>
                <td data-label="Actions">
                    <div class="actions-inline">
                        <a class="btn btn-primary btn-sm" href="${API}/cartes/${c.id}/pdf/" target="_blank">PDF</a>
                        ${c.qr_code_url ? `<a class="btn btn-secondary btn-sm" href="${escapeHtml(c.qr_code_url)}" target="_blank">QR</a>` : ''}
                    </div>
                </td>
            </tr>
        `).join('') : emptyRow(4, 'Aucune carte', 'La carte sera générée après validation d\'enrôlement.');

        return eleve;
    }

    function initEleveDetail() {
        chargerEleveDetail().catch((e) => toast(e.message, 'error'));

        document.getElementById('inputPhotoDetail')?.addEventListener('change', async (e) => {
            const file = e.target.files && e.target.files[0];
            if (!file) return;
            const root = document.getElementById('eleveDetail');
            const id = root?.dataset.eleveId;
            const fd = new FormData();
            fd.append('photo', file);
            try {
                await api(`${API}/eleves/${id}/photo/`, { method: 'POST', body: fd, headers: {} });
                toast('Photo mise à jour.', 'success');
                await chargerEleveDetail();
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                e.target.value = '';
            }
        });
    }

    /* ---------- Enrôlement ---------- */
    let pageEnrolements = 1;

    async function chargerSelectEleves() {
        const data = await api(`${API}/eleves/?page_size=300`);
        const list = data.results || data;
        const sel = document.getElementById('selectEleveEnrolement');
        if (!sel) return;
        sel.innerHTML = list.map((e) =>
            `<option value="${e.id}">${e.matricule} — ${e.nom_complet}</option>`
        ).join('');
    }

    async function chargerEnrolements(page = 1) {
        pageEnrolements = page;
        const statut = document.getElementById('filtreStatut')?.value || '';
        let url = `${API}/enrolements/?page=${page}`;
        if (statut) url += `&statut=${encodeURIComponent(statut)}`;
        const data = await api(url);
        const rows = data.results || data;
        const tbody = document.querySelector('#tableEnrolements tbody');

        setCount('countEnrolements', data.count ?? rows.length);

        tbody.innerHTML = rows.length ? rows.map((r) => {
            const badge =
                r.statut === 'valide' ? 'badge-success' :
                r.statut === 'rejete' ? 'badge-danger' : 'badge-warning';
            const actions = r.statut === 'en_attente' ? `
                <div class="actions-inline">
                    <button class="btn btn-secondary btn-sm" type="button" data-bio="${r.eleve}" data-enr="${r.id}">Biométrie</button>
                    <button class="btn btn-success btn-sm" type="button" data-valider="${r.id}">Valider</button>
                    <button class="btn btn-danger btn-sm" type="button" data-rejeter="${r.id}">Rejeter</button>
                </div>` : `<span class="badge badge-neutral">Terminé</span>`;

            return `
                <tr>
                    <td data-label="Élève">
                        <div class="entity-cell">
                            <div class="entity-avatar">${escapeHtml(initials(r.eleve_nom))}</div>
                            <div class="entity-meta">
                                <strong>${escapeHtml(r.eleve_nom || '—')}</strong>
                                <span>Dossier #${r.id}</span>
                            </div>
                        </div>
                    </td>
                    <td data-label="Matricule"><span class="code-chip">${escapeHtml(r.eleve_matricule || '—')}</span></td>
                    <td data-label="Année">${escapeHtml(r.annee_scolaire)}</td>
                    <td data-label="Statut"><span class="badge ${badge}">${escapeHtml(r.statut_display)}</span></td>
                    <td data-label="Date">${escapeHtml((r.date_enrolement || '').slice(0, 10))}</td>
                    <td data-label="Actions">${actions}</td>
                </tr>`;
        }).join('') : emptyRow(6, 'Aucun enrôlement', 'Créez un dossier pour démarrer le workflow.');

        tbody.querySelectorAll('[data-bio]').forEach((btn) => {
            btn.addEventListener('click', () => {
                document.getElementById('bioEleveId').value = btn.dataset.bio;
                openModal('modalBiometrie');
            });
        });
        tbody.querySelectorAll('[data-valider]').forEach((btn) => {
            btn.addEventListener('click', () => validerEnrolement(btn.dataset.valider));
        });
        tbody.querySelectorAll('[data-rejeter]').forEach((btn) => {
            btn.addEventListener('click', () => rejeterEnrolement(btn.dataset.rejeter));
        });

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationEnrolements', pageEnrolements, totalPages, chargerEnrolements);
    }

    async function validerEnrolement(id) {
        try {
            const res = await api(`${API}/enrolements/${id}/valider/`, { method: 'POST', body: '{}' });
            toast(res.detail || 'Enrôlement validé et carte générée.', 'success');
            await chargerEnrolements(pageEnrolements);
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function rejeterEnrolement(id) {
        const observations = prompt('Motif du rejet :') || '';
        try {
            await api(`${API}/enrolements/${id}/rejeter/`, {
                method: 'POST',
                body: JSON.stringify({ observations }),
            });
            toast('Enrôlement rejeté.', 'warning');
            await chargerEnrolements(pageEnrolements);
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    function initEnrolement() {
        bindModalClosers();
        bindFileDropPreview('bioPhoto');
        chargerSelectEleves().catch((e) => toast(e.message, 'error'));
        chargerEnrolements().catch((e) => toast(e.message, 'error'));

        document.getElementById('btnNouvelEnrolement')?.addEventListener('click', () => openModal('modalEnrolement'));
        document.getElementById('btnFiltrerEnrolement')?.addEventListener('click', () => chargerEnrolements(1));
        document.getElementById('filtreStatut')?.addEventListener('change', () => chargerEnrolements(1));

        document.getElementById('formEnrolement')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = Object.fromEntries(new FormData(e.target).entries());
            payload.eleve = Number(payload.eleve);
            try {
                await api(`${API}/enrolements/`, { method: 'POST', body: JSON.stringify(payload) });
                toast('Enrôlement créé.', 'success');
                e.target.reset();
                closeModal('modalEnrolement');
                await chargerEnrolements(1);
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('formBiometrie')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const fd = new FormData(form);
            if (!fd.get('photo') || !fd.get('photo').size) {
                toast('La photo est obligatoire.', 'warning');
                return;
            }
            try {
                await api(`${API}/biometrie/`, { method: 'POST', body: fd, headers: {} });
                toast('Biométrie enregistrée.', 'success');
                form.reset();
                closeModal('modalBiometrie');
            } catch (err) {
                toast(err.message, 'error');
            }
        });
    }

    /* ---------- Cartes ---------- */
    let pageCartes = 1;

    async function chargerCartes(page = 1) {
        pageCartes = page;
        const q = document.getElementById('searchCartes')?.value || '';
        let url = `${API}/cartes/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        const data = await api(url);
        const rows = data.results || data;
        const tbody = document.querySelector('#tableCartes tbody');
        setCount('countCartes', data.count ?? rows.length);

        tbody.innerHTML = rows.length ? rows.map((c) => `
            <tr>
                <td data-label="Carte">
                    <div class="entity-cell">
                        <div class="entity-avatar card">${escapeHtml(initials(c.numero_carte))}</div>
                        <div class="entity-meta">
                            <strong>${escapeHtml(c.numero_carte)}</strong>
                            <span>Matricule ${escapeHtml(c.eleve_matricule || '—')}</span>
                        </div>
                    </div>
                </td>
                <td data-label="Élève">
                    <div class="entity-meta">
                        <strong>${escapeHtml(c.eleve_nom || '—')}</strong>
                        <span>${escapeHtml(c.eleve_matricule || '')}</span>
                    </div>
                </td>
                <td data-label="École">${escapeHtml(c.ecole_nom || '—')}</td>
                <td data-label="Émission">${escapeHtml((c.date_emission || '').slice(0, 10))}</td>
                <td data-label="Expiration">${escapeHtml(c.date_expiration)}</td>
                <td data-label="Statut"><span class="badge badge-info">${escapeHtml(c.statut_display || c.statut)}</span></td>
                <td data-label="Actions">
                    <div class="actions-inline">
                        <a class="btn btn-primary btn-sm" href="${API}/cartes/${c.id}/pdf/" target="_blank">PDF</a>
                        ${c.qr_code_url ? `<a class="btn btn-secondary btn-sm" href="${c.qr_code_url}" target="_blank">QR</a>` : ''}
                    </div>
                </td>
            </tr>
        `).join('') : emptyRow(7, 'Aucune carte produite', 'Les cartes apparaissent après validation d\'un enrôlement.');

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationCartes', pageCartes, totalPages, chargerCartes);
    }

    function initCartes() {
        chargerCartes().catch((e) => toast(e.message, 'error'));
        document.getElementById('btnSearchCartes')?.addEventListener('click', () => chargerCartes(1));
        document.getElementById('searchCartes')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerCartes(1);
        });
    }

    /* ---------- Rapports ---------- */
    let rapportsBound = false;

    async function initRapports() {
        try {
            const stats = await api(`${API}/stats/`);
            setText('rEleves', stats.nb_eleves);
            setText('rEcoles', stats.nb_ecoles);
            setText('rCartes', stats.nb_cartes);
            setText('rValides', stats.enrolements_valides);
            const labels = (stats.par_province || []).map((p) => p.nom);
            const values = (stats.par_province || []).map((p) => p.nb_ecoles);
            drawBarChart('chartRapports', labels, values);
        } catch (err) {
            toast(err.message, 'error');
        }
        if (!rapportsBound) {
            document.getElementById('btnRefreshStats')?.addEventListener('click', () => initRapports());
            rapportsBound = true;
        }
    }

    /* ---------- Menu mobile / tablette ---------- */
    function initNavigationMobile() {
        const toggle = document.getElementById('menuToggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        if (!toggle || !sidebar) return;

        const isMobileNav = () => window.matchMedia('(max-width: 1024px)').matches;

        const setOpen = (open) => {
            const shouldOpen = open && isMobileNav();
            sidebar.classList.toggle('open', shouldOpen);
            overlay?.classList.toggle('visible', shouldOpen);
            document.body.classList.toggle('nav-open', shouldOpen);
            if (overlay) overlay.setAttribute('aria-hidden', shouldOpen ? 'false' : 'true');
            toggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
            toggle.setAttribute('aria-label', shouldOpen ? 'Fermer le menu' : 'Ouvrir le menu');
        };

        toggle.addEventListener('click', () => setOpen(!sidebar.classList.contains('open')));
        overlay?.addEventListener('click', () => setOpen(false));

        sidebar.querySelectorAll('.nav-link').forEach((link) => {
            link.addEventListener('click', () => {
                if (isMobileNav()) setOpen(false);
            });
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') setOpen(false);
        });

        let resizeTimer;
        window.addEventListener('resize', () => {
            if (!isMobileNav()) setOpen(false);
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                if (document.getElementById('chartProvinces')) chargerDashboard();
                if (document.getElementById('chartRapports')) initRapports();
            }, 180);
        });
    }

    document.addEventListener('DOMContentLoaded', initNavigationMobile);

    /* ---------- Paramètres (référentiels) ---------- */
    let pageProvinces = 1;
    let pageAntennes = 1;
    let cacheProvinces = [];
    let cacheAntennes = [];

    function activerOnglet(tabName) {
        document.querySelectorAll('.tab-btn').forEach((btn) => {
            const active = btn.dataset.tab === tabName;
            btn.classList.toggle('active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        document.querySelectorAll('.tab-panel').forEach((panel) => {
            const active = panel.id === `tab-${tabName}`;
            panel.hidden = !active;
            panel.classList.toggle('active', active);
        });
    }

    async function chargerOptionsProvinces() {
        const data = await api(`${API}/provinces/?page_size=200`);
        const list = data.results || data;
        const filtre = document.getElementById('filtreProvinceAntenne');
        const formSel = document.getElementById('selectProvinceAntenneForm');
        const options = list.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');
        if (filtre) {
            const current = filtre.value;
            filtre.innerHTML = `<option value="">Toutes les provinces</option>${options}`;
            filtre.value = current;
        }
        if (formSel) formSel.innerHTML = options;
        return list;
    }

    async function chargerProvinces(page = 1) {
        pageProvinces = page;
        const q = document.getElementById('searchProvinces')?.value || '';
        let url = `${API}/provinces/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        const data = await api(url);
        const rows = data.results || data;
        cacheProvinces = rows;
        setCount('countProvinces', data.count ?? rows.length);
        const tbody = document.querySelector('#tableProvinces tbody');
        tbody.innerHTML = rows.length ? rows.map((p) => `
            <tr>
                <td data-label="Nom"><strong>${escapeHtml(p.nom)}</strong></td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(p.code)}</span></td>
                <td data-label="Création">${escapeHtml((p.date_creation || '').slice(0, 10))}</td>
                <td data-label="Actions">
                    <div class="actions-inline">
                        <button type="button" class="btn btn-ghost btn-sm" data-edit-province="${p.id}">Modifier</button>
                        <button type="button" class="btn btn-danger btn-sm" data-del-province="${p.id}">Supprimer</button>
                    </div>
                </td>
            </tr>
        `).join('') : emptyRow(4, 'Aucune province', 'Ajoutez une province de référence.');

        tbody.querySelectorAll('[data-edit-province]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const p = cacheProvinces.find((x) => String(x.id) === String(btn.dataset.editProvince));
                if (!p) return;
                document.getElementById('titreModalProvince').textContent = 'Modifier la province';
                document.getElementById('provinceId').value = p.id;
                const form = document.getElementById('formProvince');
                form.nom.value = p.nom;
                form.code.value = p.code;
                openModal('modalProvince');
            });
        });
        tbody.querySelectorAll('[data-del-province]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                if (!confirm('Supprimer cette province ?')) return;
                try {
                    await api(`${API}/provinces/${btn.dataset.delProvince}/`, { method: 'DELETE' });
                    toast('Province supprimée.', 'success');
                    await chargerProvinces(pageProvinces);
                    await chargerOptionsProvinces();
                } catch (err) {
                    toast(err.message, 'error');
                }
            });
        });

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationProvinces', pageProvinces, totalPages, chargerProvinces);
    }

    async function chargerAntennes(page = 1) {
        pageAntennes = page;
        const q = document.getElementById('searchAntennes')?.value || '';
        const province = document.getElementById('filtreProvinceAntenne')?.value || '';
        let url = `${API}/antennes/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        if (province) url += `&province=${encodeURIComponent(province)}`;
        const data = await api(url);
        const rows = data.results || data;
        cacheAntennes = rows;
        setCount('countAntennes', data.count ?? rows.length);
        const tbody = document.querySelector('#tableAntennes tbody');
        tbody.innerHTML = rows.length ? rows.map((a) => `
            <tr>
                <td data-label="Antenne">
                    <div class="entity-meta">
                        <strong>${escapeHtml(a.nom)}</strong>
                        <span>${escapeHtml(a.adresse || 'Adresse non renseignée')}</span>
                    </div>
                </td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(a.code)}</span></td>
                <td data-label="Province">${escapeHtml(a.province_nom || '')}</td>
                <td data-label="Contact">${escapeHtml(a.telephone || '—')}</td>
                <td data-label="Actions">
                    <div class="actions-inline">
                        <button type="button" class="btn btn-ghost btn-sm" data-edit-antenne="${a.id}">Modifier</button>
                        <button type="button" class="btn btn-danger btn-sm" data-del-antenne="${a.id}">Supprimer</button>
                    </div>
                </td>
            </tr>
        `).join('') : emptyRow(5, 'Aucune antenne', 'Créez une antenne rattachée à une province.');

        tbody.querySelectorAll('[data-edit-antenne]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const a = cacheAntennes.find((x) => String(x.id) === String(btn.dataset.editAntenne));
                if (!a) return;
                document.getElementById('titreModalAntenne').textContent = 'Modifier l\'antenne';
                document.getElementById('antenneId').value = a.id;
                const form = document.getElementById('formAntenne');
                form.nom.value = a.nom;
                form.code.value = a.code;
                form.province.value = a.province;
                form.adresse.value = a.adresse || '';
                form.telephone.value = a.telephone || '';
                openModal('modalAntenne');
            });
        });
        tbody.querySelectorAll('[data-del-antenne]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                if (!confirm('Supprimer cette antenne ?')) return;
                try {
                    await api(`${API}/antennes/${btn.dataset.delAntenne}/`, { method: 'DELETE' });
                    toast('Antenne supprimée.', 'success');
                    await chargerAntennes(pageAntennes);
                } catch (err) {
                    toast(err.message, 'error');
                }
            });
        });

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationAntennes', pageAntennes, totalPages, chargerAntennes);
    }

    function initParametres() {
        bindModalClosers();

        document.querySelectorAll('.tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                activerOnglet(btn.dataset.tab);
                if (btn.dataset.tab === 'antennes') {
                    chargerAntennes(1).catch((e) => toast(e.message, 'error'));
                }
            });
        });

        chargerOptionsProvinces()
            .then(() => chargerProvinces(1))
            .catch((e) => toast(e.message, 'error'));

        document.getElementById('btnSearchProvinces')?.addEventListener('click', () => chargerProvinces(1));
        document.getElementById('searchProvinces')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerProvinces(1);
        });
        document.getElementById('btnNouvelleProvince')?.addEventListener('click', () => {
            document.getElementById('titreModalProvince').textContent = 'Nouvelle province';
            document.getElementById('formProvince').reset();
            document.getElementById('provinceId').value = '';
            openModal('modalProvince');
        });

        document.getElementById('formProvince')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            const id = document.getElementById('provinceId').value;
            const payload = {
                nom: form.nom.value.trim(),
                code: form.code.value.trim().toUpperCase(),
            };
            try {
                if (id) {
                    await api(`${API}/provinces/${id}/`, { method: 'PUT', body: JSON.stringify(payload) });
                    toast('Province mise à jour.', 'success');
                } else {
                    await api(`${API}/provinces/`, { method: 'POST', body: JSON.stringify(payload) });
                    toast('Province créée.', 'success');
                }
                closeModal('modalProvince');
                form.reset();
                await chargerOptionsProvinces();
                await chargerProvinces(1);
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('btnSearchAntennes')?.addEventListener('click', () => chargerAntennes(1));
        document.getElementById('searchAntennes')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerAntennes(1);
        });
        document.getElementById('filtreProvinceAntenne')?.addEventListener('change', () => chargerAntennes(1));
        document.getElementById('btnNouvelleAntenne')?.addEventListener('click', async () => {
            await chargerOptionsProvinces();
            document.getElementById('titreModalAntenne').textContent = 'Nouvelle antenne';
            document.getElementById('formAntenne').reset();
            document.getElementById('antenneId').value = '';
            openModal('modalAntenne');
        });

        document.getElementById('formAntenne')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            const id = document.getElementById('antenneId').value;
            const payload = {
                nom: form.nom.value.trim(),
                code: form.code.value.trim().toUpperCase(),
                province: Number(form.province.value),
                adresse: form.adresse.value.trim(),
                telephone: form.telephone.value.trim(),
            };
            try {
                if (id) {
                    await api(`${API}/antennes/${id}/`, { method: 'PUT', body: JSON.stringify(payload) });
                    toast('Antenne mise à jour.', 'success');
                } else {
                    await api(`${API}/antennes/`, { method: 'POST', body: JSON.stringify(payload) });
                    toast('Antenne créée.', 'success');
                }
                closeModal('modalAntenne');
                form.reset();
                await chargerAntennes(1);
            } catch (err) {
                toast(err.message, 'error');
            }
        });
    }

    return {
        chargerDashboard,
        initEcoles,
        initEleves,
        initEleveDetail,
        initEnrolement,
        initCartes,
        initRapports,
        initParametres,
        toast,
        api,
    };
})();
