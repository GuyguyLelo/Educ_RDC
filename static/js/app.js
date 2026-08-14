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
            const labels = {
                libelle: 'Libellé',
                date_debut: 'Date de début',
                date_fin: 'Date de fin',
                regime: 'Régime',
                non_field_errors: '',
            };
            const parts = Object.entries(data).map(([field, msgs]) => {
                const text = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
                if (field === 'non_field_errors') return text;
                // Message déjà autonome (ex. unicité) : pas de préfixe technique
                if (/existe déjà|obligatoire|postérieure/i.test(text)) return text;
                const label = labels[field] || field;
                return label ? `${label} : ${text}` : text;
            });
            if (parts.length) return parts.join(' · ');
        }
        return 'Une erreur est survenue.';
    }

    /** Affiche une date ISO au format documentaire : JJ-MM-AAAA. */
    function formatDateFr(value) {
        if (value == null || value === '') return '';
        const raw = String(value).trim();
        const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return `${m[3]}-${m[2]}-${m[1]}`;
        const d = new Date(raw);
        if (!Number.isNaN(d.getTime())) {
            const jj = String(d.getDate()).padStart(2, '0');
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const aaaa = String(d.getFullYear());
            return `${jj}-${mm}-${aaaa}`;
        }
        return raw;
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
        const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
        if (isFormData) {
            // Laisser le navigateur définir le boundary multipart
            delete headers['Content-Type'];
            delete headers['content-type'];
        } else {
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
        // Empêche le même clic (qui ouvre le modal) de le refermer via le backdrop
        modal.dataset.justOpened = '1';
        modal.hidden = false;
        // Pendant ce court délai, ignorer les clics backdrop
        window.setTimeout(() => {
            delete modal.dataset.justOpened;
        }, 200);
    }

    function closeModal(id) {
        const modal = document.getElementById(id);
        if (modal) {
            delete modal.dataset.justOpened;
            modal.hidden = true;
        }
    }

    function bindModalClosers() {
        document.querySelectorAll('.modal').forEach((modal) => {
            if (modal.dataset.closeBound === '1') return;
            modal.dataset.closeBound = '1';
            modal.querySelectorAll('[data-close]').forEach((btn) => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    delete modal.dataset.justOpened;
                    modal.hidden = true;
                });
            });
            modal.addEventListener('click', (e) => {
                if (modal.dataset.justOpened) return;
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

    function ico(name) {
        return `<svg class="btn-ico" aria-hidden="true" focusable="false"><use href="#i-${name}" xlink:href="#i-${name}"></use></svg>`;
    }

    function btnLabel(iconName, text) {
        return `${ico(iconName)}${escapeHtml(text)}`;
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

    function fileMatchesAccept(file, accept) {
        const rules = (accept || '').trim();
        if (!rules || rules === '*/*') return true;
        return rules.split(',').some((rule) => {
            const r = rule.trim();
            if (!r) return false;
            if (r === 'image/*') return file.type.startsWith('image/');
            if (r.endsWith('/*')) return file.type.startsWith(r.replace('/*', '/'));
            if (r.startsWith('.')) return file.name.toLowerCase().endsWith(r.toLowerCase());
            return file.type === r;
        });
    }

    function bindFileDropPreview(inputId) {
        const input = document.getElementById(inputId);
        if (!input || input.dataset.dropBound === '1') return;
        const drop = input.closest('.file-drop');
        if (!drop) return;
        input.dataset.dropBound = '1';
        const title = drop.querySelector('.file-drop-title');
        const sub = drop.querySelector('.file-drop-sub');
        const defaultTitle = title?.textContent || 'Déposer un fichier ou cliquer pour parcourir';
        const allowMultiple = input.hasAttribute('multiple');
        const acceptsImages = !input.accept || input.accept.includes('image');
        let objectUrl = null;

        let preview = drop.querySelector('.file-drop-preview');
        if (!preview && acceptsImages) {
            preview = document.createElement('div');
            preview.className = 'file-drop-preview';
            preview.hidden = true;
            preview.innerHTML = '<img alt="Aperçu">';
            drop.insertBefore(preview, title || input.nextSibling);
        }
        const previewImg = preview?.querySelector('img');

        const clearPreview = () => {
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }
            if (preview) preview.hidden = true;
            if (previewImg) previewImg.removeAttribute('src');
            drop.classList.remove('has-preview');
        };

        const showFileName = () => {
            const files = input.files ? Array.from(input.files) : [];
            if (title) {
                if (!files.length) {
                    title.textContent = defaultTitle;
                } else if (files.length === 1) {
                    title.textContent = files[0].name;
                } else {
                    title.textContent = `${files.length} fichiers sélectionnés`;
                }
            }
            drop.classList.toggle('has-file', files.length > 0);

            clearPreview();
            const file = files[0];
            if (file && file.type.startsWith('image/') && previewImg) {
                objectUrl = URL.createObjectURL(file);
                previewImg.src = objectUrl;
                preview.hidden = false;
                drop.classList.add('has-preview');
                if (sub) sub.textContent = 'Cliquez pour changer la photo';
            } else if (sub) {
                sub.textContent = sub.dataset.defaultSub || sub.textContent;
            }
        };

        input.addEventListener('change', showFileName);
        input._resetFileDropPreview = () => {
            clearPreview();
            if (title) title.textContent = defaultTitle;
            drop.classList.remove('has-file', 'is-dragover');
            if (sub && sub.dataset.defaultSub) sub.textContent = sub.dataset.defaultSub;
        };
        if (sub && !sub.dataset.defaultSub) {
            sub.dataset.defaultSub = sub.textContent || '';
        }

        ['dragenter', 'dragover'].forEach((evt) => {
            drop.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                drop.classList.add('is-dragover');
            });
        });
        ['dragleave', 'drop'].forEach((evt) => {
            drop.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (evt === 'dragleave') drop.classList.remove('is-dragover');
            });
        });
        drop.addEventListener('drop', (e) => {
            drop.classList.remove('is-dragover');
            const dropped = e.dataTransfer?.files;
            if (!dropped || !dropped.length) return;
            const accept = (input.accept || '').trim();
            const matched = Array.from(dropped).filter((f) => fileMatchesAccept(f, accept));
            if (!matched.length) {
                toast('Type de fichier non accepté.', 'warning');
                return;
            }
            const dt = new DataTransfer();
            const chosen = allowMultiple ? matched : [matched[0]];
            chosen.forEach((f) => dt.items.add(f));
            input.files = dt.files;
            showFileName();
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

    function drawPieChart(canvasId, series) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const sized = sizeChartCanvas(canvas);
        const ctx = sized.ctx;
        const w = sized.width;
        const h = sized.height;
        ctx.clearRect(0, 0, w, h);

        const rows = (series || []).filter((s) => Number(s.valeur) > 0);
        const total = rows.reduce((acc, s) => acc + Number(s.valeur || 0), 0);
        if (!total) {
            ctx.fillStyle = '#6b7a8d';
            ctx.font = '500 15px Figtree, sans-serif';
            ctx.fillText('Aucune donnée disponible', Math.max(24, w / 2 - 90), h / 2);
            return;
        }

        const cx = w * 0.38;
        const cy = h / 2;
        const radius = Math.min(w, h) * 0.32;
        const inner = radius * 0.55;
        let start = -Math.PI / 2;
        const colors = ['#007FFF', '#CE1126', '#FCD116', '#0a7a32', '#6b7a8d'];

        rows.forEach((s, i) => {
            const val = Number(s.valeur || 0);
            const slice = (val / total) * Math.PI * 2;
            const color = s.couleur || colors[i % colors.length];
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, radius, start, start + slice);
            ctx.closePath();
            ctx.fillStyle = color;
            ctx.fill();
            start += slice;
        });

        // Trou central (donut)
        ctx.beginPath();
        ctx.arc(cx, cy, inner, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();

        ctx.fillStyle = '#142033';
        ctx.font = '700 22px Sora, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(String(total), cx, cy - 2);
        ctx.fillStyle = '#6b7a8d';
        ctx.font = '500 11px Figtree, sans-serif';
        ctx.fillText('Total', cx, cy + 16);
        ctx.textAlign = 'left';

        // Légende
        let ly = Math.max(28, cy - rows.length * 18);
        rows.forEach((s, i) => {
            const val = Number(s.valeur || 0);
            const pct = Math.round((val / total) * 100);
            const color = s.couleur || colors[i % colors.length];
            const lx = w * 0.68;
            ctx.fillStyle = color;
            ctx.fillRect(lx, ly, 12, 12);
            ctx.fillStyle = '#142033';
            ctx.font = '600 13px Figtree, sans-serif';
            ctx.fillText(`${s.nom || '—'}`, lx + 20, ly + 11);
            ctx.fillStyle = '#6b7a8d';
            ctx.font = '500 12px Figtree, sans-serif';
            ctx.fillText(`${val} (${pct} %)`, lx + 20, ly + 28);
            ly += 44;
        });
    }

    /* ---------- Dashboard ---------- */
    function renderDashCards(cards) {
        const grid = document.getElementById('statsGrid');
        if (!grid || !Array.isArray(cards)) return;
        cards.forEach((card, i) => {
            let el = grid.querySelector(`[data-card-slot="${i}"]`);
            if (!el) {
                el = document.createElement('article');
                el.className = 'stat-card';
                el.dataset.cardSlot = String(i);
                el.innerHTML = '<span class="stat-label"></span><strong class="stat-value"></strong><div class="stat-hint"></div>';
                grid.appendChild(el);
            }
            el.classList.toggle('accent', !!card.accent);
            el.hidden = false;
            const label = el.querySelector('.stat-label');
            const value = el.querySelector('.stat-value');
            const hint = el.querySelector('.stat-hint');
            if (label) label.textContent = card.label || '';
            if (value) {
                value.textContent = card.value ?? '—';
                const asText = card.text === true
                    || (typeof card.value === 'string' && Number.isNaN(Number(card.value)));
                value.classList.toggle('stat-value-text', asText);
            }
            if (hint) hint.textContent = card.hint || '';
        });
        grid.querySelectorAll('[data-card-slot]').forEach((el) => {
            const idx = Number(el.dataset.cardSlot);
            if (idx >= cards.length) el.hidden = true;
        });
    }

    function renderDashActions(actions) {
        const wrap = document.getElementById('dashActions');
        if (!wrap) return;
        if (!actions || !actions.length) {
            wrap.innerHTML = '';
            return;
        }
        wrap.innerHTML = actions.map((a) => {
            const cls = a.style === 'primary' ? 'btn btn-primary btn-sm' : 'btn btn-ghost btn-sm';
            const url = a.url || '';
            let icon = 'eye';
            if (url.includes('/eleves')) icon = 'users';
            else if (url.includes('/cartes')) icon = 'pdf';
            else if (url.includes('/ecoles')) icon = 'school';
            else if (url.includes('/rapports')) icon = 'pdf';
            else if (url.includes('/utilisateurs')) icon = 'user';
            return `<a class="${cls}" href="${escapeHtml(url || '#')}">${ico(icon)}${escapeHtml(a.label || '')}</a>`;
        }).join('');
    }

    function renderDashWorkflow(items) {
        const ol = document.getElementById('dashWorkflow');
        const panel = ol?.closest('.panel');
        if (!ol) return;
        const list = items || [];
        ol.innerHTML = list.map((t) => `<li>${escapeHtml(t)}</li>`).join('');
        if (panel) panel.hidden = list.length === 0;
    }

    let dashChargementEnCours = false;
    let cacheEffectifsEcoles = [];
    let pageEffectifsEcoles = 1;
    const PAGE_SIZE_EFFECTIFS_ECOLES = 20;

    function renderEffectifsEcolesPage(rows, page = 1) {
        cacheEffectifsEcoles = Array.isArray(rows) ? rows : cacheEffectifsEcoles;
        const tbody = document.querySelector('#tableEffectifsEcoles tbody');
        const footer = document.getElementById('footerEffectifsEcoles');
        const info = document.getElementById('infoEffectifsEcoles');
        if (!tbody) return;

        const total = cacheEffectifsEcoles.length;
        const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE_EFFECTIFS_ECOLES));
        pageEffectifsEcoles = Math.min(Math.max(1, page), totalPages);
        const start = (pageEffectifsEcoles - 1) * PAGE_SIZE_EFFECTIFS_ECOLES;
        const slice = cacheEffectifsEcoles.slice(start, start + PAGE_SIZE_EFFECTIFS_ECOLES);

        tbody.innerHTML = slice.length ? slice.map((e) => `
            <tr>
                <td data-label="École">
                    <a class="entity-link" href="/ecoles/${e.id}/">${escapeHtml(e.nom || '—')}</a>
                </td>
                <td data-label="Code"><span class="code-chip">${escapeHtml(e.code || '—')}</span></td>
                <td data-label="Élèves"><strong>${e.nb_eleves ?? 0}</strong></td>
                <td data-label="Garçons">${e.nb_garcons ?? 0}</td>
                <td data-label="Filles">${e.nb_filles ?? 0}</td>
            </tr>
        `).join('') : '';

        if (footer) footer.hidden = total === 0;
        if (info) {
            const from = total ? start + 1 : 0;
            const to = Math.min(start + PAGE_SIZE_EFFECTIFS_ECOLES, total);
            info.textContent = total
                ? `${from}–${to} sur ${total} école(s)`
                : 'Aucune école';
        }
        renderPagination(
            'paginationEffectifsEcoles',
            pageEffectifsEcoles,
            totalPages,
            (p) => renderEffectifsEcolesPage(cacheEffectifsEcoles, p),
        );
    }

    async function chargerDashboard({ fromUser = false } = {}) {
        if (dashChargementEnCours) return;
        dashChargementEnCours = true;
        const btnRefresh = document.getElementById('btnRefreshDashboard');
        if (btnRefresh) {
            btnRefresh.disabled = true;
            btnRefresh.classList.add('is-refreshing');
            btnRefresh.setAttribute('aria-busy', 'true');
        }
        try {
            const stats = await api(`${API}/stats/`);

            const subtitle = document.querySelector('.topbar-title p');
            if (subtitle && stats.scope_label) subtitle.textContent = stats.scope_label;

            const banner = document.getElementById('dashBanner');
            if (banner) {
                banner.hidden = false;
                setText('dashRoleBadge', stats.role_display || stats.role || '—');
                setText('dashScopeLabel', stats.scope_label || '—');
                const welcome = document.getElementById('dashWelcome');
                if (welcome) {
                    const who = stats.ecole_nom
                        ? `Tableau de bord — ${stats.ecole_nom}`
                        : `Tableau de bord ${stats.role_display || ''}`.trim();
                    welcome.textContent = who;
                }
            }

            if (stats.cards) {
                renderDashCards(stats.cards);
            } else {
                // Fallback ancien format
                renderDashCards([
                    { key: 'eleves', label: 'Élèves inscrits', value: stats.nb_eleves, hint: 'Population scolaire active' },
                    { key: 'ecoles', label: 'Écoles', value: stats.nb_ecoles, hint: 'Établissements identifiés' },
                    { key: 'cartes', label: 'Cartes produites', value: stats.nb_cartes, hint: 'Cartes scolaires actives', accent: true },
                    { key: 'biometries', label: 'Biométries', value: stats.biometries_validees, hint: 'Captures validées' },
                ]);
            }

            const chart = stats.chart || {};
            const barPanel = document.getElementById('panelBarChart')
                || document.getElementById('chartProvinces')?.closest('.panel');
            const isClasse = stats.scope === 'classe';
            const hideBar = isClasse || stats.scope === 'antenne' || stats.scope === 'province' || stats.scope === 'province_admin';
            if (barPanel) barPanel.hidden = hideBar;
            if (!hideBar) {
                setText('chartTitle', chart.title || 'Répartition');
                setText('chartSubtitle', chart.subtitle || '');
                const series = chart.series || (stats.par_province || []).map((p) => ({
                    nom: p.nom,
                    valeur: p.nb_eleves,
                }));
                drawBarChart(
                    'chartProvinces',
                    series.map((s) => s.nom),
                    series.map((s) => s.valeur),
                );
            }

            const renderExtraBar = (panelId, titleId, subId, canvasId, data) => {
                const panel = document.getElementById(panelId);
                if (!panel) return;
                const has = data && Array.isArray(data.series) && data.series.length;
                panel.hidden = !has;
                if (!has) return;
                setText(titleId, data.title || '');
                setText(subId, data.subtitle || '');
                drawBarChart(
                    canvasId,
                    data.series.map((s) => s.nom),
                    data.series.map((s) => s.valeur),
                );
            };
            renderExtraBar(
                'panelSecondaryChart',
                'secondaryChartTitle',
                'secondaryChartSubtitle',
                'chartSecondary',
                stats.secondary_chart,
            );
            renderExtraBar(
                'panelTertiaryChart',
                'tertiaryChartTitle',
                'tertiaryChartSubtitle',
                'chartTertiary',
                stats.tertiary_chart,
            );

            const pie = stats.pie_chart || {};
            const piePanel = document.getElementById('panelPieChart');
            const hidePie = stats.hide_pie || !(pie.series && pie.series.length);
            if (piePanel) piePanel.hidden = hidePie;
            if (!hidePie) {
                setText('pieChartTitle', pie.title || 'Répartition par sexe');
                setText('pieChartSubtitle', pie.subtitle || '');
                drawPieChart('chartSexePie', pie.series);
            }

            const panelEff = document.getElementById('panelEffectifsEcoles');
            const tbodyEff = document.querySelector('#tableEffectifsEcoles tbody');
            const rowsEff = stats.effectifs_par_ecole || [];
            const footerEff = document.getElementById('footerEffectifsEcoles');
            if (panelEff && tbodyEff) {
                const showTable = stats.scope === 'antenne' && rowsEff.length;
                panelEff.hidden = !showTable;
                if (showTable) {
                    setText(
                        'effectifsEcolesSubtitle',
                        `${rowsEff.length} établissement(s) — ${stats.nb_eleves ?? 0} élève(s) actif(s)`,
                    );
                    renderEffectifsEcolesPage(rowsEff, 1);
                } else {
                    cacheEffectifsEcoles = [];
                    pageEffectifsEcoles = 1;
                    tbodyEff.innerHTML = '';
                    if (footerEff) footerEff.hidden = true;
                    const pag = document.getElementById('paginationEffectifsEcoles');
                    if (pag) pag.innerHTML = '';
                }
            }

            const panelAnt = document.getElementById('panelEffectifsAntennes');
            const tbodyAnt = document.querySelector('#tableEffectifsAntennes tbody');
            const rowsAnt = stats.effectifs_par_antenne || [];
            if (panelAnt && tbodyAnt) {
                const showAnt = stats.scope === 'province' && rowsAnt.length;
                panelAnt.hidden = !showAnt;
                if (showAnt) {
                    setText(
                        'effectifsAntennesSubtitle',
                        `${rowsAnt.length} antenne(s) — ${stats.nb_eleves ?? 0} élève(s) actif(s)`,
                    );
                    tbodyAnt.innerHTML = rowsAnt.map((a) => `
                        <tr>
                            <td data-label="Antenne"><strong>${escapeHtml(a.nom || '—')}</strong></td>
                            <td data-label="Code"><span class="code-chip">${escapeHtml(a.code || '—')}</span></td>
                            <td data-label="Écoles">${a.nb_ecoles ?? 0}</td>
                            <td data-label="Élèves"><strong>${a.nb_eleves ?? 0}</strong></td>
                            <td data-label="Garçons">${a.nb_garcons ?? 0}</td>
                            <td data-label="Filles">${a.nb_filles ?? 0}</td>
                        </tr>
                    `).join('');
                } else {
                    tbodyAnt.innerHTML = '';
                }
            }

            const panelPE = document.getElementById('panelEffectifsPE');
            const tbodyPE = document.querySelector('#tableEffectifsPE tbody');
            const rowsPE = stats.effectifs_par_pe || [];
            if (panelPE && tbodyPE) {
                const showPE = stats.scope === 'province_admin' && rowsPE.length;
                panelPE.hidden = !showPE;
                if (showPE) {
                    setText(
                        'effectifsPESubtitle',
                        `${rowsPE.length} province(s) éduc. — ${stats.nb_eleves ?? 0} élève(s) actif(s)`,
                    );
                    tbodyPE.innerHTML = rowsPE.map((p) => `
                        <tr>
                            <td data-label="Province éduc."><strong>${escapeHtml(p.nom || '—')}</strong></td>
                            <td data-label="Code"><span class="code-chip">${escapeHtml(p.code || '—')}</span></td>
                            <td data-label="Antennes">${p.nb_antennes ?? 0}</td>
                            <td data-label="Écoles">${p.nb_ecoles ?? 0}</td>
                            <td data-label="Élèves"><strong>${p.nb_eleves ?? 0}</strong></td>
                            <td data-label="Garçons">${p.nb_garcons ?? 0}</td>
                            <td data-label="Filles">${p.nb_filles ?? 0}</td>
                        </tr>
                    `).join('');
                } else {
                    tbodyPE.innerHTML = '';
                }
            }

            renderDashActions(stats.actions || []);
            const wfPanel = document.getElementById('panelWorkflow')
                || document.getElementById('dashWorkflow')?.closest('.panel');
            if (stats.hide_workflow || stats.scope === 'ecole' || stats.scope === 'antenne' || stats.scope === 'province' || stats.scope === 'province_admin') {
                if (wfPanel) wfPanel.hidden = true;
            } else {
                if (wfPanel) wfPanel.hidden = false;
                renderDashWorkflow(stats.workflow || []);
                if (stats.scope !== 'classe') {
                    setText('workflowTitle', 'Processus métier');
                    setText('workflowSubtitle', stats.role_display || 'Selon votre rôle');
                }
            }
            if (fromUser) toast('Tableau de bord actualisé.', 'success');
        } catch (err) {
            const banner = document.getElementById('dashBanner');
            if (banner) banner.hidden = false;
            toast(err.message, 'error');
        } finally {
            dashChargementEnCours = false;
            if (btnRefresh) {
                btnRefresh.disabled = false;
                btnRefresh.classList.remove('is-refreshing');
                btnRefresh.removeAttribute('aria-busy');
            }
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

        document.getElementById('btnNouvelleEcole')?.addEventListener('click', async () => {
            resetDocsCreationEcole();
            await chargerSelectArretesEcole();
            openModal('modalEcole');
        });
        document.getElementById('selectArreteEcole')?.addEventListener('change', () => {
            const sel = document.getElementById('selectArreteEcole');
            const input = document.getElementById('inputNumeroAgrementEcole');
            if (!sel || !input) return;
            const opt = sel.options[sel.selectedIndex];
            const numero = opt?.dataset?.numero || '';
            if (sel.value && numero) input.value = numero;
        });
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

        document.getElementById('btnAjouterLigneDocEcole')?.addEventListener('click', () => ajouterLigneDocCreation());
        document.getElementById('listeDocsCreationEcole')?.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-doc-row-remove]');
            if (!btn) return;
            btn.closest('.doc-creation-row')?.remove();
        });

        document.getElementById('formEcole')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            const fdForm = new FormData(form);
            const payload = Object.fromEntries(fdForm.entries());
            // Retirer champs documents (gérés à part)
            delete payload.type_document;
            delete payload.titre;
            delete payload.date_document;
            delete payload.fichier;
            payload.province_educationnelle = Number(payload.province_educationnelle);
            payload.antenne = Number(payload.antenne);
            if (payload.arrete) payload.arrete = Number(payload.arrete);
            else payload.arrete = null;
            if (!payload.email) payload.email = '';
            if (payload.latitude === '' || payload.latitude == null) payload.latitude = null;
            else payload.latitude = Number(payload.latitude);
            if (payload.longitude === '' || payload.longitude == null) payload.longitude = null;
            else payload.longitude = Number(payload.longitude);

            const docs = collecterDocsCreationEcole();
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Enregistrement…';
            }
            try {
                const created = await api(`${API}/ecoles/`, { method: 'POST', body: JSON.stringify(payload) });
                let docsOk = 0;
                let docsErr = 0;
                if (created?.id && docs.length) {
                    for (const doc of docs) {
                        const fd = new FormData();
                        fd.append('fichier', doc.fichier, doc.fichier.name);
                        fd.append('type_document', doc.type_document);
                        if (doc.titre) fd.append('titre', doc.titre);
                        if (doc.date_document) fd.append('date_document', doc.date_document);
                        try {
                            await api(`${API}/ecoles/${created.id}/documents/`, {
                                method: 'POST',
                                body: fd,
                                headers: {},
                            });
                            docsOk += 1;
                        } catch (_) {
                            docsErr += 1;
                        }
                    }
                }
                if (docs.length && docsErr) {
                    toast(
                        `École créée. ${docsOk} document(s) déposé(s), ${docsErr} échec(s).`,
                        docsOk ? 'warning' : 'error',
                    );
                } else if (docsOk) {
                    toast(`École créée avec ${docsOk} document(s).`, 'success');
                } else {
                    toast('École créée avec succès.', 'success');
                }
                form.reset();
                resetDocsCreationEcole();
                closeModal('modalEcole');
                await chargerHierarchieEcole();
                await chargerEcoles(1);
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = `${ico('save')}Enregistrer l'école`;
                }
            }
        });
    }

    const TYPES_DOC_ECOLE = [
        { value: 'agrement', label: "Arrêté / décision d'agrément" },
        { value: 'autorisation', label: "Autorisation d'ouverture" },
        { value: 'statuts', label: "Statuts de l'établissement" },
        { value: 'plan', label: 'Plan de localisation' },
        { value: 'attestation_epsp', label: 'Attestation EPSP' },
        { value: 'autre', label: 'Autre document' },
    ];

    function optionsTypeDocEcole(selected = 'agrement') {
        return TYPES_DOC_ECOLE.map((t) =>
            `<option value="${t.value}"${t.value === selected ? ' selected' : ''}>${escapeHtml(t.label)}</option>`
        ).join('');
    }

    function ajouterLigneDocCreation(prefill = null) {
        const list = document.getElementById('listeDocsCreationEcole');
        if (!list) return;
        const row = document.createElement('div');
        row.className = 'doc-creation-row';
        row.innerHTML = `
            <div class="form-grid">
                <div class="form-group">
                    <label>Type</label>
                    <select name="type_document">${optionsTypeDocEcole(prefill?.type_document || 'agrement')}</select>
                </div>
                <div class="form-group">
                    <label>Date</label>
                    <input type="date" name="date_document" value="${escapeHtml(prefill?.date_document || '')}">
                </div>
                <div class="form-group">
                    <label>Titre / référence</label>
                    <input name="titre" placeholder="Ex: AGR/EPSP/2024/001" value="${escapeHtml(prefill?.titre || '')}">
                </div>
                <div class="form-group">
                    <label>Fichier <span class="req">*</span></label>
                    <input type="file" name="fichier" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.webp,application/pdf,image/*">
                </div>
            </div>
            <button type="button" class="btn-link danger doc-row-remove" data-doc-row-remove title="Retirer">${ico('trash')}Retirer</button>
        `;
        list.appendChild(row);
    }

    function resetDocsCreationEcole() {
        const list = document.getElementById('listeDocsCreationEcole');
        if (!list) return;
        list.innerHTML = '';
        ajouterLigneDocCreation();
    }

    async function chargerSelectArretesEcole(selectedId = '', selectId = 'selectArreteEcole') {
        const sel = document.getElementById(selectId);
        if (!sel) return [];
        try {
            const data = await api(`${API}/arretes/?actif=1&page_size=200`);
            const rows = Array.isArray(data) ? data : (data.results || []);
            const cur = selectedId || sel.value || '';
            sel.innerHTML = '<option value="">— Aucun / saisie libre —</option>' + rows.map((a) =>
                `<option value="${a.id}" data-numero="${escapeHtml(a.numero || '')}">${escapeHtml(a.numero)} — ${escapeHtml(a.objet || '')}</option>`
            ).join('');
            // Inclure l'arrêté actuel même s'il est inactif
            if (cur && ![...sel.options].some((o) => o.value === String(cur))) {
                // laisser ; rechargé via option injectée par l'appelant si besoin
            }
            if (cur) sel.value = String(cur);
            return rows;
        } catch (err) {
            console.warn('Arrêtés référentiel:', err.message);
            return [];
        }
    }

    function collecterDocsCreationEcole() {
        const list = document.getElementById('listeDocsCreationEcole');
        if (!list) return [];
        const docs = [];
        list.querySelectorAll('.doc-creation-row').forEach((row) => {
            const fichier = row.querySelector('[name="fichier"]')?.files?.[0];
            if (!fichier || !fichier.size) return;
            docs.push({
                type_document: row.querySelector('[name="type_document"]')?.value || 'agrement',
                titre: (row.querySelector('[name="titre"]')?.value || '').trim(),
                date_document: row.querySelector('[name="date_document"]')?.value || '',
                fichier,
            });
        });
        return docs;
    }

    /* ---------- Détail école ---------- */
    async function chargerSectionsEcole(ecoleId, selectEl, selectedId = '') {
        if (!selectEl) return [];
        const data = await api(`${API}/sections-scolaires/?ecole=${ecoleId}&actif=1&page_size=200`);
        const rows = data.results || data;
        selectEl.innerHTML = '<option value="">— Choisir —</option>' + rows.map((s) =>
            `<option value="${s.id}">${escapeHtml(s.nom)}</option>`
        ).join('');
        if (selectedId) selectEl.value = String(selectedId);
        return rows;
    }

    async function chargerOptionsEcole(ecoleId, sectionId, selectEl, selectedId = '') {
        if (!selectEl) return [];
        if (!sectionId) {
            selectEl.innerHTML = '<option value="">— Choisir la section —</option>';
            return [];
        }
        const data = await api(`${API}/options-scolaires/?ecole=${ecoleId}&section=${sectionId}&actif=1&page_size=200`);
        const rows = data.results || data;
        selectEl.innerHTML = '<option value="">— Choisir —</option>' + rows.map((o) =>
            `<option value="${o.id}">${escapeHtml(o.nom)}</option>`
        ).join('');
        if (selectedId) selectEl.value = String(selectedId);
        return rows;
    }

    function grouperClassesParOption(rows) {
        const sections = new Map();
        const sorted = [...rows].sort((a, b) => {
            const sa = (a.section_nom || 'Sans section').localeCompare(b.section_nom || 'Sans section', 'fr');
            if (sa !== 0) return sa;
            const oa = (a.option_nom || 'Sans option').localeCompare(b.option_nom || 'Sans option', 'fr');
            if (oa !== 0) return oa;
            return (a.nom || '').localeCompare(b.nom || '', 'fr');
        });
        for (const c of sorted) {
            const secKey = c.section || c.section_nom || '0';
            const secNom = c.section_nom || 'Sans section';
            if (!sections.has(secKey)) {
                sections.set(secKey, { key: secKey, nom: secNom, code: '', options: new Map() });
            }
            const sec = sections.get(secKey);
            const optKey = c.option || c.option_nom || '0';
            const optNom = c.option_nom || 'Sans option';
            if (!sec.options.has(optKey)) {
                sec.options.set(optKey, { key: optKey, nom: optNom, classes: [] });
            }
            sec.options.get(optKey).classes.push(c);
        }
        return [...sections.values()].map((s) => ({
            ...s,
            options: [...s.options.values()],
        }));
    }

    function initialsShort(text) {
        const parts = String(text || '').trim().split(/[\s—\-]+/).filter(Boolean);
        if (!parts.length) return '—';
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }

    function renderClassesHierarchy(container, rows, { onEdit, expandSections = false } = {}) {
        if (!container) return;
        if (!rows.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <strong>Aucune classe</strong>
                    <span>Créez une section, une option puis une classe — ou chargez le programme RDC.</span>
                </div>`;
            return;
        }
        const groups = grouperClassesParOption(rows);
        const openAttr = expandSections ? ' open' : '';
        container.innerHTML = groups.map((sec) => {
            const nbOpt = sec.options.length;
            const nbCls = sec.options.reduce((n, o) => n + o.classes.length, 0);
            const optionsHtml = sec.options.map((opt) => `
                <div class="class-option">
                    <div class="class-option-head">
                        <span class="class-option-dot" aria-hidden="true"></span>
                        <strong>${escapeHtml(opt.nom)}</strong>
                        <span class="class-option-count">${opt.classes.length} classe${opt.classes.length > 1 ? 's' : ''}</span>
                    </div>
                    <ul class="class-option-list">
                        ${opt.classes.map((c) => `
                            <li class="class-item">
                                <div class="class-item-main">
                                    <strong>${escapeHtml(c.nom)}</strong>
                                    ${c.code ? `<span class="code-chip">${escapeHtml(c.code)}</span>` : ''}
                                </div>
                                <div class="class-item-meta">
                                    <span class="class-item-eleves"><strong>${c.nb_eleves ?? 0}</strong> élève${(c.nb_eleves ?? 0) > 1 ? 's' : ''}</span>
                                    <span class="badge ${c.active ? 'badge-success' : 'badge-neutral'}">${c.active ? 'Active' : 'Inactive'}</span>
                                    <button type="button" class="btn btn-ghost btn-sm" data-edit-classe="${c.id}">${ico('edit')}Modifier</button>
                                </div>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `).join('');
            return `
                <details class="class-section"${openAttr}>
                    <summary class="class-section-head">
                        <span class="class-section-mark">${escapeHtml(initialsShort(sec.nom))}</span>
                        <span class="class-section-title">${escapeHtml(sec.nom)}</span>
                        <span class="class-section-meta">${nbOpt} option${nbOpt > 1 ? 's' : ''} · ${nbCls} classe${nbCls > 1 ? 's' : ''}</span>
                    </summary>
                    <div class="class-section-body">${optionsHtml}</div>
                </details>
            `;
        }).join('');

        container.querySelectorAll('[data-edit-classe]').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const c = rows.find((x) => String(x.id) === String(btn.dataset.editClasse));
                if (c && typeof onEdit === 'function') onEdit(c);
            });
        });
    }

    function setHierarchyExpanded(container, open) {
        container?.querySelectorAll('details.class-section').forEach((d) => {
            d.open = open;
        });
    }

    /**
     * Modal de sélection des options réellement organisées par l'école.
     * Ne charge jamais tout le catalogue EPSP d'un coup.
     */
    async function ouvrirSelecteurProgrammeRdc(ecoleId, { onDone } = {}) {
        if (!ecoleId) {
            toast('Sélectionnez d\'abord une école.', 'warning');
            return;
        }
        bindModalClosers();
        const tree = document.getElementById('progRdcTree');
        const countEl = document.getElementById('progRdcCount');
        if (!tree || !document.getElementById('modalProgrammeRdc')) {
            toast('Interface de sélection indisponible.', 'error');
            return;
        }

        const majCompte = () => {
            const n = tree.querySelectorAll('input[data-opt-code]:checked').length;
            if (countEl) countEl.textContent = n ? `${n} option(s) cochée(s)` : 'Aucune option cochée';
        };

        tree.innerHTML = '<p class="empty-state">Chargement du référentiel…</p>';
        openModal('modalProgrammeRdc');

        try {
            const eco = await api(`${API}/ecoles/${ecoleId}/?leger=1`);
            const nEco = String(eco.niveau || '').toLowerCase();
            let niveauRef = 'tous';
            if (nEco === 'creche' || nEco === 'crèche') niveauRef = 'creche';
            else if (nEco === 'maternelle') niveauRef = 'prescolaire';
            else if (nEco === 'primaire') niveauRef = 'primaire';
            else if (nEco === 'secondaire') niveauRef = 'secondaire';
            let data = await api(`${API}/ecoles/${ecoleId}/referentiel-rdc/?niveau_programme=${encodeURIComponent(niveauRef)}`);
            if (!(data.sections || []).length) {
                data = await api(`${API}/ecoles/${ecoleId}/referentiel-rdc/?niveau_programme=tous`);
                niveauRef = 'tous';
            }
            const sections = data.sections || [];
            if (!sections.length) {
                tree.innerHTML = '<div class="empty-state"><strong>Référentiel vide</strong><span>Aucune option pour ce niveau. Redémarrez le serveur Django pour charger crèche / maternelle.</span></div>';
                return;
            }
            tree.dataset.niveauRef = niveauRef;
            tree.innerHTML = sections.map((sec) => {
                const opts = (sec.options || []).map((o) => `
                    <li class="prog-rdc-option">
                        <label>
                            <input type="checkbox" data-opt-code="${escapeHtml(o.code || '')}"
                                value="${escapeHtml(o.code || '')}"
                                ${o.deja_present ? 'checked' : ''}>
                            <span>${escapeHtml(o.nom)}</span>
                            ${o.code ? `<span class="code-chip">${escapeHtml(o.code)}</span>` : ''}
                        </label>
                        <span class="prog-rdc-meta">${o.nb_classes || 0} cl.</span>
                        ${o.deja_present ? '<span class="prog-rdc-badge">déjà présente</span>' : ''}
                    </li>
                `).join('');
                return `
                    <div class="prog-rdc-section" data-sec-code="${escapeHtml(sec.code || '')}">
                        <div class="prog-rdc-section-head">
                            <label>
                                <input type="checkbox" data-sec-toggle="${escapeHtml(sec.code || '')}">
                                <span>${escapeHtml(sec.nom)}</span>
                                ${sec.code ? `<span class="code-chip">${escapeHtml(sec.code)}</span>` : ''}
                            </label>
                        </div>
                        <ul class="prog-rdc-options">${opts}</ul>
                    </div>
                `;
            }).join('');

            tree.querySelectorAll('[data-sec-toggle]').forEach((cb) => {
                cb.addEventListener('change', () => {
                    const box = cb.closest('.prog-rdc-section');
                    box?.querySelectorAll('input[data-opt-code]').forEach((o) => {
                        o.checked = cb.checked;
                    });
                    majCompte();
                });
            });
            tree.querySelectorAll('input[data-opt-code]').forEach((cb) => {
                cb.addEventListener('change', majCompte);
            });
            majCompte();
        } catch (err) {
            tree.innerHTML = `<div class="empty-state"><strong>Erreur</strong><span>${escapeHtml(err.message)}</span></div>`;
            toast(err.message, 'error');
            return;
        }

        const btnTout = document.getElementById('btnProgRdcTout');
        const btnRien = document.getElementById('btnProgRdcRien');
        const btnPres = document.getElementById('btnProgRdcPresents');
        const btnOk = document.getElementById('btnProgRdcValider');

        const setAll = (checked) => {
            tree.querySelectorAll('input[data-opt-code]').forEach((o) => { o.checked = checked; });
            tree.querySelectorAll('[data-sec-toggle]').forEach((o) => { o.checked = checked; });
            majCompte();
        };

        btnTout.onclick = () => setAll(true);
        btnRien.onclick = () => setAll(false);
        btnPres.onclick = () => {
            tree.querySelectorAll('.prog-rdc-option').forEach((li) => {
                const cb = li.querySelector('input[data-opt-code]');
                if (cb) cb.checked = !!li.querySelector('.prog-rdc-badge');
            });
            majCompte();
        };

        btnOk.onclick = async () => {
            const codes = [...tree.querySelectorAll('input[data-opt-code]:checked')]
                .map((el) => (el.value || el.getAttribute('data-opt-code') || '').trim())
                .filter(Boolean);
            if (!codes.length) {
                toast('Cochez au moins une option organisée par l\'école.', 'warning');
                return;
            }
            btnOk.disabled = true;
            try {
                const data = await api(`${API}/ecoles/${ecoleId}/affecter-structure/`, {
                    method: 'POST',
                    body: JSON.stringify({
                        niveau: tree.dataset.niveauRef || 'tous',
                        options: codes,
                    }),
                });
                toast(data.detail || 'Options affectées à l\'école.', 'success');
                closeModal('modalProgrammeRdc');
                if (typeof onDone === 'function') await onDone(data);
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                btnOk.disabled = false;
            }
        };
    }

    async function chargerEcoleClasses(ecoleId) {
        const container = document.getElementById('ecoleClassesHierarchy');
        if (!container) return;
        try {
            const data = await api(`${API}/classes/?ecole=${ecoleId}&page_size=300&ordering=nom`);
            const rows = data.results || data;
            setCount('countEcoleClasses', data.count ?? rows.length, 'classe');
            // Sur la fiche école : sections repliées pour ne pas encombrer la page
            renderClassesHierarchy(container, rows, {
                onEdit: (c) => ouvrirModalClasseEcole(c),
                expandSections: false,
            });
        } catch (err) {
            container.innerHTML = `
                <div class="empty-state">
                    <strong>Accès limité</strong>
                    <span>${escapeHtml(err.message || 'Impossible de charger les classes.')}</span>
                </div>`;
            setCount('countEcoleClasses', 0, 'classe');
        }
    }

    async function ouvrirModalClasseEcole(classe = null) {
        const form = document.getElementById('formClasseEcole');
        const titre = document.getElementById('titreModalClasseEcole');
        const root = document.getElementById('ecoleDetail');
        const ecoleId = root?.dataset?.ecoleId;
        if (!form || !titre || !ecoleId) return;
        form.reset();
        document.getElementById('classeEcoleId').value = classe?.id || '';
        document.getElementById('classeEcoleActive').checked = classe ? classe.active !== false : true;
        const btnDel = document.getElementById('btnSupprimerClasse');
        if (btnDel) btnDel.hidden = !classe?.id;
        await chargerSectionsEcole(ecoleId, document.getElementById('classeEcoleSection'), classe?.section || '');
        await chargerOptionsEcole(
            ecoleId,
            classe?.section || document.getElementById('classeEcoleSection')?.value,
            document.getElementById('classeEcoleOption'),
            classe?.option || '',
        );
        if (classe) {
            titre.textContent = 'Modifier la classe';
            form.nom.value = classe.nom || '';
            form.code.value = classe.code || '';
        } else {
            titre.textContent = 'Nouvelle classe';
        }
        openModal('modalClasseEcole');
    }

    let cacheEcoleUtilisateurs = [];

    function syncRoleUserEcoleUI() {
        const role = document.getElementById('selectRoleUserEcole')?.value || '';
        const enseignant = role === 'enseignant';
        const edition = Boolean(document.getElementById('userEcoleId')?.value);
        // Section / option / classe : uniquement pour le rôle enseignant
        ['groupeSectionUserEcole', 'groupeOptionUserEcole', 'groupeClasseUserEcole', 'groupePersonnelUserEcole'].forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            if (id === 'groupePersonnelUserEcole') {
                el.hidden = !enseignant || edition;
            } else {
                el.hidden = !enseignant;
            }
        });
        const sel = document.getElementById('selectClasseUserEcole');
        const selSec = document.getElementById('selectSectionUserEcole');
        const selOpt = document.getElementById('selectOptionUserEcole');
        const selPers = document.getElementById('selectPersonnelUserEcole');
        if (sel) {
            sel.required = enseignant;
            if (!enseignant) sel.value = '';
        }
        if (selSec) selSec.required = enseignant;
        if (selPers) {
            selPers.required = enseignant && !edition;
            if (!enseignant) selPers.value = '';
        }
        if (!enseignant) {
            if (selSec) selSec.value = '';
            if (selOpt) selOpt.value = '';
        }
    }

    async function chargerPersonnelsSansCompte(ecoleId, selectedId = '', { fonction = 'enseignant' } = {}) {
        const sel = document.getElementById('selectPersonnelUserEcole');
        if (!sel) return;
        sel.innerHTML = '<option value="">— Choisir un agent déjà identifié —</option>';
        if (!ecoleId) return;
        try {
            let url = `${API}/personnels/?ecole=${ecoleId}&sans_compte=1&actif=1&page_size=200&ordering=nom`;
            if (fonction) url += `&fonction=${encodeURIComponent(fonction)}`;
            const data = await api(url);
            const rows = data.results || data;
            sel.innerHTML = '<option value="">— Choisir un agent déjà identifié —</option>' + rows.map((p) => `
                <option value="${p.id}"
                    data-prenom="${escapeHtml(p.prenom || '')}"
                    data-nom="${escapeHtml(p.nom || '')}"
                    data-postnom="${escapeHtml(p.postnom || '')}"
                    data-email="${escapeHtml(p.email || '')}"
                    data-telephone="${escapeHtml(p.telephone || '')}"
                    data-fonction="${escapeHtml(p.fonction || '')}">
                    ${escapeHtml(p.nom_complet || `${p.nom} ${p.prenom}`)} — ${escapeHtml(p.fonction_display || p.fonction || '')}
                </option>
            `).join('');
            if (selectedId) sel.value = String(selectedId);
            if (!rows.length) {
                sel.insertAdjacentHTML(
                    'beforeend',
                    '<option value="" disabled>Aucun agent sans compte — identifiez d’abord le personnel</option>',
                );
            }
        } catch (err) {
            toast(err.message || 'Impossible de charger le personnel.', 'error');
        }
    }

    function appliquerPersonnelSurFormUserEcole() {
        const form = document.getElementById('formUserEcole');
        const sel = document.getElementById('selectPersonnelUserEcole');
        const opt = sel?.selectedOptions?.[0];
        if (!form || !opt?.value) return;
        form.first_name.value = opt.dataset.prenom || '';
        const nom = [opt.dataset.nom, opt.dataset.postnom].filter(Boolean).join(' ').trim();
        form.last_name.value = nom;
        if (opt.dataset.email) form.email.value = opt.dataset.email;
        if (opt.dataset.telephone) form.telephone.value = opt.dataset.telephone;
    }

    async function chargerClassesUserEcole(ecoleId, selectedClasseId = '') {
        const selSec = document.getElementById('selectSectionUserEcole');
        const selOpt = document.getElementById('selectOptionUserEcole');
        const selCla = document.getElementById('selectClasseUserEcole');
        if (!selCla) return;
        const sectionId = selSec?.value || '';
        const optionId = selOpt?.value || '';
        selCla.innerHTML = '<option value="">— Sélectionner —</option>';
        if (!ecoleId || !sectionId) return;
        let url = `${API}/classes/?ecole=${ecoleId}&actif=1&section=${sectionId}&page_size=200&ordering=nom`;
        if (optionId) url += `&option=${optionId}`;
        try {
            const data = await api(url);
            const rows = data.results || data;
            selCla.innerHTML = '<option value="">— Sélectionner —</option>' + rows.map((c) => {
                const parts = [c.section_nom, c.option_nom, c.nom].filter(Boolean);
                return `<option value="${c.id}" data-section="${c.section || ''}" data-option="${c.option || ''}">${escapeHtml(parts.join(' · '))}</option>`;
            }).join('');
            if (selectedClasseId) selCla.value = String(selectedClasseId);
        } catch (err) {
            toast(err.message || 'Impossible de charger les classes.', 'error');
        }
    }

    async function preparerAffectationEnseignant(ecoleId, user = null) {
        const selSec = document.getElementById('selectSectionUserEcole');
        const selOpt = document.getElementById('selectOptionUserEcole');
        await chargerSectionsEcole(ecoleId, selSec, user?.section || '');
        await chargerOptionsEcole(ecoleId, selSec?.value || user?.section || '', selOpt, user?.option || '');
        await chargerClassesUserEcole(ecoleId, user?.classe || '');
    }

    function setModePasswordUserEcole(edition) {
        const input = document.getElementById('inputPasswordUserEcole');
        const label = document.getElementById('labelPasswordUserEcole');
        const hint = document.getElementById('hintPasswordUserEcole');
        if (!input || !label || !hint) return;
        if (edition) {
            input.required = false;
            label.innerHTML = 'Nouveau mot de passe';
            hint.textContent = 'Laisser vide pour conserver le mot de passe actuel.';
        } else {
            input.required = true;
            label.innerHTML = 'Mot de passe <span class="req">*</span>';
            hint.textContent = 'Obligatoire à la création.';
        }
    }

    async function ouvrirModalUserEcole(user = null) {
        const form = document.getElementById('formUserEcole');
        if (!form) return;
        const root = document.getElementById('ecoleDetail');
        const ecoleId = root?.dataset.ecoleId;
        const ecole = root?._ecoleCache;
        form.reset();
        const titre = document.getElementById('titreModalUserEcole');
        const sub = document.getElementById('sousTitreUserEcole');
        const idEl = document.getElementById('userEcoleId');
        const btnSubmit = document.getElementById('btnSubmitUserEcole');
        if (idEl) idEl.value = user?.id || '';
        setModePasswordUserEcole(Boolean(user));
        if (titre) titre.textContent = user ? 'Modifier le compte' : 'Créer un compte école';
        if (btnSubmit) btnSubmit.innerHTML = `${ico('save')}${user ? 'Enregistrer' : 'Créer le compte'}`;
        if (sub && ecole) {
            sub.textContent = ecole.code
                ? `${ecole.nom} · ${ecole.code}`
                : (ecole.nom || 'Compte rattaché à cette école');
        }
        if (user) {
            form.username.value = user.username || '';
            form.first_name.value = user.first_name || '';
            form.last_name.value = user.last_name || '';
            form.email.value = user.email || '';
            form.telephone.value = user.telephone || '';
            form.role.value = user.role || 'enseignant';
            const actif = document.getElementById('userEcoleActif');
            if (actif) actif.checked = user.is_active !== false;
        } else {
            const actif = document.getElementById('userEcoleActif');
            if (actif) actif.checked = true;
        }
        if (!user) {
            const rolePrefer = form.dataset.rolePrefer || 'enseignant';
            form.role.value = rolePrefer;
            delete form.dataset.rolePrefer;
            // personnelAdmin conservé si création depuis une fiche non-enseignant
            if (rolePrefer === 'enseignant') delete form.dataset.personnelAdmin;
        } else {
            delete form.dataset.personnelAdmin;
            delete form.dataset.rolePrefer;
        }
        syncRoleUserEcoleUI();
        const role = document.getElementById('selectRoleUserEcole')?.value || '';
        if (ecoleId && role === 'enseignant') {
            if (!user) {
                const preselectPers = form.dataset.personnelPreselect || '';
                await chargerPersonnelsSansCompte(ecoleId, preselectPers, { fonction: 'enseignant' });
                delete form.dataset.personnelPreselect;
                if (preselectPers) appliquerPersonnelSurFormUserEcole();
            }
            await preparerAffectationEnseignant(ecoleId, user);
        }
        openModal('modalUserEcole');
    }

    async function ouvrirCompteDepuisPersonnel(personnel) {
        if (!personnel?.id) return;
        if (personnel.a_compte || personnel.utilisateur) {
            toast('Cette fiche a déjà un compte associé.', 'warning');
            return;
        }
        const estEnseignant = personnel.fonction === 'enseignant';
        const form = document.getElementById('formUserEcole');
        // Section / option / classe uniquement pour la fonction enseignant
        if (form && estEnseignant) {
            form.dataset.personnelPreselect = String(personnel.id);
            form.dataset.rolePrefer = 'enseignant';
        } else if (form) {
            form.dataset.rolePrefer = 'admin_ecole';
            form.dataset.personnelAdmin = String(personnel.id);
        }
        await ouvrirModalUserEcole(null);
        if (!estEnseignant && form) {
            form.first_name.value = personnel.prenom || '';
            form.last_name.value = [personnel.nom, personnel.postnom].filter(Boolean).join(' ').trim();
            if (personnel.email) form.email.value = personnel.email;
            if (personnel.telephone) form.telephone.value = personnel.telephone;
        }
    }

    async function chargerEcoleUtilisateurs(ecoleId) {
        const tbody = document.querySelector('#tableEcoleUtilisateurs tbody');
        if (!tbody) return;
        try {
            const data = await api(`${API}/utilisateurs/?ecole=${ecoleId}&page_size=100`);
            const rows = data.results || data;
            cacheEcoleUtilisateurs = rows;
            setCount('countEcoleUtilisateurs', data.count ?? rows.length, 'compte');
            tbody.innerHTML = rows.length ? rows.map((u) => {
                const nom = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username;
                const affectation = u.role === 'enseignant'
                    ? [u.section_nom, u.option_nom, u.classe_nom].filter(Boolean).join(' · ')
                    : '';
                const roleHtml = u.role === 'enseignant' && affectation
                    ? `<span class="badge badge-neutral">${escapeHtml(u.role_display || u.role)}</span> <span class="code-chip" title="Section · Option · Classe">${escapeHtml(affectation)}</span>`
                    : `<span class="badge badge-neutral">${escapeHtml(u.role_display || u.role)}</span>`;
                return `
                <tr>
                    <td data-label="Utilisateur"><strong>${escapeHtml(nom)}</strong></td>
                    <td data-label="Identifiant"><span class="code-chip">${escapeHtml(u.username)}</span></td>
                    <td data-label="Rôle">${roleHtml}</td>
                    <td data-label="Téléphone">${escapeHtml(u.telephone || '—')}</td>
                    <td data-label="Statut"><span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">${u.is_active ? 'Actif' : 'Inactif'}</span></td>
                    <td data-label="Actions"><div class="actions-inline">
                        <button type="button" class="btn btn-ghost btn-sm" data-edit-user-ecole="${u.id}">${ico('edit')}Modifier</button>
                    </div></td>
                </tr>`;
            }).join('') : emptyRow(6, 'Aucun compte école', 'Créez un administratif ou un enseignant pour cette école.');
            tbody.querySelectorAll('[data-edit-user-ecole]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const user = cacheEcoleUtilisateurs.find((x) => String(x.id) === String(btn.dataset.editUserEcole));
                    ouvrirModalUserEcole(user || null);
                });
            });
        } catch (err) {
            cacheEcoleUtilisateurs = [];
            tbody.innerHTML = emptyRow(6, 'Accès limité', err.message || 'Impossible de charger les comptes.');
            setCount('countEcoleUtilisateurs', 0, 'compte');
        }
    }

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
        const peutGerer = peutModifierEcole();
        tbody.innerHTML = rows.length ? rows.map((p) => {
            const avatar = p.photo_url
                ? `<div class="entity-avatar has-photo"><img src="${escapeHtml(p.photo_url)}" alt=""></div>`
                : `<div class="entity-avatar">${escapeHtml(initialsShort(p.nom_complet || '?'))}</div>`;
            const actions = peutGerer
                ? `<div class="actions-inline">
                        <button type="button" class="btn btn-ghost btn-sm" data-edit-personnel="${p.id}">${ico('edit')}Modifier</button>
                        ${!p.a_compte ? `<button type="button" class="btn btn-secondary btn-sm" data-compte-personnel="${p.id}">${ico('user')}Créer compte</button>` : ''}
                    </div>`
                : '—';
            return `
            <tr>
                <td data-label="Photo">${avatar}</td>
                <td data-label="Nom"><strong>${escapeHtml(p.nom_complet)}</strong></td>
                <td data-label="Matricule"><span class="code-chip">${escapeHtml(p.matricule || '—')}</span></td>
                <td data-label="Acte d'engagement"><span class="code-chip">${escapeHtml(p.reference_acte_engagement || '—')}</span></td>
                <td data-label="Fonction"><span class="badge badge-neutral">${escapeHtml(p.fonction_display || p.fonction)}</span></td>
                <td data-label="Sexe">${escapeHtml(p.sexe_display || p.sexe || '—')}</td>
                <td data-label="Téléphone">${escapeHtml(p.telephone || '—')}</td>
                <td data-label="Compte">${
                    p.a_compte
                        ? `<span class="badge badge-success" title="${escapeHtml(p.utilisateur_username || '')}">Compte lié</span>`
                        : '<span class="badge badge-neutral">Sans compte</span>'
                }</td>
                <td data-label="Statut"><span class="badge ${p.actif ? 'badge-success' : 'badge-danger'}">${p.actif ? 'Actif' : 'Inactif'}</span></td>
                <td data-label="Actions">${actions}</td>
            </tr>
        `;
        }).join('') : emptyRow(
            10,
            'Aucun personnel identifié',
            peutGerer
                ? 'Cliquez sur « Identifier un agent » puis créez éventuellement son compte.'
                : 'Aucun agent n\'est encore identifié pour cet établissement.',
        );

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
        tbody.querySelectorAll('[data-compte-personnel]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                try {
                    const p = await api(`${API}/personnels/${btn.dataset.comptePersonnel}/`);
                    await ouvrirCompteDepuisPersonnel(p);
                } catch (err) {
                    toast(err.message, 'error');
                }
            });
        });
    }

    function resetPersonnelPhotoPreview(url = '') {
        const preview = document.getElementById('personnelPhotoPreview');
        const drop = document.getElementById('personnelPhoto')?.closest('.file-drop');
        const title = drop?.querySelector('.file-drop-title');
        if (preview) {
            if (url) {
                preview.classList.add('has-photo');
                preview.innerHTML = `<img src="${escapeHtml(url)}" alt="">`;
            } else {
                preview.classList.remove('has-photo');
                preview.textContent = '—';
            }
        }
        if (drop) drop.classList.remove('has-file', 'is-dragover');
        if (title) title.textContent = 'Déposer une photo ou cliquer pour parcourir';
    }

    function ouvrirModalPersonnel(personnel = null) {
        if (!peutModifierEcole()) {
            toast('Votre rôle ne permet pas cette action.', 'error');
            return;
        }
        const form = document.getElementById('formPersonnel');
        if (!form) return;
        form.reset();
        document.getElementById('personnelId').value = personnel?.id || '';
        document.getElementById('titreModalPersonnel').textContent = personnel
            ? 'Modifier le personnel'
            : 'Identifier un agent';
        resetPersonnelPhotoPreview(personnel?.photo_url || '');
        if (personnel) {
            form.nom.value = personnel.nom || '';
            form.postnom.value = personnel.postnom || '';
            form.prenom.value = personnel.prenom || '';
            form.sexe.value = personnel.sexe || 'M';
            form.matricule.value = personnel.matricule || '';
            if (form.reference_acte_engagement) {
                form.reference_acte_engagement.value = personnel.reference_acte_engagement || '';
            }
            form.fonction.value = personnel.fonction || 'enseignant';
            form.telephone.value = personnel.telephone || '';
            form.email.value = personnel.email || '';
            form.date_naissance.value = personnel.date_naissance || '';
            form.date_prise_service.value = personnel.date_prise_service || '';
        }
        openModal('modalPersonnel');
    }

    function estAgentTerritorial(role) {
        const r = role
            || document.getElementById('ecoleDetail')?.dataset.role
            || document.getElementById('eleveDetail')?.dataset.role
            || document.getElementById('elevesApp')?.dataset.role
            || '';
        return r === 'agent_antenne' || r === 'agent_provincial' || r === 'agent_province_admin';
    }

    function peutModifierEcole() {
        return !estAgentTerritorial(document.getElementById('ecoleDetail')?.dataset.role);
    }

    function renderPhotosEcole(ecole) {
        const grille = document.getElementById('grillePhotosEcole');
        if (!grille) return;
        const photos = ecole.photos || [];
        const peutGerer = peutModifierEcole();
        setCount('countEcolePhotos', photos.length, 'photo');
        if (!photos.length) {
            grille.innerHTML = peutGerer
                ? '<p class="empty-inline">Aucune photo pour le moment. Ajoutez une vue de l\'établissement.</p>'
                : '<p class="empty-inline">Aucune photo pour le moment.</p>';
            return;
        }
        grille.innerHTML = photos.map((p) => {
            const src = escapeHtml(p.image_url || p.image || '');
            const legende = escapeHtml(p.legende || '');
            const badge = p.est_principale ? '<span class="photo-badge">Principale</span>' : '';
            const actions = peutGerer
                ? `<button type="button" class="btn-link danger" data-photo-delete="${p.id}" title="Supprimer">${ico('trash')}Supprimer</button>`
                : '';
            return `
                <figure class="ecole-photo-card${p.est_principale ? ' is-main' : ''}">
                    <a href="${src}" target="_blank" rel="noopener" class="ecole-photo-link">
                        <img src="${src}" alt="${legende || 'Photo école'}">
                    </a>
                    ${badge}
                    <figcaption>
                        <span>${legende || 'Sans légende'}</span>
                        ${actions}
                    </figcaption>
                </figure>
            `;
        }).join('');
    }

    function renderDocumentsEcole(ecole) {
        const liste = document.getElementById('listeDocumentsEcole');
        if (!liste) return;
        const docs = ecole.documents || [];
        const peutGerer = peutModifierEcole();
        setCount('countEcoleDocuments', docs.length, 'document');
        if (!docs.length) {
            liste.innerHTML = peutGerer
                ? '<p class="empty-inline">Aucun document de création. Ajoutez l\'agrément ou l\'autorisation d\'ouverture.</p>'
                : '<p class="empty-inline">Aucun document de création.</p>';
            return;
        }
        liste.innerHTML = docs.map((d) => {
            const url = escapeHtml(d.fichier_url || d.fichier || '#');
            const titre = escapeHtml(d.titre || d.nom_fichier || 'Document');
            const type = escapeHtml(d.type_display || d.type_document || '');
            const date = d.date_document ? escapeHtml(String(d.date_document).slice(0, 10)) : '—';
            const supprimer = peutGerer
                ? `<button type="button" class="btn-link danger" data-document-delete="${d.id}" title="Supprimer">${ico('trash')}Supprimer</button>`
                : '';
            return `
                <article class="ecole-doc-card">
                    <div class="ecole-doc-meta">
                        <strong>${type}</strong>
                        <span>${titre}</span>
                        <span class="form-hint">Date : ${date}</span>
                    </div>
                    <div class="ecole-doc-actions">
                        <a class="btn btn-ghost btn-sm" href="${url}" target="_blank" rel="noopener">${ico('download')}Ouvrir</a>
                        ${supprimer}
                    </div>
                </article>
            `;
        }).join('');
    }

    async function chargerEcoleDetail() {
        const root = document.getElementById('ecoleDetail');
        if (!root) return;
        const id = root.dataset.ecoleId;
        const ecole = await api(`${API}/ecoles/${id}/`);

        const sousTitre = document.getElementById('detailEcoleSousTitre');
        if (sousTitre) {
            sousTitre.textContent =
                `${ecole.antenne_nom || '—'} · ${ecole.province_educationnelle_nom || ecole.province_nom || '—'}`;
        }
        // En-tête de page : nom + code (unique — plus de doublon dans le hero)
        const pageNom = document.getElementById('pageEcoleNom');
        const pageCode = document.getElementById('pageEcoleCode');
        if (pageNom) pageNom.textContent = ecole.nom || 'École';
        if (pageCode) {
            pageCode.textContent = ecole.code || '—';
            pageCode.hidden = !ecole.code;
        }
        if (ecole.nom) document.title = `${ecole.nom} — Educ_RDC`;
        document.getElementById('detailEcoleType').textContent = ecole.type_display || ecole.type_ecole || '—';
        document.getElementById('detailEcoleNiveau').textContent = ecole.niveau_display || ecole.niveau || '—';

        const statut = document.getElementById('detailEcoleStatut');
        statut.textContent = ecole.active ? 'Active' : 'Inactive';
        statut.className = `badge ${ecole.active ? 'badge-success' : 'badge-danger'}`;

        const eff = ecole.effectifs ?? 0;
        document.getElementById('detailEcoleEffectifs').textContent = `${eff} élève${eff > 1 ? 's' : ''}`;

        fillDetailList('blocEcoleIdentite', [
            ['Nom', ecole.nom],
            ['Code école', ecole.code],
            ["N° d'agrément", ecole.numero_agrement],
            ['Document', ecole.arrete_numero
                ? `${ecole.arrete_numero}${ecole.arrete_objet ? ` — ${ecole.arrete_objet}` : ''}`
                : ''],
            ['Type', ecole.type_display || ecole.type_ecole],
            ['Niveau', ecole.niveau_display || ecole.niveau],
            ['Directeur', ecole.directeur],
        ]);

        fillDetailList('blocEcoleLocalisation', [
            ['Province administrative', ecole.province_administrative_nom],
            ['Province éducationnelle', ecole.province_educationnelle_nom || ecole.province_nom],
            ['Antenne', ecole.antenne_nom],
            ['Adresse', ecole.adresse],
            ['Latitude', ecole.latitude != null ? String(ecole.latitude) : '—'],
            ['Longitude', ecole.longitude != null ? String(ecole.longitude) : '—'],
        ]);

        const mapsEl = document.getElementById('lienMapsEcole');
        if (mapsEl) {
            if (ecole.maps_url) {
                mapsEl.hidden = false;
                mapsEl.innerHTML = `<a href="${escapeHtml(ecole.maps_url)}" target="_blank" rel="noopener">Voir sur Google Maps</a>`;
            } else {
                mapsEl.hidden = true;
                mapsEl.innerHTML = '';
            }
        }

        fillDetailList('blocEcoleContact', [
            ['Téléphone', ecole.telephone],
            ['Email', ecole.email],
            ['Créée le', (ecole.date_creation || '').slice(0, 10)],
        ]);

        renderPhotosEcole(ecole);
        renderDocumentsEcole(ecole);

        fillDetailList('blocEcoleEffectifs', [
            ['MAT', String(ecole.effectif_mat ?? 0)],
            ['PRIM', String(ecole.effectif_prim ?? 0)],
            ['SEC', String(ecole.effectif_sec ?? 0)],
            ['EFFECTIFS', String(eff)],
            ['Élèves enregistrés', String(ecole.nombre_eleves ?? 0)],
            ['Personnels identifiés', String(ecole.nombre_personnels ?? 0)],
        ]);

        const avatar = document.getElementById('detailEcoleAvatar');
        if (avatar) {
            if (ecole.photo_principale_url) {
                avatar.classList.add('has-photo');
                avatar.innerHTML = `<img src="${escapeHtml(ecole.photo_principale_url)}" alt="">`;
            } else {
                avatar.classList.remove('has-photo');
                avatar.textContent = initials(ecole.nom);
            }
        }

        root._ecoleCache = ecole;
        if (document.getElementById('sectionClassesEcole')) {
            await chargerEcoleClasses(id);
        }
        if (document.getElementById('comptes-ecole')) {
            await chargerEcoleUtilisateurs(id);
        }
        await chargerEcolePersonnels(id);

        const btnEleves = document.getElementById('btnListeElevesEcole');
        if (btnEleves && id) {
            btnEleves.href = `/eleves/?ecole=${encodeURIComponent(id)}&fige=1`;
        }
    }

    async function ensureCacheHierarchieEcole() {
        if (cacheEcolesPA.length && cacheEcolesPE.length && cacheEcolesAntennes.length) return;
        const [pas, pes, antennes] = await Promise.all([
            api(`${API}/provinces-administratives/?page_size=200`),
            api(`${API}/provinces-educationnelles/?page_size=200`),
            api(`${API}/antennes/?page_size=200`),
        ]);
        cacheEcolesPA = pas.results || pas;
        cacheEcolesPE = pes.results || pes;
        cacheEcolesAntennes = antennes.results || antennes;
    }

    function bindEditEcoleHierarchie() {
        const selPA = document.getElementById('editSelectProvinceAdmin');
        const selPE = document.getElementById('editSelectProvinceEduc');
        const selA = document.getElementById('editSelectAntenne');
        if (!selPA || !selPE || !selA || selPA.dataset.cascadeBound === '1') return;
        selPA.dataset.cascadeBound = '1';

        const fillPE = () => {
            const paId = selPA.value;
            const filtered = cacheEcolesPE.filter((p) => String(p.province_administrative) === String(paId));
            const cur = selPE.value;
            selPE.innerHTML = filtered.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');
            if (cur && filtered.some((p) => String(p.id) === String(cur))) selPE.value = cur;
            fillAntennes();
        };
        const fillAntennes = () => {
            const peId = selPE.value;
            const filtered = cacheEcolesAntennes.filter((a) => String(a.province_educationnelle) === String(peId));
            const cur = selA.value;
            selA.innerHTML = filtered.map((a) => `<option value="${a.id}">${escapeHtml(a.nom)}</option>`).join('');
            if (cur && filtered.some((a) => String(a.id) === String(cur))) selA.value = cur;
        };

        selPA.addEventListener('change', fillPE);
        selPE.addEventListener('change', fillAntennes);
        selPA._fillPE = fillPE;
        selPE._fillAntennes = fillAntennes;
    }

    async function ouvrirModalEditEcole() {
        if (estAgentTerritorial(document.getElementById('ecoleDetail')?.dataset.role)) {
            toast('Votre rôle ne permet pas cette action.', 'error');
            return;
        }
        const root = document.getElementById('ecoleDetail');
        const form = document.getElementById('formEditEcole');
        const ecole = root?._ecoleCache;
        if (!form || !ecole) {
            toast('Données de l\'école non chargées.', 'warning');
            return;
        }
        await ensureCacheHierarchieEcole();
        bindEditEcoleHierarchie();

        const selPA = document.getElementById('editSelectProvinceAdmin');
        const selPE = document.getElementById('editSelectProvinceEduc');
        const selA = document.getElementById('editSelectAntenne');
        if (!selPA || !selPE || !selA) {
            toast('Formulaire de modification introuvable.', 'error');
            return;
        }

        selPA.innerHTML = cacheEcolesPA.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)}</option>`).join('');

        let paId = ecole.province_administrative_id;
        if (!paId) {
            const pe = cacheEcolesPE.find((p) => String(p.id) === String(ecole.province_educationnelle));
            paId = pe?.province_administrative;
        }
        if (paId) selPA.value = String(paId);
        if (typeof selPA._fillPE === 'function') selPA._fillPE();
        if (ecole.province_educationnelle) selPE.value = String(ecole.province_educationnelle);
        if (typeof selPE._fillAntennes === 'function') selPE._fillAntennes();
        if (ecole.antenne) selA.value = String(ecole.antenne);

        // Si l'antenne / PE n'est pas dans la liste filtrée, forcer l'option
        if (ecole.province_educationnelle && String(selPE.value) !== String(ecole.province_educationnelle)) {
            const pe = cacheEcolesPE.find((p) => String(p.id) === String(ecole.province_educationnelle));
            if (pe) {
                selPE.insertAdjacentHTML(
                    'beforeend',
                    `<option value="${pe.id}">${escapeHtml(pe.nom)}</option>`,
                );
                selPE.value = String(pe.id);
                if (typeof selPE._fillAntennes === 'function') selPE._fillAntennes();
            }
        }
        if (ecole.antenne && String(selA.value) !== String(ecole.antenne)) {
            const ant = cacheEcolesAntennes.find((a) => String(a.id) === String(ecole.antenne));
            if (ant) {
                selA.insertAdjacentHTML(
                    'beforeend',
                    `<option value="${ant.id}">${escapeHtml(ant.nom)}</option>`,
                );
                selA.value = String(ant.id);
            }
        }

        form.nom.value = ecole.nom || '';
        form.code.value = ecole.code || '';
        form.numero_agrement.value = ecole.numero_agrement || '';
        form.directeur.value = ecole.directeur || '';
        form.type_ecole.value = ecole.type_ecole || 'publique';
        form.niveau.value = ecole.niveau || 'primaire';
        form.adresse.value = ecole.adresse || '';
        form.telephone.value = ecole.telephone || '';
        form.email.value = ecole.email || '';
        form.latitude.value = ecole.latitude != null ? ecole.latitude : '';
        form.longitude.value = ecole.longitude != null ? ecole.longitude : '';
        form.effectif_mat.value = ecole.effectif_mat ?? 0;
        form.effectif_prim.value = ecole.effectif_prim ?? 0;
        form.effectif_sec.value = ecole.effectif_sec ?? 0;
        const active = document.getElementById('editEcoleActive');
        if (active) active.checked = ecole.active !== false;

        await chargerSelectArretesEcole(ecole.arrete || '', 'selectArreteEditEcole');
        const selArrete = document.getElementById('selectArreteEditEcole');
        if (selArrete && ecole.arrete && String(selArrete.value) !== String(ecole.arrete)) {
            selArrete.insertAdjacentHTML(
                'beforeend',
                `<option value="${ecole.arrete}" data-numero="${escapeHtml(ecole.arrete_numero || '')}">${escapeHtml(ecole.arrete_numero || String(ecole.arrete))} — ${escapeHtml(ecole.arrete_objet || '')}</option>`,
            );
            selArrete.value = String(ecole.arrete);
        }

        openModal('modalEditEcole');
    }

    function initEcoleDetail() {
        bindModalClosers();
        bindFileDropPreview('importPersonnelFile');
        bindFileDropPreview('importClassesFile');
        bindFileDropPreview('personnelPhoto');
        document.getElementById('personnelPhoto')?.addEventListener('change', (e) => {
            const file = e.target.files?.[0];
            const preview = document.getElementById('personnelPhotoPreview');
            if (!preview) return;
            if (!file) return;
            const url = URL.createObjectURL(file);
            preview.classList.add('has-photo');
            preview.innerHTML = `<img src="${url}" alt="">`;
        });
        const root = document.getElementById('ecoleDetail');
        const ecoleId = root?.dataset.ecoleId;

        const goPersonnel = () => {
            document.getElementById('sectionPersonnelEcole')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        };
        document.getElementById('btnPersonnelEcole')?.addEventListener('click', goPersonnel);
        document.getElementById('btnNouveauPersonnel')?.addEventListener('click', () => ouvrirModalPersonnel());
        document.getElementById('btnNouveauPersonnel2')?.addEventListener('click', () => ouvrirModalPersonnel());
        document.getElementById('btnImporterPersonnel')?.addEventListener('click', () => {
            const result = document.getElementById('importPersonnelResult');
            if (result) {
                result.hidden = true;
                result.textContent = '';
            }
            openModal('modalImportPersonnel');
        });

        document.getElementById('btnModifierEcole')?.addEventListener('click', () => {
            ouvrirModalEditEcole().catch((err) => toast(err.message, 'error'));
        });

        document.getElementById('btnSupprimerEcole')?.addEventListener('click', async () => {
            if (!ecoleId || !confirm('Supprimer définitivement cette école ?')) return;
            try {
                await api(`${API}/ecoles/${ecoleId}/`, { method: 'DELETE' });
                toast('École supprimée.', 'success');
                window.location.href = '/ecoles/';
            } catch (err) { toast(err.message, 'error'); }
        });

        document.getElementById('btnSupprimerClasse')?.addEventListener('click', async () => {
            const id = document.getElementById('classeEcoleId')?.value;
            if (!id || !confirm('Supprimer cette classe ?')) return;
            try {
                await api(`${API}/classes/${id}/`, { method: 'DELETE' });
                toast('Classe supprimée.', 'success');
                closeModal('modalClasseEcole');
                await chargerEcoleClasses(ecoleId);
            } catch (err) { toast(err.message, 'error'); }
        });

        document.getElementById('btnNouvelleClasse')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            ouvrirModalClasseEcole();
        });
        document.getElementById('btnExpandClassesEcole')?.addEventListener('click', () => {
            setHierarchyExpanded(document.getElementById('ecoleClassesHierarchy'), true);
        });
        document.getElementById('btnCollapseClassesEcole')?.addEventListener('click', () => {
            setHierarchyExpanded(document.getElementById('ecoleClassesHierarchy'), false);
        });
        // Empêcher les boutons du bandeau de basculer le panneau
        document.querySelector('#sectionClassesEcole .detail-collapse-actions')?.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        document.getElementById('btnProgrammeRdc')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            ouvrirSelecteurProgrammeRdc(ecoleId, {
                onDone: async () => { await chargerEcoleClasses(ecoleId); },
            });
        });
        document.getElementById('classeEcoleSection')?.addEventListener('change', async (e) => {
            await chargerOptionsEcole(ecoleId, e.target.value, document.getElementById('classeEcoleOption'));
        });

        document.getElementById('btnQuickSection')?.addEventListener('click', async () => {
            const nom = prompt('Nom de la nouvelle section (ex. Technique) :');
            if (!nom || !nom.trim()) return;
            try {
                const s = await api(`${API}/sections-scolaires/`, {
                    method: 'POST',
                    body: JSON.stringify({ ecole: Number(ecoleId), nom: nom.trim(), active: true }),
                });
                await chargerSectionsEcole(ecoleId, document.getElementById('classeEcoleSection'), s.id);
                await chargerOptionsEcole(ecoleId, s.id, document.getElementById('classeEcoleOption'));
                toast('Section créée.', 'success');
            } catch (err) { toast(err.message, 'error'); }
        });

        document.getElementById('btnQuickOption')?.addEventListener('click', async () => {
            const sectionId = document.getElementById('classeEcoleSection')?.value;
            if (!sectionId) {
                toast('Choisissez d\'abord une section.', 'warning');
                return;
            }
            const nom = prompt('Nom de la nouvelle option (ex. Coupe et Couture) :');
            if (!nom || !nom.trim()) return;
            try {
                const o = await api(`${API}/options-scolaires/`, {
                    method: 'POST',
                    body: JSON.stringify({ section: Number(sectionId), nom: nom.trim(), active: true }),
                });
                await chargerOptionsEcole(ecoleId, sectionId, document.getElementById('classeEcoleOption'), o.id);
                toast('Option créée.', 'success');
            } catch (err) { toast(err.message, 'error'); }
        });

        document.getElementById('btnImporterClasses')?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const result = document.getElementById('importClassesResult');
            if (result) {
                result.hidden = true;
                result.textContent = '';
            }
            openModal('modalImportClasses');
        });

        document.getElementById('formImportClasses')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fichier = document.getElementById('importClassesFile')?.files?.[0];
            if (!fichier) {
                toast('Choisissez un fichier Excel à importer.', 'warning');
                return;
            }
            if (!ecoleId) {
                toast('École introuvable.', 'error');
                return;
            }
            const fd = new FormData();
            fd.append('fichier', fichier);
            fd.append('ecole', ecoleId);
            fd.append(
                'update_existing',
                document.getElementById('importClassesUpdate')?.checked ? '1' : '0',
            );
            const btn = document.getElementById('btnSubmitImportClasses');
            const resultEl = document.getElementById('importClassesResult');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Import…';
            }
            try {
                const data = await api(`${API}/classes/import/`, { method: 'POST', body: fd, headers: {} });
                toast(data.detail || 'Import terminé.', data.errors_count ? 'warning' : 'success');
                if (resultEl) {
                    const errs = (data.errors || []).slice(0, 8).map((x) => `L.${x.ligne}: ${x.message}`).join(' · ');
                    resultEl.textContent = errs || data.detail || 'Import terminé.';
                    resultEl.hidden = false;
                }
                if (!data.errors_count) {
                    document.getElementById('formImportClasses')?.reset();
                    closeModal('modalImportClasses');
                }
                await chargerEcoleClasses(ecoleId);
            } catch (err) {
                toast(err.message, 'error');
                if (resultEl) {
                    resultEl.textContent = err.message;
                    resultEl.hidden = false;
                }
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `${ico('upload')}Lancer l'import`;
                }
            }
        });

        document.getElementById('formClasseEcole')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                toast('Veuillez indiquer le nom de la classe.', 'warning');
                form.reportValidity();
                return;
            }
            if (!ecoleId) {
                toast('École introuvable.', 'error');
                return;
            }
            const id = document.getElementById('classeEcoleId')?.value;
            const section = form.section?.value || document.getElementById('classeEcoleSection')?.value;
            const option = form.option?.value || document.getElementById('classeEcoleOption')?.value;
            if (!section || !option) {
                toast('Section et option sont obligatoires.', 'warning');
                return;
            }
            const payload = {
                ecole: Number(ecoleId),
                section: Number(section),
                option: Number(option),
                nom: form.nom.value.trim(),
                code: form.code.value.trim(),
                active: document.getElementById('classeEcoleActive')?.checked !== false,
            };
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                if (id) {
                    await api(`${API}/classes/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                    toast('Classe mise à jour.', 'success');
                } else {
                    await api(`${API}/classes/`, { method: 'POST', body: JSON.stringify(payload) });
                    toast('Classe créée.', 'success');
                }
                closeModal('modalClasseEcole');
                form.reset();
                await chargerEcoleClasses(ecoleId);
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        document.getElementById('btnNouveauUserEcole')?.addEventListener('click', () => ouvrirModalUserEcole());

        document.getElementById('selectRoleUserEcole')?.addEventListener('change', async () => {
            syncRoleUserEcoleUI();
            const role = document.getElementById('selectRoleUserEcole')?.value;
            const edition = Boolean(document.getElementById('userEcoleId')?.value);
            const form = document.getElementById('formUserEcole');
            if (role !== 'enseignant' && form) {
                delete form.dataset.personnelPreselect;
            }
            if (role === 'enseignant' && ecoleId) {
                if (!edition) await chargerPersonnelsSansCompte(ecoleId, '', { fonction: 'enseignant' });
                await preparerAffectationEnseignant(ecoleId);
            }
        });
        document.getElementById('selectPersonnelUserEcole')?.addEventListener('change', () => {
            appliquerPersonnelSurFormUserEcole();
        });
        document.getElementById('selectSectionUserEcole')?.addEventListener('change', async (e) => {
            await chargerOptionsEcole(ecoleId, e.target.value, document.getElementById('selectOptionUserEcole'));
            await chargerClassesUserEcole(ecoleId);
        });
        document.getElementById('selectOptionUserEcole')?.addEventListener('change', async () => {
            await chargerClassesUserEcole(ecoleId);
        });

        document.getElementById('formUserEcole')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const id = document.getElementById('userEcoleId')?.value || '';
            const role = form.role.value;
            if (role === 'enseignant') {
                const personnelId = document.getElementById('selectPersonnelUserEcole')?.value;
                if (!id && !personnelId) {
                    toast('Sélectionnez d’abord la fiche Personnel de l’enseignant.', 'warning');
                    return;
                }
                const sectionId = document.getElementById('selectSectionUserEcole')?.value;
                if (!sectionId) {
                    toast('Sélectionnez la section de l’enseignant.', 'warning');
                    return;
                }
                if (!form.classe?.value) {
                    toast('Sélectionnez la classe dont l’enseignant est titulaire.', 'warning');
                    return;
                }
            }
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            if (!ecoleId) {
                toast('École introuvable.', 'error');
                return;
            }
            const password = (form.password.value || '').trim();
            if (!id && !password) {
                toast('Le mot de passe est obligatoire à la création.', 'warning');
                return;
            }
            const payload = {
                username: form.username.value.trim(),
                first_name: form.first_name.value.trim(),
                last_name: form.last_name.value.trim(),
                email: form.email.value.trim(),
                telephone: form.telephone.value.trim(),
                role,
                ecole: Number(ecoleId),
                is_active: document.getElementById('userEcoleActif')?.checked !== false,
            };
            if (role === 'enseignant') {
                payload.classe = Number(form.classe.value);
                if (!id) {
                    payload.personnel = Number(document.getElementById('selectPersonnelUserEcole').value);
                }
            } else {
                payload.classe = null;
                // Lien éventuel fiche personnel (directeur, etc.) — sans section/option/classe
                const persAdmin = form.dataset.personnelAdmin;
                if (!id && persAdmin) payload.personnel = Number(persAdmin);
            }
            if (password) payload.password = password;
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                if (id) {
                    await api(`${API}/utilisateurs/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                    toast('Compte mis à jour.', 'success');
                } else {
                    await api(`${API}/utilisateurs/`, { method: 'POST', body: JSON.stringify(payload) });
                    toast(
                        role === 'enseignant'
                            ? 'Compte enseignant créé (section / option / classe).'
                            : 'Compte administratif école créé.',
                        'success',
                    );
                }
                delete form.dataset.personnelAdmin;
                closeModal('modalUserEcole');
                form.reset();
                await Promise.all([
                    chargerEcoleUtilisateurs(ecoleId),
                    chargerEcolePersonnels(ecoleId),
                ]);
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        document.getElementById('formEditEcole')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const pe = form.province_educationnelle?.value;
            const antenne = form.antenne?.value;
            if (!form.nom.value?.trim() || !form.code.value?.trim() || !form.adresse.value?.trim() || !pe || !antenne) {
                toast('Veuillez compléter les champs obligatoires (nom, code, adresse, PE, antenne).', 'warning');
                form.reportValidity();
                return;
            }
            const payload = Object.fromEntries(new FormData(form).entries());
            delete payload.active;
            payload.province_educationnelle = Number(pe);
            payload.antenne = Number(antenne);
            if (payload.arrete) payload.arrete = Number(payload.arrete);
            else payload.arrete = null;
            payload.effectif_mat = Number(payload.effectif_mat || 0);
            payload.effectif_prim = Number(payload.effectif_prim || 0);
            payload.effectif_sec = Number(payload.effectif_sec || 0);
            payload.effectifs = payload.effectif_mat + payload.effectif_prim + payload.effectif_sec;
            payload.active = Boolean(document.getElementById('editEcoleActive')?.checked);
            if (!payload.email) payload.email = '';
            if (payload.latitude === '' || payload.latitude == null) payload.latitude = null;
            else payload.latitude = Number(payload.latitude);
            if (payload.longitude === '' || payload.longitude == null) payload.longitude = null;
            else payload.longitude = Number(payload.longitude);

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                await api(`${API}/ecoles/${ecoleId}/`, {
                    method: 'PATCH',
                    body: JSON.stringify(payload),
                });
                toast('École mise à jour.', 'success');
                closeModal('modalEditEcole');
                await chargerEcoleDetail();
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        document.getElementById('selectArreteEditEcole')?.addEventListener('change', () => {
            const sel = document.getElementById('selectArreteEditEcole');
            const input = document.getElementById('inputNumeroAgrementEditEcole');
            if (!sel || !input) return;
            const opt = sel.options[sel.selectedIndex];
            const numero = opt?.dataset?.numero || '';
            if (sel.value && numero) input.value = numero;
        });

        document.getElementById('btnAjouterPhotoEcole')?.addEventListener('click', () => {
            const form = document.getElementById('formPhotoEcole');
            if (form) form.reset();
            const drop = form?.querySelector('.file-drop');
            const title = form?.querySelector('.file-drop-title');
            if (title) title.textContent = 'Déposer des photos ou cliquer pour parcourir';
            drop?.classList.remove('has-file', 'is-dragover');
            openModal('modalPhotoEcole');
        });

        bindFileDropPreview('ecolePhotoFile');

        document.getElementById('formPhotoEcole')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!peutModifierEcole()) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            const fileInput = document.getElementById('ecolePhotoFile');
            const fichiers = fileInput?.files ? Array.from(fileInput.files).filter((f) => f && f.size) : [];
            if (!fichiers.length) {
                toast('Choisissez une ou plusieurs images.', 'warning');
                return;
            }
            if (!ecoleId) {
                toast('École introuvable.', 'error');
                return;
            }
            const fd = new FormData();
            fichiers.forEach((fichier) => fd.append('image', fichier, fichier.name));
            fd.append('legende', (form.querySelector('[name="legende"]')?.value || '').trim());
            fd.append(
                'est_principale',
                document.getElementById('ecolePhotoPrincipale')?.checked ? '1' : '0',
            );
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = fichiers.length > 1 ? `Envoi (${fichiers.length})…` : 'Envoi…';
            }
            try {
                const data = await api(`${API}/ecoles/${ecoleId}/photos/`, {
                    method: 'POST',
                    body: fd,
                    headers: {},
                });
                toast(data.detail || `${fichiers.length} photo(s) ajoutée(s).`, 'success');
                closeModal('modalPhotoEcole');
                form.reset();
                const title = form.querySelector('.file-drop-title');
                if (title) title.textContent = 'Déposer des photos ou cliquer pour parcourir';
                form.querySelector('.file-drop')?.classList.remove('has-file', 'is-dragover');
                await chargerEcoleDetail();
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Ajouter';
                }
            }
        });

        document.getElementById('grillePhotosEcole')?.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-photo-delete]');
            if (!btn) return;
            if (!peutModifierEcole()) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const photoId = btn.getAttribute('data-photo-delete');
            if (!photoId || !window.confirm('Supprimer cette photo ?')) return;
            try {
                await api(`${API}/ecoles/${ecoleId}/photos/${photoId}/`, { method: 'DELETE' });
                toast('Photo supprimée.', 'success');
                await chargerEcoleDetail();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        bindFileDropPreview('ecoleDocumentFile');
        document.getElementById('btnAjouterDocumentEcole')?.addEventListener('click', () => {
            const form = document.getElementById('formDocumentEcole');
            form?.reset();
            const title = form?.querySelector('.file-drop-title');
            if (title) title.textContent = 'Déposer le fichier ou cliquer pour parcourir';
            form?.querySelector('.file-drop')?.classList.remove('has-file', 'is-dragover');
            openModal('modalDocumentEcole');
        });

        document.getElementById('formDocumentEcole')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!peutModifierEcole()) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            const fileInput = document.getElementById('ecoleDocumentFile');
            const fichier = fileInput?.files?.[0];
            if (!fichier || !fichier.size) {
                toast('Choisissez un fichier.', 'warning');
                return;
            }
            if (!ecoleId) {
                toast('École introuvable.', 'error');
                return;
            }
            const fd = new FormData(form);
            if (!fd.get('fichier') && fichier) fd.set('fichier', fichier, fichier.name);
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Envoi…';
            }
            try {
                await api(`${API}/ecoles/${ecoleId}/documents/`, {
                    method: 'POST',
                    body: fd,
                    headers: {},
                });
                toast('Document ajouté.', 'success');
                closeModal('modalDocumentEcole');
                form.reset();
                const title = form.querySelector('.file-drop-title');
                if (title) title.textContent = 'Déposer le fichier ou cliquer pour parcourir';
                form.querySelector('.file-drop')?.classList.remove('has-file', 'is-dragover');
                await chargerEcoleDetail();
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = `${ico('plus')}Ajouter`;
                }
            }
        });

        document.getElementById('listeDocumentsEcole')?.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-document-delete]');
            if (!btn) return;
            if (!peutModifierEcole()) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const documentId = btn.getAttribute('data-document-delete');
            if (!documentId || !ecoleId) return;
            if (!window.confirm('Supprimer ce document ?')) return;
            try {
                await api(`${API}/ecoles/${ecoleId}/documents/${documentId}/`, { method: 'DELETE' });
                toast('Document supprimé.', 'success');
                await chargerEcoleDetail();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('formPersonnel')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!peutModifierEcole()) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            const id = document.getElementById('personnelId').value;
            const fd = new FormData(form);
            fd.set('ecole', String(ecoleId));
            fd.set('actif', 'true');
            if (!fd.get('date_naissance')) fd.delete('date_naissance');
            if (!fd.get('date_prise_service')) fd.delete('date_prise_service');
            const photo = fd.get('photo');
            if (photo instanceof File && !photo.size) fd.delete('photo');
            try {
                if (id) {
                    await api(`${API}/personnels/${id}/`, { method: 'PATCH', body: fd, headers: {} });
                    toast('Personnel mis à jour.', 'success');
                } else {
                    await api(`${API}/personnels/`, { method: 'POST', body: fd, headers: {} });
                    toast('Personnel identifié avec succès.', 'success');
                }
                closeModal('modalPersonnel');
                form.reset();
                resetPersonnelPhotoPreview();
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

        document.getElementById('formImportPersonnel')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!peutModifierEcole()) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            const fichier = document.getElementById('importPersonnelFile')?.files?.[0];
            if (!fichier) {
                toast('Choisissez un fichier Excel à importer.', 'warning');
                return;
            }
            if (!ecoleId) {
                toast('École introuvable.', 'error');
                return;
            }
            const fd = new FormData();
            fd.append('fichier', fichier);
            fd.append('ecole', ecoleId);
            fd.append(
                'update_existing',
                document.getElementById('importPersonnelUpdate')?.checked ? '1' : '0',
            );

            const btn = document.getElementById('btnSubmitImportPersonnel');
            const resultEl = document.getElementById('importPersonnelResult');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Import en cours…';
            }
            try {
                const data = await api(`${API}/personnels/import/`, { method: 'POST', body: fd, headers: {} });
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
                if (!data.errors_count) {
                    form.reset();
                    const title = form.querySelector('.file-drop-title');
                    if (title) title.textContent = 'Déposer un Excel ou cliquer pour parcourir';
                    closeModal('modalImportPersonnel');
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

        chargerEcoleDetail().catch((err) => toast(err.message, 'error'));
    }

    /* ---------- Élèves ---------- */
    let pageEleves = 1;

    function ordreDepuisMatricule(matricule) {
        const s = String(matricule || '').trim();
        const std = s.match(/^(\d{4})-(\d+)$/);
        if (std) return std[2];
        const m = s.match(/(\d+)\s*$/);
        return m ? m[1] : '';
    }

    function majNumeroIdentificationEleve() {
        const form = document.getElementById('formEleve');
        if (!form) return;
        const input = form.numero_identification;
        if (!input) return;
        const mat = form.matricule?.value || '';
        const sel = document.getElementById('selectEcoleEleve');
        const code = sel?.selectedOptions?.[0]?.getAttribute('data-code') || '';
        const ordre = ordreDepuisMatricule(mat);
        input.value = (code && ordre) ? `${code}-${ordre}` : '';
    }

    async function majMatriculeEleve() {
        const form = document.getElementById('formEleve');
        if (!form?.matricule) return;
        try {
            const data = await api(`${API}/eleves/prochain-matricule/`);
            form.matricule.value = data.matricule || '';
        } catch (_) {
            form.matricule.value = '';
        }
        majNumeroIdentificationEleve();
    }

    async function chargerSelectEcoles(selectId, { placeholder = '' } = {}) {
        const data = await api(`${API}/ecoles/?leger=1&page_size=200`);
        const list = data.results || data;
        const sel = document.getElementById(selectId);
        if (!sel) return;
        const opts = list.map((e) =>
            `<option value="${e.id}" data-code="${escapeHtml(e.code || '')}">${escapeHtml(e.nom)} (${escapeHtml(e.code)})</option>`
        ).join('');
        sel.innerHTML = placeholder
            ? `<option value="">${escapeHtml(placeholder)}</option>${opts}`
            : opts;
    }

    async function remplirFiltreClassesEleves(ecoleId, selectedId = '') {
        const sel = document.getElementById('filtreClasseEleves');
        if (!sel) return;
        const keep = selectedId || sel.value || '';
        sel.innerHTML = '<option value="">Toutes les classes</option>';
        const app = document.getElementById('elevesApp');
        const ecole = ecoleId || app?.dataset.ecoleId || '';
        if (!ecole) return;
        try {
            const data = await api(
                `${API}/classes/?ecole=${encodeURIComponent(ecole)}&actif=1&page_size=300&ordering=nom`,
            );
            const rows = data.results || data;
            rows.forEach((c) => {
                const label = [c.nom, c.section_nom, c.option_nom].filter(Boolean).join(' · ');
                sel.insertAdjacentHTML(
                    'beforeend',
                    `<option value="${c.id}">${escapeHtml(label || c.nom || `Classe #${c.id}`)}</option>`,
                );
            });
            if (keep && [...sel.options].some((o) => o.value === String(keep))) {
                sel.value = String(keep);
            }
        } catch (err) {
            toast(err.message, 'error');
        }
    }

    async function chargerEleves(page = 1) {
        pageEleves = page;
        const app = document.getElementById('elevesApp');
        const isAdminEcole = app?.dataset.role === 'admin_ecole';
        const q = document.getElementById('searchEleves')?.value || '';
        const ecoleFigee = app?.dataset.ecoleFigee === '1';
        const ecoleId = ecoleFigee
            ? (app?.dataset.ecoleId || '')
            : (document.getElementById('filtreEcoleEleves')?.value || app?.dataset.ecoleId || '');
        const classeId = document.getElementById('filtreClasseEleves')?.value || '';
        let url = `${API}/eleves/?page=${page}`;
        if (q) url += `&q=${encodeURIComponent(q)}`;
        if (ecoleId) url += `&ecole=${encodeURIComponent(ecoleId)}`;
        if (classeId) url += `&classe=${encodeURIComponent(classeId)}`;
        const data = await api(url);
        const rows = data.results || data;
        const tbody = document.querySelector('#tableEleves tbody');
        setCount('countEleves', data.count ?? rows.length);
        const colCount = isAdminEcole ? 7 : 8;

        tbody.innerHTML = rows.length ? rows.map((e) => {
            const avatar = e.photo_url
                ? `<div class="entity-avatar has-photo"><img src="${escapeHtml(e.photo_url)}" alt="${escapeHtml(e.nom_complet)}"></div>`
                : `<div class="entity-avatar">${escapeHtml(initials(e.nom_complet))}</div>`;
            const classeLibelle = [e.classe_nom, e.section_nom, e.option_nom].filter(Boolean).join(' · ') || '—';
            const ecoleCell = isAdminEcole
                ? ''
                : `<td data-label="École">
                    <strong title="${escapeHtml(e.ecole_nom || '')}">${escapeHtml(e.ecole_nom || '—')}</strong>
                   </td>`;
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
                <td data-label="N° Identification"><span class="code-chip">${escapeHtml(e.numero_identification || '—')}</span></td>
                <td data-label="N° Permanent"><span class="code-chip">${escapeHtml(e.numero_permanent || '—')}</span></td>
                <td data-label="Sexe">${escapeHtml(e.sexe_display || e.sexe)}</td>
                ${ecoleCell}
                <td data-label="Classe">${escapeHtml(classeLibelle)}</td>
                <td data-label="Statut"><span class="badge ${e.actif ? 'badge-success' : 'badge-danger'}">${e.actif ? 'Actif' : 'Inactif'}</span></td>
                <td data-label="Actions">
                    <a class="btn btn-secondary btn-sm" href="/eleves/${e.id}/">${ico('eye')}Détail</a>
                </td>
            </tr>`;
        }).join('') : emptyRow(
            colCount,
            'Aucun élève trouvé',
            ecoleId || classeId
                ? 'Aucun élève pour ce filtre — affinez la recherche ou ajoutez un élève.'
                : 'Sélectionnez une école ou affinez votre recherche.',
        );

        const totalPages = data.count ? Math.ceil(data.count / 20) : 1;
        renderPagination('paginationEleves', pageEleves, totalPages, chargerEleves);
    }

    function initEleves() {
        bindModalClosers();
        bindFileDropPreview('elevePhoto');
        bindFileDropPreview('elevePhotoPere');
        bindFileDropPreview('elevePhotoMere');
        bindFileDropPreview('elevePhotoTuteur');
        bindFileDropPreview('importElevesFile');

        const app = document.getElementById('elevesApp');
        const paramsUrl = new URLSearchParams(window.location.search);
        const ecoleUrl = (paramsUrl.get('ecole') || '').trim();
        const figeUrl = paramsUrl.get('fige') === '1' || paramsUrl.get('fige') === 'true';
        // Verrouillage : compte école OU arrivée depuis la fiche école (?ecole=&fige=1)
        let ecoleFigee = app?.dataset.ecoleFigee === '1' || (Boolean(ecoleUrl) && figeUrl);
        let ecoleFigeeId = ecoleFigee
            ? (app?.dataset.ecoleId || ecoleUrl)
            : (app?.dataset.ecoleId || '');
        if (ecoleUrl && figeUrl) {
            ecoleFigee = true;
            ecoleFigeeId = ecoleUrl;
            if (app) {
                app.dataset.ecoleFigee = '1';
                app.dataset.ecoleId = ecoleUrl;
            }
        }

        const boot = async () => {
            await chargerSelectEcoles('selectEcoleEleve');
            await chargerSelectEcoles('selectEcoleImportEleves', {
                placeholder: '— Utiliser le code école du fichier —',
            });
            const filtreEcole = document.getElementById('filtreEcoleEleves');
            const badgeEcole = document.getElementById('badgeEcoleEleves');

            if (ecoleFigee && ecoleFigeeId) {
                if (filtreEcole) filtreEcole.hidden = true;
                let nomEcole = app?.dataset.ecoleNom || '';
                if (!nomEcole) {
                    try {
                        const eco = await api(`${API}/ecoles/${ecoleFigeeId}/?leger=1`);
                        nomEcole = eco.nom || `École #${ecoleFigeeId}`;
                        if (app) app.dataset.ecoleNom = nomEcole;
                    } catch (_) {
                        nomEcole = `École #${ecoleFigeeId}`;
                    }
                }
                if (badgeEcole) {
                    badgeEcole.hidden = false;
                    badgeEcole.textContent = nomEcole;
                }
            } else if (filtreEcole) {
                filtreEcole.hidden = false;
                await chargerSelectEcoles('filtreEcoleEleves', {
                    placeholder: 'Toutes les écoles',
                });
                if (ecoleUrl) filtreEcole.value = String(ecoleUrl);
                if (badgeEcole) badgeEcole.hidden = true;
            }

            if (ecoleFigee && ecoleFigeeId) {
                const selCreate = document.getElementById('selectEcoleEleve');
                const selImport = document.getElementById('selectEcoleImportEleves');
                if (selCreate) {
                    // S'assurer que l'option existe
                    if (![...selCreate.options].some((o) => o.value === String(ecoleFigeeId))) {
                        selCreate.insertAdjacentHTML(
                            'beforeend',
                            `<option value="${ecoleFigeeId}">${escapeHtml(app?.dataset.ecoleNom || `École #${ecoleFigeeId}`)}</option>`,
                        );
                    }
                    selCreate.value = String(ecoleFigeeId);
                    selCreate.disabled = true;
                }
                if (selImport) {
                    if (![...selImport.options].some((o) => o.value === String(ecoleFigeeId))) {
                        selImport.insertAdjacentHTML(
                            'beforeend',
                            `<option value="${ecoleFigeeId}">${escapeHtml(app?.dataset.ecoleNom || `École #${ecoleFigeeId}`)}</option>`,
                        );
                    }
                    selImport.value = String(ecoleFigeeId);
                    selImport.disabled = true;
                }
                await syncScolariteEleveCascade(ecoleFigeeId, { from: 'ecole' });
            }
            const ecolePourClasses = ecoleFigee && ecoleFigeeId
                ? ecoleFigeeId
                : (filtreEcole?.value || app?.dataset.ecoleId || ecoleUrl || '');
            if (app?.dataset.role === 'admin_ecole') {
                await remplirFiltreClassesEleves(ecolePourClasses || app?.dataset.ecoleId);
            }
            await chargerEleves(1);
        };
        boot().catch((e) => toast(e.message, 'error'));

        const openImportEleves = () => {
            if (estAgentTerritorial(app?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const result = document.getElementById('importElevesResult');
            if (result) {
                result.hidden = true;
                result.textContent = '';
            }
            const lien = document.getElementById('lienModeleImportEleves');
            if (lien) {
                const ecoleId = ecoleFigee && ecoleFigeeId
                    ? ecoleFigeeId
                    : (document.getElementById('selectEcoleImportEleves')?.value
                        || document.getElementById('filtreEcoleEleves')?.value
                        || app?.dataset.ecoleId
                        || '');
                lien.href = ecoleId
                    ? `${API}/eleves/modele-import/?ecole=${encodeURIComponent(ecoleId)}`
                    : `${API}/eleves/modele-import/`;
            }
            openModal('modalImportEleves');
        };
        document.getElementById('selectEcoleImportEleves')?.addEventListener('change', () => {
            const lien = document.getElementById('lienModeleImportEleves');
            if (!lien) return;
            const ecoleId = ecoleFigee && ecoleFigeeId
                ? ecoleFigeeId
                : (document.getElementById('selectEcoleImportEleves')?.value || '');
            lien.href = ecoleId
                ? `${API}/eleves/modele-import/?ecole=${encodeURIComponent(ecoleId)}`
                : `${API}/eleves/modele-import/`;
        });
        const ecoleEleveCourante = () => (
            ecoleFigee && ecoleFigeeId
                ? ecoleFigeeId
                : document.getElementById('selectEcoleEleve')?.value
        );
        document.getElementById('selectEcoleEleve')?.addEventListener('change', (e) => {
            syncScolariteEleveCascade(e.target.value, { from: 'ecole' }).catch((err) => toast(err.message, 'error'));
            majNumeroIdentificationEleve();
        });
        document.getElementById('selectSectionEleve')?.addEventListener('change', () => {
            syncScolariteEleveCascade(ecoleEleveCourante(), { from: 'section' })
                .catch((err) => toast(err.message, 'error'));
        });
        document.getElementById('selectOptionEleve')?.addEventListener('change', () => {
            syncScolariteEleveCascade(ecoleEleveCourante(), { from: 'option' })
                .catch((err) => toast(err.message, 'error'));
        });
        document.getElementById('formEleve')?.querySelector('[name="matricule"]')
            ?.addEventListener('input', majNumeroIdentificationEleve);
        document.getElementById('filtreEcoleEleves')?.addEventListener('change', () => {
            const ecoleId = document.getElementById('filtreEcoleEleves')?.value || '';
            remplirFiltreClassesEleves(ecoleId)
                .then(() => chargerEleves(1))
                .catch((err) => toast(err.message, 'error'));
        });
        document.getElementById('filtreClasseEleves')?.addEventListener('change', () => {
            chargerEleves(1).catch((err) => toast(err.message, 'error'));
        });
        function setEleveWizardStep(step) {
            const form = document.getElementById('formEleve');
            if (!form) return;
            const panels = [...form.querySelectorAll('[data-step-panel]')];
            const total = panels.length || 5;
            const n = Math.min(Math.max(parseInt(step, 10) || 1, 1), total);
            form.dataset.step = String(n);
            form.setAttribute('data-step', String(n));
            panels.forEach((panel) => {
                const active = parseInt(panel.getAttribute('data-step-panel'), 10) === n;
                panel.classList.toggle('is-active', active);
                panel.toggleAttribute('hidden', !active);
                panel.setAttribute('aria-hidden', active ? 'false' : 'true');
            });
            form.querySelectorAll('[data-goto-step]').forEach((btn) => {
                const s = parseInt(btn.getAttribute('data-goto-step'), 10);
                btn.classList.toggle('is-active', s === n);
                btn.classList.toggle('is-done', s < n);
            });
            const btnPrev = document.getElementById('btnElevePrev');
            const btnNext = document.getElementById('btnEleveNext');
            const btnSubmit = document.getElementById('btnEleveSubmit');
            if (btnPrev) {
                btnPrev.hidden = n <= 1;
                btnPrev.classList.toggle('is-wizard-hidden', n <= 1);
            }
            // Dernière étape (Tuteur) : pas de Suivant, uniquement Enregistrer
            const derniere = n >= total;
            if (btnNext) {
                btnNext.hidden = derniere;
                btnNext.classList.toggle('is-wizard-hidden', derniere);
                btnNext.setAttribute('aria-hidden', derniere ? 'true' : 'false');
            }
            if (btnSubmit) {
                btnSubmit.hidden = !derniere;
                btnSubmit.classList.toggle('is-wizard-hidden', !derniere);
                btnSubmit.setAttribute('aria-hidden', derniere ? 'false' : 'true');
            }
        }

        function validerEtapeEleveCourante() {
            const form = document.getElementById('formEleve');
            if (!form) return true;
            const panel = form.querySelector('.wizard-panel.is-active')
                || form.querySelector(`[data-step-panel="${form.dataset.step || 1}"]`);
            if (!panel) return true;
            const fields = panel.querySelectorAll('input[required], select[required], textarea[required]');
            for (const field of fields) {
                if (field.disabled || field.readOnly) continue;
                if (field.type === 'file') continue;
                if (!(field.value || '').toString().trim()) {
                    try { field.focus(); } catch (_) { /* ignore */ }
                    toast('Complétez les champs obligatoires (*) avant de continuer.', 'warning');
                    return false;
                }
            }
            return true;
        }

        function allerEtapeEleveSuivante(e) {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            const form = document.getElementById('formEleve');
            if (!form) return;
            if (!validerEtapeEleveCourante()) return;
            const current = parseInt(form.getAttribute('data-step') || '1', 10);
            setEleveWizardStep(current + 1);
        }

        function allerEtapeElevePrecedente(e) {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            const form = document.getElementById('formEleve');
            if (!form) return;
            const current = parseInt(form.getAttribute('data-step') || '1', 10);
            setEleveWizardStep(current - 1);
        }

        // Délégation : fiable même si le modal est déplacé vers <body>
        if (document.body.dataset.eleveWizardBound !== '1') {
            document.body.dataset.eleveWizardBound = '1';
            document.body.addEventListener('click', (e) => {
                const nextBtn = e.target.closest('#btnEleveNext');
                if (nextBtn) {
                    allerEtapeEleveSuivante(e);
                    return;
                }
                const prevBtn = e.target.closest('#btnElevePrev');
                if (prevBtn) {
                    allerEtapeElevePrecedente(e);
                    return;
                }
                const stepBtn = e.target.closest('#formEleve [data-goto-step]');
                if (stepBtn) {
                    e.preventDefault();
                    const form = document.getElementById('formEleve');
                    if (!form) return;
                    const target = parseInt(stepBtn.getAttribute('data-goto-step'), 10);
                    const current = parseInt(form.getAttribute('data-step') || '1', 10);
                    if (target === current) return;
                    if (target > current) {
                        if (!validerEtapeEleveCourante()) return;
                        if (target > current + 1) {
                            toast('Utilisez le bouton Suivant pour avancer étape par étape.', 'warning');
                            return;
                        }
                    }
                    setEleveWizardStep(target);
                }
            });
        }

        function resetEleveFileDrops() {
            ['elevePhoto', 'elevePhotoPere', 'elevePhotoMere', 'elevePhotoTuteur'].forEach((id) => {
                const input = document.getElementById(id);
                if (typeof input?._resetFileDropPreview === 'function') {
                    input._resetFileDropPreview();
                }
            });
        }

        document.getElementById('btnNouvelEleve')?.addEventListener('click', () => {
            if (estAgentTerritorial(app?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = document.getElementById('formEleve');
            form?.reset();
            resetEleveFileDrops();
            const ecoleId = ecoleFigee
                ? ecoleFigeeId
                : document.getElementById('selectEcoleEleve')?.value;
            if (ecoleFigee && ecoleFigeeId) {
                const sel = document.getElementById('selectEcoleEleve');
                if (sel) {
                    sel.value = String(ecoleFigeeId);
                    sel.disabled = true;
                }
            }
            if (ecoleId) {
                syncScolariteEleveCascade(ecoleId, { from: 'ecole' }).catch(() => {});
            } else {
                const selSec = document.getElementById('selectSectionEleve');
                const selOpt = document.getElementById('selectOptionEleve');
                const sel = document.getElementById('selectClasseEleve');
                if (selSec) selSec.innerHTML = `<option value="">— Sélectionner une section —</option>`;
                if (selOpt) selOpt.innerHTML = `<option value="">— Sélectionner une option —</option>`;
                if (sel) sel.innerHTML = `<option value="">— Sélectionner une classe —</option>`;
            }
            majNumeroIdentificationEleve();
            majMatriculeEleve().catch(() => {});
            openModal('modalEleve');
            setEleveWizardStep(1);
        });
        document.getElementById('btnImporterEleves')?.addEventListener('click', openImportEleves);
        document.getElementById('btnImporterEleves2')?.addEventListener('click', openImportEleves);
        document.getElementById('btnSearchEleves')?.addEventListener('click', () => chargerEleves(1));
        document.getElementById('searchEleves')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerEleves(1);
        });
        document.getElementById('btnImprimerListeEleves')?.addEventListener('click', (e) => {
            const q = (document.getElementById('searchEleves')?.value || '').trim();
            const base = `${API}/eleves/liste-pdf/`;
            e.currentTarget.href = q ? `${base}?q=${encodeURIComponent(q)}` : base;
        });

        document.getElementById('formEleve')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (estAgentTerritorial(app?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            // Valider toutes les étapes (les panels [hidden] sont exclus de checkValidity())
            const panels = [...form.querySelectorAll('[data-step-panel]')];
            for (const panel of panels) {
                const fields = panel.querySelectorAll('input, select, textarea');
                for (const field of fields) {
                    if (field.disabled) continue;
                    if (!field.checkValidity()) {
                        setEleveWizardStep(Number(panel.dataset.stepPanel));
                        field.reportValidity();
                        toast('Veuillez compléter les champs obligatoires.', 'warning');
                        return;
                    }
                }
            }
            const fd = new FormData(form);
            if (ecoleFigee && ecoleFigeeId) {
                fd.set('ecole', ecoleFigeeId);
            }
            // Retirer photos vides pour éviter erreur API
            ['photo', 'photo_pere', 'photo_mere', 'photo_tuteur'].forEach((key) => {
                const file = fd.get(key);
                if (file instanceof File && !file.size) fd.delete(key);
            });
            try {
                await api(`${API}/eleves/`, { method: 'POST', body: fd, headers: {} });
                toast('Élève enregistré.', 'success');
                form.reset();
                resetEleveFileDrops();
                setEleveWizardStep(1);
                closeModal('modalEleve');
                await chargerSelectEcoles('selectEcoleEleve');
                await chargerEleves(1);
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('formImportEleves')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (estAgentTerritorial(app?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            const fileInput = document.getElementById('importElevesFile');
            const fichier = fileInput?.files?.[0];
            if (!fichier) {
                toast('Choisissez un fichier CSV à importer.', 'warning');
                return;
            }
            const fd = new FormData();
            fd.append('fichier', fichier);
            const ecole = (ecoleFigee && ecoleFigeeId)
                ? ecoleFigeeId
                : form.ecole?.value;
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
                    if (title) title.textContent = 'Déposer un Excel ou cliquer pour parcourir';
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
    let cacheEleveDetail = null;

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

    function libellePhotoParent(role) {
        if (role === 'mere') return { de: 'de la mère', titre: 'Photo de la mère', cible: 'la mère' };
        if (role === 'pere') return { de: 'du père', titre: 'Photo du père', cible: 'le père' };
        return { de: 'du tuteur', titre: 'Photo du tuteur', cible: 'le tuteur' };
    }

    /**
     * Affiche le modal d’aperçu / confirmation avant upload photo.
     * @returns {Promise<boolean>}
     */
    function demanderConfirmationPhoto(file, input, texts = {}, opts = {}) {
        const modalId = opts.modalId || 'modalConfirmPhotoEleve';
        const previewId = opts.previewId || 'confirmPhotoElevePreview';
        const nomId = opts.nomId || 'confirmPhotoEleveNom';
        const btnOkId = opts.btnOkId || 'btnConfirmPhotoEleve';
        const titleId = opts.titleId || 'confirmPhotoEleveTitle';
        const subtitleId = opts.subtitleId || 'confirmPhotoEleveSubtitle';
        const leadId = opts.leadId || 'confirmPhotoEleveLead';
        const noticeId = opts.noticeId || 'confirmPhotoEleveNotice';

        const modal = document.getElementById(modalId);
        const preview = document.getElementById(previewId);
        const img = preview?.querySelector('img');
        const fallback = preview?.querySelector('.confirm-photo-fallback');
        const nomEl = document.getElementById(nomId);
        const btnOk = document.getElementById(btnOkId);
        const titleEl = document.getElementById(titleId);
        const subtitleEl = document.getElementById(subtitleId);
        const leadEl = document.getElementById(leadId);
        const noticeEl = document.getElementById(noticeId);
        if (!modal || !btnOk || !file) {
            if (input) input.value = '';
            return Promise.resolve(false);
        }

        if (titleEl) titleEl.textContent = texts.titre || 'Changer la photo';
        if (subtitleEl) {
            subtitleEl.textContent = texts.sousTitre || 'Aperçu avant remplacement sur la fiche';
        }
        if (leadEl) {
            leadEl.innerHTML = texts.question || 'Utiliser cette photo&nbsp;?';
        }
        if (noticeEl) {
            noticeEl.textContent = texts.notice
                || 'La photo actuelle sera remplacée. Cette action est immédiate.';
        }

        let objectUrl = URL.createObjectURL(file);
        const nettoyerApercu = () => {
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }
            if (img) {
                img.removeAttribute('src');
                img.hidden = true;
            }
            if (fallback) fallback.hidden = false;
            if (nomEl) {
                nomEl.textContent = '';
                nomEl.hidden = true;
            }
        };

        if (img) {
            img.src = objectUrl;
            img.hidden = false;
        }
        if (fallback) fallback.hidden = true;
        if (nomEl) {
            nomEl.textContent = file.name || '';
            nomEl.hidden = !file.name;
        }

        return new Promise((resolve) => {
            let settled = false;
            const cleanup = (ok) => {
                if (settled) return;
                settled = true;
                btnOk.removeEventListener('click', onOk);
                modal.querySelectorAll('[data-close]').forEach((el) => {
                    el.removeEventListener('click', onCancel);
                });
                modal.removeEventListener('click', onBackdrop);
                closeModal(modalId);
                if (!ok) {
                    nettoyerApercu();
                    if (input) input.value = '';
                } else {
                    nettoyerApercu();
                }
                resolve(ok);
            };
            const onOk = (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                cleanup(true);
            };
            const onCancel = () => cleanup(false);
            const onBackdrop = (ev) => {
                if (ev.target === modal && !modal.dataset.justOpened) cleanup(false);
            };
            btnOk.addEventListener('click', onOk);
            modal.querySelectorAll('[data-close]').forEach((el) => {
                el.addEventListener('click', onCancel);
            });
            modal.addEventListener('click', onBackdrop);
            openModal(modalId);
        });
    }

    function renderParentCards(eleve) {
        const wrap = document.getElementById('blocParents');
        if (!wrap) return;
        const canEdit = Boolean(document.getElementById('btnModifierParents'));
        const cards = [
            {
                role: 'pere',
                label: 'Père',
                name: eleve.nom_complet_pere,
                phone: eleve.telephone_pere,
                email: eleve.email_pere,
                extra: eleve.profession_pere,
                photo: eleve.photo_pere_url,
            },
            {
                role: 'mere',
                label: 'Mère',
                name: eleve.nom_complet_mere,
                phone: eleve.telephone_mere,
                email: eleve.email_mere,
                extra: eleve.profession_mere,
                photo: eleve.photo_mere_url,
            },
            {
                role: 'tuteur',
                label: eleve.lien_tuteur_display || 'Tuteur',
                name: eleve.nom_tuteur,
                phone: eleve.telephone_tuteur,
                email: eleve.email_tuteur,
                extra: eleve.lien_tuteur_display || '',
                photo: eleve.photo_tuteur_url,
            },
        ];

        wrap.innerHTML = cards.map((c) => {
            const name = c.name || 'Non renseigné';
            const photoHtml = c.photo
                ? `<img src="${escapeHtml(c.photo)}" alt="Photo ${escapeHtml(c.label)}">`
                : escapeHtml(initials(c.name || c.label));
            const phoneHtml = c.phone
                ? `<a href="tel:${escapeHtml(c.phone)}">${escapeHtml(c.phone)}</a>`
                : '—';
            const emailHtml = c.email
                ? `<a href="mailto:${escapeHtml(c.email)}">${escapeHtml(c.email)}</a>`
                : '—';
            const actions = canEdit
                ? `<div class="parent-card-actions">
                        <label class="btn btn-ghost btn-sm" for="inputPhotoParent_${c.role}">${ico('photo')}Photo</label>
                        <input type="file" id="inputPhotoParent_${c.role}" accept="image/*" hidden data-parent-photo="${c.role}">
                   </div>`
                : '';
            return `
                <article class="parent-card">
                    <div class="parent-card-photo">${photoHtml}</div>
                    <div class="parent-card-body">
                        <p class="parent-card-role">${escapeHtml(c.label)}</p>
                        <h4 class="parent-card-name">${escapeHtml(name)}</h4>
                        <div class="parent-card-meta">
                            <span>Tél. ${phoneHtml}</span>
                            <span>E-mail ${emailHtml}</span>
                            ${c.extra && c.role !== 'tuteur' ? `<span>${escapeHtml(c.extra)}</span>` : ''}
                        </div>
                        ${actions}
                    </div>
                </article>
            `;
        }).join('');

        wrap.querySelectorAll('[data-parent-photo]').forEach((input) => {
            input.addEventListener('change', async (e) => {
                const file = e.target.files && e.target.files[0];
                const role = e.target.dataset.parentPhoto;
                if (!file || !role) return;
                const labels = libellePhotoParent(role);
                const confirme = await demanderConfirmationPhoto(file, e.target, {
                    titre: labels.titre,
                    sousTitre: 'Aperçu avant remplacement sur la fiche',
                    question: `Utiliser cette photo pour ${labels.cible}&nbsp;?`,
                    notice: `La photo actuelle ${labels.de} sera remplacée. Cette action est immédiate.`,
                });
                if (!confirme) return;

                const id = document.getElementById('eleveDetail')?.dataset.eleveId;
                if (!id) {
                    e.target.value = '';
                    return;
                }
                const fd = new FormData();
                fd.append('photo', file);
                fd.append('role', role);
                const btnOk = document.getElementById('btnConfirmPhotoEleve');
                if (btnOk) btnOk.disabled = true;
                try {
                    await api(`${API}/eleves/${id}/photo-parent/`, { method: 'POST', body: fd, headers: {} });
                    toast(`Photo ${labels.de} mise à jour.`, 'success');
                    await chargerEleveDetail();
                } catch (err) {
                    toast(err.message, 'error');
                } finally {
                    e.target.value = '';
                    if (btnOk) btnOk.disabled = false;
                }
            });
        });
    }

    function setEditEleveWizardStep(step) {
        const form = document.getElementById('formEditEleve');
        if (!form) return;
        const panels = [...form.querySelectorAll('[data-step-panel]')];
        const total = panels.length || 5;
        const n = Math.min(Math.max(parseInt(step, 10) || 1, 1), total);
        form.dataset.step = String(n);
        form.setAttribute('data-step', String(n));
        panels.forEach((panel) => {
            const active = parseInt(panel.getAttribute('data-step-panel'), 10) === n;
            panel.classList.toggle('is-active', active);
            panel.toggleAttribute('hidden', !active);
            panel.setAttribute('aria-hidden', active ? 'false' : 'true');
        });
        form.querySelectorAll('[data-goto-step]').forEach((btn) => {
            const s = parseInt(btn.getAttribute('data-goto-step'), 10);
            btn.classList.toggle('is-active', s === n);
            btn.classList.toggle('is-done', s < n);
        });
        const btnPrev = document.getElementById('btnEditElevePrev');
        const btnNext = document.getElementById('btnEditEleveNext');
        const btnSubmit = document.getElementById('btnEditEleveSubmit');
        if (btnPrev) {
            btnPrev.hidden = n <= 1;
            btnPrev.classList.toggle('is-wizard-hidden', n <= 1);
        }
        const derniere = n >= total;
        if (btnNext) {
            btnNext.hidden = derniere;
            btnNext.classList.toggle('is-wizard-hidden', derniere);
            btnNext.setAttribute('aria-hidden', derniere ? 'true' : 'false');
        }
        if (btnSubmit) {
            btnSubmit.hidden = !derniere;
            btnSubmit.classList.toggle('is-wizard-hidden', !derniere);
            btnSubmit.setAttribute('aria-hidden', derniere ? 'false' : 'true');
        }
    }

    function validerEtapeEditEleveCourante() {
        const form = document.getElementById('formEditEleve');
        if (!form) return true;
        const panel = form.querySelector('.wizard-panel.is-active')
            || form.querySelector(`[data-step-panel="${form.dataset.step || 1}"]`);
        if (!panel) return true;
        const fields = panel.querySelectorAll('input[required], select[required], textarea[required]');
        for (const field of fields) {
            if (field.disabled || field.readOnly) continue;
            if (field.type === 'file') continue;
            if (!(field.value || '').toString().trim()) {
                try { field.focus(); } catch (_) { /* ignore */ }
                toast('Complétez les champs obligatoires (*) avant de continuer.', 'warning');
                return false;
            }
        }
        return true;
    }

    function resetEditEleveFileDrops() {
        ['editElevePhoto', 'editElevePhotoPere', 'editElevePhotoMere', 'editElevePhotoTuteur'].forEach((id) => {
            const input = document.getElementById(id);
            if (input) input.value = '';
            if (typeof input?._resetFileDropPreview === 'function') {
                input._resetFileDropPreview();
            }
        });
    }

    function remplirFormEditEleve(eleve) {
        const form = document.getElementById('formEditEleve');
        if (!form || !eleve) return;
        form.matricule.value = eleve.matricule || '';
        form.numero_identification.value = eleve.numero_identification || '';
        form.numero_permanent.value = eleve.numero_permanent || '';
        form.numero_impot.value = eleve.numero_impot || '';
        form.sexe.value = eleve.sexe || 'M';
        form.nom.value = eleve.nom || '';
        form.postnom.value = eleve.postnom || '';
        form.prenom.value = eleve.prenom || '';
        form.date_naissance.value = (eleve.date_naissance || '').slice(0, 10);
        form.lieu_naissance.value = eleve.lieu_naissance || '';
        form.adresse.value = eleve.adresse || '';
        form.actif.value = eleve.actif ? 'true' : 'false';
        form.nom_pere.value = eleve.nom_complet_pere || eleve.nom_pere || '';
        form.telephone_pere.value = eleve.telephone_pere || '';
        form.email_pere.value = eleve.email_pere || '';
        form.profession_pere.value = eleve.profession_pere || '';
        form.nom_mere.value = eleve.nom_complet_mere || eleve.nom_mere || '';
        form.telephone_mere.value = eleve.telephone_mere || '';
        form.email_mere.value = eleve.email_mere || '';
        form.profession_mere.value = eleve.profession_mere || '';
        form.lien_tuteur.value = eleve.lien_tuteur || '';
        form.nom_tuteur.value = eleve.nom_tuteur || '';
        form.telephone_tuteur.value = eleve.telephone_tuteur || '';
        form.email_tuteur.value = eleve.email_tuteur || '';
        resetEditEleveFileDrops();
    }

    function majNumeroIdentificationEditEleve() {
        const form = document.getElementById('formEditEleve');
        if (!form) return;
        const mat = form.matricule?.value || '';
        const sel = document.getElementById('selectEcoleEditEleve');
        const code = sel?.selectedOptions?.[0]?.getAttribute('data-code') || '';
        const ordre = ordreDepuisMatricule(mat);
        if (form.numero_identification) {
            form.numero_identification.value = (code && ordre) ? `${code}-${ordre}` : (form.numero_identification.value || '');
        }
    }

    function majPhotoHeaderEditEleve(eleve) {
        const photo = document.getElementById('editEleveHeaderPhoto');
        const sub = document.getElementById('editEleveHeaderSub');
        const ecoleEl = document.getElementById('editEleveHeaderEcole');
        if (sub) {
            const nom = (eleve?.nom_complet || [eleve?.nom, eleve?.postnom, eleve?.prenom].filter(Boolean).join(' ') || 'Élève').trim();
            const mat = eleve?.matricule ? ` · ${eleve.matricule}` : '';
            sub.textContent = `${nom}${mat}`;
        }
        if (ecoleEl) {
            const ecoleNom = (eleve?.ecole_nom || '').trim();
            const ecoleCode = (eleve?.ecole_code || '').trim();
            if (ecoleNom || ecoleCode) {
                ecoleEl.hidden = false;
                ecoleEl.textContent = ecoleCode
                    ? `École : ${ecoleNom}${ecoleNom ? ' · ' : ''}${ecoleCode}`
                    : `École : ${ecoleNom}`;
            } else {
                ecoleEl.hidden = true;
                ecoleEl.textContent = '';
            }
        }
        if (!photo) return;
        if (eleve?.photo_url) {
            photo.classList.add('has-photo');
            photo.innerHTML = `<img src="${escapeHtml(eleve.photo_url)}" alt="">`;
        } else {
            const initials = [eleve?.prenom, eleve?.nom]
                .map((p) => (p || '').trim().charAt(0).toUpperCase())
                .filter(Boolean)
                .join('')
                .slice(0, 2) || '—';
            photo.classList.remove('has-photo');
            photo.textContent = initials;
        }
    }

    async function ouvrirModalEditEleve(step = 1) {
        const eleve = cacheEleveDetail;
        if (!eleve) return;
        const root = document.getElementById('eleveDetail');
        remplirFormEditEleve(eleve);
        majPhotoHeaderEditEleve(eleve);
        await chargerSelectEcoles('selectEcoleEditEleve');
        const selEcole = document.getElementById('selectEcoleEditEleve');
        const ecoleId = (() => {
            if (!selEcole) return eleve.ecole || '';
            const ecoleFigee = root?.dataset.ecoleFigee === '1';
            const ecoleUser = root?.dataset.ecoleId || '';
            selEcole.value = String(ecoleFigee && ecoleUser ? ecoleUser : (eleve.ecole || ''));
            selEcole.disabled = ecoleFigee;
            return selEcole.value || eleve.ecole || '';
        })();
        await syncScolariteCascade(ecoleId, {
            sectionSelectId: 'selectSectionEditEleve',
            optionSelectId: 'selectOptionEditEleve',
            classeSelectId: 'selectClasseEditEleve',
            sectionId: eleve.section || '',
            optionId: eleve.option || '',
            classeId: eleve.classe || '',
            from: 'ecole',
        });
        majNumeroIdentificationEditEleve();
        setEditEleveWizardStep(step);
        openModal('modalEditEleve');
    }

    function remplirFormParents(eleve) {
        const form = document.getElementById('formParentsEleve');
        if (!form || !eleve) return;
        const fields = [
            'adresse',
            'nom_pere', 'postnom_pere', 'prenom_pere', 'telephone_pere', 'email_pere', 'profession_pere',
            'nom_mere', 'postnom_mere', 'prenom_mere', 'telephone_mere', 'email_mere', 'profession_mere',
            'lien_tuteur', 'nom_tuteur', 'telephone_tuteur', 'email_tuteur',
        ];
        fields.forEach((name) => {
            if (form.elements.namedItem(name)) {
                form.elements.namedItem(name).value = eleve[name] || '';
            }
        });
    }

    async function chargerEleveDetail() {
        const root = document.getElementById('eleveDetail');
        if (!root) return;
        const id = root.dataset.eleveId;
        const eleve = await api(`${API}/eleves/${id}/`);
        cacheEleveDetail = eleve;

        const classeLigne = [eleve.classe_nom, eleve.section_nom, eleve.option_nom]
            .filter(Boolean).join(' · ') || '—';
        document.getElementById('detailMatricule').textContent = eleve.matricule;
        document.getElementById('detailNom').textContent = eleve.nom_complet;
        document.getElementById('detailSousTitre').textContent =
            `${eleve.ecole_nom || '—'} · ${classeLigne}`;
        document.getElementById('detailSexe').textContent = eleve.sexe_display || eleve.sexe;
        document.getElementById('detailClasse').textContent = classeLigne;
        const statut = document.getElementById('detailStatut');
        statut.textContent = eleve.actif ? 'Actif' : 'Inactif';
        statut.className = `badge ${eleve.actif ? 'badge-success' : 'badge-danger'}`;

        renderDetailPhoto(eleve);

        fillDetailList('blocIdentite', [
            ['Matricule', eleve.matricule],
            ['Numéro Identification', eleve.numero_identification],
            ['Numéro Permanent', eleve.numero_permanent],
            ['Numéro Impôt', eleve.numero_impot],
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
            ['Classe / Section / Option', classeLigne],
            ['Province admin.', eleve.province_administrative_nom],
            ['Province éduc.', eleve.province_nom],
            ['Antenne', eleve.antenne_nom],
            ['Inscription', (eleve.date_inscription || '').slice(0, 10)],
        ]);

        fillDetailList('blocAdresse', [
            ['Résidence', eleve.adresse],
        ]);

        const codeUnique = document.getElementById('detailCodeUnique');
        if (codeUnique) codeUnique.textContent = eleve.code_unique || '—';
        const qrImg = document.getElementById('detailQrEleve');
        const qrFallback = document.getElementById('detailQrEleveFallback');
        const lienQr = document.getElementById('lienQrEleve');
        if (eleve.qr_code_url && qrImg) {
            qrImg.src = eleve.qr_code_url;
            qrImg.hidden = false;
            if (qrFallback) qrFallback.hidden = true;
            if (lienQr) {
                lienQr.href = eleve.qr_code_url;
                lienQr.hidden = false;
            }
        } else if (qrImg) {
            qrImg.removeAttribute('src');
            qrImg.hidden = true;
            if (qrFallback) qrFallback.hidden = false;
            if (lienQr) lienQr.hidden = true;
        }

        renderParentCards(eleve);

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

        const tCartes = document.querySelector('#tableDetailCartes tbody');
        if (tCartes) {
            const cartes = eleve.cartes || [];
            tCartes.innerHTML = cartes.length ? cartes.map((c) => `
            <tr>
                <td data-label="N° Carte"><span class="code-chip">${escapeHtml(c.numero_carte)}</span></td>
                <td data-label="Statut"><span class="badge badge-info">${escapeHtml(c.statut_display)}</span></td>
                <td data-label="Expiration">${escapeHtml(c.date_expiration)}</td>
                <td data-label="Actions">
                    <div class="actions-inline">
                        <a class="btn btn-primary btn-sm" href="${API}/cartes/${c.id}/pdf/" target="_blank">${ico('pdf')}PDF</a>
                        ${c.qr_code_url ? `<a class="btn btn-secondary btn-sm" href="${escapeHtml(c.qr_code_url)}" target="_blank">${ico('qr')}QR</a>` : ''}
                    </div>
                </td>
            </tr>
        `).join('') : emptyRow(4, 'Aucune carte', 'Aucune carte scolaire n\'est encore associée à cet élève.');
        }

        return eleve;
    }

    function initEleveDetail() {
        bindModalClosers();
        bindFileDropPreview('editElevePhoto');
        bindFileDropPreview('editElevePhotoPere');
        bindFileDropPreview('editElevePhotoMere');
        bindFileDropPreview('editElevePhotoTuteur');
        chargerEleveDetail().catch((e) => toast(e.message, 'error'));

        if (document.body.dataset.editEleveWizardBound !== '1') {
            document.body.dataset.editEleveWizardBound = '1';
            document.body.addEventListener('click', (e) => {
                const nextBtn = e.target.closest('#btnEditEleveNext');
                if (nextBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (!validerEtapeEditEleveCourante()) return;
                    const form = document.getElementById('formEditEleve');
                    const current = parseInt(form?.getAttribute('data-step') || '1', 10);
                    setEditEleveWizardStep(current + 1);
                    return;
                }
                const prevBtn = e.target.closest('#btnEditElevePrev');
                if (prevBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    const form = document.getElementById('formEditEleve');
                    const current = parseInt(form?.getAttribute('data-step') || '1', 10);
                    setEditEleveWizardStep(current - 1);
                    return;
                }
                const stepBtn = e.target.closest('#formEditEleve [data-goto-step]');
                if (stepBtn) {
                    e.preventDefault();
                    const form = document.getElementById('formEditEleve');
                    if (!form) return;
                    const target = parseInt(stepBtn.getAttribute('data-goto-step'), 10);
                    const current = parseInt(form.getAttribute('data-step') || '1', 10);
                    if (target === current) return;
                    if (target > current) {
                        if (!validerEtapeEditEleveCourante()) return;
                        if (target > current + 1) {
                            toast('Utilisez le bouton Suivant pour avancer étape par étape.', 'warning');
                            return;
                        }
                    }
                    setEditEleveWizardStep(target);
                }
            });
        }

        document.getElementById('btnRegenererQrEleve')?.addEventListener('click', async () => {
            if (estAgentTerritorial(document.getElementById('eleveDetail')?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const id = document.getElementById('eleveDetail')?.dataset.eleveId;
            if (!id || !confirm('Régénérer le QR code de cet élève ?')) return;
            try {
                await api(`${API}/eleves/${id}/regenerer-qr/`, { method: 'POST', body: '{}' });
                toast('QR code régénéré.', 'success');
                await chargerEleveDetail();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('btnSupprimerEleve')?.addEventListener('click', async () => {
            if (estAgentTerritorial(document.getElementById('eleveDetail')?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const id = document.getElementById('eleveDetail')?.dataset.eleveId;
            if (!id || !confirm('Supprimer définitivement cet élève ?')) return;
            try {
                await api(`${API}/eleves/${id}/`, { method: 'DELETE' });
                toast('Élève supprimé.', 'success');
                window.location.href = '/eleves/';
            } catch (err) { toast(err.message, 'error'); }
        });

        document.getElementById('btnModifierEleve')?.addEventListener('click', () => {
            if (estAgentTerritorial(document.getElementById('eleveDetail')?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            ouvrirModalEditEleve(1).catch((err) => toast(err.message, 'error'));
        });

        document.getElementById('selectEcoleEditEleve')?.addEventListener('change', (e) => {
            syncScolariteCascade(e.target.value, {
                sectionSelectId: 'selectSectionEditEleve',
                optionSelectId: 'selectOptionEditEleve',
                classeSelectId: 'selectClasseEditEleve',
                from: 'ecole',
            }).catch((err) => toast(err.message, 'error'));
            majNumeroIdentificationEditEleve();
        });
        document.getElementById('selectSectionEditEleve')?.addEventListener('change', () => {
            const ecoleId = document.getElementById('selectEcoleEditEleve')?.value;
            syncScolariteCascade(ecoleId, {
                sectionSelectId: 'selectSectionEditEleve',
                optionSelectId: 'selectOptionEditEleve',
                classeSelectId: 'selectClasseEditEleve',
                from: 'section',
            }).catch((err) => toast(err.message, 'error'));
        });
        document.getElementById('selectOptionEditEleve')?.addEventListener('change', () => {
            const ecoleId = document.getElementById('selectEcoleEditEleve')?.value;
            syncScolariteCascade(ecoleId, {
                sectionSelectId: 'selectSectionEditEleve',
                optionSelectId: 'selectOptionEditEleve',
                classeSelectId: 'selectClasseEditEleve',
                from: 'option',
            }).catch((err) => toast(err.message, 'error'));
        });

        document.getElementById('formEditEleve')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (estAgentTerritorial(document.getElementById('eleveDetail')?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            const panels = [...form.querySelectorAll('[data-step-panel]')];
            for (const panel of panels) {
                const fields = panel.querySelectorAll('input, select, textarea');
                for (const field of fields) {
                    if (field.disabled) continue;
                    if (!field.checkValidity()) {
                        setEditEleveWizardStep(Number(panel.dataset.stepPanel));
                        field.reportValidity();
                        toast('Veuillez compléter les champs obligatoires.', 'warning');
                        return;
                    }
                }
            }
            const id = document.getElementById('eleveDetail')?.dataset.eleveId;
            if (!id) return;
            const root = document.getElementById('eleveDetail');
            const selEcole = document.getElementById('selectEcoleEditEleve');
            const fd = new FormData(form);
            if (root?.dataset.ecoleFigee === '1' && root.dataset.ecoleId) {
                fd.set('ecole', root.dataset.ecoleId);
            } else if (selEcole?.value) {
                fd.set('ecole', selEcole.value);
            }
            fd.set('actif', form.actif.value === 'true' ? 'true' : 'false');
            // Nom complet parents → un seul champ (comme à l’enregistrement)
            fd.set('postnom_pere', '');
            fd.set('prenom_pere', '');
            fd.set('postnom_mere', '');
            fd.set('prenom_mere', '');
            ['photo', 'photo_pere', 'photo_mere', 'photo_tuteur'].forEach((key) => {
                const file = fd.get(key);
                if (file instanceof File && !file.size) fd.delete(key);
            });
            // Matricule / n° identification en lecture seule : ne pas les renvoyer
            fd.delete('matricule');
            fd.delete('numero_identification');

            const submitBtn = document.getElementById('btnEditEleveSubmit')
                || form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                await api(`${API}/eleves/${id}/`, { method: 'PATCH', body: fd, headers: {} });
                toast('Élève mis à jour.', 'success');
                closeModal('modalEditEleve');
                resetEditEleveFileDrops();
                setEditEleveWizardStep(1);
                await chargerEleveDetail();
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        document.getElementById('btnModifierParents')?.addEventListener('click', () => {
            if (estAgentTerritorial(document.getElementById('eleveDetail')?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            ouvrirModalEditEleve(4).catch((err) => toast(err.message, 'error'));
        });

        document.getElementById('formParentsEleve')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (estAgentTerritorial(document.getElementById('eleveDetail')?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                return;
            }
            const form = e.target;
            const id = document.getElementById('eleveDetail')?.dataset.eleveId;
            if (!id) return;
            const payload = {};
            [
                'adresse',
                'nom_pere', 'postnom_pere', 'prenom_pere', 'telephone_pere', 'email_pere', 'profession_pere',
                'nom_mere', 'postnom_mere', 'prenom_mere', 'telephone_mere', 'email_mere', 'profession_mere',
                'lien_tuteur', 'nom_tuteur', 'telephone_tuteur', 'email_tuteur',
            ].forEach((name) => {
                payload[name] = (form.elements.namedItem(name)?.value || '').trim();
            });
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                await api(`${API}/eleves/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                toast('Parents et contacts mis à jour.', 'success');
                closeModal('modalParentsEleve');
                await chargerEleveDetail();
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        document.getElementById('inputPhotoDetail')?.addEventListener('change', async (e) => {
            if (estAgentTerritorial(document.getElementById('eleveDetail')?.dataset.role)) {
                toast('Votre rôle ne permet pas cette action.', 'error');
                e.target.value = '';
                return;
            }
            const file = e.target.files && e.target.files[0];
            if (!file) return;
            const input = e.target;
            const confirme = await demanderConfirmationPhoto(file, input, {
                titre: 'Changer la photo',
                sousTitre: 'Aperçu avant remplacement sur la fiche',
                question: 'Utiliser cette photo pour la fiche de l’élève&nbsp;?',
                notice: 'La photo actuelle sera remplacée. Cette action est immédiate.',
            });
            if (!confirme) return;

            const root = document.getElementById('eleveDetail');
            const id = root?.dataset.eleveId;
            if (!id) {
                input.value = '';
                return;
            }
            const fd = new FormData();
            fd.append('photo', file);
            const btnOk = document.getElementById('btnConfirmPhotoEleve');
            if (btnOk) btnOk.disabled = true;
            try {
                await api(`${API}/eleves/${id}/photo/`, { method: 'POST', body: fd, headers: {} });
                toast('Photo mise à jour.', 'success');
                input.value = '';
                await chargerEleveDetail();
            } catch (err) {
                toast(err.message, 'error');
                input.value = '';
            } finally {
                if (btnOk) btnOk.disabled = false;
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
                        <a class="btn btn-primary btn-sm" href="${API}/cartes/${c.id}/pdf/" target="_blank">${ico('pdf')}PDF</a>
                        ${c.qr_code_url ? `<a class="btn btn-secondary btn-sm" href="${c.qr_code_url}" target="_blank">${ico('qr')}QR</a>` : ''}
                    </div>
                </td>
            </tr>
        `).join('') : emptyRow(7, 'Aucune carte produite', 'Les cartes scolaires apparaîtront ici une fois émises.');

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
        // Enseignant : page exports uniquement (pas de stats / graphique)
        if (!document.getElementById('statsRapports') && !document.getElementById('chartRapports')) {
            return;
        }
        try {
            const stats = await api(`${API}/stats/`);
            setText('rEleves', stats.nb_eleves);
            setText('rEcoles', stats.nb_ecoles);
            setText('rAntennes', stats.nb_antennes);
            setText('rProvincesEduc', stats.nb_provinces_educ);
            setText('rCartes', stats.nb_cartes);
            setText('rBiometries', stats.biometries_validees);

            const subtitle = document.querySelector('.topbar-title p');
            if (subtitle && stats.scope_label) {
                subtitle.textContent = `${stats.scope_label} — statistiques et exports`;
            }

            const chartTitle = document.querySelector('#chartRapports')?.closest('.panel')?.querySelector('.panel-header h2');
            const chartSub = document.querySelector('#chartRapports')?.closest('.panel')?.querySelector('.panel-header p');
            if (chartTitle && stats.chart?.title) chartTitle.textContent = stats.chart.title;
            if (chartSub && stats.chart?.subtitle) chartSub.textContent = stats.chart.subtitle;

            if (document.getElementById('chartRapports')) {
                const series = stats.chart?.series || (stats.par_province || []).map((p) => ({
                    nom: p.nom,
                    valeur: p.nb_ecoles ?? p.nb_eleves ?? 0,
                }));
                const values = series.map((s) => (
                    s.nb_ecoles != null && stats.scope !== 'ecole' ? s.nb_ecoles : s.valeur
                ));
                drawBarChart('chartRapports', series.map((s) => s.nom), values);
            }
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

        sidebar.querySelectorAll('.nav-group-toggle').forEach((btn) => {
            btn.addEventListener('click', () => {
                const group = btn.closest('.nav-group');
                if (!group) return;
                const open = !group.classList.contains('open');
                group.classList.toggle('open', open);
                btn.setAttribute('aria-expanded', open ? 'true' : 'false');
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
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-pa="${p.id}">${ico('edit')}Modifier</button>
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
                const btnDel = document.getElementById('btnSupprimerPA');
                if (btnDel) btnDel.hidden = false;
                openModal('modalPA');
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
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-pe="${p.id}">${ico('edit')}Modifier</button>
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
                const btnDel = document.getElementById('btnSupprimerPE');
                if (btnDel) btnDel.hidden = false;
                openModal('modalPE');
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
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-antenne="${a.id}">${ico('edit')}Modifier</button>
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
                const btnDel = document.getElementById('btnSupprimerAntenne');
                if (btnDel) btnDel.hidden = false;
                openModal('modalAntenne');
            });
        });
        renderPagination('paginationAntennes', pageAntennes, data.count ? Math.ceil(data.count / 20) : 1, chargerAntennes);
    }

    async function chargerModelesImport() {
        const grille = document.getElementById('grilleModelesImport');
        if (!grille) return;
        const data = await api(`${API}/modeles-import/`);
        const items = data.results || data;
        setCount('countModelesImport', data.count ?? items.length, 'modèle');

        const ops = items.filter((m) => m.categorie === 'opérationnel' || m.categorie === 'operationnel');
        const refs = items.filter((m) => m.categorie === 'referentiel');
        const autres = items.filter((m) => !ops.includes(m) && !refs.includes(m));

        const renderCard = (m) => `
            <article class="import-modele-card">
                <div class="import-modele-card-top">
                    <h3>${escapeHtml(m.titre)}</h3>
                    <span class="badge ${m.categorie === 'referentiel' ? 'badge-info' : 'badge-success'}">
                        ${m.categorie === 'referentiel' ? 'Référentiel' : 'Opérationnel'}
                    </span>
                </div>
                <p>${escapeHtml(m.description || '')}</p>
                <p class="form-hint" style="margin:0.35rem 0 0">
                    <strong>Obligatoires :</strong> ${(m.obligatoires || []).map((c) => `<code>${escapeHtml(c)}</code>`).join(' ')}
                </p>
                <p class="form-hint" style="margin:0.35rem 0 0">
                    <strong>Colonnes :</strong> ${(m.colonnes || []).map((c) => `<code>${escapeHtml(c)}</code>`).join(' ')}
                </p>
                ${m.notes ? `<p class="form-hint" style="margin:0.35rem 0 0">${escapeHtml(m.notes)}</p>` : ''}
                <div class="import-modele-card-actions">
                    <a class="btn btn-primary btn-sm" href="${escapeHtml(m.url)}" download>
                        ${ico('download')}Télécharger ${escapeHtml(m.fichier || '.xlsx')}
                    </a>
                </div>
            </article>
        `;

        const section = (title, list) => {
            if (!list.length) return '';
            return `
                <div class="import-modeles-section">
                    <h3 class="detail-card-title">${escapeHtml(title)}</h3>
                    <div class="import-modeles-cards">${list.map(renderCard).join('')}</div>
                </div>
            `;
        };

        grille.innerHTML = items.length
            ? [
                section('Données opérationnelles', ops),
                section('Référentiel territorial', refs),
                section('Autres', autres),
            ].join('')
            : '<p class="empty-state">Aucun modèle disponible.</p>';
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
                if (btn.dataset.tab === 'modeles-import') chargerModelesImport().catch((e) => toast(e.message, 'error'));
            });
        });
        document.getElementById('btnRefreshModelesImport')?.addEventListener('click', () => {
            chargerModelesImport().catch((e) => toast(e.message, 'error'));
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
            const btnDel = document.getElementById('btnSupprimerPA');
            if (btnDel) btnDel.hidden = true;
            openModal('modalPA');
        });
        document.getElementById('btnSupprimerPA')?.addEventListener('click', async () => {
            const id = document.getElementById('paId')?.value;
            if (!id || !confirm('Supprimer cette province administrative ?')) return;
            try {
                await api(`${API}/provinces-administratives/${id}/`, { method: 'DELETE' });
                toast('Province administrative supprimée.', 'success');
                closeModal('modalPA');
                await chargerPA(pagePA);
                await chargerOptionsHierarchie();
                await chargerOrganigramme().catch(() => {});
            } catch (err) { toast(err.message, 'error'); }
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
            const btnDel = document.getElementById('btnSupprimerPE');
            if (btnDel) btnDel.hidden = true;
            openModal('modalPE');
        });
        document.getElementById('btnSupprimerPE')?.addEventListener('click', async () => {
            const id = document.getElementById('peId')?.value;
            if (!id || !confirm('Supprimer cette province éducationnelle ?')) return;
            try {
                await api(`${API}/provinces-educationnelles/${id}/`, { method: 'DELETE' });
                toast('Province éducationnelle supprimée.', 'success');
                closeModal('modalPE');
                await chargerPE(pagePE);
                await chargerOptionsHierarchie();
                await chargerOrganigramme().catch(() => {});
            } catch (err) { toast(err.message, 'error'); }
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
            const btnDel = document.getElementById('btnSupprimerAntenne');
            if (btnDel) btnDel.hidden = true;
            openModal('modalAntenne');
        });
        document.getElementById('btnSupprimerAntenne')?.addEventListener('click', async () => {
            const id = document.getElementById('antenneId')?.value;
            if (!id || !confirm('Supprimer cette antenne ?')) return;
            try {
                await api(`${API}/antennes/${id}/`, { method: 'DELETE' });
                toast('Antenne supprimée.', 'success');
                closeModal('modalAntenne');
                await chargerAntennes(pageAntennes);
                await chargerOrganigramme().catch(() => {});
            } catch (err) { toast(err.message, 'error'); }
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

    /* ---------- Utilisateurs ---------- */
    let pageUtilisateurs = 1;
    let cacheUtilisateurs = [];
    let cacheUserPA = [];
    let cacheUserPE = [];
    let cacheUserAntennes = [];

    let cacheUserEcoles = [];

    async function remplirSelectClasses(ecoleId, selectId, selectedId = '', { sectionId = '', optionId = '' } = {}) {
        const sel = document.getElementById(selectId);
        if (!sel) return;
        const current = selectedId || sel.value || '';
        sel.innerHTML = `<option value="">— Sélectionner une classe —</option>`;
        if (!ecoleId) return;
        try {
            let url = `${API}/classes/?ecole=${ecoleId}&actif=1&page_size=200&ordering=nom`;
            if (sectionId) url += `&section=${sectionId}`;
            if (optionId) url += `&option=${optionId}`;
            const data = await api(url);
            const rows = data.results || data;
            sel.innerHTML = `<option value="">— Sélectionner une classe —</option>${
                rows.map((c) => {
                    const label = sectionId
                        ? `${escapeHtml(c.nom)}${c.code ? ` (${escapeHtml(c.code)})` : ''}`
                        : `${escapeHtml([c.section_nom, c.option_nom, c.nom].filter(Boolean).join(' · '))}`;
                    return `<option value="${c.id}">${label}</option>`;
                }).join('')
            }`;
            if (current) sel.value = String(current);
        } catch (err) {
            toast(err.message || 'Impossible de charger les classes.', 'error');
        }
    }

    async function syncScolariteCascade(ecoleId, {
        sectionSelectId = 'selectSectionEleve',
        optionSelectId = 'selectOptionEleve',
        classeSelectId = 'selectClasseEleve',
        sectionId = '',
        optionId = '',
        classeId = '',
        from = 'ecole',
    } = {}) {
        const selSec = document.getElementById(sectionSelectId);
        const selOpt = document.getElementById(optionSelectId);
        const selCla = document.getElementById(classeSelectId);
        if (!ecoleId) {
            if (selSec) selSec.innerHTML = '<option value="">— Choisir l’école —</option>';
            if (selOpt) selOpt.innerHTML = '<option value="">— Choisir la section —</option>';
            if (selCla) selCla.innerHTML = '<option value="">— Sélectionner une classe —</option>';
            return;
        }
        // Écoles crèche / maternelle : garantir sections EPSP préscolaires
        if (from === 'ecole') {
            try {
                const eco = await api(`${API}/ecoles/${ecoleId}/?leger=1`);
                if (eco.niveau === 'creche' || eco.niveau === 'maternelle') {
                    await api(`${API}/ecoles/${ecoleId}/assurer-structure-niveau/`, {
                        method: 'POST',
                        body: JSON.stringify({}),
                    });
                }
            } catch (_) { /* non bloquant */ }
            await chargerSectionsEcole(ecoleId, selSec, sectionId);
        }
        const secVal = from === 'ecole'
            ? (sectionId || selSec?.value || '')
            : (selSec?.value || sectionId || '');
        if (from === 'ecole' || from === 'section') {
            await chargerOptionsEcole(ecoleId, secVal, selOpt, from === 'section' ? '' : optionId);
        }
        const optVal = from === 'option'
            ? (selOpt?.value || optionId || '')
            : (from === 'section' ? (selOpt?.value || '') : (optionId || selOpt?.value || ''));
        if (!secVal) {
            if (selCla) selCla.innerHTML = '<option value="">— Sélectionner une classe —</option>';
            return;
        }
        await remplirSelectClasses(ecoleId, classeSelectId, from === 'ecole' ? classeId : '', {
            sectionId: secVal,
            optionId: optVal,
        });
    }

    async function syncScolariteEleveCascade(ecoleId, opts = {}) {
        return syncScolariteCascade(ecoleId, {
            sectionSelectId: 'selectSectionEleve',
            optionSelectId: 'selectOptionEleve',
            classeSelectId: 'selectClasseEleve',
            ...opts,
        });
    }

    async function chargerOptionsUtilisateur() {
        const [pas, pes, ants, ecoles] = await Promise.all([
            api(`${API}/provinces-administratives/?page_size=500`),
            api(`${API}/provinces-educationnelles/?page_size=500`),
            api(`${API}/antennes/?page_size=500`),
            api(`${API}/ecoles/?page_size=500`),
        ]);
        cacheUserPA = pas.results || pas;
        cacheUserPE = pes.results || pes;
        cacheUserAntennes = ants.results || ants;
        cacheUserEcoles = ecoles.results || ecoles;
        syncSelectsUtilisateur();
        syncRoleUtilisateurUI();
    }

    function syncRoleUtilisateurUI() {
        const role = document.getElementById('selectRoleUtilisateur')?.value || '';
        const school = role === 'admin_ecole';
        const req = document.getElementById('reqEcoleUtilisateur');
        const selEcole = document.getElementById('selectUserEcole');
        if (req) req.hidden = !school;
        if (selEcole) selEcole.required = school;
    }

    function syncSelectsUtilisateur(selected = {}) {
        const selPA = document.getElementById('selectUserPA');
        const selPE = document.getElementById('selectUserPE');
        const selAnt = document.getElementById('selectUserAntenne');
        const selEcole = document.getElementById('selectUserEcole');
        if (!selPA || !selPE || !selAnt) return;

        const paId = selected.province_administrative || selPA.value || '';
        const peId = selected.province_educationnelle || selPE.value || '';
        const antId = selected.antenne || selAnt.value || '';
        const ecoleId = selected.ecole || selEcole?.value || '';

        if (selEcole) {
            selEcole.innerHTML = `<option value="">— Aucune —</option>${
                cacheUserEcoles.map((e) =>
                    `<option value="${e.id}">${escapeHtml(e.nom)} (${escapeHtml(e.code)})</option>`
                ).join('')
            }`;
            selEcole.value = ecoleId ? String(ecoleId) : '';
        }

        selPA.innerHTML = `<option value="">— Aucune —</option>${
            cacheUserPA.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)} (${escapeHtml(p.code)})</option>`).join('')
        }`;
        selPA.value = paId ? String(paId) : '';

        const peFiltered = selPA.value
            ? cacheUserPE.filter((p) => String(p.province_administrative) === String(selPA.value))
            : cacheUserPE;
        selPE.innerHTML = `<option value="">— Aucune —</option>${
            peFiltered.map((p) => `<option value="${p.id}">${escapeHtml(p.nom)} (${escapeHtml(p.code)})</option>`).join('')
        }`;
        selPE.value = peId && peFiltered.some((p) => String(p.id) === String(peId)) ? String(peId) : '';

        const antFiltered = selPE.value
            ? cacheUserAntennes.filter((a) => String(a.province_educationnelle) === String(selPE.value))
            : (selPA.value
                ? cacheUserAntennes.filter((a) => String(a.province_administrative_id) === String(selPA.value))
                : cacheUserAntennes);
        selAnt.innerHTML = `<option value="">— Aucune —</option>${
            antFiltered.map((a) => `<option value="${a.id}">${escapeHtml(a.nom)} (${escapeHtml(a.code)})</option>`).join('')
        }`;
        selAnt.value = antId && antFiltered.some((a) => String(a.id) === String(antId)) ? String(antId) : '';
        syncRoleUtilisateurUI();
    }

    function rattachementLabel(u) {
        if (u.ecole_nom) {
            return u.ecole_code ? `${u.ecole_nom} (${u.ecole_code})` : u.ecole_nom;
        }
        const parts = [
            u.antenne_nom,
            u.province_educationnelle_nom,
            u.province_administrative_nom,
        ].filter(Boolean);
        return parts.length ? parts.join(' · ') : '—';
    }

    async function chargerUtilisateurs(page = 1) {
        pageUtilisateurs = page;
        const q = document.getElementById('searchUtilisateurs')?.value || '';
        const role = document.getElementById('filtreRoleUtilisateurs')?.value || '';
        let url = `${API}/utilisateurs/?page=${page}`;
        if (q) url += `&q=${encodeURIComponent(q)}`;
        if (role) url += `&role=${encodeURIComponent(role)}`;
        const data = await api(url);
        const rows = data.results || data;
        cacheUtilisateurs = rows;
        setCount('countUtilisateurs', data.count ?? rows.length);
        const tbody = document.querySelector('#tableUtilisateurs tbody');
        tbody.innerHTML = rows.length ? rows.map((u) => {
            const nom = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username;
            return `
            <tr>
                <td data-label="Utilisateur">
                    <div class="entity-cell">
                        <div class="entity-avatar">${escapeHtml(initials(nom))}</div>
                        <div class="entity-meta">
                            <strong title="${escapeHtml(nom)}">${escapeHtml(nom)}</strong>
                            <span>${escapeHtml(u.email || u.telephone || 'Contact non renseigné')}</span>
                        </div>
                    </div>
                </td>
                <td data-label="Identifiant"><span class="code-chip">${escapeHtml(u.username)}</span></td>
                <td data-label="Rôle">${escapeHtml(u.role_display || u.role)}</td>
                <td data-label="Rattachement">
                    <div class="entity-meta">
                        <strong title="${escapeHtml(rattachementLabel(u))}">${escapeHtml(rattachementLabel(u))}</strong>
                    </div>
                </td>
                <td data-label="Statut"><span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">${u.is_active ? 'Actif' : 'Inactif'}</span></td>
                <td data-label="Actions"><div class="actions-inline">
                    <a class="btn btn-secondary btn-sm" href="/utilisateurs/${u.id}/">${ico('eye')}Détail</a>
                    <button type="button" class="btn btn-ghost btn-sm" data-edit-user="${u.id}">${ico('edit')}Modifier</button>
                </div></td>
            </tr>`;
        }).join('') : emptyRow(6, 'Aucun utilisateur trouvé', 'Ajoutez un compte ou affinez la recherche.');

        tbody.querySelectorAll('[data-edit-user]').forEach((btn) => {
            btn.addEventListener('click', () => ouvrirModalUtilisateur(cacheUtilisateurs.find((x) => String(x.id) === String(btn.dataset.editUser))));
        });
        renderPagination(
            'paginationUtilisateurs',
            pageUtilisateurs,
            data.count ? Math.ceil(data.count / 20) : 1,
            chargerUtilisateurs,
        );
    }

    function setModePasswordUtilisateur(edition) {
        const input = document.getElementById('inputPasswordUtilisateur');
        const label = document.getElementById('labelPasswordUtilisateur');
        const hint = document.getElementById('hintPasswordUtilisateur');
        if (!input || !label || !hint) return;
        if (edition) {
            input.required = false;
            label.innerHTML = 'Nouveau mot de passe';
            hint.textContent = 'Laisser vide pour conserver le mot de passe actuel.';
        } else {
            input.required = true;
            label.innerHTML = 'Mot de passe <span class="req">*</span>';
            hint.textContent = 'Obligatoire à la création.';
        }
    }

    async function ouvrirModalUtilisateur(user = null) {
        const form = document.getElementById('formUtilisateur');
        const titre = document.getElementById('titreModalUtilisateur');
        if (!form || !titre) return;
        form.reset();
        document.getElementById('utilisateurId').value = user?.id || '';
        setModePasswordUtilisateur(Boolean(user));
        const btnDel = document.getElementById('btnSupprimerUtilisateur');
        if (btnDel) {
            // Pas de suppression depuis la fiche détail (uniquement via le modal liste si besoin)
            const surDetail = Boolean(document.getElementById('utilisateurDetail'));
            btnDel.hidden = surDetail || !user?.id;
        }
        if (user) {
            titre.textContent = "Modifier l'utilisateur";
            form.username.value = user.username || '';
            form.email.value = user.email || '';
            form.first_name.value = user.first_name || '';
            form.last_name.value = user.last_name || '';
            form.telephone.value = user.telephone || '';
            form.role.value = user.role || 'agent_antenne';
            document.getElementById('utilisateurActif').checked = user.is_active !== false;
            syncSelectsUtilisateur({
                province_administrative: user.province_administrative || '',
                province_educationnelle: user.province_educationnelle || '',
                antenne: user.antenne || '',
                ecole: user.ecole || '',
            });
        } else {
            titre.textContent = 'Nouvel utilisateur';
            document.getElementById('utilisateurActif').checked = true;
            syncSelectsUtilisateur({});
        }
        syncRoleUtilisateurUI();
        openModal('modalUtilisateur');
    }

    /* ---------- Monitoring utilisateurs connectés (admin) ---------- */
    let cacheMonitoringSessions = [];
    let monitoringTimer = null;

    function formatDateTimeFr(value) {
        if (!value) return '—';
        const d = new Date(value);
        if (Number.isNaN(d.getTime())) return formatDateFr(value) || '—';
        const jj = String(d.getDate()).padStart(2, '0');
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const aaaa = d.getFullYear();
        const hh = String(d.getHours()).padStart(2, '0');
        const mi = String(d.getMinutes()).padStart(2, '0');
        return `${jj}-${mm}-${aaaa} ${hh}:${mi}`;
    }

    function filtrerMonitoringSessions(rows) {
        const q = (document.getElementById('searchMonitoring')?.value || '').trim().toLowerCase();
        const statut = document.getElementById('filtreStatutMonitoring')?.value || '';
        return rows.filter((s) => {
            if (statut === 'en_ligne' && !s.en_ligne) return false;
            if (statut === 'session' && s.en_ligne) return false;
            if (!q) return true;
            const blob = [
                s.nom_complet, s.username, s.role_display, s.rattachement, s.ip,
                s.geo_label, s.email,
            ].join(' ').toLowerCase();
            return blob.includes(q);
        });
    }

    function celluleGeoMonitoring(s) {
        const label = s.geo_label || s.geo?.label || '—';
        const lat = s.geo_lat ?? s.geo?.lat;
        const lon = s.geo_lon ?? s.geo?.lon;
        const source = s.geo_source || s.geo?.source || '';
        const badge = source === 'browser'
            ? '<span class="badge badge-info">GPS</span>'
            : (source === 'ip'
                ? '<span class="badge badge-neutral">IP</span>'
                : (source === 'local' ? '<span class="badge badge-warning">Local</span>' : ''));
        let maps = '';
        if (lat != null && lon != null && !Number.isNaN(Number(lat)) && !Number.isNaN(Number(lon))) {
            maps = ` <a class="btn btn-ghost btn-sm" href="/monitoring/utilisateurs-connectes/carte/" title="Voir sur la carte interne">Carte</a>`;
        }
        return `<div class="entity-meta">
            <strong title="${escapeHtml(label)}">${escapeHtml(label)}</strong>
            <span>${badge}${maps}</span>
        </div>`;
    }

    function renderMonitoringSessions() {
        const rows = filtrerMonitoringSessions(cacheMonitoringSessions);
        const tbody = document.querySelector('#tableMonitoring tbody');
        if (!tbody) return;
        setCount('countMonitoring', rows.length);
        tbody.innerHTML = rows.length ? rows.map((s) => {
            const statut = s.en_ligne
                ? '<span class="badge badge-success">En ligne</span>'
                : '<span class="badge badge-neutral">Session active</span>';
            const moi = s.est_session_courante
                ? ' <span class="badge badge-info">Vous</span>'
                : '';
            const actions = s.est_session_courante
                ? '<span class="muted">—</span>'
                : `<button type="button" class="btn btn-danger btn-sm" data-kick-session="${escapeHtml(s.session_key)}">${ico('trash')}Déconnecter</button>`;
            return `
            <tr>
                <td data-label="Utilisateur">
                    <div class="entity-meta">
                        <strong>${escapeHtml(s.nom_complet)}${moi}</strong>
                        <span>${escapeHtml(s.username)}</span>
                    </div>
                </td>
                <td data-label="Rôle"><span class="code-chip">${escapeHtml(s.role_display || s.role)}</span></td>
                <td data-label="Rattachement">${escapeHtml(s.rattachement || '—')}</td>
                <td data-label="IP"><span class="code-chip">${escapeHtml(s.ip || '—')}</span></td>
                <td data-label="Géolocalisation">${celluleGeoMonitoring(s)}</td>
                <td data-label="Activité">${escapeHtml(formatDateTimeFr(s.presence_at || s.last_login))}</td>
                <td data-label="Expiration">${escapeHtml(formatDateTimeFr(s.expire_date))}</td>
                <td data-label="Statut">${statut}</td>
                <td data-label="Actions"><div class="actions-inline">${actions}</div></td>
            </tr>`;
        }).join('') : emptyRow(
            9,
            'Aucune session active',
            'Aucun utilisateur connecté pour le moment (ou filtre trop strict).',
        );
    }

    async function chargerMonitoringSessions() {
        const data = await api(`${API}/monitoring/sessions/`);
        cacheMonitoringSessions = data.results || [];
        const resume = data.resume || {};
        const elS = document.getElementById('monSessions');
        const elU = document.getElementById('monUniques');
        const elL = document.getElementById('monEnLigne');
        const elM = document.getElementById('monMaj');
        const elR = document.getElementById('monParRole');
        if (elS) elS.textContent = String(resume.sessions ?? cacheMonitoringSessions.length);
        if (elU) elU.textContent = String(resume.utilisateurs_uniques ?? '—');
        if (elL) elL.textContent = String(resume.en_ligne ?? '—');
        if (elM) elM.textContent = formatDateTimeFr(new Date().toISOString());
        if (elR) {
            const parts = Object.entries(resume.par_role || {}).map(([k, v]) => `${k} : ${v}`);
            elR.textContent = parts.length ? `Répartition : ${parts.join(' · ')}` : '';
        }
        renderMonitoringSessions();
        await chargerAccesExterieur().catch(() => {});
    }

    async function chargerAccesExterieur() {
        const tbody = document.querySelector('#tableAccesExterieur tbody');
        if (!tbody) return;
        const data = await api(`${API}/monitoring/acces-exterieur/`);
        const rows = data.results || [];
        setCount('countAccesExterieur', data.en_attente ?? rows.filter((r) => r.statut === 'en_attente').length);
        tbody.innerHTML = rows.length ? rows.map((r) => {
            const ipLabel = r.toutes_ip ? 'Toutes IP' : (r.adresse_ip || '—');
            const badge = r.statut === 'en_attente'
                ? '<span class="badge badge-warning">En attente</span>'
                : (r.statut === 'autorise'
                    ? '<span class="badge badge-success">Autorisé</span>'
                    : `<span class="badge badge-danger">${escapeHtml(r.statut_display || r.statut)}</span>`);
            let actions = '—';
            if (r.statut === 'en_attente') {
                actions = `
                    <button type="button" class="btn btn-primary btn-sm" data-acces-action="autoriser" data-acces-id="${r.id}">Autoriser 7j</button>
                    <button type="button" class="btn btn-secondary btn-sm" data-acces-action="autoriser-toutes" data-acces-id="${r.id}">Autoriser (toutes IP)</button>
                    <button type="button" class="btn btn-danger btn-sm" data-acces-action="refuser" data-acces-id="${r.id}">Refuser</button>`;
            } else if (r.statut === 'autorise' && r.est_valide) {
                actions = `<button type="button" class="btn btn-danger btn-sm" data-acces-action="revoquer" data-acces-id="${r.id}">Révoquer</button>`;
            }
            return `<tr>
                <td data-label="Utilisateur">
                    <div class="entity-meta">
                        <strong>${escapeHtml(r.nom_complet)}</strong>
                        <span>${escapeHtml(r.username)} · ${escapeHtml(r.role_display || '')}</span>
                    </div>
                </td>
                <td data-label="IP">
                    <div class="entity-meta">
                        <strong>${escapeHtml(ipLabel)}</strong>
                        <span>${escapeHtml(r.geo_label || '—')}${r.country_code ? ` (${escapeHtml(r.country_code)})` : ''}</span>
                    </div>
                </td>
                <td data-label="Demande">${escapeHtml(formatDateTimeFr(r.date_demande))}</td>
                <td data-label="Statut">${badge}</td>
                <td data-label="Expiration">${escapeHtml(formatDateTimeFr(r.date_expiration))}</td>
                <td data-label="Actions"><div class="actions-inline">${actions}</div></td>
            </tr>`;
        }).join('') : emptyRow(
            6,
            'Aucune demande hors RDC',
            'Les tentatives de connexion depuis l’étranger apparaîtront ici.',
        );
    }

    async function decideAccesExterieur(id, action) {
        const payload = { action };
        if (action === 'autoriser') {
            payload.jours = 7;
            payload.toutes_ip = false;
        } else if (action === 'autoriser-toutes') {
            payload.action = 'autoriser';
            payload.jours = 7;
            payload.toutes_ip = true;
        }
        await api(`${API}/monitoring/acces-exterieur/${id}/`, {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    function planifierAutoRefreshMonitoring() {
        if (monitoringTimer) {
            clearInterval(monitoringTimer);
            monitoringTimer = null;
        }
        const auto = document.getElementById('autoRefreshMonitoring')?.checked;
        if (!auto) return;
        monitoringTimer = setInterval(() => {
            chargerMonitoringSessions().catch(() => {});
        }, 30000);
    }

    function initMonitoringUtilisateurs() {
        chargerMonitoringSessions().catch((e) => toast(e.message, 'error'));
        planifierAutoRefreshMonitoring();

        document.getElementById('btnRefreshMonitoring')?.addEventListener('click', () => {
            chargerMonitoringSessions().catch((e) => toast(e.message, 'error'));
        });
        document.getElementById('searchMonitoring')?.addEventListener('input', () => renderMonitoringSessions());
        document.getElementById('filtreStatutMonitoring')?.addEventListener('change', () => renderMonitoringSessions());
        document.getElementById('autoRefreshMonitoring')?.addEventListener('change', planifierAutoRefreshMonitoring);

        document.getElementById('tableMonitoring')?.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-kick-session]');
            if (!btn) return;
            const key = btn.getAttribute('data-kick-session');
            if (!key || !confirm('Forcer la déconnexion de cette session ?')) return;
            try {
                await api(`${API}/monitoring/sessions/${encodeURIComponent(key)}/`, { method: 'DELETE' });
                toast('Session déconnectée.', 'success');
                await chargerMonitoringSessions();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('tableAccesExterieur')?.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-acces-action]');
            if (!btn) return;
            const id = btn.getAttribute('data-acces-id');
            const action = btn.getAttribute('data-acces-action');
            if (!id || !action) return;
            const labels = {
                autoriser: 'Autoriser cet accès hors RDC pour 7 jours ?',
                'autoriser-toutes': 'Autoriser cet utilisateur hors RDC (toutes IP) pour 7 jours ?',
                refuser: 'Refuser cette demande ?',
                revoquer: 'Révoquer cette autorisation ?',
            };
            if (!confirm(labels[action] || 'Confirmer ?')) return;
            try {
                await decideAccesExterieur(id, action);
                toast('Décision enregistrée.', 'success');
                await chargerAccesExterieur();
            } catch (err) {
                toast(err.message, 'error');
            }
        });
    }

    /* ---------- Carte monitoring (Leaflet, page interne) ---------- */
    let monitoringCarteMap = null;
    let monitoringCarteLayer = null;
    let monitoringCarteTimer = null;
    let cacheMonitoringCarte = [];

    // Emprise RDC (sud-ouest → nord-est)
    const RDC_BOUNDS = [
        [-13.46, 12.20],
        [5.39, 31.31],
    ];

    // Contour simplifié de la RDC [lat, lon] — pour masquer le reste du monde
    const RDC_CONTOUR = [
        [-4.40, 12.45], [-5.90, 12.35], [-8.00, 13.05], [-10.90, 13.40],
        [-13.00, 16.70], [-13.45, 22.80], [-12.20, 25.10], [-11.70, 28.40],
        [-10.30, 28.90], [-8.20, 30.60], [-5.90, 29.50], [-3.40, 29.20],
        [-1.20, 30.20], [0.90, 30.00], [2.20, 31.20], [4.30, 30.00],
        [5.30, 27.40], [4.60, 24.90], [5.00, 19.80], [3.60, 18.60],
        [3.40, 16.20], [1.70, 15.90], [-0.20, 17.60], [-1.70, 17.30],
        [-2.90, 16.20], [-3.40, 13.10], [-4.40, 12.45],
    ];

    function centrerCarteRDC(map, { animate = false } = {}) {
        if (!map) return;
        map.fitBounds(RDC_BOUNDS, { padding: [18, 18], maxZoom: 6, animate });
    }

    function restreindreVueRDC(map) {
        if (!map) return;
        const bounds = L.latLngBounds(RDC_BOUNDS).pad(0.04);
        map.setMaxBounds(bounds);
        map.options.maxBoundsViscosity = 1.0;
        // Empêche le dézoom mondial : zoom min = niveau « toute la RDC »
        const z = map.getBoundsZoom(bounds, false);
        map.setMinZoom(Math.max(5, Math.floor(z)));
    }

    function masquerHorsRDC(map) {
        // Anneau monde + trou RDC → seul le territoire RDC reste lisible
        const monde = [
            [-85, -180], [-85, 180], [85, 180], [85, -180],
        ];
        L.polygon([monde, RDC_CONTOUR], {
            stroke: false,
            fillColor: '#061a2e',
            fillOpacity: 0.78,
            interactive: false,
        }).addTo(map);
        L.polyline(RDC_CONTOUR, {
            color: '#f0c400',
            weight: 2,
            opacity: 0.95,
            interactive: false,
        }).addTo(map);
    }

    function sessionsAvecCoords(rows) {
        return (rows || []).filter((s) => {
            const lat = Number(s.geo_lat ?? s.geo?.lat);
            const lon = Number(s.geo_lon ?? s.geo?.lon);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
            // Uniquement les points situés en RDC (emprise)
            return lat >= -13.5 && lat <= 5.5 && lon >= 12.1 && lon <= 31.4;
        });
    }

    function popupHtmlMonitoring(s) {
        const statut = s.en_ligne ? 'En ligne' : 'Session active';
        return `<strong>${escapeHtml(s.nom_complet || s.username)}</strong><br>`
            + `${escapeHtml(s.role_display || s.role || '')}<br>`
            + `${escapeHtml(s.geo_label || '—')}<br>`
            + `IP ${escapeHtml(s.ip || '—')} · ${escapeHtml(statut)}`;
    }

    function renderMonitoringCarte() {
        const mapEl = document.getElementById('monitoringMap');
        const legend = document.getElementById('monitoringMapLegend');
        const hint = document.getElementById('monitoringMapHint');
        if (!mapEl || typeof L === 'undefined') return;

        if (!monitoringCarteMap) {
            monitoringCarteMap = L.map(mapEl, {
                scrollWheelZoom: true,
                worldCopyJump: false,
                maxBoundsViscosity: 1.0,
                zoomControl: true,
            });
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 16,
                attribution: '&copy; OpenStreetMap — vue RDC',
            }).addTo(monitoringCarteMap);
            masquerHorsRDC(monitoringCarteMap);
            monitoringCarteLayer = L.layerGroup().addTo(monitoringCarteMap);
            centrerCarteRDC(monitoringCarteMap);
            restreindreVueRDC(monitoringCarteMap);
        }

        const localises = sessionsAvecCoords(cacheMonitoringCarte);
        const horsRdc = (cacheMonitoringCarte || []).filter((s) => {
            const lat = Number(s.geo_lat ?? s.geo?.lat);
            const lon = Number(s.geo_lon ?? s.geo?.lon);
            return Number.isFinite(lat) && Number.isFinite(lon)
                && !(lat >= -13.5 && lat <= 5.5 && lon >= 12.1 && lon <= 31.4);
        }).length;
        const sansCoords = cacheMonitoringCarte.length - localises.length - horsRdc;
        setCount('countMonitoringCarte', localises.length);
        if (hint) {
            let txt = localises.length
                ? `${localises.length} position(s) en RDC`
                : 'Aucune position en RDC — carte limitée au territoire national.';
            if (sansCoords) txt += ` · ${sansCoords} sans coordonnées`;
            if (horsRdc) txt += ` · ${horsRdc} hors RDC (masquée)`;
            hint.textContent = txt;
        }

        monitoringCarteLayer.clearLayers();
        const bounds = [];
        if (legend) legend.innerHTML = '';

        localises.forEach((s) => {
            const lat = Number(s.geo_lat ?? s.geo?.lat);
            const lon = Number(s.geo_lon ?? s.geo?.lon);
            const marker = L.circleMarker([lat, lon], {
                radius: 8,
                color: s.en_ligne ? '#0a7a32' : '#007fff',
                fillColor: s.en_ligne ? '#1fbf57' : '#4da3ff',
                fillOpacity: 0.9,
                weight: 2,
            }).bindPopup(popupHtmlMonitoring(s));
            marker.addTo(monitoringCarteLayer);
            bounds.push([lat, lon]);

            if (legend) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'monitoring-map-item';
                btn.innerHTML = `<strong>${escapeHtml(s.nom_complet || s.username)}</strong>`
                    + `<span>${escapeHtml(s.role_display || '')} · ${escapeHtml(s.geo_label || '')}</span>`
                    + `<span>${s.en_ligne ? 'En ligne' : 'Session active'} · ${escapeHtml(s.ip || '—')}</span>`;
                btn.addEventListener('click', () => {
                    legend.querySelectorAll('.monitoring-map-item').forEach((el) => el.classList.remove('active'));
                    btn.classList.add('active');
                    monitoringCarteMap.setView([lat, lon], Math.max(monitoringCarteMap.getZoom(), 10));
                    marker.openPopup();
                });
                legend.appendChild(btn);
            }
        });

        if (bounds.length === 1) {
            monitoringCarteMap.setView(bounds[0], 10);
        } else if (bounds.length > 1) {
            monitoringCarteMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
        } else {
            centrerCarteRDC(monitoringCarteMap);
        }
        setTimeout(() => {
            monitoringCarteMap.invalidateSize();
            restreindreVueRDC(monitoringCarteMap);
        }, 80);
    }

    async function chargerMonitoringCarte() {
        const data = await api(`${API}/monitoring/sessions/`);
        cacheMonitoringCarte = data.results || [];
        renderMonitoringCarte();
    }

    function planifierAutoRefreshMonitoringCarte() {
        if (monitoringCarteTimer) {
            clearInterval(monitoringCarteTimer);
            monitoringCarteTimer = null;
        }
        const auto = document.getElementById('autoRefreshMonitoringCarte')?.checked;
        if (!auto) return;
        monitoringCarteTimer = setInterval(() => {
            chargerMonitoringCarte().catch(() => {});
        }, 30000);
    }

    function initMonitoringCarte() {
        if (typeof L === 'undefined') {
            toast('Impossible de charger la carte.', 'error');
            return;
        }
        chargerMonitoringCarte().catch((e) => toast(e.message, 'error'));
        planifierAutoRefreshMonitoringCarte();
        document.getElementById('btnRefreshMonitoringCarte')?.addEventListener('click', () => {
            chargerMonitoringCarte().catch((e) => toast(e.message, 'error'));
        });
        document.getElementById('btnCentrerRDC')?.addEventListener('click', () => {
            centrerCarteRDC(monitoringCarteMap, { animate: true });
        });
        document.getElementById('autoRefreshMonitoringCarte')?.addEventListener('change', planifierAutoRefreshMonitoringCarte);
        window.addEventListener('resize', () => {
            if (monitoringCarteMap) monitoringCarteMap.invalidateSize();
        });
    }

    function initUtilisateurs() {
        bindModalClosers();
        chargerOptionsUtilisateur().catch((e) => toast(e.message, 'error'));
        chargerUtilisateurs(1).catch((e) => toast(e.message, 'error'));

        document.getElementById('btnSearchUtilisateurs')?.addEventListener('click', () => chargerUtilisateurs(1));
        document.getElementById('filtreRoleUtilisateurs')?.addEventListener('change', () => chargerUtilisateurs(1));
        document.getElementById('searchUtilisateurs')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerUtilisateurs(1);
        });
        document.getElementById('btnNouvelUtilisateur')?.addEventListener('click', () => ouvrirModalUtilisateur());
        document.getElementById('btnSupprimerUtilisateur')?.addEventListener('click', async () => {
            const id = document.getElementById('utilisateurId')?.value;
            if (!id || !confirm('Supprimer cet utilisateur ?')) return;
            try {
                await api(`${API}/utilisateurs/${id}/`, { method: 'DELETE' });
                toast('Utilisateur supprimé.', 'success');
                closeModal('modalUtilisateur');
                await chargerUtilisateurs(pageUtilisateurs);
            } catch (err) { toast(err.message, 'error'); }
        });

        document.getElementById('selectUserPA')?.addEventListener('change', () => syncSelectsUtilisateur());
        document.getElementById('selectUserPE')?.addEventListener('change', () => syncSelectsUtilisateur());
        document.getElementById('selectRoleUtilisateur')?.addEventListener('change', () => syncRoleUtilisateurUI());
        document.getElementById('selectUserEcole')?.addEventListener('change', () => syncRoleUtilisateurUI());

        document.getElementById('formUtilisateur')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const id = document.getElementById('utilisateurId').value;
            const role = form.role.value;
            if (role === 'enseignant') {
                toast('Les enseignants se créent depuis la fiche de l’école.', 'warning');
                return;
            }
            if (role === 'admin_ecole' && !form.ecole?.value) {
                toast("Sélectionnez l'école pour un administratif école.", 'warning');
                return;
            }
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            const password = (form.password.value || '').trim();
            if (!id && !password) {
                toast('Le mot de passe est obligatoire à la création.', 'warning');
                return;
            }
            const payload = {
                username: form.username.value.trim(),
                email: form.email.value.trim(),
                first_name: form.first_name.value.trim(),
                last_name: form.last_name.value.trim(),
                telephone: form.telephone.value.trim(),
                role,
                is_active: document.getElementById('utilisateurActif')?.checked !== false,
                province_administrative: form.province_administrative.value || null,
                province_educationnelle: form.province_educationnelle.value || null,
                antenne: form.antenne.value || null,
                ecole: role === 'admin_ecole' ? Number(form.ecole.value) : null,
                classe: null,
            };
            if (password) payload.password = password;

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                if (id) {
                    await api(`${API}/utilisateurs/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                    toast('Utilisateur mis à jour.', 'success');
                } else {
                    await api(`${API}/utilisateurs/`, { method: 'POST', body: JSON.stringify(payload) });
                    toast('Utilisateur créé.', 'success');
                }
                closeModal('modalUtilisateur');
                form.reset();
                if (document.getElementById('utilisateurDetail')) {
                    await chargerUtilisateurDetail();
                } else {
                    await chargerUtilisateurs(1);
                }
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });
    }

    let cacheUtilisateurDetail = null;

    function perimetreLibelle(u) {
        if (!u) return '—';
        if (u.role === 'admin' || u.role === 'agent_national') {
            return 'Accès national / plateforme';
        }
        if (u.role === 'agent_province_admin') {
            return u.province_administrative_nom
                ? `Province administrative : ${u.province_administrative_nom}`
                : 'Périmètre province administrative';
        }
        if (u.role === 'agent_provincial') {
            return u.province_educationnelle_nom
                ? `Province éducationnelle : ${u.province_educationnelle_nom}`
                : 'Périmètre provincial';
        }
        if (u.role === 'agent_antenne') {
            return u.antenne_nom ? `Antenne : ${u.antenne_nom}` : 'Périmètre antenne';
        }
        if (u.role === 'admin_ecole') {
            return u.ecole_nom
                ? `École : ${u.ecole_nom}${u.ecole_code ? ` (${u.ecole_code})` : ''}`
                : 'Administratif école';
        }
        if (u.role === 'enseignant') {
            const parts = [u.ecole_nom, u.classe_nom].filter(Boolean);
            return parts.length ? parts.join(' · ') : 'Enseignant';
        }
        return rattachementLabel(u);
    }

    async function chargerUtilisateurDetail() {
        const root = document.getElementById('utilisateurDetail');
        const id = root?.dataset.utilisateurId;
        if (!id) return null;
        const u = await api(`${API}/utilisateurs/${id}/`);
        cacheUtilisateurDetail = u;

        const nom = [u.first_name, u.last_name].filter(Boolean).join(' ').trim() || u.username;
        const photoEl = document.getElementById('detailUserPhoto');
        const fallback = document.getElementById('detailUserPhotoFallback');
        const badgePhoto = document.getElementById('detailUserBadgePhoto');
        if (photoEl && fallback) {
            if (u.photo_url) {
                photoEl.src = u.photo_url;
                photoEl.hidden = false;
                fallback.hidden = true;
                if (badgePhoto) {
                    badgePhoto.textContent = 'Photo';
                    badgePhoto.className = 'badge badge-success';
                }
            } else {
                photoEl.hidden = true;
                photoEl.removeAttribute('src');
                fallback.hidden = false;
                fallback.textContent = initials(nom);
                if (badgePhoto) {
                    badgePhoto.textContent = 'Sans photo';
                    badgePhoto.className = 'badge';
                }
            }
        }

        const setText = (idEl, value) => {
            const el = document.getElementById(idEl);
            if (el) el.textContent = value || '—';
        };
        setText('detailUserUsername', `@${u.username}`);
        setText('detailUserNom', nom);
        setText('detailUserSousTitre', u.email || u.telephone || 'Contact non renseigné');
        setText('detailUserRole', u.role_display || u.role);

        const statut = document.getElementById('detailUserStatut');
        if (statut) {
            statut.textContent = u.is_active ? 'Actif' : 'Inactif';
            statut.className = `badge ${u.is_active ? 'badge-success' : 'badge-danger'}`;
        }

        fillDetailList('blocUserIdentite', [
            ['Identifiant', u.username],
            ['Prénom', u.first_name || '—'],
            ['Nom', u.last_name || '—'],
            ['E-mail', u.email || '—'],
            ['Téléphone', u.telephone || '—'],
        ]);
        fillDetailList('blocUserCompte', [
            ['Rôle', u.role_display || u.role],
            ['Statut', u.is_active ? 'Actif' : 'Inactif'],
            ['Créé le', formatDateFr(u.date_creation) || '—'],
        ]);
        fillDetailList('blocUserRattachement', [
            ['Province administrative', u.province_administrative_nom || '—'],
            ['Province éducationnelle', u.province_educationnelle_nom || '—'],
            ['Antenne', u.antenne_nom || '—'],
            ['École', u.ecole_nom
                ? `${u.ecole_nom}${u.ecole_code ? ` · ${u.ecole_code}` : ''}`
                : '—'],
            ['Classe', u.classe_nom || '—'],
        ]);
        fillDetailList('blocUserPerimetre', [
            ['Couverture', perimetreLibelle(u)],
            ['Section', u.section_nom || '—'],
            ['Option', u.option_nom || '—'],
        ]);

        const sectionLiens = document.getElementById('sectionUserLiens');
        const blocLiens = document.getElementById('blocUserLiens');
        if (sectionLiens && blocLiens) {
            const liens = [];
            if (u.ecole) {
                liens.push(`<a class="btn btn-secondary btn-sm" href="/ecoles/${u.ecole}/">${ico('school')}Fiche école</a>`);
            }
            if (liens.length) {
                sectionLiens.hidden = false;
                blocLiens.innerHTML = liens.join('');
            } else {
                sectionLiens.hidden = true;
                blocLiens.innerHTML = '';
            }
        }
        return u;
    }

    function initUtilisateurDetail() {
        bindModalClosers();
        chargerOptionsUtilisateur().catch((e) => toast(e.message, 'error'));
        chargerUtilisateurDetail().catch((e) => toast(e.message, 'error'));

        document.getElementById('btnModifierUtilisateurDetail')?.addEventListener('click', () => {
            if (!cacheUtilisateurDetail) return;
            ouvrirModalUtilisateur(cacheUtilisateurDetail);
        });

        // Réutilise le handler de formulaire liste (même modal)
        document.getElementById('selectUserPA')?.addEventListener('change', () => syncSelectsUtilisateur());
        document.getElementById('selectUserPE')?.addEventListener('change', () => syncSelectsUtilisateur());
        document.getElementById('selectRoleUtilisateur')?.addEventListener('change', () => syncRoleUtilisateurUI());
        document.getElementById('selectUserEcole')?.addEventListener('change', () => syncRoleUtilisateurUI());
        document.getElementById('btnSupprimerUtilisateur')?.addEventListener('click', async () => {
            const id = document.getElementById('utilisateurId')?.value;
            if (!id || !confirm('Supprimer cet utilisateur ?')) return;
            try {
                await api(`${API}/utilisateurs/${id}/`, { method: 'DELETE' });
                toast('Utilisateur supprimé.', 'success');
                window.location.href = '/utilisateurs/';
            } catch (err) {
                toast(err.message, 'error');
            }
        });
        document.getElementById('formUtilisateur')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const id = document.getElementById('utilisateurId').value;
            const role = form.role.value;
            if (role === 'enseignant') {
                toast('Les enseignants se créent depuis la fiche de l’école.', 'warning');
                return;
            }
            if (role === 'admin_ecole' && !form.ecole?.value) {
                toast("Sélectionnez l'école pour un administratif école.", 'warning');
                return;
            }
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            const password = (form.password.value || '').trim();
            const payload = {
                username: form.username.value.trim(),
                email: form.email.value.trim(),
                first_name: form.first_name.value.trim(),
                last_name: form.last_name.value.trim(),
                telephone: form.telephone.value.trim(),
                role,
                is_active: document.getElementById('utilisateurActif')?.checked !== false,
                province_administrative: form.province_administrative.value || null,
                province_educationnelle: form.province_educationnelle.value || null,
                antenne: form.antenne.value || null,
                ecole: role === 'admin_ecole' ? Number(form.ecole.value) : null,
                classe: null,
            };
            if (password) payload.password = password;
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                await api(`${API}/utilisateurs/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                toast('Utilisateur mis à jour.', 'success');
                closeModal('modalUtilisateur');
                await chargerUtilisateurDetail();
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        document.getElementById('inputPhotoUserDetail')?.addEventListener('change', async (e) => {
            const file = e.target.files && e.target.files[0];
            if (!file) return;
            const input = e.target;
            const confirme = await demanderConfirmationPhoto(file, input, {
                titre: 'Changer la photo',
                sousTitre: 'Aperçu avant remplacement du profil',
                question: 'Utiliser cette photo pour le profil utilisateur&nbsp;?',
            }, {
                modalId: 'modalConfirmPhotoUser',
                previewId: 'confirmPhotoUserPreview',
                nomId: 'confirmPhotoUserNom',
                btnOkId: 'btnConfirmPhotoUser',
                titleId: 'confirmPhotoUserTitle',
                subtitleId: 'confirmPhotoUserSubtitle',
                leadId: 'confirmPhotoUserLead',
            });
            if (!confirme) return;
            const id = document.getElementById('utilisateurDetail')?.dataset.utilisateurId;
            if (!id) {
                input.value = '';
                return;
            }
            const fd = new FormData();
            fd.append('photo', file);
            const btnOk = document.getElementById('btnConfirmPhotoUser');
            if (btnOk) btnOk.disabled = true;
            try {
                await api(`${API}/utilisateurs/${id}/`, { method: 'PATCH', body: fd, headers: {} });
                toast('Photo mise à jour.', 'success');
                input.value = '';
                await chargerUtilisateurDetail();
            } catch (err) {
                toast(err.message, 'error');
                input.value = '';
            } finally {
                if (btnOk) btnOk.disabled = false;
            }
        });
    }

    /* ---------- Évaluations / bulletins RDC ---------- */
    function initEvaluations() {
        const root = document.getElementById('evaluationsPage');
        if (!root) return;
        bindModalClosers();

        const estEnseignant = root.dataset.enseignant === '1';
        const classeFixe = root.dataset.classeId || '';
        const ecoleId = root.dataset.ecoleId || '';
        const peutConfigurer = root.dataset.peutConfigurer === '1';
        let cacheGrille = null;
        let periodeVerrouillee = false;

        function selectedLabel(sel) {
            if (!sel || !sel.value) return '';
            const opt = sel.options[sel.selectedIndex];
            return (opt && opt.textContent ? opt.textContent : '').trim();
        }

        function majBannerPeriode() {
            const banner = document.getElementById('bannerPeriodeEval');
            const txt = document.getElementById('txtPeriodeEval');
            const btnUnlock = document.getElementById('btnDeverrouillerPeriode');
            const periodeSel = document.getElementById('selectPeriodeEval');
            if (!banner || !txt || !periodeSel?.value) {
                if (banner) banner.hidden = true;
                if (btnUnlock) btnUnlock.hidden = true;
                return;
            }
            banner.hidden = false;
            banner.classList.toggle('is-locked', periodeVerrouillee);
            const lab = selectedLabel(periodeSel).replace(/\s*[—-]\s*Verrouillée\s*$/i, '');
            txt.textContent = periodeVerrouillee
                ? `${lab} — verrouillée (lecture seule). Les notes ne sont plus modifiables.`
                : `${lab} — saisie ouverte. En passant à la période suivante, celle-ci sera verrouillée.`;
            if (btnUnlock) btnUnlock.hidden = !(peutConfigurer && periodeVerrouillee);
        }

        function majResumeSession() {
            const anneeSel = document.getElementById('selectAnneeEval');
            const classeSel = document.getElementById('selectClasseEval');
            const periodeSel = document.getElementById('selectPeriodeEval');
            const progSel = document.getElementById('selectProgrammeEval');
            const chipA = document.getElementById('chipAnneeEval');
            const chipC = document.getElementById('chipClasseEval');
            const chipP = document.getElementById('chipPeriodeEval');
            const chipM = document.getElementById('chipMatiereEval');
            if (chipA) chipA.textContent = selectedLabel(anneeSel) || 'Année —';
            if (chipC) {
                if (estEnseignant) {
                    const parts = [
                        root.dataset.sectionNom,
                        root.dataset.optionNom,
                        root.dataset.classeNom || selectedLabel(classeSel),
                    ].filter(Boolean);
                    chipC.textContent = parts.length ? parts.join(' · ') : 'Classe —';
                } else {
                    chipC.textContent = selectedLabel(classeSel) || 'Classe —';
                }
            }
            if (chipP) {
                const lab = selectedLabel(periodeSel);
                chipP.textContent = lab && !lab.startsWith('—')
                    ? lab.replace(/\s*[—-]\s*Verrouillée\s*$/i, '')
                    : 'Période —';
            }
            if (chipM) {
                const lab = selectedLabel(progSel);
                chipM.textContent = lab && !lab.startsWith('—') ? lab.replace(/\s*\(max.*\)$/, '') : 'Matière —';
            }
            const step1 = !!anneeSel?.value && !!classeSel?.value;
            const step2 = !!periodeSel?.value && !!progSel?.value;
            const tabBulletins = document.querySelector('[data-eval-tab="bulletins"]')?.classList.contains('active');
            document.querySelectorAll('[data-eval-step]').forEach((el) => {
                const n = el.dataset.evalStep;
                el.classList.remove('is-active', 'is-done');
                if (n === '1') {
                    el.classList.add(step1 ? 'is-done' : 'is-active');
                } else if (n === '2') {
                    if (step2) el.classList.add(tabBulletins ? 'is-done' : 'is-active');
                    else if (step1) el.classList.add('is-active');
                } else if (n === '3' && tabBulletins) {
                    el.classList.add('is-active');
                }
            });
            majBannerPeriode();
        }

        function badgeDecision(decision, label) {
            const map = {
                passe: 'badge-success',
                double: 'badge-danger',
                application: 'badge-warning',
                en_attente: 'badge-neutral',
            };
            return `<span class="badge ${map[decision] || 'badge-info'}">${escapeHtml(label || decision || '—')}</span>`;
        }

        document.querySelectorAll('[data-eval-tab]').forEach((btn) => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('[data-eval-tab]').forEach((b) => {
                    b.classList.remove('active');
                    b.setAttribute('aria-selected', 'false');
                });
                btn.classList.add('active');
                btn.setAttribute('aria-selected', 'true');
                const tab = btn.dataset.evalTab;
                document.getElementById('tabSaisieEval').hidden = tab !== 'saisie';
                document.getElementById('tabBulletinsEval').hidden = tab !== 'bulletins';
                const tabMat = document.getElementById('tabMatieresEval');
                if (tabMat) tabMat.hidden = tab !== 'matieres';
                majResumeSession();
                if (tab === 'bulletins') chargerBulletinsEval().catch((e) => toast(e.message, 'error'));
                if (tab === 'matieres') chargerMatieresEval().catch((e) => toast(e.message, 'error'));
            });
        });

        async function chargerAnnees() {
            const data = await api(`${API}/annees-scolaires/?page_size=50`);
            const rows = data.results || data;
            const sel = document.getElementById('selectAnneeEval');
            const active = rows.find((a) => a.active) || rows[0] || null;
            if (!sel) return;
            if (active) {
                sel.innerHTML = `<option value="${active.id}" selected>${escapeHtml(active.libelle)}${active.active ? ' (active)' : ''}</option>`;
                sel.value = String(active.id);
                sel.disabled = true;
            } else {
                sel.innerHTML = '<option value="">— Aucune année scolaire —</option>';
                sel.disabled = true;
            }
            majResumeSession();
        }

        function labelClasseEval(c) {
            const parts = [c.section_nom, c.option_nom].filter(Boolean);
            const prefix = parts.length ? `${parts.join(' · ')} — ` : '';
            return `${prefix}${c.nom || ''}`;
        }

        async function chargerClasses() {
            const sel = document.getElementById('selectClasseEval');
            if (!sel) return;
            // Enseignant : uniquement sa classe (section / option / classe figées)
            if (estEnseignant && classeFixe) {
                const secNom = root.dataset.sectionNom || '';
                const optNom = root.dataset.optionNom || '';
                const claNom = root.dataset.classeNom || `Classe #${classeFixe}`;
                const label = [secNom, optNom, claNom].filter(Boolean).join(' · ') || claNom;
                sel.innerHTML = `<option value="${classeFixe}"
                    data-section="${escapeHtml(root.dataset.sectionId || '')}"
                    data-option="${escapeHtml(root.dataset.optionId || '')}"
                    data-section-nom="${escapeHtml(secNom)}"
                    data-option-nom="${escapeHtml(optNom)}"
                    data-ecole="${escapeHtml(ecoleId)}"
                    selected>${escapeHtml(label)}</option>`;
                sel.disabled = true;
                majResumeSession();
                return;
            }
            let url = `${API}/classes/?actif=1&page_size=300&ordering=nom`;
            if (ecoleId) url += `&ecole=${ecoleId}`;
            const data = await api(url);
            const rows = data.results || data;
            rows.sort((a, b) => labelClasseEval(a).localeCompare(labelClasseEval(b), 'fr'));
            sel.innerHTML = rows.map((c) => `
                <option value="${c.id}"
                    data-section="${c.section || ''}"
                    data-option="${c.option || ''}"
                    data-section-nom="${escapeHtml(c.section_nom || '')}"
                    data-option-nom="${escapeHtml(c.option_nom || '')}"
                    data-ecole="${c.ecole || ecoleId || ''}">
                    ${escapeHtml(labelClasseEval(c))}
                </option>
            `).join('') || '<option value="">— Aucune classe —</option>';
            majResumeSession();
        }

        function classeSessionMeta() {
            const sel = document.getElementById('selectClasseEval');
            const opt = sel?.selectedOptions?.[0];
            if (!sel?.value || !opt) return null;
            return {
                id: Number(sel.value),
                section: opt.dataset.section ? Number(opt.dataset.section) : null,
                option: opt.dataset.option ? Number(opt.dataset.option) : null,
                sectionNom: opt.dataset.sectionNom || '',
                optionNom: opt.dataset.optionNom || '',
                ecole: opt.dataset.ecole || ecoleId || '',
                label: (opt.textContent || '').trim(),
            };
        }

        async function chargerPeriodes(opts = {}) {
            const { ouvrir = false } = opts;
            const annee = document.getElementById('selectAnneeEval')?.value;
            const classe = document.getElementById('selectClasseEval')?.value;
            const sel = document.getElementById('selectPeriodeEval');
            if (!sel) return;
            const prev = sel.value;
            if (!annee || !classe) {
                sel.innerHTML = '<option value="">— Choisir la classe —</option>';
                periodeVerrouillee = false;
                majResumeSession();
                return;
            }
            const data = await api(`${API}/periodes-evaluation/?annee=${annee}&classe=${classe}&page_size=50`);
            const rows = data.results || data;
            sel.innerHTML = rows.length
                ? rows.map((p) => {
                    const lock = p.verrouillee ? ' — Verrouillée' : '';
                    return `<option value="${p.id}" data-verrouillee="${p.verrouillee ? '1' : '0'}">${escapeHtml(p.libelle)}${lock}</option>`;
                }).join('')
                : '<option value="">— Aucune période —</option>';
            if (prev && [...sel.options].some((o) => o.value === prev)) sel.value = prev;
            const opt = sel.options[sel.selectedIndex];
            periodeVerrouillee = opt?.dataset?.verrouillee === '1';
            if (ouvrir && sel.value && !periodeVerrouillee) {
                try {
                    const res = await api(`${API}/periodes-evaluation/${sel.value}/ouvrir/`, {
                        method: 'POST',
                        body: JSON.stringify({ classe: Number(classe) }),
                    });
                    if (res.verrouilles > 0) toast(res.detail, 'success');
                    // Recharger pour marquer les périodes antérieures verrouillées
                    await chargerPeriodes({ ouvrir: false });
                    return;
                } catch (err) {
                    toast(err.message, 'error');
                }
            }
            majResumeSession();
        }

        async function chargerProgrammes() {
            const annee = document.getElementById('selectAnneeEval')?.value;
            const classe = document.getElementById('selectClasseEval')?.value;
            const sel = document.getElementById('selectProgrammeEval');
            if (!annee || !classe) {
                sel.innerHTML = '<option value="">— Sélectionner —</option>';
                majResumeSession();
                return;
            }
            const data = await api(`${API}/programmes-classe/?annee=${annee}&classe=${classe}&page_size=200`);
            const rows = data.results || data;
            sel.innerHTML = rows.length
                ? rows.map((p) => `<option value="${p.id}">${escapeHtml(p.matiere_nom)} (max ${p.maximum_effectif})</option>`).join('')
                : `<option value="">— ${estEnseignant
                    ? 'Aucun cours pour votre classe (demandez à l’administratif d’appliquer le programme)'
                    : 'Aucune matière au programme'} —</option>`;
            majResumeSession();
        }

        async function chargerGrille() {
            const programme = document.getElementById('selectProgrammeEval')?.value;
            const periode = document.getElementById('selectPeriodeEval')?.value;
            const thead = document.querySelector('#tableNotesEval thead');
            const tbody = document.querySelector('#tableNotesEval tbody');
            const btn = document.getElementById('btnEnregistrerNotes');
            const hint = document.getElementById('hintGrilleEval');
            if (!periode) {
                thead.innerHTML = '';
                tbody.innerHTML = emptyRow(3, 'Période requise', 'Sélectionnez d\'abord la période de saisie.');
                if (btn) btn.disabled = true;
                return;
            }
            if (!programme) {
                thead.innerHTML = '';
                tbody.innerHTML = emptyRow(3, 'Aucune matière', 'Appliquez un programme de classe ou sélectionnez une matière.');
                if (btn) btn.disabled = true;
                return;
            }
            const data = await api(`${API}/notes/grille/?programme=${programme}&periode=${periode}`);
            cacheGrille = data;
            periodeVerrouillee = !!data.verrouillee;
            const pLib = data.periode?.libelle || 'Période';
            hint.textContent = periodeVerrouillee
                ? `${data.programme.matiere_nom} · ${pLib} · ${data.eleves.length} élève(s) · verrouillée`
                : `${data.programme.matiere_nom} · ${pLib} · ${data.eleves.length} élève(s) · max ${data.maximum}`;
            thead.innerHTML = `<tr>
                <th>Élève</th>
                <th>Matricule</th>
                <th>${escapeHtml(pLib)}<br><span class="form-hint">max ${escapeHtml(data.maximum || '')}</span></th>
            </tr>`;
            const lockedAttr = periodeVerrouillee ? 'disabled' : '';
            tbody.innerHTML = data.eleves.length ? data.eleves.map((el) => `
                <tr data-eleve="${el.eleve_id}">
                    <td data-label="Élève"><strong>${escapeHtml(el.eleve_nom)}</strong></td>
                    <td data-label="Matricule"><span class="code-chip">${escapeHtml(el.matricule)}</span></td>
                    <td data-label="${escapeHtml(pLib)}">
                        <input type="number" class="input-note" min="0" step="0.5"
                            max="${escapeHtml(data.maximum || '')}"
                            data-periode="${data.periode.id}"
                            value="${escapeHtml(el.note || '')}"
                            inputmode="decimal"
                            ${lockedAttr}
                            aria-label="Note ${escapeHtml(el.eleve_nom)} — ${escapeHtml(pLib)}">
                    </td>
                </tr>
            `).join('') : emptyRow(3, 'Aucun élève', 'Aucun élève actif dans cette classe.');
            if (btn) btn.disabled = !data.eleves.length || periodeVerrouillee;
            majResumeSession();
        }

        async function chargerBulletinsEval() {
            const annee = document.getElementById('selectAnneeEval')?.value;
            const classe = document.getElementById('selectClasseEval')?.value;
            const tbody = document.querySelector('#tableBulletinsEval tbody');
            if (!annee || !classe) {
                tbody.innerHTML = emptyRow(7, 'Sélection requise', 'Choisissez une année et une classe.');
                return;
            }
            const data = await api(`${API}/bulletins/?annee=${annee}&classe=${classe}`);
            const rows = data.results || [];
            tbody.innerHTML = rows.length ? rows.map((b) => `
                <tr>
                    <td data-label="Élève"><strong>${escapeHtml(b.eleve_nom)}</strong></td>
                    <td data-label="Matricule"><span class="code-chip">${escapeHtml(b.matricule)}</span></td>
                    <td data-label="Total">${b.total_obtenu != null ? `${escapeHtml(String(b.total_obtenu))} / ${escapeHtml(String(b.total_max))}` : '—'}</td>
                    <td data-label="%">${b.pourcentage != null ? `${escapeHtml(String(b.pourcentage))} %` : '—'}</td>
                    <td data-label="Place">${b.place != null ? escapeHtml(String(b.place)) : '—'}</td>
                    <td data-label="Décision">${badgeDecision(b.decision, b.decision_display || b.decision)}</td>
                    <td data-label="Actions">
                        <a class="btn btn-primary btn-sm" target="_blank"
                           href="${API}/bulletins/${b.eleve_id}/pdf/?annee=${annee}">${ico('pdf')}PDF</a>
                    </td>
                </tr>
            `).join('') : emptyRow(7, 'Aucun bulletin', 'Saisissez des notes puis actualisez le classement.');
        }

        async function chargerMatieresEval() {
            if (!peutConfigurer) return;
            const tbody = document.querySelector('#tableMatieresEval tbody');
            const hint = document.getElementById('hintMatieresEval');
            const meta = classeSessionMeta();
            if (!meta) {
                if (hint) hint.textContent = 'Sélectionnez une classe — les matières de sa section / option s’affichent';
                tbody.innerHTML = emptyRow(8, 'Classe requise', 'Choisissez une classe dans la barre de session.');
                return;
            }
            if (hint) {
                const scope = [meta.sectionNom, meta.optionNom].filter(Boolean).join(' · ') || meta.label;
                hint.textContent = `Catalogue pour ${scope} — maximum = note d’une période TJ`;
            }
            let url = `${API}/matieres/?page_size=300&actif=1&scope=hierarchie&classe=${meta.id}`;
            if (meta.ecole) url += `&ecole=${meta.ecole}`;
            else if (ecoleId) url += `&ecole=${ecoleId}`;
            const data = await api(url);
            const rows = data.results || data;
            tbody.innerHTML = rows.length ? rows.map((m) => `
                <tr>
                    <td data-label="Nom"><strong>${escapeHtml(m.nom)}</strong></td>
                    <td data-label="Section">${escapeHtml(m.section_nom || '—')}</td>
                    <td data-label="Option">${escapeHtml(m.option_nom || '—')}</td>
                    <td data-label="Classe">${escapeHtml(m.classe_nom || '—')}</td>
                    <td data-label="Code"><span class="code-chip">${escapeHtml(m.code || '—')}</span></td>
                    <td data-label="Maximum">${escapeHtml(String(m.maximum))}</td>
                    <td data-label="Ordre">${escapeHtml(String(m.ordre))}</td>
                    <td data-label="Statut"><span class="badge ${m.active ? 'badge-success' : 'badge-danger'}">${m.active ? 'Active' : 'Inactive'}</span></td>
                </tr>
            `).join('') : emptyRow(8, 'Aucune matière', 'Aucune matière pour cette section / option. Catalogue géré par l’administration nationale.');
        }

        async function regimeAnneeCourante() {
            const anneeSel = document.getElementById('selectAnneeEval');
            let regime = 'secondaire';
            try {
                const annees = await api(`${API}/annees-scolaires/?page_size=50`);
                const rows = annees.results || annees;
                const cur = rows.find((a) => String(a.id) === String(anneeSel?.value));
                if (cur?.regime) regime = cur.regime;
            } catch (_) { /* ignore */ }
            return regime;
        }

        async function chargerCataloguePourClasse() {
            const meta = classeSessionMeta();
            if (!meta) {
                toast('Sélectionnez d\'abord une classe.', 'warning');
                return null;
            }
            const regime = await regimeAnneeCourante();
            const data = await api(`${API}/matieres/charger-catalogue/`, {
                method: 'POST',
                body: JSON.stringify({
                    ecole: meta.ecole || ecoleId || undefined,
                    regime,
                    classe: meta.id,
                    section: meta.section || undefined,
                    option: meta.option || undefined,
                }),
            });
            return data;
        }

        async function remplirSelectsMatiereEval() {
            const sec = document.getElementById('matiereEvalSection');
            const opt = document.getElementById('matiereEvalOption');
            const cla = document.getElementById('matiereEvalClasse');
            if (!sec || !ecoleId) return;
            const sections = await api(`${API}/sections-scolaires/?ecole=${ecoleId}&actif=1&page_size=200`);
            const secRows = sections.results || sections;
            sec.innerHTML = '<option value="">—</option>' + secRows.map((s) =>
                `<option value="${s.id}">${escapeHtml(s.nom)}</option>`
            ).join('');
            const fillOptions = async () => {
                const sid = sec.value;
                if (!sid) {
                    opt.innerHTML = '<option value="">—</option>';
                    return;
                }
                const options = await api(`${API}/options-scolaires/?ecole=${ecoleId}&section=${sid}&actif=1&page_size=200`);
                const oRows = options.results || options;
                opt.innerHTML = '<option value="">—</option>' + oRows.map((o) =>
                    `<option value="${o.id}">${escapeHtml(o.nom)}</option>`
                ).join('');
            };
            const fillClasses = async () => {
                const oid = opt.value;
                let url = `${API}/classes/?ecole=${ecoleId}&actif=1&page_size=200`;
                if (oid) url += `&option=${oid}`;
                else if (sec.value) url += `&section=${sec.value}`;
                const classes = await api(url);
                const cRows = classes.results || classes;
                cla.innerHTML = '<option value="">—</option>' + cRows.map((c) =>
                    `<option value="${c.id}">${escapeHtml(c.nom)}</option>`
                ).join('');
            };
            sec.onchange = async () => { await fillOptions(); await fillClasses(); };
            opt.onchange = async () => { await fillClasses(); };
            await fillOptions();
            await fillClasses();
            // Préremplir depuis la session
            const classeSel = document.getElementById('selectClasseEval');
            if (classeSel?.value) {
                try {
                    const c = await api(`${API}/classes/${classeSel.value}/`);
                    if (c.section) {
                        sec.value = String(c.section);
                        await fillOptions();
                    }
                    if (c.option) {
                        opt.value = String(c.option);
                        await fillClasses();
                    }
                    cla.value = String(c.id);
                } catch (_) { /* ignore */ }
            }
        }

        document.getElementById('selectAnneeEval')?.addEventListener('change', async () => {
            majResumeSession();
            await chargerPeriodes({ ouvrir: false });
            await chargerProgrammes();
            await chargerGrille().catch((e) => toast(e.message, 'error'));
        });
        document.getElementById('selectClasseEval')?.addEventListener('change', async () => {
            majResumeSession();
            await chargerPeriodes({ ouvrir: false });
            await chargerProgrammes();
            await chargerGrille().catch((e) => toast(e.message, 'error'));
            const tabMat = document.getElementById('tabMatieresEval');
            if (tabMat && !tabMat.hidden) {
                await chargerMatieresEval().catch((e) => toast(e.message, 'error'));
            }
        });
        document.getElementById('selectPeriodeEval')?.addEventListener('change', async () => {
            const opt = document.getElementById('selectPeriodeEval')?.selectedOptions?.[0];
            periodeVerrouillee = opt?.dataset?.verrouillee === '1';
            majResumeSession();
            // Ouvrir la période = verrouiller les périodes antérieures
            if (!periodeVerrouillee) {
                await chargerPeriodes({ ouvrir: true });
            }
            await chargerGrille().catch((e) => toast(e.message, 'error'));
        });
        document.getElementById('selectProgrammeEval')?.addEventListener('change', () => {
            majResumeSession();
            chargerGrille().catch((e) => toast(e.message, 'error'));
        });

        document.getElementById('btnDeverrouillerPeriode')?.addEventListener('click', async () => {
            const periode = document.getElementById('selectPeriodeEval')?.value;
            const classe = document.getElementById('selectClasseEval')?.value;
            if (!periode || !classe) return;
            try {
                await api(`${API}/periodes-evaluation/${periode}/deverrouiller/`, {
                    method: 'POST',
                    body: JSON.stringify({ classe: Number(classe) }),
                });
                toast('Période déverrouillée.', 'success');
                await chargerPeriodes({ ouvrir: false });
                await chargerGrille();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('btnEnregistrerNotes')?.addEventListener('click', async () => {
            const programme = document.getElementById('selectProgrammeEval')?.value;
            const periode = document.getElementById('selectPeriodeEval')?.value;
            if (!programme || !periode || !cacheGrille) return;
            if (periodeVerrouillee || cacheGrille.verrouillee) {
                toast('Cette période est verrouillée.', 'error');
                return;
            }
            const notes = [];
            document.querySelectorAll('#tableNotesEval tbody tr[data-eleve]').forEach((tr) => {
                const eleve = Number(tr.dataset.eleve);
                const input = tr.querySelector('.input-note');
                if (!input) return;
                const raw = (input.value || '').trim();
                notes.push({
                    eleve,
                    periode: Number(periode),
                    valeur: raw === '' ? null : Number(raw),
                });
            });
            try {
                const data = await api(`${API}/notes/saisie-bulk/`, {
                    method: 'POST',
                    body: JSON.stringify({ programme: Number(programme), notes }),
                });
                toast(data.detail || 'Notes enregistrées.', data.errors_count ? 'warning' : 'success');
                await chargerGrille();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('btnClasserBulletins')?.addEventListener('click', async () => {
            const annee = document.getElementById('selectAnneeEval')?.value;
            const classe = document.getElementById('selectClasseEval')?.value;
            if (!annee || !classe) return;
            try {
                await api(`${API}/bulletins/classer/`, {
                    method: 'POST',
                    body: JSON.stringify({ annee: Number(annee), classe: Number(classe) }),
                });
                toast('Classement actualisé.', 'success');
                await chargerBulletinsEval();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        async function onCatalogueClick() {
            try {
                const data = await chargerCataloguePourClasse();
                if (!data) return;
                toast(data.detail || 'Catalogue chargé pour l\'option / classe.', 'success');
                await chargerMatieresEval();
                await chargerProgrammes();
            } catch (err) {
                toast(err.message, 'error');
            }
        }
        document.getElementById('btnCatalogueMatieres')?.addEventListener('click', onCatalogueClick);
        document.getElementById('btnCatalogueMatieresTab')?.addEventListener('click', onCatalogueClick);

        document.getElementById('btnAppliquerProgramme')?.addEventListener('click', async () => {
            const annee = document.getElementById('selectAnneeEval')?.value;
            const meta = classeSessionMeta();
            if (!annee || !meta) {
                toast('Choisissez une année et une classe.', 'warning');
                return;
            }
            try {
                const data = await api(`${API}/programmes-classe/appliquer-matieres-ecole/`, {
                    method: 'POST',
                    body: JSON.stringify({ annee: Number(annee), classe: meta.id }),
                });
                toast(data.detail || 'Programme appliqué.', 'success');
                await chargerMatieresEval().catch(() => {});
                await chargerProgrammes();
                await chargerGrille();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('btnNouvelleMatiere')?.addEventListener('click', async () => {
            try {
                await remplirSelectsMatiereEval();
            } catch (err) {
                toast(err.message, 'error');
                return;
            }
            openModal('modalMatiereEval');
        });
        document.getElementById('formMatiereEval')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            if (!form.section.value || !form.option.value || !form.classe.value) {
                toast('Section, option et classe sont obligatoires.', 'warning');
                return;
            }
            if (!ecoleId && !estEnseignant) {
                // Admin national : besoin d'une école — prendre celle de la classe
                const classeId = document.getElementById('selectClasseEval')?.value;
                if (!classeId) {
                    toast('Sélectionnez d\'abord une classe.', 'warning');
                    return;
                }
            }
            let ecole = ecoleId;
            if (!ecole) {
                try {
                    const classeId = document.getElementById('selectClasseEval')?.value;
                    const classes = await api(`${API}/classes/${classeId}/`);
                    ecole = classes.ecole;
                } catch (err) {
                    toast(err.message, 'error');
                    return;
                }
            }
            const payload = {
                ecole: Number(ecole),
                section: Number(form.section.value),
                option: Number(form.option.value),
                classe: Number(form.classe.value),
                nom: form.nom.value.trim(),
                code: form.code.value.trim(),
                maximum: Number(form.maximum.value),
                ordre: Number(form.ordre.value || 1),
                active: true,
            };
            try {
                await api(`${API}/matieres/`, { method: 'POST', body: JSON.stringify(payload) });
                toast('Matière créée.', 'success');
                closeModal('modalMatiereEval');
                form.reset();
                await chargerMatieresEval();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        (async () => {
            try {
                await chargerAnnees();
                await chargerClasses();
                await chargerPeriodes({ ouvrir: false });
                await chargerProgrammes();
                await chargerGrille();
            } catch (err) {
                toast(err.message, 'error');
            }
        })();
    }

    /* ---------- Paramètres — Années scolaires (CRUD national) ---------- */
    function initParametresAnnees() {
        const app = document.getElementById('anneesApp')
            || document.getElementById('paramAnneesApp');
        if (!app) {
            console.warn('[EducRDC] #anneesApp introuvable');
            return;
        }
        if (app.dataset.bound === '1') return;
        app.dataset.bound = '1';
        bindModalClosers();

        const table = document.getElementById('tableAnnees')
            || document.getElementById('tableAnneesParam');
        const countId = document.getElementById('countAnnees')
            ? 'countAnnees'
            : 'countAnneesParam';
        const btnNew = document.getElementById('btnNouvelleAnnee')
            || document.getElementById('btnNouvelleAnneeParam');
        const btnSearch = document.getElementById('btnSearchAnnees')
            || document.getElementById('btnSearchAnneesParam');
        const searchInput = document.getElementById('searchAnnees')
            || document.getElementById('searchAnneesParam');
        const form = document.getElementById('formAnnee')
            || document.getElementById('formAnneeParam');
        const modalId = document.getElementById('modalAnnee')
            ? 'modalAnnee'
            : 'modalAnneeParam';

        let cache = [];

        function el(id) {
            return document.getElementById(id);
        }

        function setError(msg) {
            const box = el('anneeError') || el('anneeParamError');
            if (!box) return;
            box.hidden = !msg;
            box.textContent = msg || '';
        }

        function field(name, fallbackId) {
            return (form && form.querySelector(`[name="${name}"]`))
                || (fallbackId ? el(fallbackId) : null);
        }

        function suggestNext() {
            const y = new Date().getFullYear();
            let start = 0;
            cache.forEach((a) => {
                const m = String(a.libelle || '').match(/^(\d{4})/);
                const n = m ? Number(m[1]) : 0;
                if (n >= y - 5 && n <= y + 2) start = Math.max(start, n);
            });
            if (!start) {
                start = y;
                if (new Date().getMonth() < 8) start -= 1;
            }
            const d = start + 1;
            return { libelle: `${d}-${d + 1}`, debut: `${d}-09-01`, fin: `${d + 1}-07-31` };
        }

        function openForm(row) {
            if (!form) {
                toast('Formulaire année introuvable. Rechargez la page (Ctrl+F5).', 'error');
                return;
            }
            form.reset();
            setError('');
            const idEl = el('anneeId') || el('anneeParamId');
            const titre = el('titreModalAnnee') || el('titreModalAnneeParam');
            const btnDel = el('btnSupprimerAnnee') || el('btnSupprimerAnneeParam');
            const btnSave = el('btnSaveAnnee') || el('btnSubmitAnneeParam');
            const libelleEl = field('libelle', 'anneeLibelle');
            const regimeEl = field('regime', 'anneeRegime');
            const debutEl = field('date_debut', 'anneeDebut');
            const finEl = field('date_fin', 'anneeFin');
            const activeEl = field('active', 'anneeActive') || el('anneeParamActive');

            if (idEl) idEl.value = row?.id || '';
            if (titre) {
                titre.textContent = row
                    ? 'Modifier l\'année scolaire'
                    : 'Nouvelle année scolaire';
            }
            if (btnDel) btnDel.hidden = !row?.id;
            if (btnSave) {
                btnSave.disabled = false;
                btnSave.innerHTML = `${ico('save')}${row ? 'Enregistrer' : 'Créer'}`;
            }
            if (row) {
                if (libelleEl) libelleEl.value = row.libelle || '';
                if (regimeEl) regimeEl.value = row.regime || 'secondaire';
                if (debutEl) debutEl.value = (row.date_debut || '').slice(0, 10);
                if (finEl) finEl.value = (row.date_fin || '').slice(0, 10);
                if (activeEl) activeEl.checked = !!row.active;
            } else {
                const s = suggestNext();
                if (libelleEl) libelleEl.value = s.libelle;
                if (debutEl) debutEl.value = s.debut;
                if (finEl) finEl.value = s.fin;
                if (activeEl) activeEl.checked = true;
            }
            openModal(modalId);
        }

        async function loadList() {
            const tbody = table?.querySelector('tbody');
            if (!tbody) {
                toast('Tableau des années introuvable. Rechargez (Ctrl+F5).', 'error');
                return;
            }
            tbody.innerHTML = emptyRow(7, 'Chargement…', 'Récupération du référentiel national.');
            try {
                const data = await api(`${API}/annees-scolaires/?page_size=100`);
                let rows = Array.isArray(data) ? data : (data.results || []);
                cache = rows;
                const q = (searchInput?.value || '').trim().toLowerCase();
                if (q) {
                    rows = rows.filter((a) => (a.libelle || '').toLowerCase().includes(q));
                }
                setCount(countId, rows.length, 'année');
                if (!rows.length) {
                    tbody.innerHTML = emptyRow(
                        7,
                        'Aucune année scolaire',
                        'Créez l\'année nationale (ex. 2025-2026).',
                    );
                    return;
                }
                tbody.innerHTML = rows.map((a) => `
                    <tr>
                        <td data-label="Libellé"><strong>${escapeHtml(a.libelle)}</strong></td>
                        <td data-label="Début">${escapeHtml(a.date_debut || '—')}</td>
                        <td data-label="Fin">${escapeHtml(a.date_fin || '—')}</td>
                        <td data-label="Régime"><span class="badge badge-neutral">${escapeHtml(a.regime_display || a.regime || '—')}</span></td>
                        <td data-label="Périodes">${a.nb_periodes ?? '—'}</td>
                        <td data-label="Statut">
                            <span class="badge ${a.active ? 'badge-success' : 'badge-neutral'}">${a.active ? 'Active (nationale)' : 'Inactive'}</span>
                        </td>
                        <td data-label="Actions"><div class="actions-inline">
                            <button type="button" class="btn btn-ghost btn-sm" data-edit="${a.id}" title="Modifier" aria-label="Modifier">${ico('edit')}<span>Modifier</span></button>
                            ${a.active ? '' : `<button type="button" class="btn btn-secondary btn-sm" data-activate="${a.id}" title="Activer" aria-label="Activer">${ico('check')}<span>Activer</span></button>`}
                            <button type="button" class="btn btn-danger btn-sm" data-del="${a.id}" title="Supprimer" aria-label="Supprimer">${ico('trash')}<span>Supprimer</span></button>
                        </div></td>
                    </tr>
                `).join('');
            } catch (err) {
                tbody.innerHTML = emptyRow(7, 'Erreur de chargement', err.message || 'Impossible de charger.');
                setCount(countId, 0, 'année');
                toast(err.message || 'Impossible de charger les années.', 'error');
            }
        }

        btnNew?.addEventListener('click', (e) => {
            e.preventDefault();
            openForm(null);
        });
        btnSearch?.addEventListener('click', () => loadList());
        searchInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                loadList();
            }
        });

        table?.querySelector('tbody')?.addEventListener('click', async (e) => {
            const edit = e.target.closest('[data-edit]');
            const activate = e.target.closest('[data-activate]');
            const del = e.target.closest('[data-del]');
            if (edit) {
                const row = cache.find((x) => String(x.id) === String(edit.dataset.edit));
                openForm(row || null);
                return;
            }
            if (activate) {
                try {
                    await api(`${API}/annees-scolaires/${activate.dataset.activate}/`, {
                        method: 'PATCH',
                        body: JSON.stringify({ active: true }),
                    });
                    toast('Année nationale activée.', 'success');
                    await loadList();
                } catch (err) {
                    toast(err.message, 'error');
                }
                return;
            }
            if (del) {
                if (!confirm('Supprimer cette année scolaire et ses périodes ?')) return;
                try {
                    await api(`${API}/annees-scolaires/${del.dataset.del}/`, { method: 'DELETE' });
                    toast('Année supprimée.', 'success');
                    await loadList();
                } catch (err) {
                    toast(err.message, 'error');
                }
            }
        });

        (el('btnSupprimerAnnee') || el('btnSupprimerAnneeParam'))?.addEventListener('click', async () => {
            const id = (el('anneeId') || el('anneeParamId'))?.value;
            if (!id || !confirm('Supprimer cette année scolaire et ses périodes ?')) return;
            try {
                await api(`${API}/annees-scolaires/${id}/`, { method: 'DELETE' });
                toast('Année supprimée.', 'success');
                closeModal(modalId);
                await loadList();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = ((el('anneeId') || el('anneeParamId'))?.value || '').trim();
            const libelle = (field('libelle', 'anneeLibelle')?.value || '').trim();
            const regime = field('regime', 'anneeRegime')?.value || 'secondaire';
            const dateDebut = field('date_debut', 'anneeDebut')?.value || '';
            const dateFin = field('date_fin', 'anneeFin')?.value || '';
            const activeEl = field('active', 'anneeActive') || el('anneeParamActive');
            const active = !!activeEl?.checked;
            setError('');

            if (!libelle || !dateDebut || !dateFin) {
                const msg = 'Libellé, début et fin sont obligatoires.';
                setError(msg);
                toast(msg, 'warning');
                return;
            }
            if (dateFin < dateDebut) {
                const msg = 'La date de fin doit être postérieure au début.';
                setError(msg);
                toast(msg, 'warning');
                return;
            }

            const payload = {
                libelle,
                regime,
                date_debut: dateDebut,
                date_fin: dateFin,
                active,
            };
            const submitBtn = el('btnSaveAnnee') || el('btnSubmitAnneeParam')
                || form.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            try {
                if (id) {
                    await api(`${API}/annees-scolaires/${id}/`, {
                        method: 'PATCH',
                        body: JSON.stringify(payload),
                    });
                    toast('Année mise à jour.', 'success');
                } else {
                    const created = await api(`${API}/annees-scolaires/`, {
                        method: 'POST',
                        body: JSON.stringify(payload),
                    });
                    const n = created?.nb_periodes ?? 0;
                    toast(n ? `Année créée avec ${n} période(s).` : 'Année créée.', 'success');
                }
                closeModal(modalId);
                form.reset();
                await loadList();
            } catch (err) {
                const msg = err.message || 'Échec de l\'enregistrement.';
                setError(msg);
                toast(msg, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        loadList().catch((err) => toast(err.message, 'error'));
    }

    /* ---------- Paramètres — Gestion documentaire (référentiel) ---------- */
    function initParametresArretes() {
        const app = document.getElementById('arretesApp');
        if (!app) return;
        if (app.dataset.bound === '1') return;
        app.dataset.bound = '1';
        bindModalClosers();
        bindFileDropPreview('arreteFichier');
        bindFileDropPreview('detailArreteFichier');

        const table = document.getElementById('tableArretes');
        const form = document.getElementById('formArrete');
        const searchInput = document.getElementById('searchArretes');
        let cache = [];
        let pageArretes = 1;
        let detailRow = null;
        const PAGE_SIZE = 20;

        function setError(msg) {
            const box = document.getElementById('arreteError');
            if (!box) return;
            box.hidden = !msg;
            box.textContent = msg || '';
        }

        function refreshDetailFileUi(row) {
            const lien = document.getElementById('lienPdfDetailArrete');
            const hint = document.getElementById('detailArreteFichierHint');
            const fileInput = document.getElementById('detailArreteFichier');
            const fileTitle = document.getElementById('detailArreteFichierTitle');
            const drop = fileInput?.closest('.file-drop');
            const pdfPanel = document.querySelector('.doc-detail-pdf');
            if (fileInput) fileInput.value = '';
            drop?.classList.remove('has-file', 'is-dragover');
            if (fileTitle) fileTitle.textContent = 'Déposer un PDF ou cliquer pour parcourir';
            if (lien) {
                if (row?.fichier_url) {
                    lien.hidden = false;
                    lien.href = row.fichier_url;
                } else {
                    lien.hidden = true;
                    lien.removeAttribute('href');
                }
            }
            if (hint) {
                hint.textContent = row?.fichier_url
                    ? `Fichier actuel : ${row.nom_fichier || 'PDF joint'}`
                    : 'Aucun fichier joint pour le moment.';
            }
            pdfPanel?.classList.toggle('has-file', !!row?.fichier_url);
        }

        function openDetail(row) {
            if (!row) return;
            detailRow = row;
            const idEl = document.getElementById('detailArreteId');
            if (idEl) idEl.value = row.id || '';

            const numeroEl = document.getElementById('titreDetailArrete');
            const objetEl = document.getElementById('detailArreteObjet');
            const sous = document.getElementById('sousTitreDetailArrete');
            const chips = document.getElementById('detailArreteChips');
            const descEl = document.getElementById('detailArreteDescription');
            const descSection = document.getElementById('sectionDetailArreteDescription');

            if (numeroEl) numeroEl.textContent = row.numero || '—';
            if (objetEl) objetEl.textContent = row.objet || 'Sans objet';
            if (sous) {
                sous.textContent = [
                    row.autorite || '',
                    formatDateFr(row.date_arrete),
                ].filter(Boolean).join(' · ') || 'Référentiel documentaire';
            }
            if (chips) {
                const type = escapeHtml(row.type_display || row.type_arrete || 'Document');
                const statut = row.actif !== false
                    ? '<span class="badge badge-success">Actif</span>'
                    : '<span class="badge badge-neutral">Inactif</span>';
                const ecoles = Number(row.nombre_ecoles || 0);
                chips.innerHTML = `
                    <span class="badge badge-info">${type}</span>
                    ${statut}
                    <span class="badge badge-neutral">${ecoles} école${ecoles > 1 ? 's' : ''}</span>
                `;
            }

            fillDetailList('blocDetailArreteIdentite', [
                ['N° référence', row.numero],
                ['Objet', row.objet],
                ['Type', row.type_display || row.type_arrete],
            ]);
            fillDetailList('blocDetailArreteEmission', [
                ['Date', formatDateFr(row.date_arrete)],
                ['Signataire', row.signataire],
                ['Autorité', row.autorite],
            ]);

            const desc = (row.description || '').trim();
            if (descEl) descEl.textContent = desc || 'Aucune description.';
            if (descSection) descSection.hidden = !desc;

            refreshDetailFileUi(row);
            openModal('modalDetailArrete');
        }

        function openForm(row) {
            if (!form) return;
            form.reset();
            setError('');
            const idEl = document.getElementById('arreteId');
            const titre = document.getElementById('titreModalArrete');
            const btnDel = document.getElementById('btnSupprimerArrete');
            const btnSave = document.getElementById('btnSaveArrete');
            const fileTitle = document.getElementById('arreteFichierTitle');
            const fileActuel = document.getElementById('arreteFichierActuel');
            form.querySelector('.file-drop')?.classList.remove('has-file', 'is-dragover');
            if (fileTitle) fileTitle.textContent = 'Déposer le fichier PDF ou cliquer';

            if (idEl) idEl.value = row?.id || '';
            if (titre) titre.textContent = row ? 'Modifier le document' : 'Nouveau document';
            if (btnDel) btnDel.hidden = !row?.id;
            if (btnSave) {
                btnSave.disabled = false;
                btnSave.innerHTML = `${ico('save')}${row ? 'Enregistrer' : 'Créer'}`;
            }
            if (row) {
                form.numero.value = row.numero || '';
                form.objet.value = row.objet || '';
                form.type_arrete.value = row.type_arrete || 'arrete';
                form.date_arrete.value = (row.date_arrete || '').slice(0, 10);
                form.signataire.value = row.signataire || '';
                form.autorite.value = row.autorite || 'EPSP';
                form.description.value = row.description || '';
                form.actif.checked = row.actif !== false;
                if (fileActuel) {
                    if (row.fichier_url) {
                        fileActuel.hidden = false;
                        fileActuel.innerHTML = `Fichier actuel : <a href="${escapeHtml(row.fichier_url)}" target="_blank" rel="noopener">${escapeHtml(row.nom_fichier || 'Ouvrir')}</a>`;
                    } else {
                        fileActuel.hidden = true;
                        fileActuel.innerHTML = '';
                    }
                }
            } else {
                form.autorite.value = 'EPSP';
                form.actif.checked = true;
                form.date_arrete.value = new Date().toISOString().slice(0, 10);
                if (fileActuel) {
                    fileActuel.hidden = true;
                    fileActuel.innerHTML = '';
                }
            }
            openModal('modalArrete');
        }

        async function loadList(page = pageArretes) {
            const tbody = table?.querySelector('tbody');
            if (!tbody) return;
            pageArretes = page;
            tbody.innerHTML = emptyRow(7, 'Chargement…', 'Récupération du référentiel.');
            try {
                const params = new URLSearchParams({
                    page: String(pageArretes),
                    page_size: String(PAGE_SIZE),
                });
                const type = document.getElementById('filtreTypeArrete')?.value || '';
                const q = (searchInput?.value || '').trim();
                if (type) params.set('type_arrete', type);
                if (q) params.set('search', q);
                const data = await api(`${API}/arretes/?${params}`);
                const rows = Array.isArray(data) ? data : (data.results || []);
                const total = Array.isArray(data) ? rows.length : (data.count ?? rows.length);
                cache = rows;
                setCount('countArretes', total, 'document');
                const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
                renderPagination('paginationArretes', pageArretes, totalPages, loadList);
                if (!rows.length) {
                    tbody.innerHTML = emptyRow(
                        7,
                        'Aucun document',
                        'Ajoutez le premier document au référentiel national.',
                    );
                    return;
                }
                tbody.innerHTML = rows.map((a) => {
                    const afficher = a.fichier_url
                        ? `<a class="btn btn-ghost btn-sm" href="${escapeHtml(a.fichier_url)}" target="_blank" rel="noopener" title="Afficher le PDF">${ico('pdf')}<span>Afficher</span></a>`
                        : '';
                    return `
                    <tr>
                        <td data-label="N°"><strong>${escapeHtml(a.numero)}</strong></td>
                        <td data-label="Objet">${escapeHtml(a.objet || '—')}</td>
                        <td data-label="Type"><span class="badge badge-neutral">${escapeHtml(a.type_display || a.type_arrete)}</span></td>
                        <td data-label="Date">${escapeHtml(formatDateFr(a.date_arrete) || '—')}</td>
                        <td data-label="Signataire">${escapeHtml(a.signataire || '—')}</td>
                        <td data-label="Autorité">${escapeHtml(a.autorite || '—')}</td>
                        <td data-label="Actions"><div class="actions-inline">
                            <button type="button" class="btn btn-ghost btn-sm" data-detail="${a.id}" title="Détail">${ico('eye')}<span>Détail</span></button>
                            ${afficher}
                        </div></td>
                    </tr>`;
                }).join('');
            } catch (err) {
                tbody.innerHTML = emptyRow(7, 'Erreur de chargement', err.message || 'Impossible de charger.');
                setCount('countArretes', 0, 'document');
                renderPagination('paginationArretes', 1, 1, loadList);
                toast(err.message || 'Impossible de charger la gestion documentaire.', 'error');
            }
        }

        document.getElementById('btnNouvelArrete')?.addEventListener('click', (e) => {
            e.preventDefault();
            openForm(null);
        });
        document.getElementById('btnSearchArretes')?.addEventListener('click', () => loadList(1));
        searchInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                loadList(1);
            }
        });
        document.getElementById('filtreTypeArrete')?.addEventListener('change', () => loadList(1));

        table?.querySelector('tbody')?.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-detail]');
            if (!btn) return;
            const row = cache.find((x) => String(x.id) === String(btn.dataset.detail));
            openDetail(row || null);
        });

        document.getElementById('btnJoindrePdfDetailArrete')?.addEventListener('click', async () => {
            const id = (document.getElementById('detailArreteId')?.value || '').trim()
                || String(detailRow?.id || '');
            const fileInput = document.getElementById('detailArreteFichier');
            const fichier = fileInput?.files?.[0];
            if (!id) {
                toast('Document introuvable.', 'error');
                return;
            }
            if (!fichier || !fichier.size) {
                toast('Choisissez un fichier PDF à joindre.', 'warning');
                return;
            }
            const name = (fichier.name || '').toLowerCase();
            const isPdf = fichier.type === 'application/pdf' || name.endsWith('.pdf');
            if (!isPdf) {
                toast('Seuls les fichiers PDF sont acceptés.', 'warning');
                return;
            }
            const btn = document.getElementById('btnJoindrePdfDetailArrete');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Envoi…';
            }
            try {
                const fd = new FormData();
                fd.append('fichier', fichier, fichier.name);
                const updated = await api(`${API}/arretes/${id}/`, {
                    method: 'PATCH',
                    body: fd,
                    headers: {},
                });
                toast('PDF joint au document.', 'success');
                detailRow = updated || detailRow;
                if (updated) {
                    const idx = cache.findIndex((x) => String(x.id) === String(updated.id));
                    if (idx >= 0) cache[idx] = updated;
                    openDetail(updated);
                }
                await loadList(pageArretes);
            } catch (err) {
                toast(err.message, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `${ico('upload')}Joindre le PDF`;
                }
            }
        });

        document.getElementById('btnSupprimerArrete')?.addEventListener('click', async () => {
            const id = document.getElementById('arreteId')?.value;
            if (!id || !confirm('Supprimer ce document du référentiel ?')) return;
            try {
                await api(`${API}/arretes/${id}/`, { method: 'DELETE' });
                toast('Document supprimé.', 'success');
                closeModal('modalArrete');
                await loadList(pageArretes);
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!form.checkValidity()) {
                toast('Veuillez compléter les champs obligatoires.', 'warning');
                form.reportValidity();
                return;
            }
            setError('');
            const id = (document.getElementById('arreteId')?.value || '').trim();
            const fd = new FormData(form);
            fd.set('actif', form.actif.checked ? 'true' : 'false');
            const fichier = document.getElementById('arreteFichier')?.files?.[0];
            if (!fichier) fd.delete('fichier');

            const submitBtn = document.getElementById('btnSaveArrete');
            if (submitBtn) submitBtn.disabled = true;
            try {
                if (id) {
                    await api(`${API}/arretes/${id}/`, {
                        method: 'PATCH',
                        body: fd,
                        headers: {},
                    });
                    toast('Document mis à jour.', 'success');
                } else {
                    await api(`${API}/arretes/`, {
                        method: 'POST',
                        body: fd,
                        headers: {},
                    });
                    toast('Document créé.', 'success');
                }
                closeModal('modalArrete');
                form.reset();
                await loadList();
            } catch (err) {
                const msg = err.message || 'Échec de l\'enregistrement.';
                setError(msg);
                toast(msg, 'error');
            } finally {
                if (submitBtn) submitBtn.disabled = false;
            }
        });

        loadList().catch((err) => toast(err.message, 'error'));
    }

    /* ---------- Paramètres — Structure scolaire (CRUD) ---------- */
    function initParametresScolaire() {
        const app = document.getElementById('paramScolaireApp');
        if (!app) return;
        bindModalClosers();

        const ecoleFigee = app.dataset.ecoleFigee === '1';
        let ecoleId = app.dataset.ecoleId || '';
        let pageSections = 1;
        let pageOptions = 1;
        let pageClasses = 1;
        let pageMatieres = 1;
        let cacheSections = [];
        let cacheOptions = [];
        let cacheClasses = [];
        let cacheMatieres = [];

        const selEcole = document.getElementById('filtreEcoleScolaire');

        function requireEcole() {
            if (!ecoleId) {
                toast('Étape 1 : sélectionnez d\'abord une école.', 'warning');
                document.getElementById('filtreEcoleScolaire')?.focus();
                return false;
            }
            return true;
        }

        function majEtatEcoleSelection() {
            const hasEcole = !!ecoleId;
            const bloc = document.getElementById('blocStructureEcole');
            const resume = document.getElementById('resumeStructureScolaire');
            const hint = document.getElementById('hintEcoleSelectionnee');
            const badgeReq = document.getElementById('badgeEcoleRequise');
            const badgeOk = document.getElementById('badgeEcoleChoisie');
            const step1 = document.querySelector('[data-struct-step="1"]');
            const step2 = document.querySelector('[data-struct-step="2"]');
            const titreAff = document.getElementById('titreAffectationEcole');

            if (bloc) {
                bloc.hidden = !hasEcole;
                bloc.classList.toggle('struct-locked', !hasEcole);
            }
            if (resume) resume.hidden = !hasEcole;
            if (badgeReq) badgeReq.hidden = hasEcole;
            if (badgeOk) badgeOk.hidden = !hasEcole;
            step1?.classList.toggle('is-active', !hasEcole);
            step1?.classList.toggle('is-done', hasEcole);
            step2?.classList.toggle('is-active', hasEcole);
            step2?.classList.toggle('is-done', false);

            if (hint) {
                if (hasEcole && selEcole) {
                    const lab = selEcole.options[selEcole.selectedIndex]?.textContent || '';
                    hint.hidden = false;
                    hint.innerHTML = `École sélectionnée : <strong>${escapeHtml(lab.trim())}</strong> — vous pouvez maintenant affecter sections, options et classes.`;
                } else {
                    hint.hidden = true;
                    hint.textContent = '';
                }
            }
            if (titreAff) {
                titreAff.textContent = hasEcole
                    ? 'Cochez les options du référentiel, puis affectez-les à cette école'
                    : 'Sélectionnez d\'abord une école (étape 1)';
            }
        }

        function statutBadge(active) {
            return active
                ? '<span class="badge badge-success">Active</span>'
                : '<span class="badge badge-neutral">Inactive</span>';
        }

        function setStat(id, value) {
            const el = document.getElementById(id);
            if (el) el.textContent = value == null ? '—' : String(value);
        }

        async function actualiserResume() {
            if (!ecoleId) {
                setStat('statSections', '—');
                setStat('statOptions', '—');
                setStat('statClasses', '—');
                setStat('statMatieres', '—');
                return;
            }
            try {
                const [sec, opt, cls, mat] = await Promise.all([
                    api(`${API}/sections-scolaires/?ecole=${ecoleId}&actif=1&page_size=1`),
                    api(`${API}/options-scolaires/?ecole=${ecoleId}&actif=1&page_size=1`),
                    api(`${API}/classes/?ecole=${ecoleId}&actif=1&page_size=1`),
                    api(`${API}/matieres/?ecole=${ecoleId}&actif=1&page_size=1`),
                ]);
                setStat('statSections', sec.count ?? (sec.results || sec).length);
                setStat('statOptions', opt.count ?? (opt.results || opt).length);
                setStat('statClasses', cls.count ?? (cls.results || cls).length);
                setStat('statMatieres', mat.count ?? (mat.results || mat).length);
            } catch (_) {
                /* résumé non bloquant */
            }
        }

        async function chargerSelectEcoles(search = '') {
            if (!selEcole) return;
            const info = document.getElementById('infoEcolesChargees');
            try {
                if (ecoleFigee && ecoleId) {
                    const e = await api(`${API}/ecoles/${ecoleId}/?leger=1`);
                    selEcole.innerHTML = `<option value="${e.id}">${escapeHtml(e.nom)} (${escapeHtml(e.code || '')})</option>`;
                    ecoleId = String(e.id);
                    if (info) info.textContent = '';
                    majEtatEcoleSelection();
                    return;
                }

                selEcole.innerHTML = '<option value="">Chargement…</option>';
                const q = (search || '').trim();
                // Liste complète des écoles actives (pas seulement celles déjà structurées)
                let url = `${API}/ecoles/choix/?active=1&page_size=200&ordering=nom`;
                if (q) url += `&search=${encodeURIComponent(q)}`;

                let data;
                try {
                    data = await api(url);
                } catch (err) {
                    data = await api(`${API}/ecoles/?leger=1&active=1&page_size=200&ordering=nom${q ? `&search=${encodeURIComponent(q)}` : ''}`);
                }
                let rows = data.results || data;
                if (!Array.isArray(rows)) rows = [];

                const total = data.count ?? rows.length;
                if (info) {
                    info.textContent = rows.length
                        ? `${rows.length}${total > rows.length ? ` / ${total}` : ''} école(s)`
                        : 'Aucune école';
                }

                if (!rows.length) {
                    selEcole.innerHTML = '<option value="">Aucune école trouvée</option>';
                    ecoleId = '';
                    majEtatEcoleSelection();
                    return;
                }

                // Pas de sélection automatique : l'utilisateur choisit l'école (étape 1)
                const previous = ecoleId || '';
                selEcole.innerHTML = `<option value="">— Choisir une école —</option>${
                    rows.map((e) => (
                        `<option value="${e.id}">${escapeHtml(e.nom)} (${escapeHtml(e.code || '')})</option>`
                    )).join('')
                }`;

                if (previous && [...selEcole.options].some((o) => o.value === String(previous))) {
                    selEcole.value = String(previous);
                    ecoleId = String(previous);
                } else {
                    ecoleId = '';
                    selEcole.value = '';
                }
                majEtatEcoleSelection();
            } catch (err) {
                selEcole.innerHTML = '<option value="">Erreur de chargement</option>';
                if (info) info.textContent = '';
                ecoleId = '';
                majEtatEcoleSelection();
                toast(err.message || 'Impossible de charger les écoles.', 'error');
            }
        }

        async function remplirSelectSections(selectEl, selected = '', includeEmpty = true) {
            if (!selectEl) return;
            selectEl.innerHTML = includeEmpty ? '<option value="">— Section —</option>' : '';
            if (!ecoleId) return;
            try {
                const data = await api(`${API}/sections-scolaires/?ecole=${ecoleId}&page_size=200`);
                const rows = data.results || data;
                selectEl.innerHTML = (includeEmpty ? '<option value="">— Section —</option>' : '')
                    + rows.map((s) => `<option value="${s.id}">${escapeHtml(s.nom)}${s.code ? ` (${escapeHtml(s.code)})` : ''}</option>`).join('');
                if (selected) selectEl.value = String(selected);
            } catch (err) {
                toast(err.message, 'error');
            }
        }

        async function remplirSelectOptions(selectEl, sectionId, selected = '', includeEmpty = true) {
            if (!selectEl) return;
            selectEl.innerHTML = includeEmpty ? '<option value="">— Option —</option>' : '';
            if (!ecoleId) return;
            let url = `${API}/options-scolaires/?ecole=${ecoleId}&page_size=200`;
            if (sectionId) url += `&section=${sectionId}`;
            try {
                const data = await api(url);
                const rows = data.results || data;
                selectEl.innerHTML = (includeEmpty ? '<option value="">— Option —</option>' : '')
                    + rows.map((o) => `<option value="${o.id}">${escapeHtml(o.nom)}${o.code ? ` (${escapeHtml(o.code)})` : ''}</option>`).join('');
                if (selected) selectEl.value = String(selected);
            } catch (err) {
                toast(err.message, 'error');
            }
        }

        async function remplirSelectClasses(selectEl, selected = '', includeEmpty = true) {
            if (!selectEl) return;
            selectEl.innerHTML = includeEmpty ? '<option value="">— Classe —</option>' : '';
            if (!ecoleId) return;
            try {
                const data = await api(`${API}/classes/?ecole=${ecoleId}&page_size=300`);
                const rows = data.results || data;
                selectEl.innerHTML = (includeEmpty ? '<option value="">— Classe —</option>' : '')
                    + rows.map((c) => `<option value="${c.id}">${escapeHtml(c.nom)}</option>`).join('');
                if (selected) selectEl.value = String(selected);
            } catch (err) {
                toast(err.message, 'error');
            }
        }

        async function rafraichirFiltres() {
            await Promise.all([
                remplirSelectSections(document.getElementById('filtreSectionOptions'), document.getElementById('filtreSectionOptions')?.value || '', true),
                remplirSelectSections(document.getElementById('filtreSectionClasses'), document.getElementById('filtreSectionClasses')?.value || '', true),
                remplirSelectClasses(document.getElementById('filtreClasseMatieres'), document.getElementById('filtreClasseMatieres')?.value || '', true),
            ]);
            const secCl = document.getElementById('filtreSectionClasses')?.value || '';
            await remplirSelectOptions(
                document.getElementById('filtreOptionClasses'),
                secCl,
                document.getElementById('filtreOptionClasses')?.value || '',
                true,
            );
            // Relabel empty options for filters
            const fo = document.getElementById('filtreSectionOptions');
            if (fo?.options[0]) fo.options[0].textContent = 'Toutes les sections';
            const fs = document.getElementById('filtreSectionClasses');
            if (fs?.options[0]) fs.options[0].textContent = 'Toutes les sections';
            const fop = document.getElementById('filtreOptionClasses');
            if (fop?.options[0]) fop.options[0].textContent = 'Toutes les options';
            const fc = document.getElementById('filtreClasseMatieres');
            if (fc?.options[0]) fc.options[0].textContent = 'Toutes les classes';
        }

        async function chargerSections(page = 1) {
            pageSections = page;
            const tbody = document.querySelector('#tableSections tbody');
            if (!tbody) return;
            if (!ecoleId) {
                tbody.innerHTML = emptyRow(5, 'Aucune école', 'Choisissez une école pour gérer les sections.');
                setCount('countSections', 0, 'section');
                return;
            }
            const q = (document.getElementById('searchSections')?.value || '').trim();
            let url = `${API}/sections-scolaires/?ecole=${ecoleId}&page=${page}&page_size=25`;
            if (q) url += `&search=${encodeURIComponent(q)}`;
            try {
                const data = await api(url);
                const rows = data.results || data;
                cacheSections = rows;
                const total = data.count ?? rows.length;
                setCount('countSections', total, 'section');
                if (!rows.length) {
                    tbody.innerHTML = emptyRow(5, 'Aucune section', 'Créez une section ou chargez le programme RDC.');
                    renderPagination('paginationSections', 1, 1, chargerSections);
                    return;
                }
                tbody.innerHTML = rows.map((s) => `
                    <tr>
                        <td data-label="Nom"><strong>${escapeHtml(s.nom)}</strong></td>
                        <td data-label="Code"><span class="code-chip">${escapeHtml(s.code || '—')}</span></td>
                        <td data-label="Options">${s.nb_options ?? 0}</td>
                        <td data-label="Statut">${statutBadge(s.active)}</td>
                        <td data-label="Actions">
                            <button type="button" class="btn btn-ghost btn-sm" data-edit-section="${s.id}">${ico('edit')}Modifier</button>
                        </td>
                    </tr>
                `).join('');
                tbody.querySelectorAll('[data-edit-section]').forEach((btn) => {
                    btn.addEventListener('click', () => {
                        const s = cacheSections.find((x) => String(x.id) === btn.dataset.editSection);
                        if (s) ouvrirModalSection(s);
                    });
                });
                const pages = data.count ? Math.ceil(data.count / 25) : 1;
                renderPagination('paginationSections', page, pages, chargerSections);
            } catch (err) {
                toast(err.message, 'error');
            }
        }

        async function chargerOptions(page = 1) {
            pageOptions = page;
            const tbody = document.querySelector('#tableOptions tbody');
            if (!tbody) return;
            if (!ecoleId) {
                tbody.innerHTML = emptyRow(5, 'Aucune école', 'Choisissez une école.');
                setCount('countOptions', 0, 'option');
                return;
            }
            const q = (document.getElementById('searchOptions')?.value || '').trim();
            const section = document.getElementById('filtreSectionOptions')?.value || '';
            let url = `${API}/options-scolaires/?ecole=${ecoleId}&page=${page}&page_size=25`;
            if (section) url += `&section=${section}`;
            if (q) url += `&search=${encodeURIComponent(q)}`;
            try {
                const data = await api(url);
                const rows = data.results || data;
                cacheOptions = rows;
                setCount('countOptions', data.count ?? rows.length, 'option');
                if (!rows.length) {
                    tbody.innerHTML = emptyRow(5, 'Aucune option', 'Créez une option pour une section.');
                    renderPagination('paginationOptions', 1, 1, chargerOptions);
                    return;
                }
                tbody.innerHTML = rows.map((o) => `
                    <tr>
                        <td data-label="Nom"><strong>${escapeHtml(o.nom)}</strong></td>
                        <td data-label="Code"><span class="code-chip">${escapeHtml(o.code || '—')}</span></td>
                        <td data-label="Section">${escapeHtml(o.section_nom || '—')}</td>
                        <td data-label="Statut">${statutBadge(o.active)}</td>
                        <td data-label="Actions">
                            <button type="button" class="btn btn-ghost btn-sm" data-edit-option="${o.id}">${ico('edit')}Modifier</button>
                        </td>
                    </tr>
                `).join('');
                tbody.querySelectorAll('[data-edit-option]').forEach((btn) => {
                    btn.addEventListener('click', () => {
                        const o = cacheOptions.find((x) => String(x.id) === btn.dataset.editOption);
                        if (o) ouvrirModalOption(o);
                    });
                });
                const pages = data.count ? Math.ceil(data.count / 25) : 1;
                renderPagination('paginationOptions', page, pages, chargerOptions);
            } catch (err) {
                toast(err.message, 'error');
            }
        }

        async function chargerClassesParam() {
            const container = document.getElementById('classesHierarchy');
            if (!container) return;
            if (!ecoleId) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>Aucune école</strong>
                        <span>Choisissez une école pour afficher les classes.</span>
                    </div>`;
                setCount('countClasses', 0, 'classe');
                return;
            }
            const q = (document.getElementById('searchClasses')?.value || '').trim();
            const section = document.getElementById('filtreSectionClasses')?.value || '';
            const option = document.getElementById('filtreOptionClasses')?.value || '';
            let url = `${API}/classes/?ecole=${ecoleId}&page_size=300&ordering=nom`;
            if (section) url += `&section=${section}`;
            if (option) url += `&option=${option}`;
            if (q) url += `&search=${encodeURIComponent(q)}`;
            container.innerHTML = '<p class="empty-state">Chargement des classes…</p>';
            try {
                const data = await api(url);
                const rows = data.results || data;
                cacheClasses = rows;
                setCount('countClasses', data.count ?? rows.length, 'classe');
                renderClassesHierarchy(container, rows, {
                    onEdit: (c) => ouvrirModalClasseParam(c),
                    expandSections: true,
                });
            } catch (err) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>Erreur</strong>
                        <span>${escapeHtml(err.message)}</span>
                    </div>`;
                toast(err.message, 'error');
            }
        }

        async function chargerMatieresParam(page = 1) {
            pageMatieres = page;
            const tbody = document.querySelector('#tableMatieresParam tbody');
            if (!tbody) return;
            if (!ecoleId) {
                tbody.innerHTML = emptyRow(9, 'Aucune école', 'Choisissez une école.');
                setCount('countMatieres', 0, 'matière');
                return;
            }
            const q = (document.getElementById('searchMatieres')?.value || '').trim();
            const classe = document.getElementById('filtreClasseMatieres')?.value || '';
            let url = `${API}/matieres/?ecole=${ecoleId}&page=${page}&page_size=25`;
            if (classe) url += `&classe=${classe}`;
            if (q) url += `&search=${encodeURIComponent(q)}`;
            try {
                const data = await api(url);
                const rows = data.results || data;
                cacheMatieres = rows;
                setCount('countMatieres', data.count ?? rows.length, 'matière');
                if (!rows.length) {
                    tbody.innerHTML = emptyRow(9, 'Aucune matière', 'Créez une matière ou chargez le catalogue.');
                    renderPagination('paginationMatieres', 1, 1, chargerMatieresParam);
                    return;
                }
                tbody.innerHTML = rows.map((m) => `
                    <tr>
                        <td data-label="Ordre">${m.ordre ?? 0}</td>
                        <td data-label="Nom"><strong>${escapeHtml(m.nom)}</strong></td>
                        <td data-label="Code"><span class="code-chip">${escapeHtml(m.code || '—')}</span></td>
                        <td data-label="Max">${m.maximum ?? '—'}</td>
                        <td data-label="Section">${escapeHtml(m.section_nom || '—')}</td>
                        <td data-label="Option">${escapeHtml(m.option_nom || '—')}</td>
                        <td data-label="Classe">${escapeHtml(m.classe_nom || '—')}</td>
                        <td data-label="Statut">${statutBadge(m.active)}</td>
                        <td data-label="Actions">
                            <button type="button" class="btn btn-ghost btn-sm" data-edit-matiere="${m.id}">${ico('edit')}Modifier</button>
                        </td>
                    </tr>
                `).join('');
                tbody.querySelectorAll('[data-edit-matiere]').forEach((btn) => {
                    btn.addEventListener('click', () => {
                        const m = cacheMatieres.find((x) => String(x.id) === btn.dataset.editMatiere);
                        if (m) ouvrirModalMatiereParam(m);
                    });
                });
                const pages = data.count ? Math.ceil(data.count / 25) : 1;
                renderPagination('paginationMatieres', page, pages, chargerMatieresParam);
            } catch (err) {
                toast(err.message, 'error');
            }
        }

        function ouvrirModalSection(row = null) {
            if (!requireEcole()) return;
            const form = document.getElementById('formSectionParam');
            form.reset();
            document.getElementById('sectionParamId').value = row?.id || '';
            document.getElementById('titreModalSection').textContent = row ? 'Modifier la section' : 'Nouvelle section';
            if (row) {
                form.nom.value = row.nom || '';
                form.code.value = row.code || '';
                form.active.value = row.active ? '1' : '0';
            }
            document.getElementById('btnSupprimerSection').hidden = !row;
            openModal('modalSectionParam');
        }

        async function ouvrirModalOption(row = null) {
            if (!requireEcole()) return;
            const form = document.getElementById('formOptionParam');
            form.reset();
            document.getElementById('optionParamId').value = row?.id || '';
            document.getElementById('titreModalOption').textContent = row ? 'Modifier l\'option' : 'Nouvelle option';
            await remplirSelectSections(document.getElementById('selectSectionOption'), row?.section || '', false);
            if (row) {
                form.nom.value = row.nom || '';
                form.code.value = row.code || '';
                form.active.value = row.active ? '1' : '0';
            }
            document.getElementById('btnSupprimerOption').hidden = !row;
            openModal('modalOptionParam');
        }

        async function ouvrirModalClasseParam(row = null) {
            if (!requireEcole()) return;
            const form = document.getElementById('formClasseParam');
            form.reset();
            document.getElementById('classeParamId').value = row?.id || '';
            document.getElementById('titreModalClasseParam').textContent = row ? 'Modifier la classe' : 'Nouvelle classe';
            await remplirSelectSections(document.getElementById('selectSectionClasse'), row?.section || '', false);
            await remplirSelectOptions(
                document.getElementById('selectOptionClasse'),
                row?.section || document.getElementById('selectSectionClasse')?.value,
                row?.option || '',
                false,
            );
            if (row) {
                form.nom.value = row.nom || '';
                form.code.value = row.code || '';
                form.active.value = row.active ? '1' : '0';
            }
            document.getElementById('btnSupprimerClasseParam').hidden = !row;
            openModal('modalClasseParam');
        }

        async function ouvrirModalMatiereParam(row = null) {
            if (!requireEcole()) return;
            const form = document.getElementById('formMatiereParam');
            form.reset();
            document.getElementById('matiereParamId').value = row?.id || '';
            document.getElementById('titreModalMatiereParam').textContent = row ? 'Modifier la matière' : 'Nouvelle matière';
            await remplirSelectSections(document.getElementById('selectSectionMatiere'), row?.section || '', true);
            await remplirSelectOptions(
                document.getElementById('selectOptionMatiere'),
                row?.section || '',
                row?.option || '',
                true,
            );
            await remplirSelectClasses(document.getElementById('selectClasseMatiere'), row?.classe || '', true);
            if (row) {
                form.nom.value = row.nom || '';
                form.code.value = row.code || '';
                form.maximum.value = row.maximum ?? 20;
                form.ordre.value = row.ordre ?? 0;
                form.active.value = row.active ? '1' : '0';
            } else {
                form.maximum.value = 20;
                form.ordre.value = 0;
            }
            document.getElementById('btnSupprimerMatiereParam').hidden = !row;
            openModal('modalMatiereParam');
        }

        function renderArbreAffectation(container, sections, { mode, filter = '' } = {}) {
            if (!container) return;
            const q = (filter || '').trim().toLowerCase();
            const filtered = (sections || []).map((sec) => {
                const options = (sec.options || []).filter((o) => {
                    const affectee = !!(o.deja_present && o.active);
                    if (mode === 'dispo' && affectee) return false;
                    if (mode === 'affecte' && !affectee) return false;
                    if (!q) return true;
                    const hay = `${sec.nom} ${sec.code} ${o.nom} ${o.code}`.toLowerCase();
                    return hay.includes(q);
                });
                return { ...sec, options };
            }).filter((sec) => sec.options.length);

            if (!filtered.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <strong>${mode === 'affecte' ? 'Aucune option affectée' : 'Rien à affecter'}</strong>
                        <span>${mode === 'affecte'
                            ? 'Affectez des options depuis le référentiel à gauche.'
                            : 'Toutes les options visibles sont déjà affectées, ou aucun résultat.'}</span>
                    </div>`;
                return;
            }

            const side = mode === 'affecte' ? 'aff' : 'dispo';
            container.innerHTML = filtered.map((sec) => `
                <div class="prog-rdc-section" data-aff-side="${side}">
                    <div class="prog-rdc-section-head">
                        <label>
                            <input type="checkbox" class="aff-sec-check" data-side="${side}">
                            <span>${escapeHtml(sec.nom)}</span>
                        </label>
                    </div>
                    <ul class="prog-rdc-options">
                        ${sec.options.map((o) => `
                            <li class="prog-rdc-option">
                                <label>
                                    <input type="checkbox" class="aff-opt-check" data-side="${side}"
                                        value="${escapeHtml(o.code || '')}"
                                        data-opt-code="${escapeHtml(o.code || '')}"
                                        data-option-id="${o.option_id || ''}">
                                    <span>${escapeHtml(o.nom)}</span>
                                    ${o.code ? `<span class="code-chip">${escapeHtml(o.code)}</span>` : ''}
                                </label>
                                <span class="prog-rdc-meta">${o.nb_classes || 0} cl.</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `).join('');

            container.querySelectorAll('.aff-sec-check').forEach((cb) => {
                cb.addEventListener('change', () => {
                    const box = cb.closest('.prog-rdc-section');
                    box?.querySelectorAll('.aff-opt-check').forEach((o) => {
                        o.checked = cb.checked;
                    });
                });
            });
        }

        let cacheReferentielAffect = { sections: [] };
        let niveauAffectation = 'prescolaire';

        function niveauCatalogueDepuisEcole(niveauEcole) {
            const n = String(niveauEcole || '').toLowerCase();
            if (n === 'creche' || n === 'crèche') return 'creche';
            if (n === 'maternelle') return 'prescolaire';
            if (n === 'primaire') return 'primaire';
            if (n === 'secondaire') return 'secondaire';
            return 'tous';
        }

        function majBoutonsNiveauAffectation(niveau) {
            document.querySelectorAll('#filtreNiveauAffectation [data-niveau-aff]').forEach((btn) => {
                btn.classList.toggle('is-active', btn.getAttribute('data-niveau-aff') === niveau);
            });
        }

        async function chargerAffectation() {
            const dispo = document.getElementById('affectationDispo');
            const affecte = document.getElementById('affectationAffecte');
            const countEl = document.getElementById('countAffectation');
            if (!dispo || !affecte) return;
            if (!ecoleId) {
                dispo.innerHTML = '<p class="empty-state">Choisissez une école…</p>';
                affecte.innerHTML = '<p class="empty-state">Choisissez une école…</p>';
                if (countEl) countEl.textContent = '—';
                return;
            }
            dispo.innerHTML = '<p class="empty-state">Chargement…</p>';
            affecte.innerHTML = '<p class="empty-state">Chargement…</p>';
            try {
                // Niveau explicite (évite un auto_niveau vide / serveur non rechargé)
                let url = `${API}/ecoles/${ecoleId}/referentiel-rdc/?niveau_programme=${encodeURIComponent(niveauAffectation)}`;
                let data = await api(url);
                if (!(data.sections || []).length && niveauAffectation !== 'tous') {
                    data = await api(`${API}/ecoles/${ecoleId}/referentiel-rdc/?niveau_programme=tous`);
                    if ((data.sections || []).length) {
                        niveauAffectation = 'tous';
                        majBoutonsNiveauAffectation('tous');
                    }
                }
                cacheReferentielAffect = data;
                const sections = data.sections || [];
                const nAff = sections.reduce(
                    (n, s) => n + (s.options || []).filter((o) => o.deja_present && o.active).length,
                    0,
                );
                if (countEl) {
                    countEl.textContent = sections.length
                        ? `${nAff} option(s) affectée(s) · ${sections.length} section(s)`
                        : 'Référentiel vide';
                }
                renderArbreAffectation(dispo, sections, {
                    mode: 'dispo',
                    filter: document.getElementById('searchAffectDispo')?.value || '',
                });
                renderArbreAffectation(affecte, sections, {
                    mode: 'affecte',
                    filter: document.getElementById('searchAffectAffecte')?.value || '',
                });
            } catch (err) {
                dispo.innerHTML = `<div class="empty-state"><strong>Erreur</strong><span>${escapeHtml(err.message)}</span></div>`;
                affecte.innerHTML = '';
                toast(err.message, 'error');
            }
        }

        function lireCodesOpt(side) {
            const rootId = side === 'aff' ? 'affectationAffecte' : 'affectationDispo';
            const root = document.getElementById(rootId);
            if (!root) return [];
            const codes = [];
            root.querySelectorAll('input.aff-opt-check:checked').forEach((el) => {
                const code = (el.value || el.getAttribute('data-opt-code') || '').trim();
                if (code && !codes.includes(code)) codes.push(code);
            });
            return codes;
        }

        async function rechargerOngletCourant() {
            const active = document.querySelector('#paramScolaireApp .tab-btn.active')?.dataset.tab || 'affectation';
            await Promise.all([rafraichirFiltres(), actualiserResume()]);
            if (active === 'affectation') await chargerAffectation();
            else if (active === 'sections') await chargerSections(1);
            else if (active === 'options') await chargerOptions(1);
            else if (active === 'classes') await chargerClassesParam();
            else if (active === 'matieres') await chargerMatieresParam(1);
        }

        // Tabs (scopés à cette page) + sync sous-menu Paramètres (?onglet=)
        document.querySelectorAll('#paramScolaireApp .tab-btn').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const tab = activerOngletStructure(btn.dataset.tab);
                const url = new URL(window.location.href);
                url.searchParams.set('onglet', tab);
                window.history.replaceState({}, '', url);
                // Mettre en évidence le lien du sous-menu
                document.querySelectorAll('.nav-group[data-nav-group="parametres"] .nav-sublink').forEach((a) => {
                    try {
                        const u = new URL(a.href, window.location.origin);
                        a.classList.toggle('active', u.searchParams.get('onglet') === tab);
                    } catch (_) { /* ignore */ }
                });
                try {
                    if (!ecoleId && tab !== 'affectation') {
                        toast('Étape 1 : sélectionnez d\'abord une école.', 'warning');
                        return;
                    }
                    if (tab === 'affectation') await chargerAffectation();
                    if (tab === 'sections') await chargerSections(1);
                    if (tab === 'options') {
                        await rafraichirFiltres();
                        await chargerOptions(1);
                    }
                    if (tab === 'classes') {
                        await rafraichirFiltres();
                        await chargerClassesParam();
                    }
                    if (tab === 'matieres') {
                        await rafraichirFiltres();
                        await chargerMatieresParam(1);
                    }
                } catch (err) {
                    toast(err.message, 'error');
                }
            });
        });

        selEcole?.addEventListener('change', async () => {
            ecoleId = selEcole.value || '';
            app.dataset.ecoleId = ecoleId;
            if (ecoleId) localStorage.setItem('educrdc_structure_ecole', ecoleId);
            else localStorage.removeItem('educrdc_structure_ecole');
            majEtatEcoleSelection();
            try {
                const url = new URL(window.location.href);
                if (ecoleId) url.searchParams.set('ecole', ecoleId);
                else url.searchParams.delete('ecole');
                window.history.replaceState({}, '', url);
            } catch (_) { /* ignore */ }
            if (!ecoleId) {
                await actualiserResume();
                return;
            }
            try {
                const eco = await api(`${API}/ecoles/${ecoleId}/?leger=1`);
                niveauAffectation = niveauCatalogueDepuisEcole(eco.niveau);
                majBoutonsNiveauAffectation(niveauAffectation);
            } catch (_) {
                niveauAffectation = 'prescolaire';
                majBoutonsNiveauAffectation(niveauAffectation);
            }
            // Conserver l'onglet courant (ex. Classes depuis le menu Référentiel)
            const tabCourant = document.querySelector('#paramScolaireApp .tab-btn.active')?.dataset.tab
                || 'affectation';
            activerOngletStructure(tabCourant);
            await rechargerOngletCourant();
        });

        document.getElementById('filtreNiveauAffectation')?.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-niveau-aff]');
            if (!btn) return;
            niveauAffectation = btn.getAttribute('data-niveau-aff') || 'tous';
            majBoutonsNiveauAffectation(niveauAffectation);
            if (ecoleId) {
                chargerAffectation().catch((err) => toast(err.message, 'error'));
            }
        });

        let searchEcoleTimer;
        document.getElementById('searchEcoleScolaire')?.addEventListener('input', (e) => {
            clearTimeout(searchEcoleTimer);
            searchEcoleTimer = setTimeout(async () => {
                try {
                    await chargerSelectEcoles(e.target.value || '');
                    await rechargerOngletCourant();
                } catch (err) {
                    toast(err.message, 'error');
                }
            }, 350);
        });

        document.getElementById('btnRefreshStructure')?.addEventListener('click', async () => {
            const q = document.getElementById('searchEcoleScolaire')?.value || '';
            try {
                await chargerSelectEcoles(q);
                await rechargerOngletCourant();
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        document.getElementById('searchAffectDispo')?.addEventListener('input', (e) => {
            renderArbreAffectation(document.getElementById('affectationDispo'), cacheReferentielAffect.sections || [], {
                mode: 'dispo', filter: e.target.value,
            });
        });
        document.getElementById('searchAffectAffecte')?.addEventListener('input', (e) => {
            renderArbreAffectation(document.getElementById('affectationAffecte'), cacheReferentielAffect.sections || [], {
                mode: 'affecte', filter: e.target.value,
            });
        });
        document.getElementById('btnAffToutDispo')?.addEventListener('click', () => {
            document.querySelectorAll('#affectationDispo .aff-opt-check, #affectationDispo .aff-sec-check')
                .forEach((o) => { o.checked = true; });
        });
        document.getElementById('btnAffRienDispo')?.addEventListener('click', () => {
            document.querySelectorAll('#affectationDispo .aff-opt-check, #affectationDispo .aff-sec-check')
                .forEach((o) => { o.checked = false; });
        });
        document.getElementById('btnAffToutAffecte')?.addEventListener('click', () => {
            document.querySelectorAll('#affectationAffecte .aff-opt-check, #affectationAffecte .aff-sec-check')
                .forEach((o) => { o.checked = true; });
        });
        document.getElementById('btnAffRienAffecte')?.addEventListener('click', () => {
            document.querySelectorAll('#affectationAffecte .aff-opt-check, #affectationAffecte .aff-sec-check')
                .forEach((o) => { o.checked = false; });
        });

        document.getElementById('btnAffecterOptions')?.addEventListener('click', async () => {
            if (!requireEcole()) return;
            const codes = lireCodesOpt('dispo');
            if (!codes.length) {
                toast('Cochez au moins une option dans la colonne « Référentiel EPSP » (à gauche).', 'warning');
                return;
            }
            try {
                const data = await api(`${API}/ecoles/${ecoleId}/affecter-structure/`, {
                    method: 'POST',
                    body: JSON.stringify({
                        niveau: niveauAffectation || 'tous',
                        options: codes,
                    }),
                });
                toast(data.detail || 'Structure affectée.', 'success');
                await Promise.all([chargerAffectation(), actualiserResume()]);
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        function demanderConfirmationRetirerOptions(nb) {
            return new Promise((resolve) => {
                const modal = document.getElementById('modalConfirmRetirerOptions');
                const msg = document.getElementById('confirmRetirerOptionsMsg');
                const btnOk = document.getElementById('btnConfirmRetirerOptions');
                if (!modal || !btnOk) {
                    resolve(false);
                    return;
                }
                if (msg) {
                    msg.textContent = `Retirer ${nb} option(s) de cette école ?`;
                }
                let settled = false;
                const cleanup = (ok) => {
                    if (settled) return;
                    settled = true;
                    btnOk.removeEventListener('click', onOk);
                    modal.querySelectorAll('[data-close]').forEach((el) => {
                        el.removeEventListener('click', onCancel);
                    });
                    modal.removeEventListener('click', onBackdrop);
                    closeModal('modalConfirmRetirerOptions');
                    resolve(ok);
                };
                const onOk = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    cleanup(true);
                };
                const onCancel = () => cleanup(false);
                const onBackdrop = (e) => {
                    if (e.target === modal && !modal.dataset.justOpened) cleanup(false);
                };
                btnOk.addEventListener('click', onOk);
                modal.querySelectorAll('[data-close]').forEach((el) => {
                    el.addEventListener('click', onCancel);
                });
                modal.addEventListener('click', onBackdrop);
                openModal('modalConfirmRetirerOptions');
            });
        }

        document.getElementById('btnRetirerOptions')?.addEventListener('click', async () => {
            if (!requireEcole()) return;
            const codes = lireCodesOpt('aff');
            if (!codes.length) {
                toast('Cochez au moins une option dans la colonne « Affecté à cette école » (à droite).', 'warning');
                return;
            }
            const ok = await demanderConfirmationRetirerOptions(codes.length);
            if (!ok) return;
            try {
                const data = await api(`${API}/ecoles/${ecoleId}/retirer-structure/`, {
                    method: 'POST',
                    body: JSON.stringify({ options: codes }),
                });
                toast(data.detail || 'Options retirées.', 'success');
                await Promise.all([chargerAffectation(), actualiserResume()]);
            } catch (err) {
                toast(err.message, 'error');
            }
        });

        // Sections CRUD
        document.getElementById('btnNouvelleSection')?.addEventListener('click', () => ouvrirModalSection());
        document.getElementById('btnSearchSections')?.addEventListener('click', () => chargerSections(1));
        document.getElementById('searchSections')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerSections(1);
        });
        document.getElementById('btnSupprimerSection')?.addEventListener('click', async () => {
            const id = document.getElementById('sectionParamId')?.value;
            if (!id || !confirm('Supprimer cette section ?')) return;
            try {
                await api(`${API}/sections-scolaires/${id}/`, { method: 'DELETE' });
                toast('Section supprimée.', 'success');
                closeModal('modalSectionParam');
                await rechargerOngletCourant();
            } catch (err) { toast(err.message, 'error'); }
        });
        document.getElementById('formSectionParam')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!requireEcole()) return;
            const form = e.target;
            if (!form.checkValidity()) { form.reportValidity(); return; }
            const id = document.getElementById('sectionParamId').value;
            const payload = {
                ecole: Number(ecoleId),
                nom: form.nom.value.trim(),
                code: (form.code.value || '').trim(),
                active: form.active.value === '1',
            };
            try {
                if (id) await api(`${API}/sections-scolaires/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                else await api(`${API}/sections-scolaires/`, { method: 'POST', body: JSON.stringify(payload) });
                toast(id ? 'Section mise à jour.' : 'Section créée.', 'success');
                closeModal('modalSectionParam');
                await rechargerOngletCourant();
            } catch (err) { toast(err.message, 'error'); }
        });

        // Options CRUD
        document.getElementById('btnNouvelleOption')?.addEventListener('click', () => ouvrirModalOption());
        document.getElementById('btnSearchOptions')?.addEventListener('click', () => chargerOptions(1));
        document.getElementById('filtreSectionOptions')?.addEventListener('change', () => chargerOptions(1));
        document.getElementById('searchOptions')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerOptions(1);
        });
        document.getElementById('btnSupprimerOption')?.addEventListener('click', async () => {
            const id = document.getElementById('optionParamId')?.value;
            if (!id || !confirm('Supprimer cette option ?')) return;
            try {
                await api(`${API}/options-scolaires/${id}/`, { method: 'DELETE' });
                toast('Option supprimée.', 'success');
                closeModal('modalOptionParam');
                await rechargerOngletCourant();
            } catch (err) { toast(err.message, 'error'); }
        });
        document.getElementById('formOptionParam')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            if (!form.checkValidity()) { form.reportValidity(); return; }
            const id = document.getElementById('optionParamId').value;
            const payload = {
                section: Number(form.section.value),
                nom: form.nom.value.trim(),
                code: (form.code.value || '').trim(),
                active: form.active.value === '1',
            };
            try {
                if (id) await api(`${API}/options-scolaires/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                else await api(`${API}/options-scolaires/`, { method: 'POST', body: JSON.stringify(payload) });
                toast(id ? 'Option mise à jour.' : 'Option créée.', 'success');
                closeModal('modalOptionParam');
                await rechargerOngletCourant();
            } catch (err) { toast(err.message, 'error'); }
        });

        // Classes CRUD
        document.getElementById('btnNouvelleClasseParam')?.addEventListener('click', () => ouvrirModalClasseParam());
        document.getElementById('btnSearchClasses')?.addEventListener('click', () => chargerClassesParam());
        document.getElementById('btnExpandClasses')?.addEventListener('click', () => {
            setHierarchyExpanded(document.getElementById('classesHierarchy'), true);
        });
        document.getElementById('btnCollapseClasses')?.addEventListener('click', () => {
            setHierarchyExpanded(document.getElementById('classesHierarchy'), false);
        });
        document.getElementById('filtreSectionClasses')?.addEventListener('change', async () => {
            await remplirSelectOptions(
                document.getElementById('filtreOptionClasses'),
                document.getElementById('filtreSectionClasses').value,
                '',
                true,
            );
            const fop = document.getElementById('filtreOptionClasses');
            if (fop?.options[0]) fop.options[0].textContent = 'Toutes les options';
            chargerClassesParam();
        });
        document.getElementById('filtreOptionClasses')?.addEventListener('change', () => chargerClassesParam());
        document.getElementById('searchClasses')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerClassesParam();
        });
        document.getElementById('selectSectionClasse')?.addEventListener('change', async (e) => {
            await remplirSelectOptions(document.getElementById('selectOptionClasse'), e.target.value, '', false);
        });
        document.getElementById('btnSupprimerClasseParam')?.addEventListener('click', async () => {
            const id = document.getElementById('classeParamId')?.value;
            if (!id || !confirm('Supprimer cette classe ?')) return;
            try {
                await api(`${API}/classes/${id}/`, { method: 'DELETE' });
                toast('Classe supprimée.', 'success');
                closeModal('modalClasseParam');
                await rechargerOngletCourant();
            } catch (err) { toast(err.message, 'error'); }
        });
        document.getElementById('formClasseParam')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!requireEcole()) return;
            const form = e.target;
            if (!form.checkValidity()) { form.reportValidity(); return; }
            const id = document.getElementById('classeParamId').value;
            const payload = {
                ecole: Number(ecoleId),
                section: Number(form.section.value),
                option: Number(form.option.value),
                nom: form.nom.value.trim(),
                code: (form.code.value || '').trim(),
                active: form.active.value === '1',
            };
            try {
                if (id) await api(`${API}/classes/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                else await api(`${API}/classes/`, { method: 'POST', body: JSON.stringify(payload) });
                toast(id ? 'Classe mise à jour.' : 'Classe créée.', 'success');
                closeModal('modalClasseParam');
                await rechargerOngletCourant();
            } catch (err) { toast(err.message, 'error'); }
        });

        // Matières CRUD
        document.getElementById('btnNouvelleMatiereParam')?.addEventListener('click', () => ouvrirModalMatiereParam());
        document.getElementById('btnSearchMatieres')?.addEventListener('click', () => chargerMatieresParam(1));
        document.getElementById('filtreClasseMatieres')?.addEventListener('change', () => chargerMatieresParam(1));
        document.getElementById('searchMatieres')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') chargerMatieresParam(1);
        });
        document.getElementById('selectSectionMatiere')?.addEventListener('change', async (e) => {
            await remplirSelectOptions(document.getElementById('selectOptionMatiere'), e.target.value, '', true);
        });
        document.getElementById('btnCatalogueMatieresParam')?.addEventListener('click', async () => {
            if (!requireEcole()) return;
            const regime = prompt('Régime du catalogue : primaire | secondaire', 'secondaire');
            if (regime === null) return;
            const r = (regime || 'secondaire').trim().toLowerCase();
            if (!['primaire', 'secondaire'].includes(r)) {
                toast('Régime invalide.', 'warning');
                return;
            }
            const classe = document.getElementById('filtreClasseMatieres')?.value || '';
            try {
                const data = await api(`${API}/matieres/charger-catalogue/`, {
                    method: 'POST',
                    body: JSON.stringify({
                        ecole: Number(ecoleId),
                        regime: r,
                        classe: classe ? Number(classe) : null,
                    }),
                });
                toast(data.detail || 'Catalogue chargé.', 'success');
                await chargerMatieresParam(1);
            } catch (err) { toast(err.message, 'error'); }
        });
        document.getElementById('btnSupprimerMatiereParam')?.addEventListener('click', async () => {
            const id = document.getElementById('matiereParamId')?.value;
            if (!id || !confirm('Supprimer cette matière ?')) return;
            try {
                await api(`${API}/matieres/${id}/`, { method: 'DELETE' });
                toast('Matière supprimée.', 'success');
                closeModal('modalMatiereParam');
                await chargerMatieresParam(pageMatieres);
            } catch (err) { toast(err.message, 'error'); }
        });
        document.getElementById('formMatiereParam')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!requireEcole()) return;
            const form = e.target;
            if (!form.checkValidity()) { form.reportValidity(); return; }
            const id = document.getElementById('matiereParamId').value;
            const payload = {
                ecole: Number(ecoleId),
                section: form.section.value ? Number(form.section.value) : null,
                option: form.option.value ? Number(form.option.value) : null,
                classe: form.classe.value ? Number(form.classe.value) : null,
                nom: form.nom.value.trim(),
                code: (form.code.value || '').trim(),
                maximum: Number(form.maximum.value),
                ordre: Number(form.ordre.value || 0),
                active: form.active.value === '1',
            };
            try {
                if (id) await api(`${API}/matieres/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) });
                else await api(`${API}/matieres/`, { method: 'POST', body: JSON.stringify(payload) });
                toast(id ? 'Matière mise à jour.' : 'Matière créée.', 'success');
                closeModal('modalMatiereParam');
                await chargerMatieresParam(1);
            } catch (err) { toast(err.message, 'error'); }
        });

        function activerOngletStructure(tabName) {
            const allowed = ['affectation', 'sections', 'options', 'classes', 'matieres'];
            const tab = allowed.includes(tabName) ? tabName : 'affectation';
            document.querySelectorAll('#paramScolaireApp .tab-btn').forEach((b) => {
                const on = b.dataset.tab === tab;
                b.classList.toggle('active', on);
                b.setAttribute('aria-selected', on ? 'true' : 'false');
            });
            document.querySelectorAll('#paramScolaireApp .tab-panel').forEach((panel) => {
                const on = panel.id === `tab-${tab}`;
                panel.hidden = !on;
                panel.classList.toggle('active', on);
            });
            return tab;
        }

        // Boot — école (?ecole=) puis onglet (?onglet=classes|affectation|…)
        (async () => {
            const params = new URLSearchParams(window.location.search);
            const ongletDemande = params.get('onglet') || params.get('tab') || 'affectation';
            const ecoleUrl = params.get('ecole');

            majEtatEcoleSelection();
            if (ecoleFigee && app.dataset.ecoleId) {
                ecoleId = String(app.dataset.ecoleId);
            } else if (ecoleUrl) {
                ecoleId = String(ecoleUrl);
            } else {
                ecoleId = '';
            }
            await chargerSelectEcoles();
            if (ecoleId && selEcole) selEcole.value = ecoleId;
            app.dataset.ecoleId = ecoleId || '';
            majEtatEcoleSelection();

            const onglet = activerOngletStructure(ongletDemande);
            const url = new URL(window.location.href);
            url.searchParams.set('onglet', onglet);
            if (ecoleId) url.searchParams.set('ecole', ecoleId);
            else url.searchParams.delete('ecole');
            window.history.replaceState({}, '', url);

            if (ecoleId) {
                try {
                    const eco = await api(`${API}/ecoles/${ecoleId}/?leger=1`);
                    niveauAffectation = niveauCatalogueDepuisEcole(eco.niveau);
                } catch (_) {
                    niveauAffectation = 'prescolaire';
                }
                majBoutonsNiveauAffectation(niveauAffectation);
                await rechargerOngletCourant();
            } else {
                majBoutonsNiveauAffectation(niveauAffectation);
                await actualiserResume();
                if (onglet !== 'affectation') {
                    toast('Sélectionnez d\'abord une école pour voir ses classes.', 'info');
                }
            }
        })().catch((err) => toast(err.message, 'error'));
    }

    function initProfil() {
        const btn = document.getElementById('btnOuvrirProfil');
        const modal = document.getElementById('modalProfil');
        if (!btn || !modal) return;
        bindModalClosers();

        function majAvatars(user) {
            const url = user.photo_url || '';
            const init = initials(user.first_name || user.username || 'U');
            const nom = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;

            const sideNom = document.getElementById('sidebarUserNom');
            if (sideNom) sideNom.textContent = nom;

            const sideAvatar = document.getElementById('sidebarUserAvatar');
            if (sideAvatar) {
                if (url) {
                    sideAvatar.innerHTML = `<img src="${escapeHtml(url)}" alt="" id="sidebarUserPhoto">`;
                } else {
                    sideAvatar.innerHTML = `<span id="sidebarUserInitial">${escapeHtml(init.slice(0, 1))}</span>`;
                }
            }

            const img = document.getElementById('profilPhotoImg');
            const fallback = document.getElementById('profilPhotoFallback');
            if (img && fallback) {
                if (url) {
                    img.src = url;
                    img.hidden = false;
                    fallback.hidden = true;
                } else {
                    img.removeAttribute('src');
                    img.hidden = true;
                    fallback.hidden = false;
                    fallback.textContent = init.slice(0, 1);
                }
            }
        }

        async function chargerProfil() {
            const user = await api(`${API}/utilisateurs/moi/`);
            document.getElementById('profilUsername').value = user.username || '';
            document.getElementById('profilRole').value = user.role_display || user.role || '';
            document.getElementById('profilFirstName').value = user.first_name || '';
            document.getElementById('profilLastName').value = user.last_name || '';
            document.getElementById('profilEmail').value = user.email || '';
            document.getElementById('profilTelephone').value = user.telephone || '';
            const gEcole = document.getElementById('groupeProfilEcole');
            const gClasse = document.getElementById('groupeProfilClasse');
            if (user.ecole_nom) {
                gEcole.hidden = false;
                document.getElementById('profilEcole').value = user.ecole_nom;
            } else {
                gEcole.hidden = true;
            }
            if (user.classe_nom) {
                gClasse.hidden = false;
                document.getElementById('profilClasse').value = [
                    user.section_nom, user.option_nom, user.classe_nom,
                ].filter(Boolean).join(' · ');
            } else {
                gClasse.hidden = true;
            }
            majAvatars(user);
            return user;
        }

        btn.addEventListener('click', async () => {
            try {
                await chargerProfil();
                document.getElementById('formProfilPassword')?.reset();
                openModal('modalProfil');
            } catch (err) {
                toast(err.message || 'Impossible de charger le profil.', 'error');
            }
        });

        document.getElementById('formProfil')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                email: document.getElementById('profilEmail').value.trim(),
                telephone: document.getElementById('profilTelephone').value.trim(),
            };
            try {
                const user = await api(`${API}/utilisateurs/moi/`, {
                    method: 'PATCH',
                    body: JSON.stringify(payload),
                });
                majAvatars(user);
                toast('Profil mis à jour.', 'success');
            } catch (err) {
                toast(err.message || 'Échec de la mise à jour.', 'error');
            }
        });

        document.getElementById('formProfilPassword')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const form = e.target;
            const payload = {
                mot_de_passe_actuel: form.mot_de_passe_actuel.value,
                nouveau_mot_de_passe: form.nouveau_mot_de_passe.value,
                confirmation: form.confirmation.value,
            };
            if (payload.nouveau_mot_de_passe !== payload.confirmation) {
                toast('La confirmation ne correspond pas.', 'warning');
                return;
            }
            try {
                await api(`${API}/utilisateurs/changer-mot-de-passe/`, {
                    method: 'POST',
                    body: JSON.stringify(payload),
                });
                form.reset();
                toast('Mot de passe mis à jour.', 'success');
            } catch (err) {
                toast(err.message || 'Échec du changement de mot de passe.', 'error');
            }
        });

        document.getElementById('inputProfilPhoto')?.addEventListener('change', async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const fd = new FormData();
            fd.append('photo', file);
            try {
                const user = await api(`${API}/utilisateurs/photo/`, {
                    method: 'POST',
                    body: fd,
                    headers: {},
                });
                majAvatars(user);
                toast('Photo de profil mise à jour.', 'success');
            } catch (err) {
                toast(err.message || 'Échec de l\'upload photo.', 'error');
            } finally {
                e.target.value = '';
            }
        });
    }

    // Profil disponible sur toutes les pages authentifiées
    if (document.getElementById('btnOuvrirProfil')) {
        initProfil();
    }

    return {
        chargerDashboard,
        initEcoles,
        initEleves,
        initEleveDetail,
        initEcoleDetail,
        initCartes,
        initRapports,
        initParametres,
        initParametresScolaire,
        initParametresAnnees,
        initParametresArretes,
        initUtilisateurs,
        initUtilisateurDetail,
        initMonitoringUtilisateurs,
        initMonitoringCarte,
        initEvaluations,
        initProfil,
        openModal,
        closeModal,
        toast,
        api,
    };
})();

window.EducRDC = EducRDC;

/* Géolocalisation navigateur (optionnelle) pour le monitoring admin */
(function initPresenceGeoClient() {
    function envoyer(position) {
        if (!window.EducRDC?.api) return;
        const { latitude, longitude, accuracy } = position.coords || {};
        if (latitude == null || longitude == null) return;
        EducRDC.api('/api/monitoring/presence-geo/', {
            method: 'POST',
            body: JSON.stringify({ latitude, longitude, accuracy }),
        }).catch(() => {});
    }

    function demarrer() {
        if (!document.querySelector('.user-chip')) return;
        if (!navigator.geolocation) return;
        const opts = { enableHighAccuracy: false, maximumAge: 300000, timeout: 8000 };
        navigator.geolocation.getCurrentPosition(envoyer, () => {}, opts);
        setInterval(() => {
            navigator.geolocation.getCurrentPosition(envoyer, () => {}, opts);
        }, 10 * 60 * 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', demarrer);
    } else {
        demarrer();
    }
})();
