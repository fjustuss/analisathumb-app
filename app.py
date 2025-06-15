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
    app.logger.info(">>> Rota /api/analyze acessada <<<")
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            app.logger.error("Chave de API (GEMINI_API_KEY) não encontrada no servidor.")
            return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500

        data = request.json
        if not data:
            return jsonify({"error": "Requisição JSON vazia ou mal formatada."}), 400

        image_a_data_url = data.get('image_a_data_url')
        if not image_a_data_url:
            return jsonify({"error": "A imagem principal não foi enviada. Por favor, tente novamente."}), 400

        title = data.get('title')
        niche = data.get('niche')
        language = data.get('language', 'português')
        
        is_comparison = 'image_b_data_url' in data and data.get('image_b_data_url') is not None

        if is_comparison:
            image_b_data_url = data.get('image_b_data_url')
            if not image_b_data_url:
                 return jsonify({"error": "Modo de comparação ativado, mas a imagem da Versão B não foi enviada."}), 400
            
            app.logger.info(f"Iniciando ANÁLISE COMPARATIVA com Gemini para o nicho '{niche}'.")
            prompt = create_comparison_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            image_b_b64 = image_b_data_url.split(',')[1]
            parts = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b_b64}}
            ]
        else:
            app.logger.info(f"Iniciando ANÁLISE SIMPLES com Gemini para o nicho '{niche}'.")
            prompt = create_single_analysis_prompt(title, niche, language)
            image_a_b64 = image_a_data_url.split(',')[1]
            parts = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_a_b64}}
            ]

        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}'
        payload = {"contents": [{"parts": parts}]}
        
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()

        result_json = response.json()
        
        if 'candidates' not in result_json or not result_json['candidates']:
             raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        cleaned_result = result_text.replace("```json", "").replace("```", "").strip()
        final_json = json.loads(cleaned_result)
        
        app.logger.info(f"JSON recebido da IA: {json.dumps(final_json, indent=2)}")
        
        # Validação da Resposta
        if is_comparison:
            if not all(k in final_json for k in ["analysis_type", "version_a", "version_b", "comparison_result"]):
                raise ValueError("A resposta JSON da IA para comparação está mal formatada.")
        else:
            if not all(k in final_json for k in ["analysis_type", "details", "recommendations"]):
                raise ValueError("A resposta JSON da IA para análise simples está mal formatada.")
            if not isinstance(final_json.get('details'), list):
                 raise TypeError("O campo 'details' na resposta da IA não é uma lista.")

        return jsonify(final_json)

    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        app.logger.error(f"Erro HTTP da API externa: {e.response.status_code} - {error_text}")
        return jsonify({"error": f"Erro na API Gemini: {e.response.status_code}. Detalhes: {error_text}"}), e.response.status_code
    except Exception as e:
        app.logger.error(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": f"Ocorreu um erro interno no servidor: {e}"}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (Gemini Edition) está no ar!"

def create_single_analysis_prompt(title, niche, language):
    """Cria um prompt muito mais explícito para garantir o formato correto da resposta."""
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails do YouTube.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma: {language}.
      **Tarefa:** Analise a thumbnail e retorne um JSON com a chave "analysis_type" como "single".
      
      **Formato de Saída OBRIGATÓRIO:**
      Sua resposta deve ser APENAS o objeto JSON. O campo "details" DEVE ser uma lista (array) de objetos. Cada objeto deve ter as chaves "name" e "score".

      Exemplo da estrutura correta:
      ```json
      {{
        "analysis_type": "single",
        "details": [
          {{"name": "Legibilidade do Texto", "score": 85}},
          {{"name": "Impacto Emocional", "score": 70}},
          {{"name": "Foco e Composição", "score": 90}},
          {{"name": "Uso de Cores", "score": 80}},
          {{"name": "Relevância (Contexto)", "score": 95}}
        ],
        "recommendations": [
          "Recomendação específica sobre a fonte...",
          "Sugestão de Prompt: cinematic photo of..."
        ]
      }}
      ```
      **Instruções para Recomendações:**
      - Para **Legibilidade**, se a pontuação for baixa, sugira uma fonte específica de alto impacto (Ex: 'Impact', 'Anton') e uma combinação de cores.
      - Para **Composição**, se a pontuação for baixa, sugira uma mudança de layout clara (Ex: 'Posicione o rosto na direita e o texto na esquerda.').
      - **Regra OBRIGATÓRIA:** Se a pontuação de "Foco e Composição" for menor que 75, inclua uma recomendação que comece com "Sugestão de Prompt:". O prompt deve ser em inglês.
    """

def create_comparison_prompt(title, niche, language):
    """Cria um prompt muito mais explícito para a comparação."""
    return f"""
      Você é o AnalisaThumb, um especialista em otimização de thumbnails.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma: {language}.
      **Tarefa:** Analise a Imagem A (primeira) e a Imagem B (segunda).
      
      **Formato de Saída OBRIGATÓRIO:**
      Retorne um JSON com "analysis_type" como "comparison". O JSON DEVE conter "version_a" e "version_b", cada um com um array "details" de 5 objetos (com "name" e "score"). Inclua também um objeto "comparison_result" com "winner" e "justification".
      
      Exemplo da estrutura correta:
       ```json
      {{
        "analysis_type": "comparison",
        "version_a": {{
          "details": [
            {{"name": "Legibilidade do Texto", "score": 80}},
            {{"name": "Impacto Emocional", "score": 90}},
            {{"name": "Foco e Composição", "score": 75}},
            {{"name": "Uso de Cores", "score": 85}},
            {{"name": "Relevância (Contexto)", "score": 95}}
          ]
        }},
        "version_b": {{
          "details": [
            {{"name": "Legibilidade do Texto", "score": 85}},
            {{"name": "Impacto Emocional", "score": 80}},
            {{"name": "Foco e Composição", "score": 85}},
            {{"name": "Uso de Cores", "score": 90}},
            {{"name": "Relevância (Contexto)", "score": 90}}
          ]
        }},
        "comparison_result": {{
            "winner": "Versão B",
            "justification": "A Versão B vence pois tem um ponto focal mais claro e cores mais vibrantes, o que é mais eficaz para o nicho de '{niche}'."
        }}
      }}
      ```
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
