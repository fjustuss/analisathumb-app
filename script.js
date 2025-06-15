// ===================================================================================
// ANALISATHUMB - JAVASCRIPT PRINCIPAL
// ===================================================================================

// --- 1. SELETORES DE ELEMENTOS DO DOM ---
const DOMElements = {
    // Seção de Inputs
    inputSection: document.getElementById('input-section'),
    abToggle: document.getElementById('ab-test-toggle'),
    
    labelVersionA: document.getElementById('label-version-a'),
    uploaderB: document.getElementById('uploader-b'),
    uploadA: document.getElementById('image-upload-a'),
    uploadB: document.getElementById('image-upload-b'),
    
    contextInputsContainer: document.getElementById('context-inputs-container'),
    previewArea: document.getElementById('preview-area'),
    previewA: document.getElementById('image-preview-a'),
    previewB: document.getElementById('image-preview-b'),
    analyzeButton: document.getElementById('analyze-button'),
    languageSelect: document.getElementById('language-select'),
    nicheSelect: document.getElementById('niche-select'),
    customNicheContainer: document.getElementById('custom-niche-container'),
    customNicheInput: document.getElementById('custom-niche-input'),
    videoTitleInput: document.getElementById('video-title-input'),
    
    // Seção de Loading e Resultados
    loadingSpinner: document.getElementById('loading-spinner'),
    loadingText: document.getElementById('loading-text'),
    resultsSection: document.getElementById('results-section'),
};

// --- 2. ESTADO DA APLICAÇÃO ---
let isComparisonMode = false;
let imageA_Data = null;
let imageB_Data = null;

// --- 3. INICIALIZAÇÃO ---
document.addEventListener('DOMContentLoaded', setupEventListeners);

// --- 4. CONFIGURAÇÃO DOS EVENT LISTENERS ---
function setupEventListeners() {
    DOMElements.abToggle.addEventListener('change', toggleComparisonMode);
    DOMElements.uploadA.addEventListener('change', (e) => handleImageUpload(e, 'A'));
    DOMElements.uploadB.addEventListener('change', (e) => handleImageUpload(e, 'B'));
    DOMElements.analyzeButton.addEventListener('click', startAnalysis);
    DOMElements.nicheSelect.addEventListener('change', () => {
        DOMElements.customNicheContainer.classList.toggle('hidden', DOMElements.nicheSelect.value !== 'Outro');
    });
}

// --- 5. LÓGICA DE CONTROLE DA INTERFACE ---

function toggleComparisonMode() {
    isComparisonMode = DOMElements.abToggle.checked;

    DOMElements.uploaderB.classList.toggle('hidden', !isComparisonMode);
    DOMElements.previewB.classList.toggle('hidden', !isComparisonMode);
    
    DOMElements.previewArea.classList.toggle('md:grid-cols-2', isComparisonMode);
    DOMElements.labelVersionA.textContent = isComparisonMode ? 'Versão A' : 'Thumbnail Principal';
    
    resetInputs();
}

function handleImageUpload(event, version) {
    const file = event.target.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) { 
        alert("Imagem muito grande (MAX. 5MB).");
        return;
    }

    const reader = new FileReader();
    reader.onload = e => {
        DOMElements.contextInputsContainer.classList.remove('hidden');
        if (version === 'A') {
            imageA_Data = e.target.result;
            DOMElements.previewA.src = imageA_Data;
            DOMElements.previewA.classList.remove('hidden');
        } else {
            imageB_Data = e.target.result;
            DOMElements.previewB.src = imageB_Data;
        }
        checkAnalysisButtonState();
    };
    reader.readAsDataURL(file);
}

function checkAnalysisButtonState() {
    if (isComparisonMode) {
        DOMElements.analyzeButton.disabled = !(imageA_Data && imageB_Data);
    } else {
        DOMElements.analyzeButton.disabled = !imageA_Data;
    }
}

function resetInputs() {
    imageA_Data = null;
    imageB_Data = null;
    DOMElements.uploadA.value = '';
    DOMElements.uploadB.value = '';
    DOMElements.previewA.src = '';
    DOMElements.previewB.src = '';
    DOMElements.previewA.classList.add('hidden');
    if(DOMElements.previewB) DOMElements.previewB.classList.add('hidden');
    DOMElements.contextInputsContainer.classList.add('hidden');
    DOMElements.analyzeButton.disabled = true;
}

// --- 6. LÓGICA PRINCIPAL DE ANÁLISE ---

async function startAnalysis() {
    DOMElements.inputSection.classList.add('hidden');
    DOMElements.loadingSpinner.classList.remove('hidden');
    DOMElements.loadingText.textContent = `Analisando com Gemini...`;

    const payload = {
        title: DOMElements.videoTitleInput.value,
        niche: DOMElements.nicheSelect.value === 'Outro' ? DOMElements.customNicheInput.value.trim() : DOMElements.nicheSelect.value,
        language: DOMElements.languageSelect.value,
        image_a_data_url: imageA_Data,
        image_b_data_url: isComparisonMode ? imageB_Data : null
    };

    try {
        const response = await fetch('https://analisathumb.onrender.com/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Erro do servidor (${response.status}): ${errorText.substring(0, 500)}`);
        }
        const results = await response.json();
        displayResults(results);
    } catch (error) {
        alert('Erro na análise: ' + error.message);
        resetApp();
    }
}

// --- 7. FUNÇÕES PARA EXIBIR OS RESULTADOS ---

function displayResults(results) {
    DOMElements.loadingSpinner.classList.add('hidden');
    const resultsContainer = DOMElements.resultsSection;
    resultsContainer.classList.remove('hidden');
    resultsContainer.innerHTML = ''; // Limpa resultados anteriores

    if (results.analysis_type === 'single') {
        resultsContainer.innerHTML = createSingleResultHTML(results);
    } else if (results.analysis_type === 'comparison') {
        resultsContainer.innerHTML = createComparisonResultHTML(results);
    }
    
    document.getElementById('restart-button-results').addEventListener('click', resetApp);
    
    setTimeout(() => {
        document.querySelectorAll('.progress-bar-fill').forEach(bar => {
            bar.style.width = bar.dataset.width;
        });
    }, 100);
}

function getScoreColor(score) {
    return score < 65 ? 'text-red-400' : score < 85 ? 'text-yellow-400' : 'text-green-400';
}

function getGradientClass(score) {
    return score < 65 ? 'from-red-500 to-orange-500' : score < 85 ? 'from-yellow-500 to-amber-500' : 'from-green-500 to-emerald-500';
}

function copyToClipboard(element, text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);

    const originalContent = element.innerHTML;
    const isColorElement = element.tagName === 'P';

    if (isColorElement) {
        element.textContent = 'Copiado!';
        setTimeout(() => { element.textContent = text; }, 1500);
    } else {
        element.innerHTML = '<svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
        setTimeout(() => { element.innerHTML = originalContent; }, 1500);
    }
}

function createSingleResultHTML(data) {
    const details = data.details && Array.isArray(data.details) ? data.details : [];
    const recommendations = data.recommendations && Array.isArray(data.recommendations) ? data.recommendations : [];
    const suggested_titles = data.suggested_titles && Array.isAr