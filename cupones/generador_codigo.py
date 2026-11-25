"""Generador de codigos unicos de cupon, por ejemplo P001-0001."""


class GeneradorCodigo:
    def __init__(self, contador):
        # 'contador' es cualquier objeto con siguiente_numero(promo_id)
        self._contador = contador

    def generar(self, promo_id):
        numero = self._contador.siguiente_numero(promo_id)
        return f"{promo_id}-{numero:04d}"
