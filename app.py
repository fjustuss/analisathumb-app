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
            return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500

        data = request.json
        
        image_a_data_url = data.get('image_a_data_url')
        if not image_a_data_url:
            return jsonify({"error": "A imagem principal não foi enviada."}), 400

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
        
        if not result_json.get('candidates'):
            raise ValueError("Resposta da API Gemini inválida: sem 'candidates'.")
        
        result_text = result_json['candidates'][0]['content']['parts'][0]['text']
        final_json = json.loads(result_text.replace("```json", "").replace("```", "").strip())
        
        return jsonify(final_json)

    except Exception as e:
        app.logger.error(f"Erro em /api/analyze: {e}")
        return jsonify({"error": f"Ocorreu um erro interno durante a análise."}), 500

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
        payload = {"model": "provider-5/gpt-image-1", "prompt": prompt, "n": 1, "size": "1792x1024"}
        
        response = requests.post("https://api.a4f.co/v1/images/generations", headers=headers, json=payload)
        response.raise_for_status()
        
        result_data = response.json()
        image_url = result_data.get('data', [{}])[0].get('url')
        if not image_url:
            raise ValueError("A resposta da API de imagem não continha uma URL.")
            
        return jsonify({"generated_image_url": image_url})

    except Exception as e:
        app.logger.error(f"Erro em /api/generate-image: {e}")
        return jsonify({"error": "Ocorreu um erro interno durante a geração da imagem."}), 500

@app.route('/')
def health_check():
    return "Backend do AnalisaThumb (v1.0) está no ar!"

def create_single_analysis_prompt(title, niche, language):
    return f"""
      Sua única tarefa é analisar a imagem e o contexto e retornar um objeto JSON. Não inclua NENHUMA palavra ou explicação antes ou depois do objeto JSON. Sua resposta deve começar com `{{` e terminar com `}}`.

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
      - Se a pontuação de 'Legibilidade do Texto' for baixa, você DEVE sugerir uma fonte específica de alto impacto (Ex: 'Impact', 'Anton', 'Bebas Neue') E uma combinação de cores (Ex: 'Use texto amarelo com um contorno preto para máximo contraste.').
      - Se a pontuação de 'Foco e Composição' for baixa, você DEVE sugerir uma mudança de layout clara (Ex: 'Posicione o rosto em close-up na direita e o texto na esquerda para guiar o olhar.').
      - Se a pontuação de "Foco e Composição" for menor que 75, inclua uma recomendação que comece com "Sugestão de Prompt:". O prompt deve ser em inglês.
    """

def create_comparison_prompt(title, niche, language):
    return f"""
      Você é o AnalisaThumb, um especialista em otimização de thumbnails.
      **Contexto:** Título: "{title or 'Não fornecido'}", Nicho: "{niche}", Idioma: {language}.
      **Tarefa:** Analise a Imagem A (primeira) e a Imagem B (segunda). Retorne um JSON com "analysis_type" como "comparison", contendo "version_a" e "version_b", cada um com um array "details" de 5 objetos (com "name" e "score"). Inclua também um objeto "comparison_result" com "winner" e "justification".
    """

if __name__ == '__main__':
    app.run(port=os.environ.get("PORT", 5000))
