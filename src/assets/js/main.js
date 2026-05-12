/* Main JS for Archive News */

/* Pagination */
const PAGE_SIZE = 20;
let currentPage = 1;

function renderPage() {
    const list = document.getElementById('newsList');
    if (!list) return;
    const allItems = list.querySelectorAll('.news-card');
    const visibleItems = Array.from(allItems).filter(el => !el.dataset.filteredOut);
    const totalPages = Math.max(1, Math.ceil(visibleItems.length / PAGE_SIZE));
    currentPage = Math.min(currentPage, totalPages);
    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const visibleSet = new Map(visibleItems.map((item, i) => [item, i]));
    allItems.forEach(item => {
        if (item.dataset.filteredOut) {
            item.style.display = 'none';
        } else {
            const idx = visibleSet.get(item);
            item.style.display = (idx >= start && idx < end) ? '' : 'none';
        }
    });
    const noResults = document.getElementById('noResults');
    if (noResults) noResults.style.display = visibleItems.length === 0 ? 'block' : 'none';
    updatePaginationUI(currentPage, totalPages);
}

function updatePaginationUI(page, totalPages) {
    const wrapper = document.getElementById('paginationWrapper');
    const prevBtn = document.getElementById('paginationPrev');
    const nextBtn = document.getElementById('paginationNext');
    const pageInfo = document.getElementById('paginationInfo');
    if (!wrapper) return;
    wrapper.style.display = totalPages > 1 ? 'flex' : 'none';
    if (prevBtn) prevBtn.disabled = page <= 1;
    if (nextBtn) nextBtn.disabled = page >= totalPages;
    if (pageInfo) pageInfo.textContent = totalPages > 1 ? `Page ${page} of ${totalPages}` : '';
}

function changePage(delta) {
    currentPage += delta;
    renderPage();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function _resolveInitialTheme() {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark' || stored === 'light') return stored;
    try {
        return window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark' : 'light';
    } catch (_) { return 'light'; }
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Theme (honors prefers-color-scheme when user hasn't toggled)
    applyTheme(_resolveInitialTheme());

    // React to live OS-level theme changes when the user hasn't manually chosen
    if (window.matchMedia) {
        try {
            const mq = window.matchMedia('(prefers-color-scheme: dark)');
            const onChange = e => {
                if (!localStorage.getItem('theme')) {
                    applyTheme(e.matches ? 'dark' : 'light');
                }
            };
            if (mq.addEventListener) mq.addEventListener('change', onChange);
            else if (mq.addListener) mq.addListener(onChange); // Safari <14
        } catch (_) { /* ignore */ }
    }

    // Debounced search
    let _searchTimer = null;
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(_searchTimer);
            _searchTimer = setTimeout(filterList, 200);
        });
    }

    // Initial pagination render
    renderPage();

    // Watch emailFrame class changes (setMode adds/removes no-scrollbar)
    // so scrollbar CSS inside the iframe stays in sync with the mode
    const emailFrame = document.getElementById('emailFrame');
    if (emailFrame) {
        new MutationObserver(() => {
            const doc = emailFrame.contentDocument;
            if (doc && doc.head) {
                const theme = document.body.getAttribute('data-theme') || 'light';
                _applyIframeScrollbar(emailFrame, doc, theme);
                _applyMobileScaling(emailFrame, doc);
            }
        }).observe(emailFrame, { attributes: true, attributeFilter: ['class'] });
    }
});

function applyTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    updateThemeIcon(theme);

    // Update Iframe if exists
    const frame = document.getElementById('emailFrame');
    if (frame) {
        const doc = frame.contentDocument;
        if (doc && doc.head) {
            const styleId = 'dm-filter';
            let oldStyle = doc.getElementById(styleId);
            if (oldStyle) oldStyle.remove();

            if (theme === 'dark') {
                if (doc.body) doc.body.setAttribute('data-theme', 'dark');
                const style = doc.createElement('style');
                style.id = styleId;
                // Smart Inversion
                style.innerHTML = `
                    html { filter: invert(1) hue-rotate(180deg); }
                    img, video, iframe, [style*="background-image"] { filter: invert(1) hue-rotate(180deg); }
                `;
                doc.head.appendChild(style);
            } else {
                if (doc.body) doc.body.setAttribute('data-theme', 'light');
            }

            _applyIframeScrollbar(frame, doc, theme);
        }
    }
}

/* Inject scrollbar CSS into the iframe document.
   hide=true  → scrollbar hidden but content still scrollable (mobile/tablet)
   hide=false → thin themed scrollbar (desktop) */
