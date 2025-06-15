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
    // Só esconde a preview B se ela realmente existir no DOM
    if(DOMElements.previewB) {
        DOMElements.previewB.classList.add('hidden');
    }
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
    if (score < 65) return 'text-red-400';
    if (score < 85) return 'text-yellow-400';
    return 'text-green-400';
}

function getGradientClass(score) {
    if (score < 65) return 'from-red-500 to-orange-500';
    if (score < 85) return 'from-yellow-500 to-amber-500';
    return 'from-green-500 to-emerald-500';
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
    const finalScore = Math.round(data.details.reduce((acc, item) => acc + item.score, 0) / data.details.length);
    
    setTimeout(() => {
        const circle = document.getElementById('score-circle-progress');
        if(circle) {
            const radius = circle.r.baseVal.value;
            const circumference = radius * 2 * Math.PI;
            const offset = circumference - (finalScore / 100) * circumference;
            circle.style.strokeDashoffset = offset;
        }
    }, 100);

    const detailsHTML = data.details.map(item => `
        <div>
            <div class="flex justify-between items-center mb-1"><p class="font-semibold">${item.name}</p><p class="font-bold text-lg ${getScoreColor(item.score)}">${item.score}/100</p></div>
            <div class="w-full bg-gray-700 rounded-full h-2.5"><div class="bg-gradient-to-r ${getGradientClass(item.score)} h-2.5 rounded-full progress-bar-fill" style="width: 0%" data-width="${item.score}%"></div></div>
        </div>`).join('');

    const recommendationsHTML = data.recommendations.map(rec => {
        const isPrompt = rec.startsWith('Sugestão de Prompt:');
        const textToCopy = isPrompt ? rec.substring(18).trim() : rec;
        
        const generateBtnHTML = isPrompt 
            ? `<button class="ml-2 p-1 text-blue-400 hover:text-white" title="Gerar Imagem com este Prompt" onclick="generateImage('${textToCopy.replace(/'/g, "\\'")}')"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M17.414 2.586a2 2 0 00-2.828 0L7 10.172V13h2.828l7.586-7.586a2 2 0 000-2.828zM5 12V7a2 2 0 012-2h2.586l-2.5 2.5L5 12zM3 16a2 2 0 012-2h10a2 2 0 012 2v2a2 2 0 01-2-2H5a2 2 0 01-2-2v-2z"></path></svg></button>`
            : '';

        const content = isPrompt ? `<div class="prompt-suggestion">${textToCopy}</div>` : `<span>${rec}</span>`;
        const icon = !isPrompt ? '<svg class="w-5 h-5 mr-3 text-indigo-400 flex-shrink-0 mt-0.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15-5-5 1.41-1.41L11 14.17l7.59-7.59L20 8l-9 9z"></path></svg>' : '';
        
        return `<li class="flex items-start">${icon}<div class="flex-grow">${content}</div><div class="flex items-center flex-shrink-0">${generateBtnHTML}<button class="ml-2 p-1 text-gray-400 hover:text-white copy-btn" onclick="copyToClipboard(this, \`${textToCopy.replace(/`/g, '\\`')}\`)"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></button></div></li>`;
    }).join('');
    
    const titlesHTML = data.suggested_titles.map(title => `
        <li class="flex items-center justify-between p-2 bg-gray-800/50 rounded-md">
            <div class="flex items-center mr-2"><svg class="w-5 h-5 mr-3 text-indigo-400 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg><span>${title}</span></div>
            <button class="ml-2 p-1 text-gray-400 hover:text-white copy-btn flex-shrink-0" onclick="copyToClipboard(this, \`${title.replace(/`/g, '\\`')}\`)"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></button>
        </li>`).join('');
    
    const paletteHTML = data.color_palette.map(color => `
        <div class="text-center cursor-pointer" onclick="copyToClipboard(this.querySelector('p'), '${color}')">
            <div class="w-16 h-16 rounded-lg border-2 border-gray-600 shadow-md" style="background-color: ${color};"></div>
            <p class="text-sm font-mono mt-2 text-gray-400">${color}</p>
        </div>`).join('');

    return `
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8">
            <div class="lg:col-span-1 bg-gray-900/50 p-6 rounded-xl flex flex-col items-center justify-center border border-gray-700">
                <h2 class="text-xl font-bold mb-4 text-center">Pontuação Final</h2>
                <div class="relative w-48 h-48"><svg class="w-full h-full" viewBox="0 0 100 100"><circle class="text-gray-700" stroke-width="10" stroke="currentColor" fill="transparent" r="45" cx="50" cy="50" /><circle id="score-circle-progress" class="score-circle text-indigo-500" stroke-width="10" stroke-linecap="round" stroke="currentColor" fill="transparent" r="45" cx="50" cy="50" style="stroke-dasharray: 283; stroke-dashoffset: 283;" /></svg><div class="absolute inset-0 flex items-center justify-center text-5xl font-extrabold gradient-text">${finalScore}</div></div>
                <img src="${imageA_Data}" alt="Thumbnail Analisada" class="mt-6 w-full rounded-lg shadow-lg border-2 border-gray-600">
            </div>
            <div class="lg:col-span-2">
                <div class="bg-gray-900/50 p-6 rounded-xl border border-gray-700 mb-6"><h3 class="text-xl font-bold mb-5">Análise Detalhada</h3><div class="space-y-4">${detailsHTML}</div></div>
                <div class="bg-gray-900/50 p-6 rounded-xl border border-gray-700"><h3 class="text-xl font-bold mb-4">Recomendações para Melhorar</h3><ul class="space-y-3 h-48 overflow-y-auto pr-2 recommendations-list">${recommendationsHTML}</ul></div>
            </div>
        </div>
        <div class="mt-6 bg-gray-900/50 p-6 rounded-xl border border-gray-700"><h3 class="text-xl font-bold mb-4">Análise de Tendências do Nicho</h3><p id="trend-analysis-text" class="text-gray-300">${data.trend_analysis}</p></div>
        <div class="mt-6 bg-gray-900/50 p-6 rounded-xl border border-gray-700"><h3 class="text-xl font-bold mb-4">Sugestões de Títulos Otimizados</h3><ul class="space-y-3 titles-list">${titlesHTML}</ul></div>
        <div class="mt-6 bg-gray-900/50 p-6 rounded-xl border border-gray-700"><h3 class="text-xl font-bold mb-4">Paleta de Cores Sugerida</h3><div id="color-palette-container" class="flex justify-center gap-4">${paletteHTML}</div></div>
        <div id="generated-image-section" class="hidden mt-6 bg-gray-900/50 p-6 rounded-xl border border-gray-700 text-center"><h3 class="text-xl font-bold mb-4">Nova Thumbnail Gerada com IA</h3><div id="generated-image-container" class="flex justify-center items-center min-h-[200px]"></div></div>
        <div class="mt-8 flex justify-center"><button id="restart-button-results" class="bg-gray-600 text-white font-bold py-3 px-10 rounded-lg hover:bg-gray-500">Analisar Outra</button></div>
    `;
}

