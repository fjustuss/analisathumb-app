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
    """Endpoint principal que recebe a requisição POST e chama a API do OpenRouter."""
    
    app.logger.info(">>> Rota /api/analyze acessada <<<")

    try:
        # A chave de API do OpenRouter é lida da variável de ambiente.
        # No Render, deve ser nomeada como DEEPSEEK_API_KEY por consistência.
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            app.logger.error("Chave de API (DEEPSEEK_API_KEY) não encontrada no servidor.")
            return jsonify({"error": "Chave de API não configurada no servidor."}), 500

        data = request.json
        if not data:
            return jsonify({"error": "Requisição JSON vazia ou mal formatada."}), 400
        
        image_data_url = data.get('image_data_url')
        title = data.get('title')
        niche = data.get('niche')
        prompt = create_analysis_prompt(title, niche)
        
        app.logger.info(f"Iniciando análise com OpenRouter (DeepSeek) para o nicho '{niche}'.")
        
        # --- ALTERAÇÕES PARA O OPENROUTER ---
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://analisathumb-frontend.onrender.com", # Adicione a URL do seu site
            "X-Title": "AnalisaThumb" # Adicione o nome do seu site
        }
        
        payload = {
            "model": "deepseek/deepseek-vision", # CORREÇÃO: Nome do modelo de visão correto
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_data_url}}]}]
        }
        
        # O endpoint agora aponta para o OpenRouter
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        # --- FIM DAS ALTERAÇÕES ---

        app.logger.info(f"Resposta do OpenRouter (status {response.status_code})")
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
        return jsonify({"error": f"Erro na API (OpenRouter): {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor."}), 500

@app.route('/')
def health_check():
    """Rota de verificação de saúde para produção."""
    return "Backend do AnalisaThumb (OpenRouter Edition) está no ar!"

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
