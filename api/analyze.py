import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# Cria a aplicação Flask
app = Flask(__name__)

# Configura o CORS para permitir requisições do seu frontend
# A linha abaixo permite requisições de qualquer origem, o que é útil para debug.
CORS(app) 

# Este é o nosso endpoint de teste
@app.route('/api/analyze', methods=['POST', 'GET'])
def analyze_endpoint():
    """
    Este endpoint de teste ignora qualquer dado recebido
    e sempre retorna um JSON de sucesso.
    """
    # Criamos uma resposta JSON fixa.
    mock_response = {
      "details": [
        {"name": "Teste de Conexão com Backend", "score": 100},
        {"name": "Servidor Python/Flask", "score": 100}
      ],
      "recommendations": [
        "Se você está vendo esta mensagem, a conexão entre o frontend e o backend está funcionando perfeitamente!",
        "O próximo passo é restaurar a lógica original das APIs no backend."
      ]
    }
    
    # Retornamos a resposta como um JSON válido.
    return jsonify(mock_response)

# Rota de "health check" para ver se o servidor está no ar
@app.route('/')
def health_check():
    return "Backend do AnalisaThumb está no ar!"

# Esta parte só é usada se você rodar o arquivo localmente.
# O Render usa o comando do Gunicorn que configuramos.
if __name__ == '__main__':
    app.run(port=5000)
