import os
import requests
import json
import logging
import time
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
        response.raise_for_status()
        
        result_json = response.json()
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        final_json = json.loads(result_text.replace("```json", "").replace("```", "").strip())
        
        return jsonify(final_json)

    except Exception as e:
        app.logger.error(f"Erro em /api/analyze: {e}")
        return jsonify({"error": f"Ocorreu um erro interno durante a análise: {e}"}), 500

# --- ROTA PARA GERAÇÃO DE IMAGEM ATUALIZADA PARA LEONARDO.AI ---
@app.route('/api/generate-image', methods=['POST'])
def generate_image_endpoint():
    app.logger.info(">>> Rota /api/generate-image acessada <<<")
    try:
        api_key = os.environ.get("LEONARDO_API_KEY")
        if not api_key:
            app.logger.error("Chave de API (LEONARDO_API_KEY) não encontrada no servidor.")
            return jsonify({"error": "Chave da API Leonardo.Ai não configurada."}), 500

        data = request.json
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({"error": "Prompt não fornecido."}), 400

        app.logger.info(f"Iniciando geração com Leonardo.Ai. Prompt: {prompt[:50]}...")
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }
        
        # ETAPA 1: Enviar o pedido para gerar a imagem
        generation_payload = {
            "height": 720,
            "width": 1280,
            "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3", # Leonardo Diffusion XL
            "prompt": prompt,
            "num_images": 1,
        }
        
        generation_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
        response_gen = requests.post(generation_url, json=generation_payload, headers=headers)
        response_gen.raise_for_status()
        
        generation_id = response_gen.json()['sdGenerationJob']['generationId']
        app.logger.info(f"Pedido de geração enviado. ID: {generation_id}")

        # ETAPA 2: Aguardar e buscar o resultado
        fetch_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        
        for _ in range(12): # Tentar por até 60 segundos (12 * 5s)
            time.sleep(5) # Esperar 5 segundos entre as tentativas
            response_fetch = requests.get(fetch_url, headers=headers)
            response_fetch.raise_for_status()
            fetch_data = response_fetch.json()
            
            status = fetch_data.get('generations_by_pk', {}).get('status')
            app.logger.info(f"Status da geração: {status}")
            
            if status == 'COMPLETE':
                image_url = fetch_data['generations_by_pk']['generated_images'][0]['url']
                return jsonify({"generated_image_url": image_url})
            elif status == 'FAILED':
                raise Exception("A geração da imagem falhou no servidor da Leonardo.Ai.")
        
        raise Exception("A geração da imagem demorou muito para completar (timeout).")

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        app.logger.error(f"Erro HTTP da API de imagem: {e.response.status_code} - {error_text}")
        return jsonify({"error": f"Erro na API Leonardo.Ai: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro em /api/generate-image: {e}")
        return jsonify({"error": f"Ocorreu um erro interno durante a geração da imagem: {e}"}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini + Leonardo.Ai) está no ar!"

def create_single_analysis_prompt(title, niche, language):
    return f"""
      Sua única tarefa é analisar a imagem e o contexto e retornar um objeto JSON...
    """

def create_comparison_prompt(title, niche, language):
    return f"""
      Você é o AnalisaThumb, um especialista em otimização de thumbnails...
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
