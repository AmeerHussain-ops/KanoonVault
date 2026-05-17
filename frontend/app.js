/**
 * KanoonVault – Frontend Application v2
 * Key improvements:
 *  - Per-case isolated chat histories (no cross-case message bleed)
 *  - Sidebar search (live filter)
 *  - Status filter tabs (All / Active / Closed / Reopened)
 *  - Case status management menu (close / reopen / activate)
 *  - Clear Chat per case
 *  - Soft delete → Trash, restore, permanent purge + retention purge (backend)
 */

const API = '';

// ── State ──────────────────────────────────────────────────────────────────
let activeCaseId = null;
let activeCaseName = null;
let activeStatus = 'active';
let isStreaming = false;
let allCases = [];
/** Soft-deleted cases for Trash tab (from GET /cases/trash) */
let trashCases = [];
let permanentDeleteTargetId = null;
let currentFilter = 'all';
let searchQuery = '';

/**
 * Per-case chat history store.
 * chatHistories[caseId] = array of { role, html }
 * We store rendered HTML so we can restore bubbles exactly.
 */
const chatHistories = {};

// ── DOM ────────────────────────────────────────────────────────────────────
const messagesEl = document.getElementById('messages');
const chatInput = document.getElementById('chat-input');
const btnSend = document.getElementById('btn-send');
const btnUpload = document.getElementById('btn-upload');
const fileInput = document.getElementById('file-input');
const casesList = document.getElementById('cases-list');
const caseBanner = document.getElementById('case-banner');
const bannerName = document.getElementById('banner-name');
const bannerStatusBadge = document.getElementById('banner-status-badge');
const btnViewTL = document.getElementById('btn-view-timeline');
const btnViewDocs = document.getElementById('btn-view-documents');
const timelinePanel = document.getElementById('timeline-panel');
const timelineEvts = document.getElementById('timeline-events');
const btnCloseTL = document.getElementById('btn-close-timeline');
const documentsPanel = document.getElementById('documents-panel');
const documentsListEl = document.getElementById('documents-list');
const documentsEmptyEl = document.getElementById('documents-empty');
const btnCloseDocs = document.getElementById('btn-close-documents');
const btnDeleteCase = document.getElementById('btn-delete-case');
const deleteModalOverlay = document.getElementById('delete-modal-overlay');
const btnDeleteModalCancel = document.getElementById('btn-delete-modal-cancel');
const btnDeleteModalConfirm = document.getElementById('btn-delete-modal-confirm');
const permanentModalOverlay = document.getElementById('permanent-delete-modal-overlay');
const btnPermanentModalCancel = document.getElementById('btn-permanent-modal-cancel');
const btnPermanentModalConfirm = document.getElementById('btn-permanent-modal-confirm');
const previewModalOverlay = document.getElementById('preview-modal-overlay');
const previewModalBody = document.getElementById('preview-modal-body');
const previewModalTitle = document.getElementById('preview-modal-title');
const btnClosePreview = document.getElementById('btn-close-preview');
const toastEl = document.getElementById('toast');
const ollamaStatus = document.getElementById('ollama-status');
const welcomeScreen = document.getElementById('welcome-screen');
const modalOverlay = document.getElementById('modal-overlay');
const modalInput = document.getElementById('modal-case-name');
const btnNewCase = document.getElementById('btn-new-case');
const btnModalCancel = document.getElementById('btn-modal-cancel');
const btnModalCreate = document.getElementById('btn-modal-create');
const sidebarSearch = document.getElementById('sidebar-search');
const btnStatusMenu = document.getElementById('btn-status-menu');
const statusDropdown = document.getElementById('status-dropdown');
const btnClearChat = document.getElementById('btn-clear-chat');

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    (async () => {
        await loadCases();
        renderCasesList();
        checkOllama();
        setupListeners();
    })();
});

