"""Registro y consulta de cupones obtenidos en MongoDB."""
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from .excepciones import ClienteYaTieneCupon


class RepositorioCupones:
    def __init__(self, coleccion):
        self._c = coleccion

    def crear_indices(self):
        # Un cliente solo puede tener un cupon por promocion
        self._c.create_index(
            [("cliente_normalizado", ASCENDING), ("promocion_id", ASCENDING)],
            unique=True,
            name="un_cupon_por_cliente_y_promocion",
        )
        self._c.create_index("codigo", unique=True, name="codigo_unico")

    def existe(self, cliente_normalizado, promo_id):
        return self._c.count_documents(
            {"cliente_normalizado": cliente_normalizado, "promocion_id": promo_id},
            limit=1,
        ) > 0

    def guardar(self, cupon):
        try:
            self._c.insert_one(dict(cupon))
        except DuplicateKeyError as e:
            if "codigo" in str(e):
                raise  # choque de codigo: error tecnico, no del cliente
            raise ClienteYaTieneCupon() from e

    def resumen_por_departamento(self):
        """Devuelve {departamento: (total_cupones, clientes_distintos)}."""
        pipeline = [
            {"$group": {
                "_id": "$departamento",
                "total": {"$sum": 1},
                "clientes": {"$addToSet": "$cliente_normalizado"},
            }},
            {"$project": {
                "_id": 0,
                "departamento": "$_id",
                "total": 1,
                "clientes_distintos": {"$size": "$clientes"},
            }},
        ]
        return {
            fila["departamento"]: (fila["total"], fila["clientes_distintos"])
            for fila in self._c.aggregate(pipeline)
        }
