// ... (código existente até a função generateImage)

async function generateImage(prompt) {
    const genSection = document.getElementById('generated-image-section');
    const genContainer = document.getElementById('generated-image-container');
    
    if (!genSection || !genContainer) {
        console.error("Elementos para geração de imagem não encontrados!");
        return;
    }
    
    genSection.classList.remove('hidden');
    // ATUALIZAÇÃO: Texto de carregamento
    genContainer.innerHTML = `<div role="status">
                                <svg class="inline w-8 h-8 text-gray-600 animate-spin fill-blue-500" viewBox="0 0 100 101" ...></svg>
                                <span class="ml-2">Gerando imagem com Leonardo.Ai... (pode levar até 30s)</span>
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

// ... (resto do script.js)