// ── Event Listeners ────────────────────────────────────────────────────────
function setupListeners() {
    // Chat
    btnSend.addEventListener('click', handleSend);
    chatInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    });
    chatInput.addEventListener('input', autoResizeTextarea);

    // Upload
    btnUpload.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) handleFileUpload(fileInput.files[0]);
        fileInput.value = '';
    });

    // Timeline
    btnViewTL.addEventListener('click', () => loadTimeline(activeCaseId));
    btnCloseTL.addEventListener('click', () => timelinePanel.classList.remove('open'));

    // Documents
    if (btnViewDocs) btnViewDocs.addEventListener('click', () => openDocumentsPanel(activeCaseId));
    if (btnCloseDocs) btnCloseDocs.addEventListener('click', () => documentsPanel.classList.remove('open'));

    // Delete case
    if (btnDeleteCase) btnDeleteCase.addEventListener('click', openDeleteCaseModal);
    if (btnDeleteModalCancel) btnDeleteModalCancel.addEventListener('click', () => deleteModalOverlay.classList.remove('open'));
    if (btnDeleteModalConfirm) btnDeleteModalConfirm.addEventListener('click', confirmDeleteCase);
    if (deleteModalOverlay) {
        deleteModalOverlay.addEventListener('click', e => {
            if (e.target === deleteModalOverlay) deleteModalOverlay.classList.remove('open');
        });
    }
    if (btnPermanentModalCancel) {
        btnPermanentModalCancel.addEventListener('click', () => {
            permanentDeleteTargetId = null;
            permanentModalOverlay?.classList.remove('open');
        });
    }
    if (btnPermanentModalConfirm) btnPermanentModalConfirm.addEventListener('click', confirmPermanentDeleteFromTrash);
    if (permanentModalOverlay) {
        permanentModalOverlay.addEventListener('click', e => {
            if (e.target === permanentModalOverlay) {
                permanentDeleteTargetId = null;
                permanentModalOverlay.classList.remove('open');
            }
        });
    }
    if (btnClosePreview) btnClosePreview.addEventListener('click', closePreviewModal);
    if (previewModalOverlay) {
        previewModalOverlay.addEventListener('click', e => {
            if (e.target === previewModalOverlay) closePreviewModal();
        });
    }

    // Status dropdown toggle
    btnStatusMenu.addEventListener('click', (e) => {
        e.stopPropagation();
        statusDropdown.classList.toggle('hidden');
    });

    // Status options
    document.querySelectorAll('.status-option').forEach(opt => {
        opt.addEventListener('click', () => {
            const newStatus = opt.dataset.status;
            statusDropdown.classList.add('hidden');
            if (activeCaseId) updateCaseStatus(activeCaseId, newStatus);
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', () => statusDropdown.classList.add('hidden'));

    // Clear chat
    btnClearChat.addEventListener('click', clearChat);

    // Modals
    btnNewCase.addEventListener('click', openModal);
    btnModalCancel.addEventListener('click', closeModal);
    btnModalCreate.addEventListener('click', createCaseFromModal);
    modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });
    modalInput.addEventListener('keydown', e => { if (e.key === 'Enter') createCaseFromModal(); });

    // Suggestion chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chatInput.value = chip.dataset.prompt;
            chatInput.focus();
        });
    });

    // Drag-and-drop
    document.getElementById('chat-area').addEventListener('dragover', e => e.preventDefault());
    document.getElementById('chat-area').addEventListener('drop', e => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });

    // Sidebar search
    sidebarSearch.addEventListener('input', () => {
        searchQuery = sidebarSearch.value.trim().toLowerCase();
        renderCasesList();
    });

    // Status filter tabs (+ Trash)
    document.querySelectorAll('.status-tab').forEach(tab => {
        tab.addEventListener('click', async () => {
            document.querySelectorAll('.status-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentFilter = tab.dataset.filter;
            await refreshCasesSidebarData();
        });
    });
}

// ── Ollama ─────────────────────────────────────────────────────────────────
async function checkOllama() {
    if (!ollamaStatus) return;
    try {
        const r = await fetch('http://localhost:11434/api/tags', { signal: AbortSignal.timeout(3000) });
        if (r.ok) {
            ollamaStatus.textContent = 'Qwen AI Ready';
            ollamaStatus.style.color = 'var(--success)';
        }
    } catch {
        ollamaStatus.textContent = 'AI Offline';
        ollamaStatus.style.color = 'var(--danger)';
    }
}

// ── Cases ──────────────────────────────────────────────────────────────────
async function loadCases() {
    try {
        allCases = await fetch(`${API}/cases`).then(r => r.json());
    } catch (e) {
        console.error('Failed to load cases:', e);
    }
}

async function loadTrashCases() {
    try {
        trashCases = await fetch(`${API}/cases/trash`).then(r => r.json());
    } catch (e) {
        console.error('Failed to load Trash:', e);
        trashCases = [];
    }
}

async function refreshCasesSidebarData() {
    if (currentFilter === 'trash') await loadTrashCases();
    else await loadCases();
    renderCasesList();
}

