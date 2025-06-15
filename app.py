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
            app.logger.error("Requisição recebida sem a imagem principal (image_a_data_url).")
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
        
        # --- LOG ADICIONAL PARA DEBUG ---
        # Imprime a estrutura exata do JSON recebido da IA para diagnóstico.
        app.logger.info(f"JSON recebido da IA: {json.dumps(final_json, indent=2)}")
        
        # --- Validação da Resposta ---
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
    # O prompt permanece o mesmo
    return f"""
      Você é o AnalisaThumb, um especialista de classe mundial em otimização de thumbnails do YouTube.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma: {language}.
      **Tarefa:** Analise a thumbnail e retorne um JSON com a chave "analysis_type" como "single", e os campos "details", "recommendations", "suggested_titles", "trend_analysis", e "color_palette".
      Para as recomendações, seja específico: sugira fontes (ex: 'Impact'), cores (ex: 'texto amarelo com contorno preto'), e layout (ex: 'rosto na direita, texto na esquerda'). Se a composição for fraca, inclua uma recomendação que comece com "Sugestão de Prompt:".
    """

def create_comparison_prompt(title, niche, language):
    # O prompt permanece o mesmo
    return f"""
      Você é o AnalisaThumb, um especialista em otimização de thumbnails.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma: {language}.
      **Tarefa:** Analise a Imagem A (primeira) e a Imagem B (segunda). Retorne um JSON com "analysis_type" como "comparison". O JSON deve conter "version_a" e "version_b", cada um com um array "details" de 5 critérios pontuados de 0-100. Inclua também um objeto "comparison_result" com uma chave "winner" ("Versão A" ou "Versão B") e uma "justification" explicando a escolha.
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
