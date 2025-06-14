import os
import requests
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Cria a aplicação Flask
app = Flask(__name__)
CORS(app)

@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    """Endpoint principal que recebe a requisição POST e chama a API do Google Gemini."""

    app.logger.info(">>> Rota /api/analyze acessada <<<")

    try:
        # A chave de API do Gemini é lida da variável de ambiente.
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            app.logger.error("Chave de API (GEMINI_API_KEY) não encontrada no servidor.")
            return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500

        data = request.json
        if not data:
            return jsonify({"error": "Requisição JSON vazia ou mal formatada."}), 400

        image_data_url = data.get('image_data_url')
        title = data.get('title')
        niche = data.get('niche')
        prompt = create_analysis_prompt(title, niche)

        app.logger.info(f"Iniciando análise com Gemini para o nicho '{niche}'.")

        # --- LÓGICA PARA A API GEMINI ---
        # Gemini espera apenas a parte base64 da imagem
        base64_image = image_data_url.split(',')[1]
        
        # CORREÇÃO: Atualizado para o novo modelo gemini-1.5-flash-latest
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}
                ]
            }]
        }
        
        response = requests.post(endpoint, json=payload)
        # --- FIM DA LÓGICA GEMINI ---

        app.logger.info(f"Resposta do Gemini (status {response.status_code})")
        response.raise_for_status()

        result_json = response.json()
        
        # Tratamento de erro específico para Gemini
        if 'candidates' not in result_json or not result_json['candidates']:
             app.logger.error(f"Resposta da API Gemini inválida, sem 'candidates': {result_json}")
             raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        result = result_json['candidates'][0]['content']['parts'][0]['text']
        cleaned_result = result.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(cleaned_result)

        if 'details' not in final_json or 'recommendations' not in final_json:
            app.logger.error(f"O JSON retornado pela IA não tem a estrutura esperada. Recebido: {final_json}")
            return jsonify({"error": "A resposta da IA não continha os dados esperados."}), 500

        return jsonify(final_json)

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        app.logger.error(f"Erro HTTP da API externa: {e.response.status_code} - {error_text}")
        return jsonify({"error": f"Erro na API Gemini: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor."}), 500

@app.route('/')
def health_check():
    """Rota de verificação de saúde para produção."""
    return "Backend do AnalisaThumb (Gemini Edition) está no ar!"

def create_analysis_prompt(title, niche):
    """
    Cria um prompt mais detalhado e instrutivo para a IA, garantindo
    recomendações mais ricas e a geração de prompts de imagem.
    """
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails do YouTube com foco em maximizar a Taxa de Cliques (CTR). Sua análise deve ser rigorosa, objetiva e baseada em princípios de design e marketing.

      **Contexto do Vídeo:**
      - **Título:** "{title or 'Não fornecido'}"
      - **Nicho:** "{niche}"

      **Sua Tarefa:**
      Analise a imagem da thumbnail fornecida e o contexto acima. Retorne **APENAS** um objeto JSON com a seguinte estrutura:

      ```json
      {{
        "details": [
          {{"name": "Legibilidade do Texto", "score": 0-100}},
          {{"name": "Impacto Emocional", "score": 0-100}},
          {{"name": "Foco e Composição", "score": 0-100}},
          {{"name": "Uso de Cores", "score": 0-100}},
          {{"name": "Relevância (Contexto)", "score": 0-100}}
        ],
        "recommendations": [
          "Recomendação 1",
          "Recomendação 2",
          "Sugestão de Prompt: (se aplicável)"
        ]
      }}
      ```

      **Instruções Detalhadas para Pontuação e Recomendações:**

      1.  **Legibilidade do Texto (score):**
          -   **Alto (85-100):** Texto grande, fonte forte (bold/heavy), ótimo contraste, poucas palavras.
          -   **Médio (50-84):** Texto legível, mas poderia ser maior, ter mais contraste ou ser mais conciso.
          -   **Baixo (0-49):** Texto pequeno, difícil de ler, fonte fina, baixo contraste, muitas palavras.
          -   **Recomendação:** Se a pontuação for baixa, sugira ações como "Aumente o tamanho da fonte" ou "Use um contorno no texto para destacá-lo".

      2.  **Impacto Emocional (score):**
          -   **Alto (85-100):** Rosto humano visível em close-up, com emoção clara e forte (surpresa, choque, alegria intensa).
          -   **Médio (50-84):** Rosto visível, mas com emoção neutra ou pouco expressiva.
          -   **Baixo (0-49):** Sem rosto humano ou o rosto está muito distante/obscurecido.
          -   **Recomendação:** Se a pontuação for baixa, sugira "Adicione um rosto com uma expressão de surpresa para gerar curiosidade".

      3.  **Foco e Composição (score):**
          -   **Alto (85-100):** Composição limpa, ponto de foco claro (regra dos terços), poucos elementos que não distraem.
          -   **Médio (50-84):** A composição é boa, mas um pouco poluída ou o ponto focal não é imediato.
          -   **Baixo (0-49):** Composição confusa, muitos elementos, sem hierarquia visual.
          -   **Recomendação:** Se a pontuação for baixa, sugira "Simplifique a imagem removendo elementos de fundo" ou "Crie um ponto de foco mais forte".

      4.  **Uso de Cores (score):**
          -   **Alto (85-100):** Cores vibrantes, saturadas, com alto contraste entre o objeto principal e o fundo. Uso eficaz de cores complementares.
          -   **Médio (50-84):** As cores são boas, mas poderiam ser mais saturadas ou ter mais contraste.
          -   **Baixo (0-49):** Cores opacas, sem vida, baixo contraste, paleta de cores confusa.
          -   **Recomendação:** Se a pontuação for baixa, sugira "Aumente a saturação das cores" ou "Use uma cor quente (amarelo, laranja) para destacar o texto".

      5.  **Relevância (Contexto) (score):**
          -   **Alto (85-100):** A imagem representa perfeitamente a promessa do título e se encaixa no nicho. Ex: Título sobre "erro de programação" mostra um código com um grande 'X' vermelho.
          -   **Médio (50-84):** A imagem tem relação com o tema, mas poderia ser mais direta ou intrigante.
          -   **Baixo (0-49):** Imagem genérica, que não se conecta claramente com o título.
          -   **Recomendação:** Se a pontuação for baixa, sugira "Adicione um elemento visual que represente diretamente o tópico '{title}'".

      **Regra para a Geração de Prompt:**
      -   **SE** a pontuação de "Foco e Composição" for **menor que 70**, você **DEVE** incluir uma recomendação começando com `"Sugestão de Prompt:"`.
      -   O prompt deve ser criativo e diretamente relacionado ao título e nicho do vídeo para ser usado em geradores de imagem como Midjourney ou DALL-E.
      -   Exemplo de prompt: `"Sugestão de Prompt: Um cérebro humano feito de circuitos de neon brilhantes, em um fundo escuro, estilo cyberpunk, fotorrealista --ar 16:9"`
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