function renderCasesList() {
    if (currentFilter === 'trash') {
        let filtered = trashCases || [];

        if (searchQuery) {
            filtered = filtered.filter(c =>
                String(c.case_name || '').toLowerCase().includes(searchQuery) ||
                String(c.deleted_at || '').toLowerCase().includes(searchQuery) ||
                String(c.deleted_by || '').toLowerCase().includes(searchQuery)
            );
        }

        if (!filtered.length) {
            const msg = searchQuery
                ? `No Trash items matching "<strong>${escHtml(searchQuery)}</strong>"`
                : 'Trash is empty.<br />Deleted cases appear here.';
            casesList.innerHTML = `<div class="empty-cases">${msg}</div>`;
            return;
        }

        casesList.innerHTML = '';
        filtered.forEach(c => {
            const item = document.createElement('div');
            item.className = 'case-item trash-case';
            item.dataset.caseId = c.id;
            const delBy = escHtml(c.deleted_by || '—');
            const delAt = escHtml(c.deleted_at || '—');
            item.innerHTML = `
      <div class="case-item-name">${escHtml(c.case_name)}</div>
      <div class="case-item-meta">
        <span>Deleted ${delAt}</span>
        <span> · By ${delBy}</span>
        <span class="case-doc-count">${c.doc_count} doc${c.doc_count !== 1 ? 's' : ''}</span>
      </div>
      <div class="trash-case-actions">
        <button type="button" class="btn-restore-case" data-id="${c.id}">Restore</button>
        <button type="button" class="btn-purge-case" data-id="${c.id}">Delete permanently</button>
      </div>
    `;
            item.querySelector('.btn-restore-case').addEventListener('click', ev => {
                ev.stopPropagation();
                restoreTrashCase(parseInt(ev.currentTarget.dataset.id, 10));
            });
            item.querySelector('.btn-purge-case').addEventListener('click', ev => {
                ev.stopPropagation();
                const id = parseInt(ev.currentTarget.dataset.id, 10);
                openPermanentDeleteModal(id, c.case_name || '');
            });
            casesList.appendChild(item);
        });
        return;
    }

    let filtered = allCases || [];

    if (currentFilter !== 'all') {
        filtered = filtered.filter(c => c.status === currentFilter);
    }

    if (searchQuery) {
        filtered = filtered.filter(c =>
            c.case_name.toLowerCase().includes(searchQuery) ||
            (c.case_number || '').toLowerCase().includes(searchQuery) ||
            (c.court_name || '').toLowerCase().includes(searchQuery)
        );
    }

    if (!filtered || filtered.length === 0) {
        const msg = searchQuery
            ? `No cases matching "<strong>${escHtml(searchQuery)}</strong>"`
            : currentFilter !== 'all'
                ? `No <strong>${currentFilter}</strong> cases`
                : 'No cases yet.<br />Upload a document to get started.';
        casesList.innerHTML = `<div class="empty-cases">${msg}</div>`;
        return;
    }

    casesList.innerHTML = '';
    filtered.forEach(c => {
        const isActive = c.id === activeCaseId;
        const item = document.createElement('div');
        item.className = `case-item${isActive ? ' active' : ''}`;
        item.dataset.caseId = c.id;
        item.innerHTML = `
      <div class="case-item-name">${escHtml(c.case_name)}</div>
      <div class="case-item-meta">
        <span class="case-badge badge-${c.status}">${c.status}</span>
        <span class="case-doc-count">${c.doc_count} doc${c.doc_count !== 1 ? 's' : ''}</span>
      </div>
    `;
        item.addEventListener('click', () => switchCase(c.id, c.case_name, c.status));
        casesList.appendChild(item);
    });
}

// ── Case switch (isolated chat) ─────────────────────────────────────────────
function switchCase(caseId, caseName, status) {
    if (activeCaseId === caseId) return; // already active

    // Save current chat history if there is one
    if (activeCaseId !== null) {
        chatHistories[activeCaseId] = collectCurrentMessages();
    }

    activeCaseId = caseId;
    activeCaseName = caseName;
    activeStatus = status || 'active';

    // Update sidebar
    document.querySelectorAll('.case-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.caseId) === caseId);
    });

    // Show banner
    bannerName.textContent = caseName;
    updateBannerBadge(status);
    caseBanner.classList.add('visible');

    // Restore or start fresh chat for this case
    restoreChatHistory(caseId, caseName);

    // Close slide-in panels
    timelinePanel.classList.remove('open');
    if (documentsPanel) documentsPanel.classList.remove('open');
}

function collectCurrentMessages() {
    return Array.from(messagesEl.querySelectorAll('.message')).map(el => el.outerHTML);
}

