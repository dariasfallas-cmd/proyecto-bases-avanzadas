"""Conexiones a MongoDB y Redis usadas por el modulo de cupones.

Usa las mismas variables de entorno que app.py, asi que apunta a las mismas bases.
"""
import os

from pymongo import MongoClient
from redis import Redis

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

cliente_mongo = MongoClient(MONGO_URI)
db = cliente_mongo["tienda_promociones_db"]
coleccion_promociones = db["promociones"]
coleccion_cupones = db["cupones"]

# decode_responses=True hace que Redis devuelva str en lugar de bytes
cliente_redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
