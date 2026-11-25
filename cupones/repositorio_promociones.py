"""Lectura del catalogo de promociones en MongoDB."""


class RepositorioPromociones:
    def __init__(self, coleccion):
        self._c = coleccion

    def obtener(self, promo_id):
        return self._c.find_one({"id": promo_id}, {"_id": 0})

    def departamentos(self):
        return sorted(self._c.distinct("departamento"))