function _applyIframeScrollbar(frameEl, doc, theme) {
    if (!doc || !doc.head) return;
    const hide = frameEl.classList.contains('no-scrollbar');
    const styleId = 'sb-style';
    let sbStyle = doc.getElementById(styleId);
    if (!sbStyle) {
        sbStyle = doc.createElement('style');
        sbStyle.id = styleId;
        doc.head.appendChild(sbStyle);
    }
    if (hide) {
        sbStyle.innerHTML = `
            html, body { scrollbar-width: none !important; overflow-y: auto !important; }
            html::-webkit-scrollbar, body::-webkit-scrollbar { display: none !important; }
        `;
    } else {
        const thumb = theme === 'dark' ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)';
        sbStyle.innerHTML = `
            html::-webkit-scrollbar { width: 6px; }
            html::-webkit-scrollbar-track { background: transparent; }
            html::-webkit-scrollbar-thumb { background: ${thumb}; border-radius: 3px; }
            html { scrollbar-width: thin; scrollbar-color: ${thumb} transparent; }
        `;
    }
}

/* Scale email content to fit narrow device frames (mobile/tablet).
   Uses CSS zoom so layout and scrolling both work naturally. */
function _applyMobileScaling(frameEl, doc) {
    if (!doc || !doc.head || !doc.body) return;
    const styleId = 'mobile-scale-style';
    let el = doc.getElementById(styleId);
    if (!el) {
        el = doc.createElement('style');
        el.id = styleId;
        doc.head.appendChild(el);
    }
    const isMobile = frameEl.classList.contains('no-scrollbar');
    if (!isMobile) { el.innerHTML = ''; return; }

    el.innerHTML = ''; // reset zoom before measuring natural width
    doc.body.offsetHeight; // force layout flush so @media-driven CSS settles
    const naturalWidth = doc.body.scrollWidth;
    const frameWidth = frameEl.getBoundingClientRect().width;
    // 4px tolerance + only zoom when content really overflows. The iframe's
    // own @media query (max-width: 480px) already collapses wide tables; if
    // it succeeded, scrollWidth ≈ frameWidth and we skip zoom so text stays
    // legible at native size.
    if (frameWidth > 0 && naturalWidth > frameWidth + 4) {
        const scale = (frameWidth / naturalWidth).toFixed(4);
        el.innerHTML = `html { zoom: ${scale}; }`;
    }
}

function toggleTheme() {
    const current = document.body.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const sun = btn.querySelector('.icon-sun');
    const moon = btn.querySelector('.icon-moon');
    if (theme === 'dark') {
        if (sun) sun.style.display = 'none';
        if (moon) moon.style.display = 'block';
    } else {
        if (sun) sun.style.display = 'block';
        if (moon) moon.style.display = 'none';
    }
}

/* Filtering Logic */
let activeCrms = new Set(); // empty = show all

document.addEventListener('DOMContentLoaded', () => {
    const chipRow = document.getElementById('crmFilterRow');
    if (chipRow) {
        chipRow.addEventListener('click', e => {
            const chip = e.target.closest('.ix-chip');
            if (!chip) return;
            const crm = chip.dataset.crm;
            if (crm === 'all') {
                activeCrms.clear();
            } else {
                if (activeCrms.has(crm)) {
                    activeCrms.delete(crm);
                } else {
                    activeCrms.add(crm);
                }
            }
            _updateChipActiveState();
            filterList();
        });
    }
});

function _updateChipActiveState() {
    document.querySelectorAll('.ix-chip').forEach(c => {
        const crm = c.dataset.crm;
        if (crm === 'all') {
            c.classList.toggle('active', activeCrms.size === 0);
        } else {
            c.classList.toggle('active', activeCrms.has(crm));
        }
    });
}

