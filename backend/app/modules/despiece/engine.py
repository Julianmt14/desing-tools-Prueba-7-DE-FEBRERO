from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class TipoEstructura(Enum):
    """Tipos de capacidad de disipacion de energia segun NSR-10."""

    DES = "Disipacion Especial de Energia"
    DMO = "Disipacion Moderada de Energia"
    DMI = "Disipacion Minima de Energia"


class TipoGancho(Enum):
    """Tipos de ganchos para barras de refuerzo."""

    GRADO_90 = 90
    GRADO_135 = 135
    GRADO_180 = 180


class TipoBarra(Enum):
    """Tipos de barras de refuerzo."""

    SUPERIOR = "superior"
    INFERIOR = "inferior"


@dataclass
class Apoyo:
    """Representa un apoyo (columna o muro)."""

    eje: str
    distancia_eje: float
    ancho_apoyo: float
    es_voladizo_inicio: bool = False
    es_voladizo_final: bool = False


@dataclass
class SeccionViga:
    """Representa una seccion de la viga."""

    inicio: float
    fin: float
    ancho: float
    alto: float
    recubrimiento: float = 0.04


@dataclass
class BarraRefuerzo:
    """Representa una barra individual de refuerzo."""

    id: int
    tipo: TipoBarra
    diametro: float
    longitud_total: float
    posiciones_traslapo: List[Tuple[float, float]]
    tiene_gancho_inicio: bool
    tiene_gancho_final: bool
    tipo_gancho_inicio: Optional[TipoGancho]
    tipo_gancho_final: Optional[TipoGancho]
    angulo_doblado: Optional[float] = None


@dataclass
class Estribo:
    """Representa la configuracion de estribos."""

    diametro: float
    separacion_zona_conf: float
    separacion_zona_centro: float
    longitud_zona_conf: float
    tipo_gancho: TipoGancho = TipoGancho.GRADO_135