function restoreChatHistory(caseId, caseName) {
    // Remove all messages except welcome screen
    Array.from(messagesEl.querySelectorAll('.message')).forEach(el => el.remove());

    if (chatHistories[caseId] && chatHistories[caseId].length > 0) {
        // Restore saved messages
        chatHistories[caseId].forEach(html => {
            const div = document.createElement('div');
            div.innerHTML = html;
            const node = div.firstChild;
            if (node) messagesEl.appendChild(node);
        });
        hideWelcome();

        // Add a visual case-switch divider at the bottom
        addContextDivider(`↩ Resumed — ${caseName}`);
    } else {
        // Fresh chat for this case − show welcome or a clean intro
        hideWelcome();
        addSystemMessage(
            `📁 Case loaded: **${caseName}**\n` +
            `Upload documents or ask questions about this case.`
        );
    }

    scrollToBottom();
}

function addContextDivider(label) {
    const div = document.createElement('div');
    div.className = 'context-divider';
    div.innerHTML = `<span class="context-divider-label">${escHtml(label)}</span>`;
    messagesEl.appendChild(div);
}

function updateBannerBadge(status) {
    activeStatus = status;
    bannerStatusBadge.textContent = status;
    bannerStatusBadge.className = `case-badge badge-${status}`;
}

