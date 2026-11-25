"""Rutas web de cupones. Aqui se arman las piezas (composition root)."""
from flask import Blueprint, render_template, request
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from .conexiones import cliente_redis, coleccion_cupones, coleccion_promociones
from .excepciones import CuponError
from .generador_codigo import GeneradorCodigo
from .inventario_redis import InventarioRedis
from .repositorio_cupones import RepositorioCupones
from .repositorio_promociones import RepositorioPromociones
from .servicio import ServicioCupones

bp = Blueprint("cupones", __name__)

_inventario = InventarioRedis(cliente_redis)
_repo_cupones = RepositorioCupones(coleccion_cupones)
_servicio = ServicioCupones(
    RepositorioPromociones(coleccion_promociones),
    _repo_cupones,
    _inventario,
    GeneradorCodigo(_inventario),
)

_ERROR_CONEXION = "No se pudo conectar con la base de datos. Verifique que MongoDB y Redis estén en ejecución."


@bp.route("/obtener-cupon", methods=["GET", "POST"])
def obtener_cupon():
    cliente = ""
    cupon = restantes = error = None

    if request.method == "POST":
        cliente = request.form.get("cliente", "")
        try:
            cupon, restantes = _servicio.obtener_cupon(
                cliente, request.form.get("promocion_id", "")
            )
        except CuponError as e:
            error = str(e)
        except (PyMongoError, RedisError):
            error = _ERROR_CONEXION

    try:
        promociones = _servicio.promociones_activas()
    except (PyMongoError, RedisError):
        promociones, error = [], error or _ERROR_CONEXION

    return render_template(
        "cupones/obtener.html",
        cliente=cliente, promociones=promociones,
        cupon=cupon, restantes=restantes, error=error,
    )


@bp.route("/consulta-cupones")
def consulta_cupones():
    try:
        filas, error = _servicio.consulta_por_departamento(), None
    except (PyMongoError, RedisError):
        filas, error = [], _ERROR_CONEXION
    return render_template("cupones/consulta.html", filas=filas, error=error)


def registrar_cupones(app):
    """Se llama una vez desde app.py."""
    _repo_cupones.crear_indices()
    app.register_blueprint(bp)
