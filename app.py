import os
import requests
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(level=logging.INFO)

# Cria a aplicação Flask
app = Flask(__name__)

# --- CONFIGURAÇÃO DE CORS ---
CORS(app, resources={r"/api/*": {"origins": "*"}})

def create_analysis_prompt(title, niche):
    """Cria o prompt detalhado para a IA."""
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails do YouTube com foco em maximizar a Taxa de Cliques (CTR).
      Analise a imagem da thumbnail e o contexto fornecido (título e nicho do vídeo).

      Contexto:
      - Título do Vídeo: "{title or 'Não fornecido'}"
      - Nicho: "{niche}"

      Sua tarefa é retornar um objeto JSON, e APENAS o objeto JSON, com a seguinte estrutura:
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
          "Sugestão de Prompt: (se a composição for fraca, sugira um prompt para gerar uma nova imagem, começando com 'Sugestão de Prompt:')"
        ]
      }}

      Seja rigoroso e forneça recomendações práticas e acionáveis.
    """

@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    """Endpoint principal que chama a API da DeepSeek."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Requisição JSON vazia ou mal formatada."}), 400

        image_data_url = data.get('image_data_url')
        title = data.get('title')
        niche = data.get('niche')

        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            app.logger.error("Chave de API DEEPSEEK_API_KEY não encontrada no servidor.")
            return jsonify({"error": "Chave de API não configurada no servidor."}), 500

        prompt = create_analysis_prompt(title, niche)
        app.logger.info(f"Iniciando análise com DeepSeek para o nicho {niche}.")

        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {
            "model": "deepseek-vision",
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_data_url}}]}]
        }
        response = requests.post('https://api.deepseek.com/chat/completions', headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()['choices'][0]['message']['content']
        cleaned_result = result.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(cleaned_result)
        
        response = jsonify(final_json)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Erro HTTP da API externa: {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"Erro na API DeepSeek: {e.response.status_code}. Verifique sua chave ou o status da API."}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": "Ocorreu um erro interno no servidor."}), 500

@app.route('/')
def health_check():
    """Rota de verificação de saúde."""
    return "Backend do AnalisaThumb (DeepSeek Edition) está no ar!"

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
