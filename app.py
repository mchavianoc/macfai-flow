from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Permite peticiones desde cualquier origen

# Almacenamiento en memoria (para pruebas)
# En producción, usa una base de datos real
solicitudes = []

@app.route('/webhook/cotizacion', methods=['POST'])
def recibir_cotizacion():
    """
    Endpoint que ElevenLabs llamará cuando el agente ejecute la tool
    """
    print("\n" + "="*70)
    print("📞 NUEVA COTIZACIÓN RECIBIDA DESDE ELEVENLABS")
    print("="*70)
    
    # 1. Obtener los datos que envía ElevenLabs
    data = request.json
    print("\n📦 JSON COMPLETO RECIBIDO:")
    print(json.dumps(data, indent=2))
    
    # 2. Extraer el campo 'texto' que definimos en la tool
    texto_completo = data.get('texto', '')
    print(f"\n📝 TEXTO DE LA COTIZACIÓN:\n{texto_completo}")
    
    # 3. Generar ID único para esta solicitud
    solicitud_id = f"COT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 4. Guardar en nuestra base de datos simulada
    solicitud = {
        "id": solicitud_id,
        "fecha": datetime.now().isoformat(),
        "texto_original": texto_completo,
        "procesado": False
    }
    solicitudes.append(solicitud)
    
    # 5. Aquí puedes agregar lógica para procesar el texto
    # Por ejemplo, extraer producto, cantidad, nombre, etc.
    print("\n🔍 PROCESANDO SOLICITUD...")
    
    # Ejemplo de extracción simple (mejorable con regex o IA)
    if "cotización" in texto_completo.lower():
        tipo = "cotización"
    elif "pedido" in texto_completo.lower():
        tipo = "pedido"
    else:
        tipo = "no especificado"
    
    print(f"   Tipo detectado: {tipo}")
    print(f"   ID generado: {solicitud_id}")
    
    # 6. Responder a ElevenLabs (esto es lo que el agente "escucha")
    respuesta = {
        "status": "success",
        "solicitud_id": solicitud_id,
        "mensaje": "Cotización recibida correctamente. Un asesor se comunicará pronto."
    }
    
    print("\n✅ RESPUESTA ENVIADA A ELEVENLABS:")
    print(json.dumps(respuesta, indent=2))
    print("="*70 + "\n")
    
    return jsonify(respuesta), 200

@app.route('/solicitudes', methods=['GET'])
def listar_solicitudes():
    """Endpoint para ver todas las solicitudes recibidas (útil para debugging)"""
    return jsonify({
        "total": len(solicitudes),
        "solicitudes": solicitudes
    })

@app.route('/solicitudes/<solicitud_id>', methods=['GET'])
def ver_solicitud(solicitud_id):
    """Ver una solicitud específica por ID"""
    for sol in solicitudes:
        if sol['id'] == solicitud_id:
            return jsonify(sol)
    return jsonify({"error": "Solicitud no encontrada"}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está vivo"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "mensaje": "Servidor de cotizaciones Classic Metals",
        "endpoints": {
            "POST /webhook/cotizacion": "Recibir cotizaciones desde ElevenLabs",
            "GET /solicitudes": "Listar todas las solicitudes",
            "GET /solicitudes/<id>": "Ver una solicitud específica",
            "GET /health": "Health check"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*70)
    print("🚀 SERVIDOR DE COTIZACIONES CLASSIC METALS INICIADO")
    print("="*70)
    print(f"\n📡 Escuchando en: http://localhost:{port}")
    print(f"   Endpoint principal: http://localhost:{port}/webhook/cotizacion")
    print("\n📝 Endpoints disponibles:")
    print(f"   POST /webhook/cotizacion  → Recibir cotizaciones")
    print(f"   GET  /solicitudes          → Listar todas")
    print(f"   GET  /health                → Health check")
    print("\n⚙️  Para probar localmente:")
    print("   python app.py")
    print("   ngrok http 5000")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=True)