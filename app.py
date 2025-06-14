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
    """Endpoint principal que recebe a requisição POST e chama a API da DeepSeek."""
    
    app.logger.info(">>> Rota /api/analyze acessada <<<")

    try:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            app.logger.error("Chave de API DEEPSEEK_API_KEY não encontrada no servidor.")
            return jsonify({"error": "Chave de API não configurada no servidor."}), 500

        # ... (O resto da sua lógica de análise) ...
        data = request.json
        if not data:
            return jsonify({"error": "Requisição JSON vazia ou mal formatada."}), 400
        image_data_url = data.get('image_data_url')
        title = data.get('title')
        niche = data.get('niche')
        prompt = create_analysis_prompt(title, niche)
        app.logger.info(f"Iniciando análise com DeepSeek para o nicho '{niche}'.")
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {
            "model": "deepseek-vision",
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_data_url}}]}]
        }
        response = requests.post('https://api.deepseek.com/chat/completions', headers=headers, json=payload)
        app.logger.info(f"Resposta da API DeepSeek (status {response.status_code})")
        response.raise_for_status()
        result_data = response.json()
        result = result_data['choices'][0]['message']['content']
        cleaned_result = result.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(cleaned_result)
        if 'details' not in final_json or 'recommendations' not in final_json:
            app.logger.error(f"O JSON retornado pela IA não tem a estrutura esperada. Recebido: {final_json}")
            return jsonify({"error": "A resposta da IA não continha os dados esperados."}), 500
        return jsonify(final_json)

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        app.logger.error(f"Erro HTTP da API externa: {e.response.status_code} - {error_text}")
        return jsonify({"error": f"Erro na API DeepSeek: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor."}), 500

@app.route('/')
def health_check():
    """
    Rota de verificação de saúde que agora também lista as variáveis de ambiente para diagnóstico.
    """
    app.logger.info(">>> Rota de Health Check acessada <<<")
    
    # Pega todas as variáveis de ambiente disponíveis
    env_vars = os.environ
    
    # Cria um dicionário para enviar como resposta JSON
    response_data = {
        "status": "Backend do AnalisaThumb está no ar!",
        "message": "Abaixo estão as chaves de ambiente que este servidor consegue ver.",
        "environment_keys": sorted(list(env_vars.keys())) # Lista os NOMES das chaves em ordem alfabética
    }
    
    return jsonify(response_data)

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

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