class ProyectoVigaNSR10:
    """Calculadora principal para vigas segun NSR-10."""

    FACTOR_TRASLAPO = {6: 1.3, 9: 1.4, 12: 1.5}
    LONGITUD_MIN_TRASLAPO = 30
    DISTANCIA_MIN_TRASLAPO = 1.5
    LONGITUD_DESARROLLO = {
        TipoEstructura.DES: 50,
        TipoEstructura.DMO: 40,
        TipoEstructura.DMI: 30,
    }

    def __init__(self, identificacion: str, nivel: str, cantidad: int = 1):
        self.identificacion = identificacion
        self.nivel = nivel
        self.cantidad = cantidad
        self.apoyos: List[Apoyo] = []
        self.secciones: List[SeccionViga] = []
        self.barras_superiores: List[BarraRefuerzo] = []
        self.barras_inferiores: List[BarraRefuerzo] = []
        self.estribos: Optional[Estribo] = None

    def agregar_apoyo(self, apoyo: Apoyo) -> None:
        self.apoyos.append(apoyo)
        self.apoyos.sort(key=lambda x: x.distancia_eje)

    def agregar_seccion(self, seccion: SeccionViga) -> None:
        self.secciones.append(seccion)
        self.secciones.sort(key=lambda x: x.inicio)

    def calcular_longitud_total(self) -> float:
        if not self.apoyos:
            return 0.0
        return max(ap.distancia_eje + ap.ancho_apoyo / 2 for ap in self.apoyos)

    def calcular_longitud_libre(self, apoyo1: Apoyo, apoyo2: Apoyo) -> float:
        return apoyo2.distancia_eje - apoyo1.distancia_eje - apoyo1.ancho_apoyo / 2 - apoyo2.ancho_apoyo / 2

    def determinar_seccion_en_punto(self, distancia: float) -> SeccionViga:
        for seccion in self.secciones:
            if seccion.inicio <= distancia <= seccion.fin:
                return seccion
        return self.secciones[0]

    def calcular_longitud_traslapo(
        self,
        diametro: float,
        tipo_estructura: TipoEstructura,
        longitud_barra: float,
    ) -> float:
        long_min = self.LONGITUD_MIN_TRASLAPO * diametro / 1000
        factor = self.FACTOR_TRASLAPO.get(longitud_barra, 1.3)
        long_desarrollo = self.LONGITUD_DESARROLLO[tipo_estructura] * diametro / 1000
        return max(long_min, long_desarrollo * factor, 0.3)

    def calcular_ubicacion_traslapos(
        self,
        longitud_total: float,
        longitud_barra: float,
        diametro: float,
        tipo_estructura: TipoEstructura,
    ) -> List[Tuple[float, float]]:
        if longitud_total <= longitud_barra:
            return []

        long_traslapo = self.calcular_longitud_traslapo(diametro, tipo_estructura, longitud_barra)
        num_traslapos = math.ceil(longitud_total / longitud_barra) - 1

        traslapos = []
        longitud_restante = longitud_total

        for _ in range(num_traslapos):
            if not traslapos:
                inicio = longitud_barra - long_traslapo
            else:
                inicio = traslapos[-1][1] + self.DISTANCIA_MIN_TRASLAPO

            fin = inicio + long_traslapo

            if fin > longitud_restante:
                ajuste = fin - longitud_restante
                inicio -= ajuste
                fin -= ajuste

            traslapos.append((inicio, fin))
            longitud_restante -= longitud_barra - long_traslapo

        return traslapos

    def disenar_barras(
        self,
        tipo_barra: TipoBarra,
        cantidad: int,
        diametro: float,
        longitud_max_barra: float,
        tipo_estructura: TipoEstructura,
        usar_ganchos: bool = True,
        tipo_gancho: TipoGancho = TipoGancho.GRADO_90,
    ) -> List[BarraRefuerzo]:
        longitud_total = self.calcular_longitud_total()
        barras: List[BarraRefuerzo] = []

        for idx in range(cantidad):
            traslapos = self.calcular_ubicacion_traslapos(
                longitud_total, longitud_max_barra, diametro, tipo_estructura
            )

            necesita_ganchos = usar_ganchos and tipo_barra == TipoBarra.INFERIOR

            barra = BarraRefuerzo(
                id=idx + 1,
                tipo=tipo_barra,
                diametro=diametro,
                longitud_total=longitud_total,
                posiciones_traslapo=traslapos,
                tiene_gancho_inicio=necesita_ganchos,
                tiene_gancho_final=necesita_ganchos,
                tipo_gancho_inicio=tipo_gancho if necesita_ganchos else None,
                tipo_gancho_final=tipo_gancho if necesita_ganchos else None,
            )
            barras.append(barra)

        return barras

    def disenar_estribos(
        self,
        diametro: float,
        resistencia_concreto: float,
        tipo_estructura: TipoEstructura,
    ) -> Estribo:
        seccion = self.secciones[0]
        if tipo_estructura == TipoEstructura.DES:
            sep_zona_conf = min(0.25 * seccion.alto, 8 * diametro / 1000, 0.15)
            long_zona_conf = max(1.5 * seccion.alto, 0.6)
            sep_zona_centro = min(0.5 * seccion.alto, 24 * diametro / 1000, 0.30)
        elif tipo_estructura == TipoEstructura.DMO:
            sep_zona_conf = min(0.25 * seccion.alto, 8 * diametro / 1000, 0.20)
            long_zona_conf = max(1.0 * seccion.alto, 0.45)
            sep_zona_centro = min(0.5 * seccion.alto, 24 * diametro / 1000, 0.30)
        else:
            sep_zona_conf = min(0.25 * seccion.alto, 8 * diametro / 1000, 0.25)
            long_zona_conf = max(0.5 * seccion.alto, 0.30)
            sep_zona_centro = min(0.5 * seccion.alto, 24 * diametro / 1000, 0.30)

        self.estribos = Estribo(
            diametro=diametro,
            separacion_zona_conf=sep_zona_conf,
            separacion_zona_centro=sep_zona_centro,
            longitud_zona_conf=long_zona_conf,
        )

        return self.estribos

    def generar_corte_barras(self) -> Dict:
        corte: Dict[str, object] = {
            "identificacion": self.identificacion,
            "nivel": self.nivel,
            "cantidad": self.cantidad,
            "longitud_total": self.calcular_longitud_total(),
            "barras_superiores": [],
            "barras_inferiores": [],
            "estribos": None,
            "resumen": {},
        }

        for barra in self.barras_superiores:
            info = {
                "id": barra.id,
                "diametro": f"{barra.diametro} mm",
                "longitud_total": f"{barra.longitud_total:.2f} m",
                "num_traslapos": len(barra.posiciones_traslapo),
                "traslapos": [(f"{inicio:.2f}m", f"{fin:.2f}m") for inicio, fin in barra.posiciones_traslapo],
                "gancho_inicio": barra.tipo_gancho_inicio.value if barra.tipo_gancho_inicio else "No",
                "gancho_final": barra.tipo_gancho_final.value if barra.tipo_gancho_final else "No",
            }
            corte["barras_superiores"].append(info)

        for barra in self.barras_inferiores:
            info = {
                "id": barra.id,
                "diametro": f"{barra.diametro} mm",
                "longitud_total": f"{barra.longitud_total:.2f} m",
                "num_traslapos": len(barra.posiciones_traslapo),
                "traslapos": [(f"{inicio:.2f}m", f"{fin:.2f}m") for inicio, fin in barra.posiciones_traslapo],
                "gancho_inicio": barra.tipo_gancho_inicio.value if barra.tipo_gancho_inicio else "No",
                "gancho_final": barra.tipo_gancho_final.value if barra.tipo_gancho_final else "No",
            }
            corte["barras_inferiores"].append(info)

        if self.estribos:
            corte["estribos"] = {
                "diametro": f"{self.estribos.diametro} mm",
                "separacion_zona_conf": f"{self.estribos.separacion_zona_conf * 100:.1f} cm",
                "separacion_zona_centro": f"{self.estribos.separacion_zona_centro * 100:.1f} cm",
                "longitud_zona_conf": f"{self.estribos.longitud_zona_conf:.2f} m",
                "tipo_gancho": self.estribos.tipo_gancho.value,
            }

        corte["resumen"] = {
            "total_barras_superiores": len(self.barras_superiores),
            "total_barras_inferiores": len(self.barras_inferiores),
            "diametros_utilizados": list(
                set([barra.diametro for barra in self.barras_superiores + self.barras_inferiores])
            ),
            "longitud_total_acero": sum(
                barra.longitud_total for barra in self.barras_superiores + self.barras_inferiores
            ),
        }

        return corte

    def imprimir_resumen(self) -> None:
        corte = self.generar_corte_barras()
        print("=" * 60)
        print(f"PROYECTO DE VIGA - {self.identificacion}")
        print(f"Nivel: {self.nivel} | Cantidad: {self.cantidad}")
        print("=" * 60)
        print("\nGEOMETRIA:")
        print(f"Longitud total: {corte['longitud_total']:.2f} m")
        print(f"Numero de apoyos: {len(self.apoyos)}")
        print("\nBARRAS DE REFUERZO:")
        print(f"Barras superiores: {corte['resumen']['total_barras_superiores']}")
        print(f"Barras inferiores: {corte['resumen']['total_barras_inferiores']}")
        if corte.get("estribos"):
            print("\nESTRIBOS:")
            print(f"Diametro: {corte['estribos']['diametro']}")
            print(
                f"Separacion zona confinamiento: {corte['estribos']['separacion_zona_conf']}"
            )
            print(f"Separacion zona central: {corte['estribos']['separacion_zona_centro']}")
            print(f"Longitud zona confinamiento: {corte['estribos']['longitud_zona_conf']}")