// ── Case Status Management ─────────────────────────────────────────────────
async function updateCaseStatus(caseId, newStatus) {
    try {
        const today = new Date().toISOString().split('T')[0];
        await fetch(`${API}/case/update/${caseId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus, date: today }),
        });

        updateBannerBadge(newStatus);

        // Update in allCases array
        const c = allCases.find(x => x.id === caseId);
        if (c) c.status = newStatus;
        renderCasesList();

        const labels = { active: '✅ Case marked active', closed: '🔒 Case closed', reopened: '🔁 Case reopened' };
        addSystemMessage(labels[newStatus] || `Status updated to ${newStatus}`);
    } catch (e) {
        addSystemMessage(`❌ Failed to update status: ${e.message}`);
    }
}

// ── Welcome ────────────────────────────────────────────────────────────────
function hideWelcome() {
    if (welcomeScreen) welcomeScreen.style.display = 'none';
}

// ── Clear Chat ─────────────────────────────────────────────────────────────
function clearChat() {
    if (!activeCaseId) return;
    if (!confirm(`Clear chat history for "${activeCaseName}"? (The case memory and documents are not deleted.)`)) return;

    Array.from(messagesEl.querySelectorAll('.message, .context-divider')).forEach(el => el.remove());
    chatHistories[activeCaseId] = [];
    addSystemMessage(`🗑 Chat cleared for case: **${activeCaseName}**`);
}

// ── Messages ───────────────────────────────────────────────────────────────
function addMessage(role, text) {
    hideWelcome();

    const avatars = { user: '👤', ai: '⚖', system: '●' };
    const labels = { user: 'You', ai: 'KanoonVault AI', system: 'System' };

    const el = document.createElement('div');
    el.className = `message ${role}`;
    el.innerHTML = `
    <div class="msg-avatar">${avatars[role] || '?'}</div>
    <div class="msg-body">
      <div class="msg-role">${labels[role] || role}</div>
      <div class="msg-bubble"></div>
    </div>
  `;
    el.querySelector('.msg-bubble').innerHTML = markdownToHtml(text);
    messagesEl.appendChild(el);
    scrollToBottom();
    return el.querySelector('.msg-bubble');
}

function addSystemMessage(text) { addMessage('system', text); }

function addStreamingBubble() {
    hideWelcome();
    const el = document.createElement('div');
    el.className = 'message ai';
    el.innerHTML = `
    <div class="msg-avatar">⚖</div>
    <div class="msg-body">
      <div class="msg-role">KanoonVault AI</div>
      <div class="msg-bubble"><span class="cursor"></span></div>
    </div>
  `;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el.querySelector('.msg-bubble');
}

function docOpenHref(documentId) {
    if (activeCaseId == null) return `${API}/documents/${documentId}/open`;
    return `${API}/documents/${documentId}/open?case_id=${activeCaseId}`;
}

function markdownToHtml(md) {
    if (!md) return '';
    let html = escHtml(md);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Handle source links in the format: [Document Name] — Page [Number] — [DOC_ID:123]
    html = html.replace(/\[([^\]]+)\] — Page \[(\d+)\] — \[DOC_ID:(\d+)\]/g, (match, docName, pageNum, docId) => {
        const href = docOpenHref(docId);
        return `<div class="source-link">[${docName}] — Page [${pageNum}] — <a href="${href}" target="_blank" rel="noopener" class="file-link">Open File</a></div>`;
    });
    
    // Handle source links without page numbers: [Document Name] — [DOC_ID:123]
    html = html.replace(/\[([^\]]+)\] — \[DOC_ID:(\d+)\]/g, (match, docName, docId) => {
        const href = docOpenHref(docId);
        return `<div class="source-link">[${docName}] — <a href="${href}" target="_blank" rel="noopener" class="file-link">Open File</a></div>`;
    });
    
    const lines = html.split('\n');
    const out = [];
    let inList = false;
    for (const line of lines) {
        if (line.match(/^[-•]\s/)) {
            if (!inList) { out.push('<ul>'); inList = true; }
            out.push(`<li>${line.replace(/^[-•]\s/, '')}</li>`);
        } else {
            if (inList) { out.push('</ul>'); inList = false; }
            out.push(line ? `<p>${line}</p>` : '');
        }
    }
    if (inList) out.push('</ul>');
    return out.join('');
}

function escHtml(str) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
}

function scrollToBottom() {
    messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
}

function autoResizeTextarea() {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
}

// ── Chat send ──────────────────────────────────────────────────────────────
async function handleSend() {
    const text = chatInput.value.trim();
    if (!text || isStreaming) return;
    chatInput.value = '';
    chatInput.style.height = 'auto';
    addMessage('user', text);
    await streamChat(text);
}

async function streamChat(question) {
    isStreaming = true;
    btnSend.disabled = true;

    const bubble = addStreamingBubble();
    let fullText = '';
    let sourcesText = '';

    try {
        const resp = await fetch(`${API}/chat/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, case_id: activeCaseId, stream: true }),
        });

        if (!resp.ok) throw new Error(`Server error ${resp.status}`);

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            for (const line of chunk.split('\n')) {
                if (line.startsWith('data: ')) {
                    const token = line.slice(6);
                    if (token === '[DONE]') break;
                    if (token.startsWith('[ERROR:')) {
                        bubble.innerHTML = `<span style="color:var(--danger)">${escHtml(token)}</span>`;
                        break;
                    }
                    
                    // Check if this is a special command response (direct file link)
                    if (token.startsWith('http') && (token.includes('/documents/') || token.includes('show original file'))) {
                        let href = token.trim();
                        const m = href.match(/\/documents\/(\d+)\/open/);
                        if (m && activeCaseId != null && !href.includes('case_id=')) {
                            href += (href.includes('?') ? '&' : '?') + `case_id=${activeCaseId}`;
                        }
                        bubble.innerHTML = `<a href="${escHtml(href)}" target="_blank" rel="noopener" class="file-link">📄 Open File</a>`;
                        break;
                    }
                    
                    // Check if this is sources section
                    if (token.startsWith('\nSources:\n') || token.startsWith('Sources:\n')) {
                        sourcesText = token;
                        // Continue collecting sources
                        continue;
                    }
                    
                    // Regular token - add to main text
                    fullText += token;
                    bubble.innerHTML = markdownToHtml(fullText + sourcesText) + '<span class="cursor"></span>';
                    scrollToBottom();
                }
            }
        }

        // Final update without cursor
        bubble.innerHTML = markdownToHtml(fullText + sourcesText);
    } catch (err) {
        bubble.innerHTML = `<span style="color:var(--danger)">⚠️ ${escHtml(err.message)}</span>`;
    } finally {
        isStreaming = false;
        btnSend.disabled = false;
        scrollToBottom();
    }
}

