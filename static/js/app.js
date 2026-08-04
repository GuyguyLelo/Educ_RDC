/**
 * Educ_RDC — Frontend JavaScript (Fetch API)
 * Gestion formulaires, validation, notifications, pagination
 */
const EducRDC = (() => {
    'use strict';

    const API = '/api';

    function getCookie(name) {
        const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
        return match ? decodeURIComponent(match[1]) : null;
    }

    function getCsrfToken() {
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input?.value) return input.value;
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta?.content) return meta.content;
        return getCookie('csrftoken');
    }

    function formatApiError(data) {
        if (!data) return 'Une erreur est survenue.';
        if (typeof data === 'string') return data.slice(0, 300);
        if (data.detail) return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        if (data.error) return data.error;
        if (typeof data === 'object') {
            const parts = Object.entries(data).map(([field, msgs]) => {
                const text = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
                return field === 'non_field_errors' ? text : `${field} : ${text}`;
            });
            if (parts.length) return parts.join(' · ');
        }
        return 'Une erreur est survenue.';
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
        const headers = { ...(options.headers || {}) };
        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = headers['Content-Type'] || 'application/json';
        }
        const csrf = getCsrfToken();
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
            throw new Error(formatApiError(data));
        }
        return data;
    }

    function openModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        if (modal.parentElement !== document.body) {
            document.body.appendChild(modal);
        }
        modal.hidden = false;
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
    let cacheEcolesPA = [];
    let cacheEcolesPE = [];
    let cacheEcolesAntennes = [];

    async function chargerHierarchieEcole() {
        const [pas, pes, antennes] = await Promise.all([
            api(`${API}/provinces-administratives/?page_size=200`),
            api(`${API}/provinces-educationnelles/?page_size=200`),
            api(`${API}/antennes/?page_size=200`),
        ]);
        cacheEcolesPA = pas.results || pas;
        cacheEcolesPE = pes.results || pes;
        cacheEcolesAntennes = antennes.results || antennes;

        // Filtres liste
        const fPA = document.getElementById('filtreEcolePA');
        const fPE = document.getElementById('filtreEcolePE');
        const fAnt = document.getElementById('filtreEcoleAntenne');
        if (fPA) {
            const cur = fPA.value;
            fPA.innerHTML = `<option value="">Toutes les prov. admin.</option>` +
                cacheEcolesPA.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');
            if (cur) fPA.value = cur;
        }
        syncFiltresEcolesPE();
        syncFiltresEcolesAntenne();

        // Formulaire modal création
        const selPA = document.getElementById('selectProvinceAdmin');
        const selPE = document.getElementById('selectProvinceEduc');
        const selA = document.getElementById('selectAntenne');
        if (!selPA || !selPE || !selA) return;

        selPA.innerHTML = cacheEcolesPA.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');

        const fillPE = () => {
            const paId = selPA.value;
            const filtered = cacheEcolesPE.filter((p) => String(p.province_administrative) === String(paId));
            selPE.innerHTML = filtered.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');
            fillAntennes();
        };
        const fillAntennes = () => {
            const peId = selPE.value;
            const filtered = cacheEcolesAntennes.filter((a) => String(a.province_educationnelle) === String(peId));
            selA.innerHTML = filtered.map((a) => `<option value="${a.id}">${escapeHtml(a.nom)}</option>`).join('');
        };

        selPA.addEventListener('change', fillPE);
        selPE.addEventListener('change', fillAntennes);
        fillPE();
    }

    function syncFiltresEcolesPE() {
        const fPA = document.getElementById('filtreEcolePA');
        const fPE = document.getElementById('filtreEcolePE');
        if (!fPE) return;
        const paId = fPA?.value || '';
        const cur = fPE.value;
        const list = paId
            ? cacheEcolesPE.filter((p) => String(p.province_administrative) === String(paId))
            : cacheEcolesPE;
        fPE.innerHTML = `<option value="">Toutes les prov. éduc.</option>` +
            list.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');
        if (cur && list.some((p) => String(p.id) === String(cur))) fPE.value = cur;
        syncFiltresEcolesAntenne();
    }

    function syncFiltresEcolesAntenne() {
        const fPE = document.getElementById('filtreEcolePE');
        const fPA = document.getElementById('filtreEcolePA');
        const fAnt = document.getElementById('filtreEcoleAntenne');
        if (!fAnt) return;
        const peId = fPE?.value || '';
        const paId = fPA?.value || '';
        const cur = fAnt.value;
        let list = cacheEcolesAntennes;
        if (peId) {
            list = list.filter((a) => String(a.province_educationnelle) === String(peId));
        } else if (paId) {
            const peIds = new Set(
                cacheEcolesPE
                    .filter((p) => String(p.province_administrative) === String(paId))
                    .map((p) => String(p.id)),
            );
            list = list.filter((a) => peIds.has(String(a.province_educationnelle)));
        }
        fAnt.innerHTML = `<option value="">Toutes les antennes</option>` +
            list.map((a) => `<option value="${a.id}">${escapeHtml(a.nom)}</option>`).join('');
        if (cur && list.some((a) => String(a.id) === String(cur))) fAnt.value = cur;
    }

    async function chargerEcoles(page = 1) {
        pageEcoles = page;
        const q = document.getElementById('searchEcoles')?.value || '';
        const pa = document.getElementById('filtreEcolePA')?.value || '';
        const pe = document.getElementById('filtreEcolePE')?.value || '';
        const antenne = document.getElementById('filtreEcoleAntenne')?.value || '';
        const typeEcole = document.getElementById('filtreEcoleType')?.value || '';
        const niveau = document.getElementById('filtreEcoleNiveau')?.value || '';

        let url = `${API}/ecoles/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        if (pa) url += `&province_administrative=${encodeURIComponent(pa)}`;
        if (pe) url += `&province_educationnelle=${encodeURIComponent(pe)}`;
        if (antenne) url += `&antenne=${encodeURIComponent(antenne)}`;
        if (typeEcole) url += `&type_ecole=${encodeURIComponent(typeEcole)}`;
        if (niveau) url += `&niveau=${encodeURIComponent(niveau)}`;

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
                            <strong title="${escapeHtml(e.nom)}">
                                <a class="entity-link" href="/ecoles/${e.id}/">${escapeHtml(e.nom)}</a>
                            </strong>
                            <span>${escapeHtml(e.directeur || 'Directeur non renseigné')}</span>
                        </div>
                    </div>
                </td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(e.code)}</span></td>
                <td data-label="N° agrément">${escapeHtml(e.numero_agrement || '—')}</td>
                <td data-label="Type"><span class="badge badge-neutral">${escapeHtml(e.type_display || e.type_ecole)}</span></td>
                <td data-label="Niveau">${escapeHtml(e.niveau_display || e.niveau)}</td>
                <td data-label="Localisation">
                    <div class="entity-meta">
                        <strong>${escapeHtml(e.province_educationnelle_nom || e.province_nom || '—')}</strong>
                        <span>${escapeHtml(e.province_administrative_nom || '')} · ${escapeHtml(e.antenne_nom || '')}</span>
                    </div>
                </td>
                <td data-label="MAT">${e.effectif_mat ?? 0}</td>
                <td data-label="PRIM">${e.effectif_prim ?? 0}</td>
                <td data-label="SEC">${e.effectif_sec ?? 0}</td>
                <td data-label="Effectifs"><strong>${e.effectifs ?? ((e.effectif_mat || 0) + (e.effectif_prim || 0) + (e.effectif_sec || 0))}</strong></td>
                <td data-label="Statut"><span class="badge ${e.active ? 'badge-success' : 'badge-danger'}">${e.active ? 'Active' : 'Inactive'}</span></td>
            </tr>
        `).join('') : emptyRow(11, 'Aucune école trouvée', 'Modifiez les filtres ou créez une nouvelle école.');

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationEcoles', pageEcoles, totalPages, chargerEcoles);
        return count;
    }

    function initEcoles() {
        bindModalClosers();
        chargerHierarchieEcole()
            .then(() => chargerEcoles())
            .catch((e) => toast(e.message, 'error'));

        document.getElementById('btnNouvelleEcole')?.addEventListener('click', () => openModal('modalEcole'));
        document.getElementById('btnSearchEcoles')?.addEventListener('click', () => chargerEcoles(1));
        document.getElementById('searchEcoles')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerEcoles(1);
        });

        document.getElementById('filtreEcolePA')?.addEventListener('change', () => {
            syncFiltresEcolesPE();
            chargerEcoles(1).catch((e) => toast(e.message, 'error'));
        });
        document.getElementById('filtreEcolePE')?.addEventListener('change', () => {
            syncFiltresEcolesAntenne();
            chargerEcoles(1).catch((e) => toast(e.message, 'error'));
        });
        ['filtreEcoleAntenne', 'filtreEcoleType', 'filtreEcoleNiveau'].forEach((id) => {
            document.getElementById(id)?.addEventListener('change', () => {
                chargerEcoles(1).catch((e) => toast(e.message, 'error'));
            });
        });
        document.getElementById('btnResetFiltresEcoles')?.addEventListener('click', () => {
            const search = document.getElementById('searchEcoles');
            if (search) search.value = '';
            ['filtreEcolePA', 'filtreEcolePE', 'filtreEcoleAntenne', 'filtreEcoleType', 'filtreEcoleNiveau']
                .forEach((id) => {
                    const el = document.getElementById(id);
                    if (el) el.value = '';
                });
            syncFiltresEcolesPE();
            chargerEcoles(1).catch((e) => toast(e.message, 'error'));
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
            payload.province_educationnelle = Number(payload.province_educationnelle);
            payload.antenne = Number(payload.antenne);
            try {
                await api(`${API}/ecoles/`, { method: 'POST', body: JSON.stringify(payload) });
                toast('École créée avec succès.', 'success');
                form.reset();
                closeModal('modalEcole');
                await chargerHierarchieEcole();
                await chargerEcoles(1);
            } catch (err) {
                toast(err.message, 'error');
            }
        });
    }

    /* ---------- Détail école ---------- */
    async function chargerEcolePersonnels(ecoleId) {
        const data = await api(`${API}/personnels/?ecole=${ecoleId}&page_size=100`);
        const rows = data.results || data;
        setCount('countEcolePersonnels', data.count ?? rows.length);
        const chip = document.getElementById('detailEcolePersonnels');
        if (chip) {
            const n = data.count ?? rows.length;
            chip.textContent = `${n} personnel${n > 1 ? 's' : ''}`;
        }
        const tbody = document.querySelector('#tableEcolePersonnels tbody');
        if (!tbody) return;
        tbody.innerHTML = rows.length ? rows.map((p) => `
            <tr>
                <td data-label="Nom"><strong>${escapeHtml(p.nom_complet)}</strong></td>
                <td data-label="Matricule"><span class="code-chip">${escapeHtml(p.matricule || '—')}</span></td>
                <td data-label="Fonction"><span class="badge badge-neutral">${escapeHtml(p.fonction_display || p.fonction)}</span></td>
                <td data-label="Sexe">${escapeHtml(p.sexe_display || p.sexe || '—')}</td>
                <td data-label="Téléphone">${escapeHtml(p.telephone || '—')}</td>
                <td data-label="Statut"><span class="badge ${p.actif ? 'badge-success' : 'badge-danger'}">${p.actif ? 'Actif' : 'Inactif'}</span></td>
                <td data-label="Actions">
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-personnel="${p.id}">Modifier</button>
                </td>
            </tr>
        `).join('') : emptyRow(7, 'Aucun personnel identifié', 'Cliquez sur « Identifier » pour enregistrer un agent.');

        tbody.querySelectorAll('[data-edit-personnel]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                try {
                    const p = await api(`${API}/personnels/${btn.dataset.editPersonnel}/`);
                    ouvrirModalPersonnel(p);
                } catch (err) {
                    toast(err.message, 'error');
                }
            });
        });
    }

    function ouvrirModalPersonnel(personnel = null) {
        const form = document.getElementById('formPersonnel');
        if (!form) return;
        form.reset();
        document.getElementById('personnelId').value = personnel?.id || '';
        document.getElementById('titreModalPersonnel').textContent = personnel
            ? 'Modifier le personnel'
            : 'Identifier un agent';
        if (personnel) {
            form.nom.value = personnel.nom || '';
            form.postnom.value = personnel.postnom || '';
            form.prenom.value = personnel.prenom || '';
            form.sexe.value = personnel.sexe || 'M';
            form.matricule.value = personnel.matricule || '';
            form.fonction.value = personnel.fonction || 'enseignant';
            form.telephone.value = personnel.telephone || '';
            form.email.value = personnel.email || '';
            form.date_naissance.value = personnel.date_naissance || '';
            form.date_prise_service.value = personnel.date_prise_service || '';
        }
        openModal('modalPersonnel');
    }

    async function chargerEcoleDetail() {
        const root = document.getElementById('ecoleDetail');
        if (!root) return;
        const id = root.dataset.ecoleId;
        const ecole = await api(`${API}/ecoles/${id}/`);

        document.getElementById('detailEcoleCode').textContent = ecole.code || '—';
        document.getElementById('detailEcoleNom').textContent = ecole.nom || '—';
        document.getElementById('detailEcoleSousTitre').textContent =
            `${ecole.antenne_nom || '—'} · ${ecole.province_educationnelle_nom || ecole.province_nom || '—'}`;
        document.getElementById('detailEcoleType').textContent = ecole.type_display || ecole.type_ecole || '—';
        document.getElementById('detailEcoleNiveau').textContent = ecole.niveau_display || ecole.niveau || '—';

        const statut = document.getElementById('detailEcoleStatut');
        statut.textContent = ecole.active ? 'Active' : 'Inactive';
        statut.className = `badge ${ecole.active ? 'badge-success' : 'badge-danger'}`;

        const eff = ecole.effectifs ?? 0;
        document.getElementById('detailEcoleEffectifs').textContent = `${eff} élève${eff > 1 ? 's' : ''}`;

        const avatar = document.getElementById('detailEcoleAvatar');
        if (avatar) avatar.textContent = initials(ecole.nom);

        fillDetailList('blocEcoleIdentite', [
            ['Nom', ecole.nom],
            ['Code école', ecole.code],
            ["N° d'agrément", ecole.numero_agrement],
            ['Type', ecole.type_display || ecole.type_ecole],
            ['Niveau', ecole.niveau_display || ecole.niveau],
            ['Directeur', ecole.directeur],
        ]);

        fillDetailList('blocEcoleLocalisation', [
            ['Province administrative', ecole.province_administrative_nom],
            ['Province éducationnelle', ecole.province_educationnelle_nom || ecole.province_nom],
            ['Antenne', ecole.antenne_nom],
            ['Adresse', ecole.adresse],
        ]);

        fillDetailList('blocEcoleContact', [
            ['Téléphone', ecole.telephone],
            ['Email', ecole.email],
            ['Créée le', (ecole.date_creation || '').slice(0, 10)],
        ]);

        fillDetailList('blocEcoleEffectifs', [
            ['MAT', String(ecole.effectif_mat ?? 0)],
            ['PRIM', String(ecole.effectif_prim ?? 0)],
            ['SEC', String(ecole.effectif_sec ?? 0)],
            ['EFFECTIFS', String(eff)],
            ['Élèves enregistrés', String(ecole.nombre_eleves ?? 0)],
            ['Personnels identifiés', String(ecole.nombre_personnels ?? 0)],
        ]);

        await chargerEcolePersonnels(id);

        const elevesData = await api(`${API}/eleves/?ecole=${id}&page_size=50`);
        const eleves = elevesData.results || elevesData;
        setCount('countEcoleEleves', elevesData.count ?? eleves.length);
        const tbody = document.querySelector('#tableEcoleEleves tbody');
        tbody.innerHTML = eleves.length ? eleves.map((el) => `
            <tr>
                <td data-label="Élève">
                    <a class="entity-link" href="/eleves/${el.id}/">${escapeHtml(el.nom_complet || `${el.nom} ${el.postnom || ''} ${el.prenom || ''}`.trim())}</a>
                </td>
                <td data-label="Matricule"><span class="code-chip">${escapeHtml(el.matricule || '—')}</span></td>
                <td data-label="Sexe">${escapeHtml(el.sexe_display || el.sexe || '—')}</td>
                <td data-label="Classe">${escapeHtml(el.classe || '—')}</td>
                <td data-label="Statut"><span class="badge ${el.actif ? 'badge-success' : 'badge-danger'}">${el.actif ? 'Actif' : 'Inactif'}</span></td>
            </tr>
        `).join('') : emptyRow(5, 'Aucun élève enregistré', 'Les élèves inscrits dans cette école apparaîtront ici.');
    }

    function initEcoleDetail() {
        bindModalClosers();
        const root = document.getElementById('ecoleDetail');
        const ecoleId = root?.dataset.ecoleId;

        const goPersonnel = () => {
            document.getElementById('sectionPersonnelEcole')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        };
        document.getElementById('btnPersonnelEcole')?.addEventListener('click', goPersonnel);
        document.getElementById('btnNouveauPersonnel')?.addEventListener('click', () => ouvrirModalPersonnel());
        document.getElementById('btnNouveauPersonnel2')?.addEventListener('click', () => ouvrirModalPersonnel());

        document.getElementById('formPersonnel')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            const id = document.getElementById('personnelId').value;
            const payload = Object.fromEntries(new FormData(form).entries());
            payload.ecole = Number(ecoleId);
            payload.actif = true;
            if (!payload.date_naissance) delete payload.date_naissance;
            if (!payload.date_prise_service) delete payload.date_prise_service;
            try {
                if (id) {
                    await api(`${API}/personnels/${id}/`, { method: 'PUT', body: JSON.stringify(payload) });
                    toast('Personnel mis à jour.', 'success');
                } else {
                    await api(`${API}/personnels/`, { method: 'POST', body: JSON.stringify(payload) });
                    toast('Personnel identifié avec succès.', 'success');
                }
                closeModal('modalPersonnel');
                form.reset();
                await chargerEcolePersonnels(ecoleId);
                const ecole = await api(`${API}/ecoles/${ecoleId}/`);
                fillDetailList('blocEcoleEffectifs', [
                    ['MAT', String(ecole.effectif_mat ?? 0)],
                    ['PRIM', String(ecole.effectif_prim ?? 0)],
                    ['SEC', String(ecole.effectif_sec ?? 0)],
                    ['EFFECTIFS', String(ecole.effectifs ?? 0)],
                    ['Élèves enregistrés', String(ecole.nombre_eleves ?? 0)],
                    ['Personnels identifiés', String(ecole.nombre_personnels ?? 0)],
                ]);
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        chargerEcoleDetail().catch((err) => toast(err.message, 'error'));
    }

    /* ---------- Élèves ---------- */
    let pageEleves = 1;

    async function chargerSelectEcoles(selectId, { placeholder = '' } = {}) {
        const data = await api(`${API}/ecoles/?page_size=200`);
        const list = data.results || data;
        const sel = document.getElementById(selectId);
        if (!sel) return;
        const opts = list.map((e) => `<option value="${e.id}">${escapeHtml(e.nom)} (${escapeHtml(e.code)})</option>`).join('');
        sel.innerHTML = placeholder
            ? `<option value="">${escapeHtml(placeholder)}</option>${opts}`
            : opts;
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
        bindFileDropPreview('importElevesFile');
        chargerSelectEcoles('selectEcoleEleve').catch((e) => toast(e.message, 'error'));
        chargerSelectEcoles('selectEcoleImportEleves', {
            placeholder: '— Utiliser le code école du fichier —',
        }).catch((e) => toast(e.message, 'error'));
        chargerEleves().catch((e) => toast(e.message, 'error'));

        document.getElementById('btnNouvelEleve')?.addEventListener('click', () => openModal('modalEleve'));
        document.getElementById('btnImporterEleves')?.addEventListener('click', () => {
            const result = document.getElementById('importElevesResult');
            if (result) {
                result.hidden = true;
                result.textContent = '';
            }
            openModal('modalImportEleves');
        });
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

        document.getElementById('formImportEleves')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const fileInput = document.getElementById('importElevesFile');
            const fichier = fileInput?.files?.[0];
            if (!fichier) {
                toast('Choisissez un fichier CSV à importer.', 'warning');
                return;
            }
            const fd = new FormData();
            fd.append('fichier', fichier);
            const ecole = form.ecole?.value;
            if (ecole) fd.append('ecole', ecole);
            fd.append(
                'update_existing',
                document.getElementById('importUpdateExisting')?.checked ? '1' : '0',
            );

            const btn = document.getElementById('btnSubmitImportEleves');
            const resultEl = document.getElementById('importElevesResult');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Import en cours…';
            }
            try {
                const data = await api(`${API}/eleves/import/`, { method: 'POST', body: fd, headers: {} });
                toast(data.detail || 'Import terminé.', data.errors_count ? 'warning' : 'success');
                if (resultEl) {
                    let html = escapeHtml(data.detail || '');
                    if (data.errors?.length) {
                        html += '<ul style="margin:0.5rem 0 0;padding-left:1.1rem">';
                        data.errors.slice(0, 8).forEach((err) => {
                            html += `<li>Ligne ${escapeHtml(err.ligne)} : ${escapeHtml(err.message)}</li>`;
                        });
                        if (data.errors_count > 8) {
                            html += `<li>… et ${data.errors_count - 8} autre(s)</li>`;
                        }
                        html += '</ul>';
                    }
                    resultEl.innerHTML = html;
                    resultEl.hidden = false;
                }
                await chargerEleves(1);
                if (!data.errors_count) {
                    form.reset();
                    const title = form.querySelector('.file-drop-title');
                    if (title) title.textContent = 'Déposer un CSV ou cliquer pour parcourir';
                    closeModal('modalImportEleves');
                }
            } catch (err) {
                toast(err.message, 'error');
                if (resultEl) {
                    resultEl.textContent = err.message;
                    resultEl.hidden = false;
                }
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = "Lancer l'import";
                }
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
            ['Province admin.', eleve.province_administrative_nom],
            ['Province éduc.', eleve.province_nom],
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


    /* ---------- Paramètres (hiérarchie référentielle) ---------- */
    let pagePA = 1;
    let pagePE = 1;
    let pageAntennes = 1;
    let cachePA = [];
    let cachePE = [];
    let cacheAntennes = [];
    let orgData = { pas: [], pes: [], antennes: [] };

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

    function matchOrgQuery(item, q) {
        if (!q) return true;
        const hay = `${item.nom || ''} ${item.code || ''} ${item.adresse || ''}`.toLowerCase();
        return hay.includes(q);
    }

    function renderOrganigramme(filter = '') {
        const root = document.getElementById('organigrammeTree');
        if (!root) return;
        const q = filter.trim().toLowerCase();
        const { pas, pes, antennes } = orgData;

        const setText = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = String(value);
        };
        setText('orgCountPA', pas.length);
        setText('orgCountPE', pes.length);
        setText('orgCountAnt', antennes.length);
        setCount('countOrganigramme', pas.length + pes.length + antennes.length, 'structure');

        const pesByPA = new Map();
        pes.forEach((pe) => {
            const key = String(pe.province_administrative);
            if (!pesByPA.has(key)) pesByPA.set(key, []);
            pesByPA.get(key).push(pe);
        });
        const antsByPE = new Map();
        antennes.forEach((a) => {
            const key = String(a.province_educationnelle);
            if (!antsByPE.has(key)) antsByPE.set(key, []);
            antsByPE.get(key).push(a);
        });

        const nodes = [];
        pas.forEach((pa) => {
            const peList = (pesByPA.get(String(pa.id)) || []).slice().sort((a, b) => a.nom.localeCompare(b.nom, 'fr'));
            const peNodes = [];
            peList.forEach((pe) => {
                const antList = (antsByPE.get(String(pe.id)) || []).slice().sort((a, b) => a.nom.localeCompare(b.nom, 'fr'));
                const antMatch = antList.filter((a) => matchOrgQuery(a, q));
                const peMatch = matchOrgQuery(pe, q);
                if (q && !peMatch && !antMatch.length) return;
                const shownAnts = q && !peMatch ? antMatch : antList;
                peNodes.push({ pe, ants: shownAnts, forceOpen: Boolean(q && antMatch.length) });
            });
            const paMatch = matchOrgQuery(pa, q);
            if (q && !paMatch && !peNodes.length) return;
            nodes.push({ pa, pes: peNodes, forceOpen: Boolean(q && (peNodes.length || paMatch)) });
        });

        if (!nodes.length) {
            root.innerHTML = `<p class="empty-state">${q ? 'Aucune structure ne correspond au filtre.' : 'Aucune structure enregistrée. Créez une province administrative pour commencer.'}</p>`;
            return;
        }

        root.innerHTML = nodes.map(({ pa, pes: peNodes, forceOpen }) => {
            const totalAnt = peNodes.reduce((n, x) => n + x.ants.length, 0);
            const peHtml = peNodes.length ? `
                <ul class="org-children">
                    ${peNodes.map(({ pe, ants, forceOpen: peOpen }) => {
                        const antHtml = ants.length ? `
                            <ul class="org-children">
                                ${ants.map((a) => `
                                    <li class="org-node org-node-ant">
                                        <div class="org-row">
                                            <button type="button" class="org-toggle" disabled aria-hidden="true">·</button>
                                            <div class="org-card">
                                                <div class="org-card-main">
                                                    <strong title="${escapeHtml(a.nom)}">${escapeHtml(a.nom)}</strong>
                                                    <span>${escapeHtml(a.adresse || 'Adresse non renseignée')}</span>
                                                </div>
                                                <div class="org-card-meta">
                                                    <span class="org-chip org-chip-ant">Antenne</span>
                                                    <span class="code-chip">${escapeHtml(a.code)}</span>
                                                    <span class="badge ${a.actif !== false ? 'badge-success' : 'badge-danger'}">${a.actif !== false ? 'Actif' : 'Inactif'}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </li>`).join('')}
                            </ul>` : '';
                        return `
                            <li class="org-node org-node-pe${peOpen ? '' : ''}" data-org-node>
                                <div class="org-row">
                                    <button type="button" class="org-toggle" data-org-toggle aria-expanded="true" ${ants.length ? '' : 'disabled'}>${ants.length ? '−' : '·'}</button>
                                    <div class="org-card">
                                        <div class="org-card-main">
                                            <strong title="${escapeHtml(pe.nom)}">${escapeHtml(pe.nom)}</strong>
                                            <span>${ants.length} antenne${ants.length > 1 ? 's' : ''}</span>
                                        </div>
                                        <div class="org-card-meta">
                                            <span class="org-chip org-chip-pe">PE</span>
                                            <span class="code-chip">${escapeHtml(pe.code)}</span>
                                            <span class="badge ${pe.actif !== false ? 'badge-success' : 'badge-danger'}">${pe.actif !== false ? 'Actif' : 'Inactif'}</span>
                                        </div>
                                    </div>
                                </div>
                                ${antHtml}
                            </li>`;
                    }).join('')}
                </ul>` : '';

            return `
                <div class="org-node org-node-pa${forceOpen ? '' : ''}" data-org-node>
                    <div class="org-row">
                        <button type="button" class="org-toggle" data-org-toggle aria-expanded="true" ${peNodes.length ? '' : 'disabled'}>${peNodes.length ? '−' : '·'}</button>
                        <div class="org-card">
                            <div class="org-card-main">
                                <strong title="${escapeHtml(pa.nom)}">${escapeHtml(pa.nom)}</strong>
                                <span>${peNodes.length} PE · ${totalAnt} antenne${totalAnt > 1 ? 's' : ''}</span>
                            </div>
                            <div class="org-card-meta">
                                <span class="org-chip org-chip-pa">PA</span>
                                <span class="code-chip">${escapeHtml(pa.code)}</span>
                                <span class="badge ${pa.actif !== false ? 'badge-success' : 'badge-danger'}">${pa.actif !== false ? 'Actif' : 'Inactif'}</span>
                            </div>
                        </div>
                    </div>
                    ${peHtml}
                </div>`;
        }).join('');

        root.querySelectorAll('[data-org-toggle]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const node = btn.closest('[data-org-node]');
                if (!node || btn.disabled) return;
                const collapsed = node.classList.toggle('is-collapsed');
                btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
                btn.textContent = collapsed ? '+' : '−';
            });
        });
    }

    async function chargerOrganigramme() {
        const root = document.getElementById('organigrammeTree');
        if (root) root.innerHTML = '<p class="empty-state">Chargement de l\'organigramme…</p>';
        const [pas, pes, antennes] = await Promise.all([
            api(`${API}/provinces-administratives/?page_size=500`),
            api(`${API}/provinces-educationnelles/?page_size=500`),
            api(`${API}/antennes/?page_size=500`),
        ]);
        orgData = {
            pas: (pas.results || pas).slice().sort((a, b) => a.nom.localeCompare(b.nom, 'fr')),
            pes: pes.results || pes,
            antennes: antennes.results || antennes,
        };
        renderOrganigramme(document.getElementById('searchOrganigramme')?.value || '');
    }

    function setOrgExpanded(expanded) {
        document.querySelectorAll('#organigrammeTree [data-org-node]').forEach((node) => {
            const btn = node.querySelector(':scope > .org-row > [data-org-toggle]');
            if (!btn || btn.disabled) return;
            node.classList.toggle('is-collapsed', !expanded);
            btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
            btn.textContent = expanded ? '−' : '+';
        });
    }

    async function chargerOptionsHierarchie() {
        const [pas, pes] = await Promise.all([
            api(`${API}/provinces-administratives/?page_size=200`),
            api(`${API}/provinces-educationnelles/?page_size=200`),
        ]);
        const paList = pas.results || pas;
        const peList = pes.results || pes;
        const filtrePA = document.getElementById('filtrePAforPE');
        const selectPA = document.getElementById('selectPAforPE');
        const filtrePE = document.getElementById('filtrePEforAntenne');
        const selectPE = document.getElementById('selectPEforAntenne');
        const paOpts = paList.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');
        const peOpts = peList.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');
        if (filtrePA) { const cur = filtrePA.value; filtrePA.innerHTML = `<option value="">Toutes les provinces admin.</option>${paOpts}`; filtrePA.value = cur; }
        if (selectPA) selectPA.innerHTML = paOpts;
        if (filtrePE) { const cur = filtrePE.value; filtrePE.innerHTML = `<option value="">Toutes les provinces éduc.</option>${peOpts}`; filtrePE.value = cur; }
        if (selectPE) selectPE.innerHTML = peOpts;
        return { paList, peList };
    }

    async function chargerPA(page = 1) {
        pagePA = page;
        const q = document.getElementById('searchPA')?.value || '';
        let url = `${API}/provinces-administratives/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        const data = await api(url);
        const rows = data.results || data;
        cachePA = rows;
        setCount('countPA', data.count ?? rows.length);
        const tbody = document.querySelector('#tablePA tbody');
        tbody.innerHTML = rows.length ? rows.map((p) => `
            <tr>
                <td data-label="Nom"><strong>${escapeHtml(p.nom)}</strong></td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(p.code)}</span></td>
                <td data-label="Statut"><span class="badge ${p.actif !== false ? 'badge-success' : 'badge-danger'}">${p.actif !== false ? 'Actif' : 'Inactif'}</span></td>
                <td data-label="Actions"><div class="actions-inline">
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-pa="${p.id}">Modifier</button>
                    <button type="button" class="btn btn-danger btn-sm" data-del-pa="${p.id}">Supprimer</button>
                </div></td>
            </tr>`).join('') : emptyRow(4, 'Aucune province administrative', 'Ajoutez le niveau 1 de la hiérarchie.');
        tbody.querySelectorAll('[data-edit-pa]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const p = cachePA.find((x) => String(x.id) === String(btn.dataset.editPa));
                if (!p) return;
                document.getElementById('titreModalPA').textContent = 'Modifier la province administrative';
                document.getElementById('paId').value = p.id;
                const form = document.getElementById('formPA');
                form.nom.value = p.nom; form.code.value = p.code;
                openModal('modalPA');
            });
        });
        tbody.querySelectorAll('[data-del-pa]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                if (!confirm('Supprimer cette province administrative ?')) return;
                try {
                    await api(`${API}/provinces-administratives/${btn.dataset.delPa}/`, { method: 'DELETE' });
                    toast('Province administrative supprimée.', 'success');
                    await chargerPA(pagePA);
                    await chargerOptionsHierarchie();
                    await chargerOrganigramme().catch(() => {});
                } catch (err) { toast(err.message, 'error'); }
            });
        });
        renderPagination('paginationPA', pagePA, data.count ? Math.ceil(data.count / 20) : 1, chargerPA);
    }

    async function chargerPE(page = 1) {
        pagePE = page;
        const q = document.getElementById('searchPE')?.value || '';
        const pa = document.getElementById('filtrePAforPE')?.value || '';
        let url = `${API}/provinces-educationnelles/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        if (pa) url += `&province_administrative=${encodeURIComponent(pa)}`;
        const data = await api(url);
        const rows = data.results || data;
        cachePE = rows;
        setCount('countPE', data.count ?? rows.length);
        const tbody = document.querySelector('#tablePE tbody');
        tbody.innerHTML = rows.length ? rows.map((p) => `
            <tr>
                <td data-label="Nom"><strong>${escapeHtml(p.nom)}</strong></td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(p.code)}</span></td>
                <td data-label="Province admin.">${escapeHtml(p.province_administrative_nom || '')}</td>
                <td data-label="Statut"><span class="badge ${p.actif !== false ? 'badge-success' : 'badge-danger'}">${p.actif !== false ? 'Actif' : 'Inactif'}</span></td>
                <td data-label="Actions"><div class="actions-inline">
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-pe="${p.id}">Modifier</button>
                    <button type="button" class="btn btn-danger btn-sm" data-del-pe="${p.id}">Supprimer</button>
                </div></td>
            </tr>`).join('') : emptyRow(5, 'Aucune province éducationnelle', 'Créez une PE rattachée à une province administrative.');
        tbody.querySelectorAll('[data-edit-pe]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const p = cachePE.find((x) => String(x.id) === String(btn.dataset.editPe));
                if (!p) return;
                document.getElementById('titreModalPE').textContent = 'Modifier la province éducationnelle';
                document.getElementById('peId').value = p.id;
                const form = document.getElementById('formPE');
                form.nom.value = p.nom; form.code.value = p.code;
                form.province_administrative.value = p.province_administrative;
                openModal('modalPE');
            });
        });
        tbody.querySelectorAll('[data-del-pe]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                if (!confirm('Supprimer cette province éducationnelle ?')) return;
                try {
                    await api(`${API}/provinces-educationnelles/${btn.dataset.delPe}/`, { method: 'DELETE' });
                    toast('Province éducationnelle supprimée.', 'success');
                    await chargerPE(pagePE);
                    await chargerOptionsHierarchie();
                    await chargerOrganigramme().catch(() => {});
                } catch (err) { toast(err.message, 'error'); }
            });
        });
        renderPagination('paginationPE', pagePE, data.count ? Math.ceil(data.count / 20) : 1, chargerPE);
    }

    async function chargerAntennes(page = 1) {
        pageAntennes = page;
        const q = document.getElementById('searchAntennes')?.value || '';
        const pe = document.getElementById('filtrePEforAntenne')?.value || '';
        let url = `${API}/antennes/?page=${page}`;
        if (q) url += `&search=${encodeURIComponent(q)}`;
        if (pe) url += `&province_educationnelle=${encodeURIComponent(pe)}`;
        const data = await api(url);
        const rows = data.results || data;
        cacheAntennes = rows;
        setCount('countAntennes', data.count ?? rows.length);
        const tbody = document.querySelector('#tableAntennes tbody');
        tbody.innerHTML = rows.length ? rows.map((a) => `
            <tr>
                <td data-label="Antenne"><div class="entity-meta"><strong>${escapeHtml(a.nom)}</strong><span>${escapeHtml(a.adresse || 'Adresse non renseignée')}</span></div></td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(a.code)}</span></td>
                <td data-label="Province éduc.">${escapeHtml(a.province_educationnelle_nom || '')}</td>
                <td data-label="Province admin.">${escapeHtml(a.province_administrative_nom || '')}</td>
                <td data-label="Actions"><div class="actions-inline">
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-antenne="${a.id}">Modifier</button>
                    <button type="button" class="btn btn-danger btn-sm" data-del-antenne="${a.id}">Supprimer</button>
                </div></td>
            </tr>`).join('') : emptyRow(5, 'Aucune antenne', 'Créez une antenne rattachée à une province éducationnelle.');
        tbody.querySelectorAll('[data-edit-antenne]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const a = cacheAntennes.find((x) => String(x.id) === String(btn.dataset.editAntenne));
                if (!a) return;
                document.getElementById('titreModalAntenne').textContent = "Modifier l'antenne";
                document.getElementById('antenneId').value = a.id;
                const form = document.getElementById('formAntenne');
                form.nom.value = a.nom; form.code.value = a.code;
                form.province_educationnelle.value = a.province_educationnelle;
                form.adresse.value = a.adresse || ''; form.telephone.value = a.telephone || '';
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
                    await chargerOrganigramme().catch(() => {});
                } catch (err) { toast(err.message, 'error'); }
            });
        });
        renderPagination('paginationAntennes', pageAntennes, data.count ? Math.ceil(data.count / 20) : 1, chargerAntennes);
    }

    function initParametres() {
        bindModalClosers();
        document.querySelectorAll('.tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                activerOnglet(btn.dataset.tab);
                if (btn.dataset.tab === 'organigramme') chargerOrganigramme().catch((e) => toast(e.message, 'error'));
                if (btn.dataset.tab === 'pa') chargerPA(1).catch((e) => toast(e.message, 'error'));
                if (btn.dataset.tab === 'pe') chargerPE(1).catch((e) => toast(e.message, 'error'));
                if (btn.dataset.tab === 'antennes') chargerAntennes(1).catch((e) => toast(e.message, 'error'));
            });
        });
        chargerOrganigramme().catch((e) => toast(e.message, 'error'));
        chargerOptionsHierarchie().catch((e) => toast(e.message, 'error'));

        const applyOrgFilter = () => renderOrganigramme(document.getElementById('searchOrganigramme')?.value || '');
        document.getElementById('btnSearchOrganigramme')?.addEventListener('click', applyOrgFilter);
        document.getElementById('searchOrganigramme')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') applyOrgFilter();
        });
        document.getElementById('searchOrganigramme')?.addEventListener('input', () => {
            if (!(document.getElementById('searchOrganigramme')?.value || '').trim()) applyOrgFilter();
        });
        document.getElementById('btnOrgExpand')?.addEventListener('click', () => setOrgExpanded(true));
        document.getElementById('btnOrgCollapse')?.addEventListener('click', () => setOrgExpanded(false));
        document.getElementById('btnOrgRefresh')?.addEventListener('click', () => {
            chargerOrganigramme().catch((e) => toast(e.message, 'error'));
        });

        document.getElementById('btnSearchPA')?.addEventListener('click', () => chargerPA(1));
        document.getElementById('searchPA')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') chargerPA(1); });
        document.getElementById('btnNouveauPA')?.addEventListener('click', () => {
            document.getElementById('titreModalPA').textContent = 'Nouvelle province administrative';
            document.getElementById('formPA').reset();
            document.getElementById('paId').value = '';
            openModal('modalPA');
        });
        document.getElementById('formPA')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const nomInput = form.elements.namedItem('nom');
            const codeInput = form.elements.namedItem('code');
            const nom = (nomInput?.value || '').trim();
            const code = (codeInput?.value || '').trim().toUpperCase();
            if (!nom || !code) {
                toast('Veuillez renseigner le nom et le code.', 'warning');
                form.reportValidity();
                return;
            }
            const id = document.getElementById('paId').value;
            const payload = { nom, code, actif: true };
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                if (id) {
                    await api(`${API}/provinces-administratives/${id}/`, { method: 'PUT', body: JSON.stringify(payload) });
                } else {
                    await api(`${API}/provinces-administratives/`, { method: 'POST', body: JSON.stringify(payload) });
                }
                toast(id ? 'Province administrative mise à jour.' : 'Province administrative créée.', 'success');
                closeModal('modalPA');
                form.reset();
                document.getElementById('paId').value = '';
                await chargerPA(1);
                await chargerOptionsHierarchie().catch(() => {});
                await chargerOrganigramme().catch(() => {});
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        document.getElementById('btnSearchPE')?.addEventListener('click', () => chargerPE(1));
        document.getElementById('filtrePAforPE')?.addEventListener('change', () => chargerPE(1));
        document.getElementById('btnNouveauPE')?.addEventListener('click', async () => {
            await chargerOptionsHierarchie();
            document.getElementById('titreModalPE').textContent = 'Nouvelle province éducationnelle';
            document.getElementById('formPE').reset(); document.getElementById('peId').value = '';
            openModal('modalPE');
        });
        document.getElementById('formPE')?.addEventListener('submit', async (e) => {
            e.preventDefault(); const form = e.target;
            if (!form.checkValidity()) { form.reportValidity(); return; }
            const id = document.getElementById('peId').value;
            const payload = { nom: form.nom.value.trim(), code: form.code.value.trim().toUpperCase(), province_administrative: Number(form.province_administrative.value) };
            try {
                if (id) await api(`${API}/provinces-educationnelles/${id}/`, { method: 'PUT', body: JSON.stringify(payload) });
                else await api(`${API}/provinces-educationnelles/`, { method: 'POST', body: JSON.stringify(payload) });
                toast(id ? 'Province éducationnelle mise à jour.' : 'Province éducationnelle créée.', 'success');
                closeModal('modalPE'); form.reset();
                await chargerOptionsHierarchie();
                await chargerPE(1);
                await chargerOrganigramme().catch(() => {});
            } catch (err) { toast(err.message, 'error'); }
        });

        document.getElementById('btnSearchAntennes')?.addEventListener('click', () => chargerAntennes(1));
        document.getElementById('filtrePEforAntenne')?.addEventListener('change', () => chargerAntennes(1));
        document.getElementById('btnNouvelleAntenne')?.addEventListener('click', async () => {
            await chargerOptionsHierarchie();
            document.getElementById('titreModalAntenne').textContent = 'Nouvelle antenne';
            document.getElementById('formAntenne').reset(); document.getElementById('antenneId').value = '';
            openModal('modalAntenne');
        });
        document.getElementById('formAntenne')?.addEventListener('submit', async (e) => {
            e.preventDefault(); const form = e.target;
            if (!form.checkValidity()) { form.reportValidity(); return; }
            const id = document.getElementById('antenneId').value;
            const payload = { nom: form.nom.value.trim(), code: form.code.value.trim().toUpperCase(), province_educationnelle: Number(form.province_educationnelle.value), adresse: form.adresse.value.trim(), telephone: form.telephone.value.trim() };
            try {
                if (id) await api(`${API}/antennes/${id}/`, { method: 'PUT', body: JSON.stringify(payload) });
                else await api(`${API}/antennes/`, { method: 'POST', body: JSON.stringify(payload) });
                toast(id ? 'Antenne mise à jour.' : 'Antenne créée.', 'success');
                closeModal('modalAntenne'); form.reset();
                await chargerAntennes(1);
                await chargerOrganigramme().catch(() => {});
            } catch (err) { toast(err.message, 'error'); }
        });
    }

    return {
        chargerDashboard,
        initEcoles,
        initEleves,
        initEleveDetail,
        initEcoleDetail,
        initEnrolement,
        initCartes,
        initRapports,
        initParametres,
        toast,
        api,
    };
})();