def ejemplo_viga_con_multiapoyos() -> ProyectoVigaNSR10:
    proyecto = ProyectoVigaNSR10(identificacion="VIGA NIVEL ENTREPISO 1", nivel="ENTREPISO 1", cantidad=2)

    apoyos = [
        Apoyo(eje="A", distancia_eje=0.0, ancho_apoyo=0.25),
        Apoyo(eje="B", distancia_eje=5.0, ancho_apoyo=0.30),
        Apoyo(eje="C", distancia_eje=8.5, ancho_apoyo=0.25),
        Apoyo(eje="D", distancia_eje=12.0, ancho_apoyo=0.35, es_voladizo_final=True),
    ]
    for apoyo in apoyos:
        proyecto.agregar_apoyo(apoyo)

    secciones = [
        SeccionViga(inicio=0.0, fin=5.0, ancho=0.25, alto=0.40),
        SeccionViga(inicio=5.0, fin=12.0, ancho=0.25, alto=0.35),
    ]
    for seccion in secciones:
        proyecto.agregar_seccion(seccion)

    proyecto.disenar_estribos(diametro=8, resistencia_concreto=21, tipo_estructura=TipoEstructura.DES)

    proyecto.barras_superiores = proyecto.disenar_barras(
        tipo_barra=TipoBarra.SUPERIOR,
        cantidad=3,
        diametro=16,
        longitud_max_barra=12,
        tipo_estructura=TipoEstructura.DES,
        usar_ganchos=False,
    )

    proyecto.barras_inferiores = proyecto.disenar_barras(
        tipo_barra=TipoBarra.INFERIOR,
        cantidad=4,
        diametro=20,
        longitud_max_barra=12,
        tipo_estructura=TipoEstructura.DES,
        usar_ganchos=True,
        tipo_gancho=TipoGancho.GRADO_90,
    )

    return proyecto


def main() -> None:
    print("PROYECTO DE BARRAS DE REFUERZO PARA VIGAS - NSR-10 COLOMBIA")
    print("=" * 60)
    proyecto = ejemplo_viga_con_multiapoyos()
    proyecto.imprimir_resumen()


if __name__ == "__main__":
    main()
