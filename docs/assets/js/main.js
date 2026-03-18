/* Main JS for Archive News */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    // Event Listeners
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterList);
    }
});

function applyTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    updateThemeIcon(theme);

    // Update Iframe if exists
    const frame = document.getElementById('emailFrame');
    if (frame) {
        const doc = frame.contentDocument;
        if (doc) {
            const styleId = 'dm-filter';
            let oldStyle = doc.getElementById(styleId);
            if (oldStyle) oldStyle.remove();

            if (theme === 'dark') {
                doc.body.setAttribute('data-theme', 'dark');
                const style = doc.createElement('style');
                style.id = styleId;
                // Smart Inversion
                style.innerHTML = `
                    html { filter: invert(1) hue-rotate(180deg); }
                    img, video, iframe, [style*="background-image"] { filter: invert(1) hue-rotate(180deg); }
                `;
                doc.head.appendChild(style);
            } else {
                doc.body.setAttribute('data-theme', 'light');
            }
        }
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
        if (sun) sun.style.display = 'block';
        if (moon) moon.style.display = 'none';
    } else {
        if (sun) sun.style.display = 'none';
        if (moon) moon.style.display = 'block';
    }
}

/* Filtering Logic */
let activeCrm = 'all';

function filterByCrm(crm) {
    activeCrm = crm;
    document.querySelectorAll('.ix-chip').forEach(c => c.classList.remove('active'));
    const btn = crm === 'all'
        ? document.querySelector('.ix-chip-all')
        : document.querySelector(`.ix-chip[data-crm="${CSS.escape(crm)}"]`);
    if (btn) btn.classList.add('active');
    filterList();
}

function filterList() {
    const input = document.getElementById('searchInput');
    if (!input) return;
    const filter = input.value.toLowerCase();
    const list = document.getElementById('newsList');
    if (!list) return;
    const items = list.querySelectorAll('.news-card');
    let visibleCount = 0;

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

        const crmMatch = activeCrm === 'all' || (item.dataset.crm || 'Unknown') === activeCrm;

        if ((!filter || matches) && crmMatch) {
            item.style.display = "";
            visibleCount++;
            if (filter && matches) {
                if (titleEl) {
                    if (titleEl.dataset.original === undefined) titleEl.dataset.original = titleEl.innerHTML;
                    titleEl.innerHTML = _highlightText(titleEl.textContent, filter);
                }
                if (senderEl) {
                    if (senderEl.dataset.original === undefined) senderEl.dataset.original = senderEl.innerHTML;
                    senderEl.innerHTML = _highlightText(senderEl.textContent, filter);
                }
            }
        } else {
            item.style.display = "none";
        }
    });

    const noResults = document.getElementById('noResults');
    if (noResults) {
        noResults.style.display = visibleCount === 0 ? "block" : "none";
    }
}

function _highlightText(text, query) {
    const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const safeText = esc(text);
    const safeQuery = esc(query);
    const regexQuery = safeQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return safeText.replace(new RegExp(`(${regexQuery})`, 'gi'), '<mark>$1</mark>');
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
