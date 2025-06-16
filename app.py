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

        if is_comparison:
            prompt = create_comparison_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            image_b_b64 = data['image_b_data_url'].split(',')[1]
            parts = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b_b64}}
            ]
        else:
            prompt = create_single_analysis_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            parts = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}}
            ]

        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": parts}]}
        
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()

        result_json = response.json()
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        final_json = json.loads(result_text.replace("```json", "").replace("```", "").strip())
        
        return jsonify(final_json)

    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor: {e}"}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini Edition) está no ar!"

def create_single_analysis_prompt(title, niche, language):
    """Cria um prompt focado apenas na análise visual."""
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails do YouTube.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma da Resposta: {language}.
      
      **Sua Tarefa:**
      Analise a imagem da thumbnail e retorne um objeto JSON com uma pontuação de 0 a 100 para cada critério. Forneça recomendações práticas e acionáveis, uma paleta de cores sugerida, e uma análise de tendências.

      **Formato de Saída OBRIGATÓRIO:**
      Sua resposta deve ser APENAS o objeto JSON, com a seguinte estrutura:
      ```json
      {{
        "analysis_type": "single",
        "details": [
          {{"name": "Legibilidade do Texto", "score": 85}},
          {{"name": "Impacto Emocional", "score": 70}},
          {{"name": "Foco e Composição", "score": 90}},
          {{"name": "Uso de Cores", "score": 80}},
          {{"name": "Relevância (Contexto)", "score": 95}}
        ],
        "recommendations": [
          "Recomendação específica sobre a fonte...",
          "Sugestão de Prompt: (se a composição for fraca, inclua esta recomendação)"
        ],
        "trend_analysis": "Análise de tendência do nicho aqui.",
        "color_palette": ["#C0392B", "#F1C40F", "#2980B9", "#ECF0F1"]
      }}
      ```
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
