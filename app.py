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
# Permite requisições da API a partir de qualquer origem.
CORS(app, resources={r"/api/*": {"origins": "*"}})

def get_api_key(ai_service):
    """Busca a chave de API correta das variáveis de ambiente do servidor."""
    key_name = f"{ai_service.upper()}_API_KEY"
    return os.environ.get(key_name)

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

      Critérios para pontuação:
      - Legibilidade: O texto é grande, claro e contrasta com o fundo?
      - Impacto Emocional: Há um rosto humano? A emoção (surpresa, alegria, choque) é forte e clara?
      - Foco e Composição: A regra dos terços é usada? O ponto focal é óbvio? A imagem é limpa ou poluída?
      - Uso de Cores: As cores são vibrantes? Há contraste? A paleta de cores atrai atenção?
      - Relevância: A imagem se conecta com o título e o nicho? Ela representa visualmente a promessa do título?

      Seja rigoroso e forneça recomendações práticas e acionáveis.
    """

@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    """Endpoint principal que recebe a requisição e chama a IA selecionada."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Requisição JSON vazia ou mal formatada."}), 400

        ai_service = data.get('ai_service')
        image_data_url = data.get('image_data_url')
        title = data.get('title')
        niche = data.get('niche')

        api_key = get_api_key(ai_service)
        if not api_key:
            app.logger.error(f"Chave de API para {ai_service.upper()} não encontrada no servidor.")
            return jsonify({"error": f"Chave de API para {ai_service.upper()} não configurada no servidor."}), 500

        prompt = create_analysis_prompt(title, niche)
        app.logger.info(f"Iniciando análise com {ai_service.upper()} para o nicho {niche}.")

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
            result_json = response.json()
            # Tratamento de erro específico para Gemini
            if 'candidates' not in result_json or not result_json['candidates']:
                 raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
            result = result_json['candidates'][0]['content']['parts'][0]['text']

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
        final_json = json.loads(cleaned_result)
        
        response = jsonify(final_json)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Erro HTTP da API externa: {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"Erro na API de IA: {e.response.status_code}. Verifique sua chave ou o status da API."}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor."}), 500

@app.route('/')
def health_check():
    """Rota de verificação de saúde."""
    return "Backend do AnalisaThumb está no ar! Versão de produção."

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))