// ── File upload ────────────────────────────────────────────────────────────
async function handleFileUpload(file) {
    // CASE WORKSPACE MEMORY RULE: Check if case is open
    if (!activeCaseId) {
        addSystemMessage('❌ **Upload failed**: Please open or create a case before uploading documents.');
        return;
    }

    hideWelcome();

    const progressEl = addOcrProgressBubble(file.name);

    try {
        await animateStep(progressEl, 0, 'Uploading…');
        const formData = new FormData();
        formData.append('file', file);

        await animateStep(progressEl, 1, 'Running OCR…');
        // Pass case_id as query parameter - file inherits case_id from workspace
        const resp = await fetch(`${API}/upload?case_id=${activeCaseId}`, { method: 'POST', body: formData });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const result = await resp.json();
        await animateStep(progressEl, 2, 'Processing document…');
        await delay(250);
        await animateStep(progressEl, 3, 'Updating timeline…');
        await delay(250);

        progressEl.closest('.message').remove();

        // Files uploaded in case workspace inherit the case_id
        const msg =
            `✅ **Document added to case**: \`${result.filename}\`\n` +
            `📄 Case: **${result.case_name}**\n` +
            `📅 Timeline events found: **${result.events_extracted}**\n` +
            `*Preview:* ${result.ocr_preview}`;

        addSystemMessage(msg);

        // Load updated case info
        await refreshCasesSidebarData();

        // Refresh timeline panel for current case
        await loadTimeline(activeCaseId);

        if (documentsPanel && documentsPanel.classList.contains('open')) {
            await refreshDocumentsList(activeCaseId);
        }

        // Patch the active item highlight without full restore
        document.querySelectorAll('.case-item').forEach(el => {
            el.classList.toggle('active', parseInt(el.dataset.caseId) === activeCaseId);
        });

        bannerName.textContent = activeCaseName;
        caseBanner.classList.add('visible');
        const freshCase = allCases.find(c => c.id === activeCaseId);
        if (freshCase) updateBannerBadge(freshCase.status);

        await delay(300);
        addMessage('ai',
            `I've read **${result.filename}** and added it to case **${result.case_name}**.\n\n` +
            `You can ask me:\n` +
            `- What is this case about?\n` +
            `- Who are the parties involved?\n` +
            `- List all dates and events\n` +
            `- Summarize the key facts`
        );
    } catch (err) {
        progressEl.closest('.message').remove();
        addSystemMessage(`❌ Upload failed: **${err.message}**`);
    }
}

function addOcrProgressBubble(filename) {
    hideWelcome();
    const el = document.createElement('div');
    el.className = 'message system';
    el.innerHTML = `
    <div class="msg-avatar">●</div>
    <div class="msg-body">
      <div class="msg-role">System</div>
      <div class="msg-bubble">
        <div class="ocr-progress-bubble">
          <div style="font-size:11px;margin-bottom:6px;color:var(--accent-secondary);font-family:var(--font-mono)">
            Processing: ${escHtml(filename)}
          </div>
          <div class="ocr-step" id="pstep-0"><span class="step-icon">·</span> Uploading document…</div>
          <div class="ocr-step" id="pstep-1"><span class="step-icon">·</span> Running OCR…</div>
          <div class="ocr-step" id="pstep-2"><span class="step-icon">·</span> Detecting case…</div>
          <div class="ocr-step" id="pstep-3"><span class="step-icon">·</span> Updating timeline…</div>
        </div>
      </div>
    </div>
  `;
    messagesEl.appendChild(el);
    scrollToBottom();
    return el.querySelector('.ocr-progress-bubble');
}

async function animateStep(bubble, stepIdx, label) {
    for (let i = 0; i < stepIdx; i++) {
        const s = bubble.querySelector(`#pstep-${i}`);
        if (s) { s.className = 'ocr-step done'; s.querySelector('.step-icon').textContent = '✓'; }
    }
    const cur = bubble.querySelector(`#pstep-${stepIdx}`);
    if (cur) {
        cur.className = 'ocr-step active';
        cur.querySelector('.step-icon').textContent = '›';
        cur.childNodes[1].textContent = ` ${label}`;
    }
    scrollToBottom();
    await delay(550);
}

// ── Timeline ───────────────────────────────────────────────────────────────
async function loadTimeline(caseId) {
    if (!caseId) return;
    try {
        const data = await fetch(`${API}/timeline/${caseId}`).then(r => r.json());
        renderTimeline(data.events, data.case_name);
        timelinePanel.classList.add('open');
    } catch (e) { console.error('Timeline load failed:', e); }
}

function formatBytes(n) {
    if (n == null || n === '') return '—';
    const num = Number(n);
    if (Number.isNaN(num)) return '—';
    if (num < 1024) return `${num} B`;
    if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
    return `${(num / (1024 * 1024)).toFixed(1)} MB`;
}

function showToast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.remove('hidden');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toastEl.classList.add('hidden'), 4200);
}

function docPreviewUrl(documentId) {
    return `${API}/documents/${documentId}/preview?case_id=${activeCaseId}`;
}

async function openDocumentsPanel(caseId) {
    if (!caseId || !documentsPanel) return;
    timelinePanel.classList.remove('open');
    documentsPanel.classList.add('open');
    await refreshDocumentsList(caseId);
}

async function refreshDocumentsList(caseId) {
    if (!caseId || !documentsListEl) return;
    try {
        const data = await fetch(`${API}/cases/${caseId}/documents`).then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        });
        renderDocumentsList(data.documents || []);
        const title = document.querySelector('.documents-header h3');
        if (title && activeCaseName) title.textContent = `${activeCaseName.toUpperCase()} — DOCUMENTS`;
    } catch (e) {
        console.error('Documents load failed:', e);
        renderDocumentsList([]);
    }
}

