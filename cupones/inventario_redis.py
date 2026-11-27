"""Acceso a Redis: cupones disponibles de las promociones activas.

Esquema de la Persona 2 (activacion):
  promo:{id}  -> Hash con el campo 'cupones_disponibles' (y los demas datos de la
                 promocion), con TTL = duracion de la promocion.

Esquema propio (generacion de codigos):
  contador_cupones:{id} -> entero, sin TTL. Esta fuera del patron 'promo:*' a proposito
                           para no aparecer como promocion activa.

Si la clave promo:{id} no existe, la promocion vencio (el TTL la elimino) o nunca se activo.
Si existe con cupones_disponibles = 0, esta agotada pero sigue vigente.
"""

VENCIDA = -2
AGOTADA = -1

CAMPO = "cupones_disponibles"

# Los scripts Lua se ejecutan de forma atomica en Redis:
# nadie puede intercalar otra operacion entre la lectura y el descuento.
_LUA_DESCONTAR = """
if redis.call('EXISTS', KEYS[1]) == 0 then return -2 end
local v = tonumber(redis.call('HGET', KEYS[1], ARGV[1]))
if not v then return -2 end
if v <= 0 then return -1 end
return redis.call('HINCRBY', KEYS[1], ARGV[1], -1)
"""

# Devuelve el cupon solo si la clave aun existe. Un HINCRBY directo sobre una clave
# ya vencida la crearia de nuevo sin TTL y la promocion quedaria activa para siempre.
_LUA_DEVOLVER = """
if redis.call('EXISTS', KEYS[1]) == 1 then
    return redis.call('HINCRBY', KEYS[1], ARGV[1], 1)
end
return -2
"""


class InventarioRedis:
    def __init__(self, cliente_redis):
        self._r = cliente_redis
        self._script_descontar = cliente_redis.register_script(_LUA_DESCONTAR)
        self._script_devolver = cliente_redis.register_script(_LUA_DEVOLVER)

    @staticmethod
    def _clave(promo_id):
        return f"promo:{promo_id}"

    def esta_activa(self, promo_id):
        return self._r.ttl(self._clave(promo_id)) != -2  # -2 = la clave no existe

    def descontar(self, promo_id):
        """Descuenta un cupon. Devuelve los que quedan, o VENCIDA / AGOTADA."""
        return int(self._script_descontar(keys=[self._clave(promo_id)], args=[CAMPO]))

    def devolver(self, promo_id):
        """Deshace un descuento (por ejemplo si fallo el guardado en MongoDB)."""
        self._script_devolver(keys=[self._clave(promo_id)], args=[CAMPO])

    def disponibles(self, promo_id):
        valor = self._r.hget(self._clave(promo_id), CAMPO)
        return int(valor) if valor is not None else None

    def segundos_restantes(self, promo_id):
        return max(int(self._r.ttl(self._clave(promo_id))), 0)

    def ids_activos(self):
        for clave in self._r.scan_iter(match="promo:*"):
            partes = clave.split(":")
            if len(partes) == 2:  # solo promo:{id}
                yield partes[1]

    def siguiente_numero(self, promo_id):
        return int(self._r.incr(f"contador_cupones:{promo_id}"))
