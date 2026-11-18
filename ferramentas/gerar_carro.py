"""
Gera o lowrider do escritório em perspectiva isométrica, com pintura perolizada, cromados e rodas raiadas.
Saída: sprites/carro_corpo.png e sprites/carro_rodas.png.

Uso: python ferramentas/gerar_carro.py
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SAIDA = Path(__file__).resolve().parent.parent / "sprites"
X0, Y0, LARGURA, ALTURA = -104, -75, 292, 226
SS = 5
FINAL = 2
V_MIN, V_MAX = 0.35, 2.65
COMPRIMENTO = 5.85
RODAS = (1.3, 4.55)
RAIO_RODA = 13.5
TINTA = np.array([150, 28, 196], dtype=float)
TINTA_ESCURA = np.array([58, 10, 88], dtype=float)
POR_DO_SOL = np.array([255, 150, 96], dtype=float)
ROSA = np.array([255, 92, 190], dtype=float)
CROMO = np.array([226, 230, 240], dtype=float)


def proj(u, v, z):
    return ((((u - v) * 28) - X0) * SS, (((u + v) * 14 - z) - Y0) * SS)


def rgb(c):
    return tuple(int(max(0, min(255, x))) for x in c)


def poli(d, pontos, cor):
    d.polygon([proj(*p) for p in pontos], fill=rgb(cor) + (255,))


def linha(d, pontos, cor, largura):
    d.line([proj(*p) for p in pontos], fill=rgb(cor) + (255,), width=int(largura * SS), joint="curve")


def topo(u):
    """Perfil do capô e do porta-malas, do fundo até a frente do carro."""
    xs = [0.0, 0.14, 0.55, 1.8, 4.1, 5.25, 5.68, 5.85]
    zs = [29.0, 33.0, 35.2, 36.2, 37.2, 35.8, 33.2, 28.0]
    return np.interp(u, xs, zs)


def carroceria(d):
    us = np.linspace(0, COMPRIMENTO, 170)
    faixas = 14
    for i in range(len(us) - 1):
        for j in range(faixas):
            t0, t1 = j / faixas, (j + 1) / faixas
            v0, v1 = V_MIN + (V_MAX - V_MIN) * t0, V_MIN + (V_MAX - V_MIN) * t1
            curva = lambda t: -3.2 * (2 * t - 1) ** 2
            z00, z01 = topo(us[i]) + curva(t0), topo(us[i]) + curva(t1)
            z10, z11 = topo(us[i + 1]) + curva(t0), topo(us[i + 1]) + curva(t1)
            meio = (t0 + t1) / 2
            brilho = math.exp(-((meio - 0.68) / 0.13) ** 2)
            reflexo = math.exp(-((meio - 0.3) / 0.2) ** 2) * (0.5 + 0.5 * math.sin(us[i] * 2.3))
            cor = TINTA * (0.72 + 0.34 * meio) + (ROSA - TINTA) * 0.42 * reflexo + (np.array([255, 235, 250.0]) - TINTA) * 0.62 * brilho
            poli(d, [(us[i], v0, z00), (us[i + 1], v0, z10), (us[i + 1], v1, z11), (us[i], v1, z01)], cor)


def cabine(d):
    bv0, bv1 = V_MIN + 0.22, V_MAX - 0.22
    tv0, tv1 = V_MIN + 0.52, V_MAX - 0.52
    zb, zt = 37.4, 56.0
    ub0, ub1, ut0, ut1 = 1.95, 4.12, 2.48, 3.55
    n = 30
    for i in range(n):
        a, b = i / n, (i + 1) / n
        cor = np.array([18, 26, 52.0]) + (np.array([255, 126, 120.0]) - np.array([18, 26, 52.0])) * (0.55 * a ** 1.6)
        poli(d, [(ub1 + (ut1 - ub1) * a, bv0 + (tv0 - bv0) * a, zb + (zt - zb) * a), (ub1 + (ut1 - ub1) * a, bv1 + (tv1 - bv1) * a, zb + (zt - zb) * a),
                 (ub1 + (ut1 - ub1) * b, bv1 + (tv1 - bv1) * b, zb + (zt - zb) * b), (ub1 + (ut1 - ub1) * b, bv0 + (tv0 - bv0) * b, zb + (zt - zb) * b)], cor)
    for i in range(n):
        a, b = i / n, (i + 1) / n
        ua0, ua1 = ub0 + (ut0 - ub0) * a, ub1 + (ut1 - ub1) * a
        ubb0, ubb1 = ub0 + (ut0 - ub0) * b, ub1 + (ut1 - ub1) * b
        va, vb = bv1 + (tv1 - bv1) * a, bv1 + (tv1 - bv1) * b
        za, zc = zb + (zt - zb) * a, zb + (zt - zb) * b
        cor = np.array([14, 20, 44.0]) + (np.array([255, 150, 110.0]) - np.array([14, 20, 44.0])) * (0.1 + 0.42 * a)
        poli(d, [(ua0, va, za), (ua1, va, za), (ubb1, vb, zc), (ubb0, vb, zc)], cor)
    # Colunas e molduras cromadas
    cromo = CROMO * 0.92
    linha(d, [(ub0, bv1, zb), (ut0, tv1, zt)], TINTA * 0.8, 2.6)
    linha(d, [(ub1, bv1, zb), (ut1, tv1, zt)], cromo, 1.5)
    linha(d, [((ub0 + ub1) / 2, bv1, zb), ((ut0 + ut1) / 2, tv1, zt)], cromo, 1.3)
    linha(d, [(ub0, bv1, zb), (ub1, bv1, zb)], cromo, 1.2)
    linha(d, [(ub1, bv0, zb), (ub1, bv1, zb)], cromo, 1.2)
    # Teto com leve curvatura e reflexo do céu
    faixas = 16
    for j in range(faixas):
        t0, t1 = j / faixas, (j + 1) / faixas
        v0, v1 = tv0 + (tv1 - tv0) * t0, tv0 + (tv1 - tv0) * t1
        brilho = math.exp(-(((t0 + t1) / 2 - 0.6) / 0.17) ** 2)
        cor = TINTA * 0.9 + (np.array([255, 225, 245.0]) - TINTA * 0.9) * 0.6 * brilho
        poli(d, [(ut0, v0, zt), (ut1, v0, zt), (ut1, v1, zt), (ut0, v1, zt)], cor)


def lateral(d):
    us = np.linspace(0, COMPRIMENTO, 120)
    base = 13.0
    faixas = 26
    for j in range(faixas):
        a, b = j / faixas, (j + 1) / faixas
        meio = (a + b) / 2
        escuro = TINTA_ESCURA + (TINTA - TINTA_ESCURA) * min(1, meio * 1.7)
        faixa_sol = math.exp(-((meio - 0.56) / 0.09) ** 2)
        faixa_clara = math.exp(-((meio - 0.86) / 0.06) ** 2)
        for i in range(len(us) - 1):
            onda = 0.65 + 0.35 * math.sin(us[i] * 1.7 + 0.5)
            cor = escuro + (POR_DO_SOL - escuro) * 0.58 * faixa_sol * onda + (np.array([255, 225, 245.0]) - escuro) * 0.55 * faixa_clara
            z0 = lambda u: base + (topo(u) - 3.2 - base) * a
            z1 = lambda u: base + (topo(u) - 3.2 - base) * b
            poli(d, [(us[i], V_MAX, z0(us[i])), (us[i + 1], V_MAX, z0(us[i + 1])), (us[i + 1], V_MAX, z1(us[i + 1])), (us[i], V_MAX, z1(us[i]))], cor)
    # Caixas de roda
    for u0 in RODAS:
        pontos = [(u0 + (RAIO_RODA * 1.2 / 28) * math.cos(t), V_MAX, 13 + RAIO_RODA * 1.2 * math.sin(t)) for t in np.linspace(0, math.pi, 40)]
        poli(d, pontos, (10, 8, 14))
    # Portas, friso cromado e maçaneta
    for u in (2.05, 3.05, 4.05):
        linha(d, [(u, V_MAX, 15), (u, V_MAX, 33)], TINTA_ESCURA * 0.7, 0.7)
    linha(d, [(u, V_MAX, 26.5) for u in (0.05, 1.8, 3.5, 5.8)], CROMO, 1.5)
    linha(d, [(u, V_MAX, 14.4) for u in (2.0, 3.9)], CROMO, 1.3)
    linha(d, [(2.72, V_MAX, 30), (2.92, V_MAX, 30)], CROMO, 1.5)
    linha(d, [(3.72, V_MAX, 30), (3.92, V_MAX, 30)], CROMO, 1.5)
    # Filetes dourados no capô
    for desvio, sinal in ((0.72, 1), (2.28, -1)):
        curva = [(u, desvio + sinal * 0.16 * math.sin((u - 4.2) * 5), float(topo(u)) - 0.8) for u in np.linspace(4.25, 5.55, 22)]
        linha(d, curva, (245, 196, 64), 0.8)


def frente(d):
    u = COMPRIMENTO
    poli(d, [(u, V_MIN, 14), (u, V_MAX, 14), (u, V_MAX, 28), (u, V_MIN, 28)], TINTA * 0.62)
    poli(d, [(u, V_MIN + 0.12, 18), (u, V_MAX - 0.12, 18), (u, V_MAX - 0.12, 26), (u, V_MIN + 0.12, 26)], (18, 16, 26))
    for i in range(1, 15):
        v = V_MIN + 0.12 + i * (V_MAX - V_MIN - 0.24) / 15
        linha(d, [(u, v, 18.5), (u, v, 25.5)], CROMO * 0.9, 0.55)
    for z in (20.5, 23.5):
        linha(d, [(u, V_MIN + 0.14, z), (u, V_MAX - 0.14, z)], CROMO * 0.8, 0.5)
    for v0 in (0.62, 0.98, 2.02, 2.38):
        anel = [(u + 0.01, v0 + 0.15 * math.cos(t), 22 + 4.2 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 28)]
        poli(d, anel, CROMO)
        luz = [(u + 0.01, v0 + 0.11 * math.cos(t), 22 + 3.1 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 28)]
        poli(d, luz, (255, 244, 196))
    # Para-choques cromados
    for j in range(8):
        a, b = j / 8, (j + 1) / 8
        cor = CROMO * (0.62 + 0.42 * math.sin(a * math.pi))
        poli(d, [(u + 0.16, V_MIN - 0.08, 15 + 6 * a), (u + 0.16, V_MAX + 0.08, 15 + 6 * a), (u + 0.16, V_MAX + 0.08, 15 + 6 * b), (u + 0.16, V_MIN - 0.08, 15 + 6 * b)], cor)
        poli(d, [(u - 0.28, V_MAX + 0.08, 15 + 6 * a), (u + 0.16, V_MAX + 0.08, 15 + 6 * a), (u + 0.16, V_MAX + 0.08, 15 + 6 * b), (u - 0.28, V_MAX + 0.08, 15 + 6 * b)], cor)
        poli(d, [(-0.14, V_MAX + 0.08, 15 + 6 * a), (0.34, V_MAX + 0.08, 15 + 6 * a), (0.34, V_MAX + 0.08, 15 + 6 * b), (-0.14, V_MAX + 0.08, 15 + 6 * b)], cor)
    poli(d, [(-0.02, V_MAX, 27), (0.1, V_MAX, 27), (0.1, V_MAX, 33), (-0.02, V_MAX, 33)], (225, 30, 44))
    # Retrovisor
    poli(d, [(4.0, V_MAX, 38), (4.16, V_MAX + 0.18, 38), (4.16, V_MAX + 0.18, 42), (4.0, V_MAX, 42)], CROMO)


def rodas(d):
    v = V_MAX + 0.03
    for u0 in RODAS:
        def circulo(r, dv=0.0, n=56):
            return [(u0 + (r / 28) * math.cos(t), v + dv, 13 + r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n)]
        poli(d, circulo(RAIO_RODA, -0.2), (8, 8, 11))
        poli(d, circulo(RAIO_RODA), (20, 20, 25))
        poli(d, circulo(RAIO_RODA * 0.82), (244, 241, 230))
        poli(d, circulo(RAIO_RODA * 0.64), (70, 62, 40))
        for i in range(30):
            t = i / 30 * 2 * math.pi
            t2 = t + 0.5
            linha(d, [(u0 + 0.05 * math.cos(t), v, 13 + 1.5 * math.sin(t)),
                      (u0 + (RAIO_RODA * 0.62 / 28) * math.cos(t2), v, 13 + RAIO_RODA * 0.62 * math.sin(t2))], (250, 214, 96) if i % 2 else (232, 234, 242), 0.32)
        poli(d, circulo(RAIO_RODA * 0.2), (245, 200, 66))
        poli(d, circulo(RAIO_RODA * 0.09), (255, 244, 196))


def salvar(desenhar, nome):
    img = Image.new("RGBA", (LARGURA * SS, ALTURA * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for etapa in desenhar:
        etapa(d)
    img.resize((LARGURA * FINAL, ALTURA * FINAL), Image.LANCZOS).save(SAIDA / nome)


if __name__ == "__main__":
    salvar((carroceria, cabine, lateral, frente), "carro_corpo.png")
    salvar((rodas,), "carro_rodas.png")
    print("carro gerado")
