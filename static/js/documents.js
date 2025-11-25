// AFG Bank Assistant - Document Management Logic

let selectedFile = null;

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadForm = document.getElementById('uploadForm');
const selectedFileDiv = document.getElementById('selectedFile');
const uploadBtn = document.getElementById('uploadBtn');
const cancelBtn = document.getElementById('cancelBtn');
const refreshBtn = document.getElementById('refreshBtn');
const documentsList = document.getElementById('documentsList');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDocuments();
    loadStats();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Upload area click
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Form actions
    uploadForm.addEventListener('submit', handleUpload);
    cancelBtn.addEventListener('click', resetUploadForm);

    // Refresh button
    refreshBtn.addEventListener('click', () => {
        loadDocuments();
        loadStats();
    });
}

// Drag & Drop handlers
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
}

function handleFile(file) {
    // Validate file type
    const allowedTypes = ['application/pdf', 'text/plain'];
    if (!allowedTypes.includes(file.type)) {
        alert('Type de fichier non valide. Seuls les fichiers PDF et TXT sont acceptés.');
        return;
    }

    // Validate file size (50MB)
    if (file.size > 50 * 1024 * 1024) {
        alert('Fichier trop volumineux. Maximum 50 MB.');
        return;
    }

    selectedFile = file;

    // Show upload form
    uploadArea.classList.add('hidden');
    uploadForm.classList.remove('hidden');

    // Set default document name
    document.getElementById('docName').value = file.name.replace(/\.[^/.]+$/, '');

    // Show selected file
    const fileSize = formatFileSize(file.size);
    selectedFileDiv.innerHTML = `
        <strong>📎 Fichier sélectionné:</strong> ${file.name} (${fileSize})
    `;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function resetUploadForm() {
    selectedFile = null;
    uploadArea.classList.remove('hidden');
    uploadForm.classList.add('hidden');
    uploadForm.reset();
    fileInput.value = '';
}

async function handleUpload(e) {
    e.preventDefault();

    if (!selectedFile) {
        alert('Aucun fichier sélectionné');
        return;
    }

    // Show loading state
    const btnText = uploadBtn.querySelector('.btn-text');
    const btnSpinner = uploadBtn.querySelector('.btn-spinner');
    btnText.classList.add('hidden');
    btnSpinner.classList.remove('hidden');
    uploadBtn.disabled = true;

    // Prepare form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('doc_name', document.getElementById('docName').value);
    formData.append('doc_type', document.getElementById('docType').value);
    formData.append('country', document.getElementById('country').value);
    formData.append('bank', document.getElementById('bank').value);

    try {
        const response = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            alert(`✅ ${data.message}`);
            resetUploadForm();
            loadDocuments();
            loadStats();
        } else {
            alert(`❌ Erreur: ${data.error}\n${data.details || ''}`);
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('❌ Erreur de connexion au serveur');
    } finally {
        // Reset button state
        btnText.classList.remove('hidden');
        btnSpinner.classList.add('hidden');
        uploadBtn.disabled = false;
    }
}

async function loadDocuments() {
    documentsList.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Chargement des documents...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/documents');
        const data = await response.json();

        if (data.documents.length === 0) {
            documentsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <p>Aucun document pour le moment</p>
                    <p style="font-size: 14px; color: #999;">Commencez par télécharger votre premier document</p>
                </div>
            `;
            return;
        }

        // Render documents
        documentsList.innerHTML = data.documents.map(doc => renderDocumentCard(doc)).join('');

        // Add delete event listeners
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', () => deleteDocument(btn.dataset.docId, btn.dataset.docName));
        });

    } catch (error) {
        console.error('Error loading documents:', error);
        documentsList.innerHTML = `
            <div class="empty-state">
                <p style="color: #dc3545;">❌ Erreur de chargement</p>
                <p style="font-size: 14px;">Impossible de charger les documents</p>
            </div>
        `;
    }
}

function renderDocumentCard(doc) {
    const statusClass = `status-${doc.status.toLowerCase()}`;
    const statusText = {
        'READY': '✅ Prêt',
        'PROCESSING': '⏳ En cours',
        'PENDING': '⏸️ En attente',
        'FAILED': '❌ Échec'
    }[doc.status] || doc.status;

    const typeIcon = {
        'tarif': '💰',
        'procedure': '📋',
        'regulation': '⚖️',
        'website': '🌐',
        'other': '📄'
    }[doc.doc_type] || '📄';

    const date = new Date(doc.created_at).toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    const errorHtml = doc.error_message ? `
        <div style="color: #dc3545; font-size: 12px; margin-top: 8px;">
            ⚠️ ${doc.error_message}
        </div>
    ` : '';

    return `
        <div class="document-card">
            <div class="document-info">
                <div class="document-name">${typeIcon} ${doc.doc_name}</div>
                <div class="document-meta">
                    <div class="meta-item">
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </div>
                    <div class="meta-item">📦 ${doc.num_chunks} chunks</div>
                    <div class="meta-item">🌍 ${doc.country}</div>
                    <div class="meta-item">🏦 ${doc.bank}</div>
                    <div class="meta-item">📅 ${date}</div>
                    ${doc.file_size ? `<div class="meta-item">💾 ${formatFileSize(doc.file_size)}</div>` : ''}
                </div>
                ${errorHtml}
            </div>
            <div class="document-actions">
                <button class="btn-delete" data-doc-id="${doc.doc_id}" data-doc-name="${doc.doc_name}">
                    🗑️ Supprimer
                </button>
            </div>
        </div>
    `;
}

async function deleteDocument(docId, docName) {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer "${docName}" ?\n\nCette action est irréversible.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/documents/${docId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            alert(`✅ Document supprimé: ${docName}`);
            loadDocuments();
            loadStats();
        } else {
            alert(`❌ Erreur: ${data.error}`);
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('❌ Erreur de connexion au serveur');
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/documents/stats');
        const stats = await response.json();

        document.getElementById('totalDocs').textContent = stats.total_documents || 0;
        document.getElementById('totalChunks').textContent = stats.total_chunks || 0;
        document.getElementById('readyDocs').textContent = stats.by_status?.READY || 0;
        document.getElementById('processingDocs').textContent = stats.by_status?.PROCESSING || 0;

    } catch (error) {
        console.error('Error loading stats:', error);
    }
}
