from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import json
import os

app = Flask(__name__)

# Configuración de la conexión a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["tienda_promociones_db"]
promociones_collection = db["promociones"]

@app.route('/')
def index():
    return "<h1>Bienvenido al Proyecto de Bases de Datos Avanzadas</h1><p><a href='/vista-carga'>Ir a Gestion de Promociones</a></p>"

@app.route('/vista-carga')
def vista_carga():
    #  interfaz donde se subirá el JSON
    return render_template('carga.html')

@app.route('/cargar', methods=['POST'])
def cargar_datos():
    # Carga inicial de datos desde el JSON
    if 'archivo_json' not in request.files:
        return "Falta el campo del archivo en la solicitud", 400
    
    archivo = request.files['archivo_json']
    
    if archivo.filename == '':
        return "No se seleccionó ningún archivo", 400

    try:
        # Leer el contenido del archivo JSON
        datos = json.load(archivo)
        
        # Limpiar la colección existente antes de la nueva carga inicial
        promociones_collection.delete_many({})
        
        # Insertar los datos en MongoDB 
        if isinstance(datos, list):
            promociones_collection.insert_many(datos)
        else:
            promociones_collection.insert_one(datos)
            
        return "¡Datos cargados exitosamente en MongoDB desde el archivo JSON!"
    except Exception as e:
        return f"Error al procesar el archivo JSON: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
