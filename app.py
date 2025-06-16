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
        
        image_data_url = data.get('image_a_data_url')
        if not image_data_url:
            app.logger.error("Requisição recebida sem a imagem principal (image_a_data_url).")
            return jsonify({"error": "A imagem principal não foi enviada. Por favor, tente novamente."}), 400

        title = data.get('title')
        niche = data.get('niche')
        language = data.get('language', 'português')
        
        # O prompt é criado com a lógica completa
        prompt = create_analysis_prompt(title, niche, language)
        
        base64_image = image_data_url.split(',')[1]
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}]}]}
        
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

# --- ROTA PARA GERAÇÃO DE IMAGEM (MODO DE DEBUG) ---
@app.route('/api/generate-image', methods=['POST'])
def generate_image_endpoint():
    app.logger.info(">>> Rota /api/generate-image acessada (MODO DEBUG) <<<")
    
    # Em vez de chamar a API externa, retornamos instantaneamente uma resposta de sucesso.
    # Usamos uma URL de imagem de placeholder para o teste.
    mock_image_url = "https://placehold.co/1792x1024/1a202c/ffffff/png?text=Imagem+Gerada+com+Sucesso!"
    
    app.logger.info(f"Retornando URL de imagem de teste: {mock_image_url}")
    
    # Retorna um JSON no formato que o frontend espera.
    # Note que a chave é 'generated_image_url' para corresponder ao script.js que espera uma URL.
    return jsonify({"generated_image_url": mock_image_url})


@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini + A4F - MODO DEBUG) está no ar!"

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
        ],
        "suggested_titles": [
          "Sugestão de título 1",
          "Sugestão de título 2"
        ],
        "trend_analysis": "Análise curta sobre como esta thumbnail se alinha com as tendências atuais do nicho.",
        "color_palette": ["#C0392B", "#F1C40F", "#2980B9", "#ECF0F1"]
      }}
      ```
      **Instruções para Recomendações:**
      - Se a pontuação de "Foco e Composição" for menor que 75, você DEVE incluir uma recomendação que comece com "Sugestão de Prompt:". O prompt deve ser em inglês.
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
