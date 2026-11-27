"""Logica de negocio de cupones.

Esta clase no sabe nada de Flask, MongoDB ni Redis: recibe sus dependencias por el
constructor (inversion de dependencias) y solo orquesta los pasos.
"""
from datetime import datetime

from .excepciones import (
    ClienteYaTieneCupon,
    DatosInvalidos,
    PromocionAgotada,
    PromocionNoActiva,
)
from .inventario_redis import AGOTADA, VENCIDA


class ServicioCupones:
    def __init__(self, repo_promociones, repo_cupones, inventario, generador,
                 reloj=datetime.now):
        self._promos = repo_promociones
        self._cupones = repo_cupones
        self._inventario = inventario
        self._generador = generador
        self._reloj = reloj

    def promociones_activas(self):
        """Promociones vigentes en Redis, con su nombre y departamento de MongoDB."""
        activas = []
        for promo_id in self._inventario.ids_activos():
            promo = self._promos.obtener(promo_id)
            disponibles = self._inventario.disponibles(promo_id)
            if promo is None or disponibles is None:  # vencio mientras la leiamos
                continue
            activas.append({
                "id": promo_id,
                "nombre": promo["nombre"],
                "departamento": promo["departamento"],
                "disponibles": disponibles,
                "segundos_restantes": self._inventario.segundos_restantes(promo_id),
            })
        return sorted(activas, key=lambda p: (p["departamento"], p["nombre"]))

    def obtener_cupon(self, cliente, promo_id):
        """Entrega un cupon. Devuelve (cupon, cupones_restantes) o lanza CuponError."""
        nombre = " ".join((cliente or "").split())
        if not nombre:
            raise DatosInvalidos("Debe indicar el nombre del cliente.")
        if not promo_id:
            raise DatosInvalidos("Debe seleccionar una promoción.")

        promo = self._promos.obtener(promo_id)
        if promo is None or not self._inventario.esta_activa(promo_id):
            raise PromocionNoActiva()

        cliente_normalizado = nombre.casefold()
        if self._cupones.existe(cliente_normalizado, promo_id):
            raise ClienteYaTieneCupon()

        restantes = self._inventario.descontar(promo_id)
        if restantes == VENCIDA:
            raise PromocionNoActiva()
        if restantes == AGOTADA:
            raise PromocionAgotada()

        try:
            cupon = {
                "codigo": self._generador.generar(promo_id),
                "cliente": nombre,
                "cliente_normalizado": cliente_normalizado,
                "promocion_id": promo_id,
                "promocion": promo["nombre"],
                "departamento": promo["departamento"],
                "fecha_obtencion": self._reloj(),
            }
            self._cupones.guardar(cupon)
        except Exception:
            # No quedo registrado en MongoDB: se le devuelve el cupon a Redis
            self._inventario.devolver(promo_id)
            raise
        return cupon, restantes

    def consulta_por_departamento(self):
        """Una fila por departamento del catalogo, incluso los que tienen 0 cupones."""
        resumen = self._cupones.resumen_por_departamento()
        departamentos = set(self._promos.departamentos()) | set(resumen)
        return [
            {
                "departamento": d,
                "total_cupones": resumen.get(d, (0, 0))[0],
                "clientes_distintos": resumen.get(d, (0, 0))[1],
            }
            for d in sorted(departamentos)
        ]
