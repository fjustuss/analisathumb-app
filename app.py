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
        # ... (código de análise do Gemini, sem alterações)
        image_data_url = data.get('image_data_url')
        title = data.get('title')
        niche = data.get('niche')
        language = data.get('language', 'português')
        prompt = create_analysis_prompt(title, niche, language)
        
        base64_image = image_data_url.split(',')[1]
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}]}]}
        
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        
        result_json = response.json()
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        final_json = json.loads(result_text.replace("```json", "").replace("```", "").strip())
        
        return jsonify(final_json)

    except Exception as e:
        app.logger.error(f"Erro em /api/analyze: {e}")
        return jsonify({"error": "Ocorreu um erro interno durante a análise."}), 500

# --- ROTA DE GERAÇÃO DE IMAGEM (ATUALIZADA PARA A4F.CO) ---
@app.route('/api/generate-image', methods=['POST'])
def generate_image_endpoint():
    app.logger.info(">>> Rota /api/generate-image acessada <<<")
    try:
        # Pega a chave da API A4F.co das variáveis de ambiente
        api_key = os.environ.get("A4F_API_KEY")
        if not api_key:
            app.logger.error("Chave de API (A4F_API_KEY) não encontrada no servidor.")
            return jsonify({"error": "Chave da API de geração de imagem não configurada."}), 500

        data = request.json
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({"error": "Prompt não fornecido."}), 400

        app.logger.info(f"Iniciando geração de imagem com A4F.co (DALL-E 3). Prompt: {prompt[:50]}...")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Payload para a API da A4F.co (compatível com OpenAI)
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1792x1024" # Tamanho ideal para thumbnail (16:9)
        }
        
        # Endpoint da API A4F.co para geração de imagem
        response = requests.post("https://api.a4f.co/v1/images/generations", headers=headers, json=payload)
        response.raise_for_status()
        
        result_data = response.json()
        
        # Extrai a URL da imagem da resposta
        image_url = result_data['data'][0]['url']
            
        return jsonify({"generated_image_url": image_url})

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        app.logger.error(f"Erro HTTP da API de imagem: {e.response.status_code} - {error_text}")
        return jsonify({"error": f"Erro na API de geração de imagem: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro em /api/generate-image: {e}")
        return jsonify({"error": "Ocorreu um erro interno durante a geração da imagem."}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini + A4F.co) está no ar!"

def create_analysis_prompt(title, niche, language):
    # O prompt de análise permanece o mesmo
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial...
      ...
      """