function renderDocumentsList(docs) {
    if (!documentsListEl || !documentsEmptyEl) return;
    if (!docs || docs.length === 0) {
        documentsListEl.innerHTML = '';
        documentsEmptyEl.classList.add('visible');
        return;
    }
    documentsEmptyEl.classList.remove('visible');
    documentsListEl.innerHTML = '';
    docs.forEach(d => {
        const card = document.createElement('div');
        card.className = 'document-card';
        const pages = d.page_count != null ? `${d.page_count} pp.` : 'pages n/a';
        card.innerHTML = `
      <div class="document-card-name">${escHtml(d.filename)}</div>
      <div class="document-card-meta">${escHtml(d.uploaded_at || '')} · ${escHtml(d.file_type || '')} · ${formatBytes(d.file_size)} · ${escHtml(pages)}</div>
      <div class="document-card-actions">
        <button type="button" class="doc-btn-open" data-id="${d.document_id}">Open file</button>
        <button type="button" class="doc-btn-preview" data-id="${d.document_id}">Preview</button>
      </div>
    `;
        card.querySelector('.doc-btn-open').addEventListener('click', () => {
            window.open(docOpenHref(d.document_id), '_blank', 'noopener,noreferrer');
        });
        card.querySelector('.doc-btn-preview').addEventListener('click', () => {
            previewDocument(d.filename, d.document_id);
        });
        documentsListEl.appendChild(card);
    });
}

function closePreviewModal() {
    if (previewModalOverlay) previewModalOverlay.classList.remove('open');
    if (previewModalBody) previewModalBody.innerHTML = '';
}

async function previewDocument(filename, documentId) {
    if (activeCaseId == null) return;
    const ext = (filename.split('.').pop() || '').toLowerCase();

    if (ext === 'pdf') {
        window.open(docPreviewUrl(documentId), '_blank', 'noopener,noreferrer');
        return;
    }

    const imageExt = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'];
    if (imageExt.includes(ext)) {
        if (!previewModalOverlay) return;
        if (previewModalTitle) previewModalTitle.textContent = filename;
        if (previewModalBody) {
            previewModalBody.innerHTML = `<img src="${docPreviewUrl(documentId)}" alt="">`;
        }
        previewModalOverlay.classList.add('open');
        return;
    }

    if (ext === 'txt') {
        if (!previewModalOverlay) return;
        try {
            const r = await fetch(docPreviewUrl(documentId));
            const data = await r.json();
            if (previewModalTitle) previewModalTitle.textContent = filename;
            const txt = escHtml(data.text || '');
            const note = data.truncated ? '<p style="font-size:10px;color:var(--text-muted);margin:0 0 8px">Preview truncated.</p>' : '';
            if (previewModalBody) {
                previewModalBody.innerHTML = `${note}<pre class="text-preview">${txt}</pre>`;
            }
            previewModalOverlay.classList.add('open');
        } catch (e) {
            showToast('Could not load text preview.');
        }
        return;
    }

    showToast('Preview not available — use Open file for the original.');
}

function openDeleteCaseModal() {
    if (!activeCaseId || !deleteModalOverlay) return;
    deleteModalOverlay.classList.add('open');
}

function resetWorkspaceUI() {
    activeCaseId = null;
    activeCaseName = null;
    activeStatus = 'active';
    timelinePanel.classList.remove('open');
    if (documentsPanel) documentsPanel.classList.remove('open');
    caseBanner.classList.remove('visible');
    Array.from(messagesEl.querySelectorAll('.message, .context-divider')).forEach(el => el.remove());
    if (welcomeScreen) welcomeScreen.style.display = '';
}

async function confirmDeleteCase() {
    const id = activeCaseId;
    if (!id || !btnDeleteModalConfirm) return;
    btnDeleteModalConfirm.disabled = true;
    try {
        const resp = await fetch(`${API}/cases/${id}`, { method: 'DELETE' });
        const raw = await resp.text();
        let body = {};
        if (raw) {
            try { body = JSON.parse(raw); } catch { /* ignore */ }
        }
        if (!resp.ok) {
            let detail = body.detail;
            if (Array.isArray(detail)) detail = detail.map(d => d.msg || d).join('; ');
            if (detail && typeof detail === 'object') detail = JSON.stringify(detail);
            throw new Error(detail || `Server error ${resp.status}`);
        }
        // Keep chatHistories[id] until permanent delete — restore recovers UX history client-side.
        deleteModalOverlay.classList.remove('open');
        resetWorkspaceUI();
        showToast(body.message || 'Case moved to Trash.');
        await refreshCasesSidebarData();
    } catch (e) {
        showToast(`Move to Trash failed: ${e.message}`);
    } finally {
        btnDeleteModalConfirm.disabled = false;
    }
}

