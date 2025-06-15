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
        language = data.get('language', 'português') # Pega o idioma, com 'português' como padrão

        prompt = create_analysis_prompt(title, niche, language) # Passa o idioma para o prompt

        app.logger.info(f"Iniciando análise com Gemini para o nicho '{niche}' em {language}.")

        base64_image = image_data_url.split(',')[1]
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}]}]
        }
        
        response = requests.post(endpoint, json=payload)
        app.logger.info(f"Resposta do Gemini (status {response.status_code})")
        response.raise_for_status()

        result_json = response.json()
        
        if 'candidates' not in result_json or not result_json['candidates']:
             app.logger.error(f"Resposta da API Gemini inválida, sem 'candidates': {result_json}")
             raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        result = result_json['candidates'][0]['content']['parts'][0]['text']
        cleaned_result = result.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(cleaned_result)

        # Verificação da nova estrutura
        if 'details' not in final_json or 'recommendations' not in final_json or 'suggested_titles' not in final_json:
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

def create_analysis_prompt(title, niche, language):
    """
    Cria um prompt detalhado que agora também solicita sugestões de títulos otimizados.
    """
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails e títulos de vídeos do YouTube para maximizar a Taxa de Cliques (CTR).

      **Contexto do Vídeo:**
      - **Título Original:** "{title or 'Não fornecido'}"
      - **Nicho:** "{niche}"
      - **Idioma para a Resposta:** {language}

      **Sua Tarefa (Dividida em Duas Partes):**
      
      **Parte 1: Análise da Thumbnail**
      Analise a imagem da thumbnail e retorne uma pontuação de 0 a 100 para cada um dos 5 critérios abaixo, junto com recomendações práticas.

      **Parte 2: Sugestões de Títulos**
      Com base na análise da imagem e no contexto, gere uma lista de 3 a 5 sugestões de títulos alternativos. Os títulos devem ser otimizados para curiosidade e CTR, e devem estar no idioma "{language}".

      **Formato de Saída Obrigatório:**
      Retorne **APENAS** um objeto JSON com a seguinte estrutura:

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
        ],
        "suggested_titles": [
          "Primeira sugestão de título no idioma {language}",
          "Segunda sugestão de título no idioma {language}",
          "Terceira sugestão de título no idioma {language}"
        ]
      }}
      ```

      **Instruções para Análise:**
      - Seja rigoroso e objetivo nas pontuações.
      - As recomendações devem ser práticas e acionáveis.
      - **Regra para a Geração de Prompt:** Se a pontuação de "Foco e Composição" for menor que 70, você **DEVE** incluir uma recomendação começando com `"Sugestão de Prompt:"`.
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
