import os
import requests
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

def create_single_analysis_prompt(title, niche, language):
    """Cria um prompt detalhado para análise única, incluindo tendências e paleta."""
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails do YouTube. Sua tarefa é analisar a imagem e o contexto fornecidos e retornar um objeto JSON. Não inclua NENHUMA palavra, explicação ou texto antes ou depois do objeto JSON. A sua resposta deve começar com `{{` e terminar com `}}`.

      **Contexto:**
      - Título: "{title or 'Não fornecido'}"
      - Nicho: "{niche}"
      - Idioma da Resposta: {language}

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
        "trend_analysis": "Análise curta sobre como esta thumbnail se alinha com as tendências atuais do nicho '{niche}'.",
        "color_palette": ["#HEX1", "#HEX2", "#HEX3", "#HEX4"]
      }}
      ```
      **Instruções para Recomendações:**
      - As recomendações devem ser uma lista de ações práticas.
      - **Regra OBRIGATÓRIA:** Se a pontuação de "Foco e Composição" for menor que 75, inclua na lista de recomendações uma sugestão de prompt para IA, começando com "Sugestão de Prompt:". O prompt deve ser em inglês.
    """

def create_comparison_prompt(title, niche, language):
    """Cria o prompt para análise comparativa."""
    return f"""
      Você é o AnalisaThumb, um especialista em otimização de thumbnails.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma: {language}.
      **Tarefa:** Analise a Imagem A (primeira) e a Imagem B (segunda). Retorne um JSON com "analysis_type" como "comparison", contendo "version_a" e "version_b", cada um com um array "details" de 5 critérios pontuados. Inclua também um objeto "comparison_result" com "winner" e "justification".
    """

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
            return jsonify({"error": "A imagem principal não foi enviada."}), 400

        title = data.get('title')
        niche = data.get('niche')
        language = data.get('language', 'português')
        is_comparison = 'image_b_data_url' in data and data.get('image_b_data_url') is not None
        
        prompt = create_comparison_prompt(title, niche, language) if is_comparison else create_single_analysis_prompt(title, niche, language)
        
        parts = [{"text": prompt}]
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_a_data_url.split(',')[1]}})
        if is_comparison:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": data['image_b_data_url'].split(',')[1]}})

        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": parts}]}
        
        response = requests.post(endpoint, json=payload)
        app.logger.info(f"Resposta bruta da API Gemini (status {response.status_code})")
        response.raise_for_status()
        
        result_json = response.json()

        if not result_json.get('candidates'):
            raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        cleaned_result = result_text.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(cleaned_result)
        
        return jsonify(final_json)

    except Exception as e:
        app.logger.error(f"Erro em /api/analyze: {e}")
        return jsonify({"error": f"Ocorreu um erro interno durante a análise: {e}"}), 500

# Rota para geração de imagem permanece a mesma
@app.route('/api/generate-image', methods=['POST'])
def generate_image_endpoint():
    app.logger.info(">>> Rota /api/generate-image acessada <<<")
    try:
        api_key = os.environ.get("A4F_API_KEY")
        if not api_key:
            return jsonify({"error": "Chave da API de geração de imagem não configurada."}), 500

        data = request.json
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({"error": "Prompt não fornecido."}), 400

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "provider-5/gpt-image-1", "prompt": prompt, "n": 1, "size": "1792x1024"}
        
        response = requests.post("https://api.a4f.co/v1/images/generations", headers=headers, json=payload)
        response.raise_for_status()
        
        result_data = response.json()
        image_url = result_data.get('data', [{}])[0].get('url')
        if not image_url:
            raise ValueError("A resposta da API de imagem não continha uma URL.")
            
        return jsonify({"generated_image_url": image_url})

    except Exception as e:
        app.logger.error(f"Erro em /api/generate-image: {e}")
        return jsonify({"error": "Ocorreu um erro interno durante a geração da imagem."}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini + A4F) está no ar!"

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
