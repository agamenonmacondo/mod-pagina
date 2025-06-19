app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """Endpoint para generar imágenes"""
    data = request.get_json()
    prompt = data.get('prompt', '')
    
    # Aquí iría tu lógica de generación de imágenes
    return jsonify({
        "service": "images",
        "image_url": f"https://placehold.co/512x512?text={prompt}",
        "prompt": prompt,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "images"})

if __name__ == '__main__':
    print("🎨 Webhook Imágenes iniciado en puerto 5002")
    app.run(debug=True, port=5002, host='0.0.0.0')