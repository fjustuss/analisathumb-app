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

# --- ROTA DE ANÁLISE (GEMINI) ---
@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    app.logger.info(">>> Rota /api/analyze acessada <<<")
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500

        data = request.json
        
        image_a_data_url = data.get('image_a_data_url')
        if not image_a_data_url:
            app.logger.error("Requisição recebida sem a imagem principal (image_a_data_url).")
            return jsonify({"error": "A imagem principal não foi enviada. Por favor, tente novamente."}), 400

        title = data.get('title')
        niche = data.get('niche')
        language = data.get('language', 'português')
        
        is_comparison = 'image_b_data_url' in data and data.get('image_b_data_url') is not None

        if is_comparison:
            prompt = create_comparison_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            image_b_b64 = data['image_b_data_url'].split(',')[1]
            parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}}, {"inline_data": {"mime_type": "image/jpeg", "data": image_b_b64}}]
        else:
            prompt = create_single_analysis_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            parts = [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}}]

        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": parts}]}
        
        response = requests.post(endpoint, json=payload)
        
        app.logger.info(f"Resposta bruta da API Gemini (status {response.status_code}): {response.text}")
        response.raise_for_status()
        
        result_json = response.json()

        if not result_json.get('candidates'):
            finish_reason = result_json.get('promptFeedback', {}).get('blockReason')
            if finish_reason:
                return jsonify({"error": f"A análise foi bloqueada por segurança. Motivo: {finish_reason}"}), 400
            raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        
        try:
            cleaned_result = result_text.replace("```json", "").replace("```", "").strip()
            if not cleaned_result:
                raise ValueError("A IA retornou uma string vazia após a limpeza.")
            final_json = json.loads(cleaned_result)
        except (json.JSONDecodeError, ValueError) as json_error:
            app.logger.error(f"Erro ao decodificar o JSON da IA: {json_error}")
            app.logger.error(f"Texto problemático recebido: {result_text}")
            return jsonify({"error": "A IA retornou uma resposta em formato inesperado. Tente novamente ou com outra imagem."}), 500
        
        return jsonify(final_json)

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        return jsonify({"error": f"Erro na API Gemini: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro em /api/analyze: {e}")
        return jsonify({"error": f"Ocorreu um erro interno durante a análise: {e}"}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Análise) está no ar!"

def create_single_analysis_prompt(title, niche, language):
    """
    Cria um prompt detalhado para análise única, incluindo tendências e paleta.
    """
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails e títulos do YouTube. Sua tarefa é analisar a imagem e o contexto fornecidos e retornar um objeto JSON. Não inclua NENHUMA palavra ou explicação antes ou depois do objeto JSON. Sua resposta deve começar com `{{` e terminar com `}}`.

      **Contexto:**
      - Título: "{title or 'Não fornecido'}"
      - Nicho: "{niche}"
      - Idioma para a Resposta: {language}

      **Formato de Saída OBRIGATÓRIO:**
      ```json
      {{
        "analysis_type": "single",
        "details": [
          {{"name": "Legibilidade do Texto", "score": 0-100}},
          {{"name": "Impacto Emocional", "score": 0-100}},
          {{"name": "Foco e Composição", "score": 0-100}},
          {{"name": "Uso de Cores", "score": 0-100}},
          {{"name": "Relevância (Contexto)", "score": 0-100}}
        ],
        "recommendations": [
          "Recomendação 1 sobre fontes, cores ou layout.",
          "Recomendação 2 sobre emoção ou clareza."
        ],
        "suggested_titles": [
          "Primeira sugestão de título.",
          "Segunda sugestão de título."
        ],
        "trend_analysis": "Análise curta sobre como esta thumbnail se alinha com as tendências atuais do nicho.",
        "color_palette": ["#C0392B", "#F1C40F", "#2980B9", "#ECF0F1"]
      }}
      ```
      **Instruções para Recomendações:**
      - Se a pontuação de 'Legibilidade do Texto' for baixa, você DEVE sugerir uma fonte específica de alto impacto (Ex: 'Impact', 'Anton') E uma combinação de cores.
      - Se a pontuação de 'Foco e Composição' for baixa, você DEVE sugerir uma mudança de layout clara (Ex: 'Posicione o rosto na direita e o texto na esquerda.').
      - Se a pontuação de "Foco e Composição" for menor que 75, inclua uma recomendação que comece com "Sugestão de Prompt:". O prompt deve ser em inglês.
    """

def create_comparison_prompt(title, niche, language):
    """Cria o prompt para a análise comparativa."""
    return f"""
      Você é o AnalisaThumb, um especialista em otimização de thumbnails.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma: {language}.
      **Tarefa:** Analise a Imagem A (primeira) e a Imagem B (segunda). Retorne um JSON com "analysis_type" como "comparison". O JSON deve conter "version_a" e "version_b", cada um com um array "details" de 5 objetos (com "name" e "score"). Inclua também um objeto "comparison_result" com "winner" e "justification".
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
