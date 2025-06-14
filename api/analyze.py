import os
import requests
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_api_key(ai_service):
    key_name = f"{ai_service.upper()}_API_KEY"
    return os.environ.get(key_name)

def create_analysis_prompt(title, niche):
    return f"""
      Você é o AnalisaThumb, um especialista em otimização de thumbnails do YouTube para maximizar CTR.
      Analise a imagem e o contexto fornecido (título e nicho).

      Contexto:
      - Título do Vídeo: "{title or 'Não fornecido'}"
      - Nicho: "{niche}"

      Sua tarefa é retornar APENAS um objeto JSON com a seguinte estrutura:
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
      Seja rigoroso e forneça recomendações práticas e acionáveis.
    """

@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    data = request.json
    ai_service = data.get('ai_service')
    image_data_url = data.get('image_data_url')
    title = data.get('title')
    niche = data.get('niche')

    api_key = get_api_key(ai_service)
    if not api_key:
        return jsonify({"error": f"Chave de API para {ai_service.upper()} não encontrada no servidor."}), 500

    prompt = create_analysis_prompt(title, niche)

    try:
        if ai_service == 'openai':
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            payload = {
                "model": "gpt-4o",
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_data_url}}]}]
            }
            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()['choices'][0]['message']['content']

        elif ai_service == 'gemini':
            base64_image = image_data_url.split(',')[1]
            endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={api_key}'
            payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}]}]}
            response = requests.post(endpoint, json=payload)
            response.raise_for_status()
            result = response.json()['candidates'][0]['content']['parts'][0]['text']

        elif ai_service == 'deepseek':
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            payload = {
                "model": "deepseek-vision",
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_data_url}}]}]
            }
            response = requests.post('https://api.deepseek.com/chat/completions', headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()['choices'][0]['message']['content']

        else:
            return jsonify({"error": "Serviço de IA desconhecido"}), 400

        cleaned_result = result.replace("```json", "").replace("```", "").strip()
        return jsonify(json.loads(cleaned_result))

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de comunicação com a API: {e}"}), 502
    except Exception as e:
        return jsonify({"error": f"Erro inesperado no servidor: {e}"}), 500

if __name__ == '__main__':
    app.run(port=5000)