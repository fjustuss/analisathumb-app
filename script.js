// ===================================================================================
// ANALISATHUMB - JAVASCRIPT PRINCIPAL
// ===================================================================================

const DOMElements = {
    // Seção de Inputs
    inputSection: document.getElementById('input-section'),
    abToggle: document.getElementById('ab-test-toggle'),
    uploadGridContainer: document.getElementById('upload-grid-container'), // Novo seletor
    labelVersionA: document.getElementById('label-version-a'),
    uploaderB: document.getElementById('uploader-b'),
    uploadA: document.getElementById('image-upload-a'),
    uploadB: document.getElementById('image-upload-b'),
    contextInputsContainer: document.getElementById('context-inputs-container'),
    previewArea: document.getElementById('preview-area'),
    previewA: document.getElementById('image-preview-a'),
    previewB: document.getElementById('image-preview-b'),
    // ... outros elementos
};

// ... (Resto do código existente)

function toggleComparisonMode() {
    isComparisonMode = DOMElements.abToggle.checked;
    
    // Mostra/Esconde o uploader da Versão B
    DOMElements.uploaderB.classList.toggle('hidden', !isComparisonMode);
    
    // ATUALIZAÇÃO: Altera dinamicamente as colunas do grid
    if (isComparisonMode) {
        DOMElements.uploadGridContainer.classList.remove('md:grid-cols-1');
        DOMElements.uploadGridContainer.classList.add('md:grid-cols-2');
        DOMElements.previewArea.classList.remove('md:grid-cols-1');
        DOMElements.previewArea.classList.add('md:grid-cols-2');
    } else {
        DOMElements.uploadGridContainer.classList.remove('md:grid-cols-2');
        DOMElements.uploadGridContainer.classList.add('md:grid-cols-1');
        DOMElements.previewArea.classList.remove('md:grid-cols-2');
        DOMElements.previewArea.classList.add('md:grid-cols-1');
    }
    
    DOMElements.labelVersionA.textContent = isComparisonMode ? 'Versão A' : 'Thumbnail Principal';
    
    resetInputs();
}

// ... (Resto do script.js sem alterações)
