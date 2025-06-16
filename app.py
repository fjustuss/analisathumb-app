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

# --- ROTA DE ANÁLISE ---
@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    app.logger.info(">>> Rota /api/analyze acessada <<<")
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500

        data = request.json
        
        image_data_url = data.get('image_a_data_url')
        if not image_data_url:
            app.logger.error("Requisição recebida sem a imagem principal (image_a_data_url).")
            return jsonify({"error": "A imagem principal não foi enviada. Por favor, tente novamente."}), 400

        title = data.get('title')
        niche = data.get('niche')
        language = data.get('language', 'português')
        prompt = create_analysis_prompt(title, niche, language)
        
        base64_image = image_data_url.split(',')[1]
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}]}]}
        
        response = requests.post(endpoint, json=payload)
        
        app.logger.info(f"Resposta bruta da API Gemini (status {response.status_code}): {response.text}")
        response.raise_for_status()
        
        result_json = response.json()

        # --- NOVA VALIDAÇÃO ROBUSTA DA RESPOSTA ---
        if not result_json.get('candidates'):
            finish_reason = result_json.get('promptFeedback', {}).get('blockReason')
            if finish_reason:
                app.logger.error(f"Requisição bloqueada pela API do Gemini. Motivo: {finish_reason}")
                return jsonify({"error": f"A análise foi bloqueada por segurança. Motivo: {finish_reason}"}), 400
            raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        candidate = result_json['candidates'][0]
        
        if not candidate.get('content') or not candidate['content'].get('parts'):
            finish_reason = candidate.get('finishReason')
            app.logger.error(f"A API do Gemini não retornou conteúdo. Motivo do término: {finish_reason}")
            return jsonify({"error": f"A IA não conseguiu processar a imagem. Motivo: {finish_reason}"}), 500

        result_text = candidate['content']['parts'][0]['text']
        
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
        app.logger.error(f"Erro HTTP da API externa: {e.response.status_code} - {error_text}")
        return jsonify({"error": f"Erro na API Gemini: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro em /api/analyze: {e}")
        return jsonify({"error": f"Ocorreu um erro interno durante a análise: {e}"}), 500

# --- ROTA PARA GERAÇÃO DE IMAGEM ---
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
        payload = {"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1792x1024"}
        
        response = requests.post("https://api.a4f.co/v1/images/generations", headers=headers, json=payload)
        response.raise_for_status()
        
        result_data = response.json()
        image_url = result_data['data'][0]['url']
            
        return jsonify({"generated_image_url": image_url})

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        return jsonify({"error": f"Erro na API de geração de imagem: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro em /api/generate-image: {e}")
        return jsonify({"error": "Ocorreu um erro interno durante a geração da imagem."}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini + A4F) está no ar!"

def create_analysis_prompt(title, niche, language):
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial...
      ...
      """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