function createComparisonResultHTML(data) {
    const winnerColor = 'border-green-500 shadow-green-500/30';
    const loserColor = 'border-gray-700';

    const renderDetails = (details) => details.map(d => `
        <div class="flex justify-between items-center text-sm">
            <span>${d.name}</span>
            <span class="font-bold">${d.score}</span>
        </div>`).join('');

    return `
        <div class="space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-gray-900/50 p-4 rounded-xl border-2 ${data.comparison_result.winner === 'Versão A' ? winnerColor : loserColor}">
                    <h3 class="font-bold text-lg text-center mb-2">Versão A</h3>
                    <img src="${imageA_Data}" class="rounded-lg mb-4">
                    <div class="space-y-2">${renderDetails(data.version_a.details)}</div>
                </div>
                <div class="bg-gray-900/50 p-4 rounded-xl border-2 ${data.comparison_result.winner === 'Versão B' ? loserColor : winnerColor}">
                    <h3 class="font-bold text-lg text-center mb-2">Versão B</h3>
                    <img src="${imageB_Data}" class="rounded-lg mb-4">
                    <div class="space-y-2">${renderDetails(data.version_b.details)}</div>
                </div>
            </div>
            <div class="bg-indigo-900/40 p-6 rounded-xl border border-indigo-700 text-center">
                <h2 class="text-2xl font-bold mb-2">Vencedora: <span class="gradient-text">${data.comparison_result.winner}</span></h2>
                <p class="text-gray-300">${data.comparison_result.justification}</p>
            </div>
            <div class="mt-8 flex justify-center"><button id="restart-button-results" class="bg-gray-600 text-white font-bold py-3 px-10 rounded-lg hover:bg-gray-500">Analisar Outras</button></div>
        </div>
    `;
}

async function generateImage(prompt) {
    const genSection = document.getElementById('generated-image-section');
    const genContainer = document.getElementById('generated-image-container');
    
    if (!genSection || !genContainer) {
        console.error("Elementos para geração de imagem não encontrados!");
        return;
    }
    
    genSection.classList.remove('hidden');
    genContainer.innerHTML = `<div role="status">
                                <svg class="inline w-8 h-8 text-gray-600 animate-spin fill-blue-500" viewBox="0 0 100 101" ...></svg>
                                <span class="ml-2">Gerando imagem...</span>
                             </div>`;

    try {
        const response = await fetch('https://analisathumb.onrender.com/api/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });

        if (!response.ok) {
            const errorResult = await response.json();
            throw new Error(errorResult.error || `Erro do servidor (${response.status})`);
        }

        const result = await response.json();
        const imageUrl = result.generated_image_url;
        genContainer.innerHTML = `<img src="${imageUrl}" class="rounded-lg shadow-lg max-w-md w-full" alt="Imagem gerada por IA">`;

    } catch (error) {
        genContainer.innerHTML = `<p class="text-red-400">Falha ao gerar a imagem: ${error.message}</p>`;
    }
}

function resetApp() {
    DOMElements.resultsSection.classList.add('hidden');
    
    const genSection = document.getElementById('generated-image-section');
    if(genSection) genSection.classList.add('hidden');
    
    const trendSection = document.getElementById('trend-analysis-section');
    if(trendSection) trendSection.classList.add('hidden');

    const titlesSection = document.getElementById('suggested-titles-section');
    if(titlesSection) titlesSection.classList.add('hidden');

    const paletteSection = document.getElementById('color-palette-section');
    if(paletteSection) paletteSection.classList.add('hidden');

    DOMElements.inputSection.classList.remove('hidden');
    resetInputs();
}

document.addEventListener('DOMContentLoaded', setupEventListeners);
