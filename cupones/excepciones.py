"""Errores de negocio. Cada uno lleva el mensaje que se le muestra al usuario."""


class CuponError(Exception):
    """Clase base de todos los errores de negocio de cupones."""


class DatosInvalidos(CuponError):
    pass


class PromocionNoActiva(CuponError):
    def __init__(self):
        super().__init__("La promoción ya venció o no está activa.")


class PromocionAgotada(CuponError):
    def __init__(self):
        super().__init__("La promoción no tiene cupones disponibles.")


class ClienteYaTieneCupon(CuponError):
    def __init__(self):
        super().__init__("Cliente ya tiene un cupón de esta promoción.")