function filterList() {
    const input = document.getElementById('searchInput');
    if (!input) return;
    const filter = input.value.toLowerCase();
    const list = document.getElementById('newsList');
    if (!list) return;
    const items = list.querySelectorAll('.news-card');

    // Compile regex once outside the per-card loop
    const searchRegex = filter
        ? new RegExp(filter.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
        : null;

    items.forEach(item => {
        const titleEl = item.querySelector('.card-title');
        const senderEl = item.querySelector('.sender-pill');

        // Restore original text before re-evaluating
        if (titleEl && titleEl.dataset.original !== undefined) {
            titleEl.innerHTML = titleEl.dataset.original;
        }
        if (senderEl && senderEl.dataset.original !== undefined) {
            senderEl.innerHTML = senderEl.dataset.original;
        }

        const title = titleEl?.textContent || "";
        const sender = senderEl?.textContent || "";
        const preview = item.querySelector('.card-preview')?.textContent || "";

        const matches = filter && (
            title.toLowerCase().includes(filter) ||
            sender.toLowerCase().includes(filter) ||
            preview.toLowerCase().includes(filter)
        );

        const crmMatch = activeCrms.size === 0 || activeCrms.has(item.dataset.crm || 'Unknown');
        const show = (!filter || matches) && crmMatch;

        item.dataset.filteredOut = show ? '' : 'true';

        if (show && filter && matches && searchRegex) {
            if (titleEl) {
                if (titleEl.dataset.original === undefined) titleEl.dataset.original = titleEl.innerHTML;
                searchRegex.lastIndex = 0;
                titleEl.innerHTML = _highlightText(titleEl.textContent, searchRegex);
            }
            if (senderEl) {
                if (senderEl.dataset.original === undefined) senderEl.dataset.original = senderEl.innerHTML;
                searchRegex.lastIndex = 0;
                senderEl.innerHTML = _highlightText(senderEl.textContent, searchRegex);
            }
        }
    });

    currentPage = 1;
    renderPage();
}

function _highlightText(text, regex) {
    const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const safeText = esc(text);
    regex.lastIndex = 0;
    return safeText.replace(regex, '<mark>$&</mark>');
}

/* Sorting Logic */
function sortList() {
    const select = document.getElementById('sortSelect');
    if (!select) return;
    const criteria = select.value;
    const list = document.getElementById('newsList');
    if (!list) return;

    const items = Array.from(list.getElementsByClassName('news-card'));

    items.sort((a, b) => {
        let valA = "", valB = "";
        if (criteria.startsWith('date')) {
            valA = a.getAttribute('data-date') || "";
            valB = b.getAttribute('data-date') || "";
            return criteria.endsWith('desc') ? valB.localeCompare(valA) : valA.localeCompare(valB);
        } else if (criteria.startsWith('sender')) {
            valA = (a.getAttribute('data-sender') || "").toLowerCase();
            valB = (b.getAttribute('data-sender') || "").toLowerCase();
            return criteria.endsWith('az') ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return 0;
    });

    // Re-append items in new order
    items.forEach(item => list.appendChild(item));
    currentPage = 1;
    renderPage();
}

/* Clipboard Utilities */
function copyToClipboard(text, btn) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓';
        btn.classList.add('copy-success');
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('copy-success');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

async function screenshotEmail(btn) {
    const iframe = document.getElementById('emailFrame');
    const deviceFrame = document.getElementById('deviceFrame');
    if (!iframe || !iframe.contentDocument || !iframe.contentDocument.documentElement) {
        alert('Email not loaded yet.');
        return;
    }

    const mode = deviceFrame ? (deviceFrame.dataset.mode || 'email') : 'email';
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px;margin-right:4px"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>…';

    try {
        const doc = iframe.contentDocument;
        const target = doc.documentElement;
        const canvas = await html2canvas(target, {
            useCORS: true,
            allowTaint: false,
            logging: false,
            scrollX: 0,
            scrollY: 0,
            windowWidth: iframe.contentWindow.innerWidth,
            windowHeight: doc.documentElement.scrollHeight,
            width: iframe.contentWindow.innerWidth,
            height: doc.documentElement.scrollHeight,
        });

        const a = document.createElement('a');
        const subject = document.querySelector('.vh-subject')?.textContent?.trim() || 'email';
        const safe = subject.replace(/[^\w\s-]/g, '').replace(/\s+/g, '-').toLowerCase().slice(0, 60);
        a.download = `${safe}-${mode}.png`;
        a.href = canvas.toDataURL('image/png');
        a.click();
    } catch (err) {
        console.error('Screenshot failed:', err);
        alert('Screenshot failed. Please try again.');
    } finally {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

/* Link Highlighting from Sidebar List */
function highlightLink(idx) {
    const frame = document.getElementById('emailFrame');
    if (!frame) return;
    const doc = frame.contentDocument;

    doc.querySelectorAll('.highlight-temp').forEach(el => {
        el.classList.remove('highlight-temp');
        el.style.outline = '';
    });

    const link = doc.querySelector(`a[data-index="${idx}"]`);
    if (link) {
        link.scrollIntoView({ behavior: 'smooth', block: 'center' });
        link.style.outline = '3px solid #ffff00';
        link.style.transition = 'outline 0.5s';
        setTimeout(() => { link.style.outline = '2px solid red'; }, 600);
    }
}

/* Copy Links Feature */
function copyLinks(links) {
    if (!links || links.length === 0) return;
    const text = links.map(l => l.original_url).join('\n');
    navigator.clipboard.writeText(text).then(() => {
        alert('Links copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy: ', err);
        // Fallback or alert
        alert('Failed to copy links.');
    });
}
