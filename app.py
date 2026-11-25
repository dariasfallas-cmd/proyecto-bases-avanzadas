from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import redis
import json
import os

app = Flask(__name__)

# Módulo de cupones (Persona 3): obtener cupón y consulta por departamento
from cupones.rutas import registrar_cupones
registrar_cupones(app)

# Configuración de la conexión a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["tienda_promociones_db"]
promociones_collection = db["promociones"]

# Configuración de la conexión a Redis (contenedor Docker en puerto 6379)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


@app.route('/')
def index():
    return "<h1>Bienvenido al Proyecto de Bases de Datos Avanzadas</h1><p><a href='/vista-carga'>1. Cargar JSON</a></p><p><a href='/activar-promocion'>2. Activar Promociones</a></p><p><a href='/promociones-activas'>3. Ver Promociones Activas</a></p><p><a href='/obtener-cupon'>4. Obtener Cupón</a></p><p><a href='/consulta-cupones'>5. Consultar Cupones</a></p>"


@app.route('/vista-carga')
def vista_carga():
    return render_template('carga.html')


@app.route('/cargar', methods=['POST'])
def cargar_datos():
    if 'archivo_json' not in request.files:
        return "Falta el campo del archivo en la solicitud", 400
    
    archivo = request.files['archivo_json']
    if archivo.filename == '':
        return "No se seleccionó ningún archivo", 400

    try:
        datos = json.load(archivo)
        promociones_collection.delete_many({})
        if isinstance(datos, list):
            promociones_collection.insert_many(datos)
        else:
            promociones_collection.insert_one(datos)
        return "¡Datos cargados exitosamente en MongoDB desde el archivo JSON! <br><br><a href='/activar-promocion'>Ir a Activar Promociones</a>"
    except Exception as e:
        return f"Error al procesar el archivo JSON: {str(e)}", 500


# ==============================================================================
# FUNCIONALIDAD 2: ACTIVAR UNA PROMOCIÓN EN REDIS CON TTL
# ==============================================================================
@app.route('/activar-promocion', methods=['GET', 'POST'])
def activar_promocion():
    catalogo = list(promociones_collection.find({}, {"_id": 0}))
    mensaje = None
    tipo_alerta = None

    if request.method == 'POST':
        promo_id = request.form.get('promo_id')
        cupones = request.form.get('cupones', type=int)
        duracion_minutos = request.form.get('duracion', type=int)

        if not promo_id or not cupones or cupones <= 0 or not duracion_minutos or duracion_minutos <= 0:
            mensaje = "Debe seleccionar una promoción e ingresar valores mayores a cero para cupones y minutos."
            tipo_alerta = "error"
        else:
            clave_redis = f"promo:{promo_id}"

            # No se puede activar una promoción que ya se encuentre activa
            if redis_client.exists(clave_redis):
                mensaje = f"La promoción {promo_id} ya se encuentra activa en este momento."
                tipo_alerta = "error"
            else:
                promo_db = promociones_collection.find_one({"id": promo_id}, {"_id": 0})
                if not promo_db:
                    mensaje = "La promoción seleccionada no existe en el catálogo de MongoDB."
                    tipo_alerta = "error"
                else:
                    # Guardar datos de la promoción en Redis como Hash
                    redis_client.hset(clave_redis, mapping={
                        "id": promo_db["id"],
                        "nombre": promo_db["nombre"],
                        "departamento": promo_db["departamento"],
                        "descuento": promo_db.get("descuento", ""),
                        "cupones_disponibles": cupones
                    })
                    # Asignar tiempo de vida (TTL) en segundos
                    redis_client.expire(clave_redis, duracion_minutos * 60)

                    mensaje = f"Promoción '{promo_db['nombre']}' activada con {cupones} cupones por {duracion_minutos} minuto(s)."
                    tipo_alerta = "exito"

    return render_template(
        'activar.html',
        promociones=catalogo,
        mensaje=mensaje,
        tipo_alerta=tipo_alerta
    )


# ==============================================================================
# FUNCIONALIDAD 3: CONSULTAR PROMOCIONES ACTIVAS DESDE REDIS
# ==============================================================================
@app.route('/promociones-activas')
def promociones_activas():
    claves = redis_client.keys("promo:*")
    lista_activas = []

    for clave in claves:
        ttl_segundos = redis_client.ttl(clave)
        # Solo mostrar llaves que aún tienen tiempo de vida vigente (> 0)
        if ttl_segundos and ttl_segundos > 0:
            datos = redis_client.hgetall(clave)
            minutos = ttl_segundos // 60
            segundos = ttl_segundos % 60
            lista_activas.append({
                "id": datos.get("id"),
                "nombre": datos.get("nombre"),
                "departamento": datos.get("departamento"),
                "descuento": datos.get("descuento"),
                "cupones_disponibles": datos.get("cupones_disponibles"),
                "minutos_restantes": minutos,
                "segundos_restantes": segundos
            })

    return render_template('activas.html', activas=lista_activas)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