async function restoreTrashCase(caseId) {
    try {
        const resp = await fetch(`${API}/cases/${caseId}/restore`, { method: 'POST' });
        const raw = await resp.text();
        let body = {};
        if (raw) {
            try { body = JSON.parse(raw); } catch { /* ignore */ }
        }
        if (!resp.ok) {
            let detail = body.detail;
            if (Array.isArray(detail)) detail = detail.map(d => d.msg || d).join('; ');
            throw new Error(detail || `Server error ${resp.status}`);
        }
        showToast(body.message || 'Case restored successfully.');
        await refreshCasesSidebarData();
    } catch (e) {
        showToast(`Restore failed: ${e.message}`);
    }
}

function openPermanentDeleteModal(caseId, caseName) {
    permanentDeleteTargetId = caseId;
    if (permanentModalOverlay) permanentModalOverlay.classList.add('open');
    const ttl = permanentModalOverlay?.querySelector('h3');
    if (ttl && caseName) {
        ttl.textContent = `Permanently delete “${caseName.trim().slice(0, 72)}”?`;
    } else if (ttl) ttl.textContent = 'Permanently delete this case?';
}

async function confirmPermanentDeleteFromTrash() {
    const id = permanentDeleteTargetId;
    if (!id || !btnPermanentModalConfirm || !permanentModalOverlay) return;
    btnPermanentModalConfirm.disabled = true;
    try {
        const resp = await fetch(`${API}/cases/${id}/permanent`, { method: 'DELETE' });
        const raw = await resp.text();
        let body = {};
        if (raw) {
            try { body = JSON.parse(raw); } catch { /* ignore */ }
        }
        if (!resp.ok) {
            let detail = body.detail;
            if (Array.isArray(detail)) detail = detail.map(d => d.msg || d).join('; ');
            throw new Error(detail || `Server error ${resp.status}`);
        }
        delete chatHistories[id];
        if (activeCaseId === id) resetWorkspaceUI();
        permanentModalOverlay.classList.remove('open');
        permanentDeleteTargetId = null;
        showToast(body.message || 'Case permanently deleted.');
        await refreshCasesSidebarData();
    } catch (e) {
        showToast(`Permanent delete failed: ${e.message}`);
    } finally {
        btnPermanentModalConfirm.disabled = false;
    }
}

function renderTimeline(events, caseName) {
    document.querySelector('.timeline-header h3').textContent = caseName.toUpperCase();
    if (!events || events.length === 0) {
        timelineEvts.innerHTML = '<div class="no-events">No timeline events yet.<br/>Upload documents to build the timeline.</div>';
        return;
    }
    timelineEvts.innerHTML = '';
    events.forEach(ev => {
        const el = document.createElement('div');
        el.className = 'timeline-event';
        el.innerHTML = `
      <div class="timeline-dot"></div>
      <div class="timeline-content">
        <div class="timeline-date">${ev.event_date || 'Date unknown'}</div>
        <div class="timeline-desc">${escHtml(ev.event_desc)}</div>
        ${ev.source_file ? `<div class="timeline-source">${escHtml(ev.source_file)}</div>` : ''}
      </div>
    `;
        timelineEvts.appendChild(el);
    });
}

// ── Modal ──────────────────────────────────────────────────────────────────
function openModal() {
    modalInput.value = '';
    modalOverlay.classList.add('open');
    setTimeout(() => modalInput.focus(), 100);
}

function closeModal() { modalOverlay.classList.remove('open'); }

async function createCaseFromModal() {
    const name = modalInput.value.trim();
    if (!name) { modalInput.focus(); return; }
    try {
        const resp = await fetch(`${API}/case/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ case_name: name, notes: '' }),
        });
        const data = await resp.json();
        closeModal();
        if (currentFilter === 'trash') {
            currentFilter = 'all';
            document.querySelectorAll('.status-tab').forEach(t =>
                t.classList.toggle('active', t.dataset.filter === 'all'));
        }
        await loadCases();
        renderCasesList();
        switchCase(data.case_id, name, 'active');
    } catch (e) {
        alert('Failed to create case: ' + e.message);
    }
}

// ── Utility ────────────────────────────────────────────────────────────────
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }
