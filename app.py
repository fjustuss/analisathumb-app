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
        language = data.get('language', 'português')

        prompt = create_analysis_prompt(title, niche, language)

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
        if 'details' not in final_json or 'recommendations' not in final_json or 'suggested_titles' not in final_json or 'trend_analysis' not in final_json or 'color_palette' not in final_json:
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
    Cria um prompt detalhado que agora também solicita uma paleta de cores.
    """
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails e títulos de vídeos do YouTube para maximizar a Taxa de Cliques (CTR).

      **Contexto do Vídeo:**
      - **Título Original:** "{title or 'Não fornecido'}"
      - **Nicho:** "{niche}"
      - **Idioma para a Resposta:** {language}

      **Sua Tarefa (Dividida em Quatro Partes):**
      
      1.  **Análise da Thumbnail:** Retorne uma pontuação de 0 a 100 para cada um dos 5 critérios abaixo, junto com recomendações práticas.
      2.  **Sugestões de Títulos:** Gere de 3 a 5 sugestões de títulos otimizados no idioma "{language}".
      3.  **Análise de Tendências:** Com base no nicho, comente em um parágrafo se o estilo da thumbnail está alinhado com as tendências atuais.
      4.  **Gerador de Paleta de Cores:** Sugira uma paleta de 4 cores (em códigos hexadecimais) que seja harmoniosa e de alto contraste, ideal para ser usada nesta thumbnail ou em designs futuros para este nicho.

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
          "Primeira sugestão de título...",
          "Segunda sugestão de título..."
        ],
        "trend_analysis": "Um parágrafo com a análise de tendência aqui.",
        "color_palette": [
          "#C0392B",
          "#F1C40F",
          "#2980B9",
          "#ECF0F1"
        ]
      }}
      ```

      **Instruções para Análise:**
      - Seja rigoroso e objetivo nas pontuações.
      - As recomendações devem ser práticas e acionáveis.
      - A paleta de cores deve conter 4 códigos hexadecimais válidos.
      - **Regra do Prompt:** Se a pontuação de "Foco e Composição" for menor que 70, **DEVE** incluir uma recomendação começando com `"Sugestão de Prompt:"`.
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
