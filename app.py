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

# --- ROTA PARA GERAÇÃO DE IMAGEM ---
@app.route('/api/generate-image', methods=['POST'])
def generate_image_endpoint():
    app.logger.info(">>> Rota /api/generate-image acessada <<<")
    try:
        api_key = os.environ.get("A4F_API_KEY") 
        if not api_key:
            app.logger.error("Chave de API (A4F_API_KEY) não encontrada no servidor.")
            return jsonify({"error": "Chave da API de geração de imagem não configurada."}), 500

        data = request.json
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({"error": "Prompt não fornecido."}), 400

        app.logger.info(f"Iniciando geração de imagem com A4F.co (FLUX.1-schnell).")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # --- ATUALIZAÇÃO: Nome do modelo alterado ---
        payload = {
            "model": "provider-3/FLUX.1-schnell",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024" # Tamanho padrão para este tipo de modelo
        }
        
        response = requests.post("https://api.a4f.co/v1/images/generations", headers=headers, json=payload)
        app.logger.info(f"Resposta da API A4F.co (status {response.status_code})")
        response.raise_for_status()
        
        result_data = response.json()
        
        image_url = result_data.get('data', [{}])[0].get('url')
        if not image_url:
            app.logger.error(f"Resposta da API de imagem não continha uma URL. Recebido: {result_data}")
            raise ValueError("A resposta da API de imagem não continha uma URL.")
            
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
    return "Backend do AnalisaThumb (Gemini + A4F) está no ar!"

def create_analysis_prompt(title, niche, language):
    """
    Cria um prompt muito mais explícito para garantir o formato correto da resposta.
    """
    return f"""
      Sua única tarefa é analisar a imagem e o contexto fornecidos e retornar um objeto JSON. Não inclua NENHUMA palavra, explicação ou texto antes ou depois do objeto JSON. A sua resposta deve começar com `{{` e terminar com `}}`.

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
          "Recomendação 1",
          "Recomendação 2"
        ]
      }}
      ```
      **Instruções para Recomendações:**
      - Se a pontuação de "Foco e Composição" for menor que 75, você DEVE incluir uma recomendação que comece com "Sugestão de Prompt:". O prompt deve ser em inglês.
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
