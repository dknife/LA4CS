"""lautils.py — 『쓸모 있는 선형대수』 시각화 도구

이 책의 그림은 모두 이 모듈로 그린다. 넘파이와 맷플롯립만 있으면 동작한다.

    from lautils import *

    fig, ax = new_axes()                    # 2차원 (정적)
    fig, ax = new_axes3d()                  # 3차원 (정적)
    fig, ax = new_axes3d(interactive=True)  # 3차원 (마우스로 돌려 보기)

    draw_vector(ax, v)                      # 어느 쪽이든 같은 함수를 쓴다
    draw_matrix(ax, A)
    draw_points(ax, P)

캔버스를 만들 때 interactive=True 를 주면 plotly 로 그리는 tuvis 백엔드가
쓰인다(별도 설치: pip install plotly). 그 뒤로는 함수 이름도 인자도 똑같다.
어떤 캔버스를 받았는지 그리기 함수가 알아서 판단해 넘겨주기 때문이다.

대화형 그림은 마우스로 회전·확대할 수 있어 외적·평행육면체·부분공간처럼
3차원이라야 보이는 것을 설명할 때 좋다. 다만 결과가 대화형 HTML이라
인쇄물에는 담을 수 없으므로, 이 책의 지면 도판은 모두 정적 그림이다.

모든 그리기 함수는 첫 인자로 캔버스(ax)를 받아 그 위에 그린다.
"""
import functools

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# ---------------------------------------------------------------- 백엔드

def _is_interactive(ax):
    """plotly 캔버스인가? (tuvis 로 만든 것)"""
    return type(ax).__module__.startswith("plotly")


def _tuvis():
    """대화형 백엔드를 필요할 때만 불러온다."""
    try:
        import tuvis
    except ImportError as e:
        raise ImportError(
            "대화형 그림에는 tuvis 와 plotly 가 필요하다.\n"
            "  pip install plotly\n"
            "정적 그림만 쓰려면 interactive=True 를 빼면 된다."
        ) from e
    return tuvis


def _backend(fn):
    """캔버스가 plotly 이면 tuvis 의 같은 이름 함수로 넘긴다.

    덕분에 독자는 lautils 하나만 import 하면 되고, 캔버스를 어떻게 만들었는지에
    따라 그리기 함수가 알아서 맞는 백엔드로 간다.
    """
    @functools.wraps(fn)
    def wrapper(ax, *args, **kw):
        if _is_interactive(ax):
            return getattr(_tuvis(), fn.__name__)(ax, *args, **kw)
        return fn(ax, *args, **kw)
    return wrapper


# 벡터를 여러 개 그릴 때 순서대로 사용할 색
PALETTE = ['crimson', 'royalblue', 'seagreen', 'darkorange',
           'purple', 'teal', 'saddlebrown', 'deeppink']

# 단위 정사각형의 네 꼭짓점 (넓이 시각화에 사용)
UNIT_SQUARE = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])

# 단위 정육면체의 여덟 꼭짓점 (부피 시각화에 사용)
UNIT_CUBE = np.array([[x, y, z] for x in (0., 1.)
                      for y in (0., 1.) for z in (0., 1.)])


# ---------------------------------------------------------------- 캔버스

def new_axes(xlim=(-5, 5), ylim=(-5, 5), figsize=(4.5, 4.5), grid=True,
             interactive=False):
    """비율이 1:1로 맞춰진 빈 2차원 좌표평면을 만들어 (fig, ax)를 돌려준다.

    interactive=True 이면 마우스로 조작할 수 있는 plotly 캔버스를 돌려준다.
    """
    if interactive:
        return _tuvis().new_axes(xlim=xlim, ylim=ylim)
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')          # 각도와 길이가 왜곡되지 않도록
    if grid:
        ax.grid(True, alpha=0.3, lw=0.5)
    ax.axhline(0, color='black', lw=0.8)
    ax.axvline(0, color='black', lw=0.8)
    return fig, ax


def new_axes3d(xlim=(-2, 2), ylim=(-2, 2), zlim=(-2, 2),
               figsize=(5, 5), axes_on=True, interactive=False):
    """빈 3차원 좌표공간을 만들어 (fig, ax)를 돌려준다.

    interactive=True 이면 마우스로 돌려 볼 수 있는 plotly 캔버스를 돌려준다.
    3차원은 각도를 바꿔 볼 수 있어야 이해가 빠르므로 특히 유용하다.
    """
    if interactive:
        return _tuvis().new_axes3d(xlim=xlim, ylim=ylim, zlim=zlim)
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_zlim(*zlim)
    ax.set_box_aspect((1, 1, 1))    # 세 축의 비율을 같게
    ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_zlabel('z')
    if axes_on:                     # 원점을 지나는 좌표축
        ax.plot(xlim, (0, 0), (0, 0), color='black', lw=0.8, alpha=0.5)
        ax.plot((0, 0), ylim, (0, 0), color='black', lw=0.8, alpha=0.5)
        ax.plot((0, 0), (0, 0), zlim, color='black', lw=0.8, alpha=0.5)
    return fig, ax


def _is3d(ax):
    return hasattr(ax, 'get_zlim')


# ---------------------------------------------------------------- 벡터

@_backend
def draw_vector(ax, v, origin=None, color='crimson', label=None,
                width=0.012, alpha=1.0, linestyle='-'):
    """원점(또는 지정한 시작점)에서 v 방향으로 화살표를 그린다. 2D/3D 공용."""
    v = np.asarray(v, dtype=float)
    dim = len(v)
    o = np.zeros(dim) if origin is None else np.asarray(origin, dtype=float)

    if dim == 2:
        ax.quiver(o[0], o[1], v[0], v[1],
                  angles='xy', scale_units='xy', scale=1,
                  color=color, width=width, alpha=alpha,
                  linestyle=linestyle, zorder=3)
    else:
        ax.quiver(o[0], o[1], o[2], v[0], v[1], v[2],
                  color=color, alpha=alpha, linestyle=linestyle,
                  arrow_length_ratio=0.12, lw=width * 120)

    if label is not None:
        mid = o + v * 0.55                      # 화살표 중간쯤에 이름표
        if dim == 2:
            ax.text(mid[0] + 0.12, mid[1] + 0.12, label,
                    color=color, fontsize=10)
        else:
            ax.text(mid[0], mid[1], mid[2], label, color=color, fontsize=10)
    return ax


@_backend
def draw_vectors(ax, vs, origin=None, labels=None, alpha=1.0):
    """여러 벡터를 PALETTE 순서대로 색을 바꿔 가며 그린다."""
    vs = np.asarray(vs, dtype=float)
    for i, v in enumerate(vs):
        lab = None if labels is None else labels[i]
        draw_vector(ax, v, origin=origin, color=PALETTE[i % len(PALETTE)],
                    label=lab, alpha=alpha)
    return ax


# ---------------------------------------------------------------- 점·도형

@_backend
def draw_points(ax, P, color='darkorange', size=40, label=None,
                labels=None, marker='o', s=None):
    """행마다 점 하나가 담긴 배열 P를 산점도로 찍는다. 2D/3D 공용."""
    P = np.atleast_2d(np.asarray(P, dtype=float))
    size = size if s is None else s             # s= 로도 쓸 수 있게
    if P.shape[1] == 2:
        ax.scatter(P[:, 0], P[:, 1], s=size, color=color, marker=marker,
                   label=label, zorder=4)
    else:
        ax.scatter(P[:, 0], P[:, 1], P[:, 2], s=size, color=color,
                   marker=marker, label=label)
    if labels is not None:                      # 점마다 이름표
        for p, t in zip(P, labels):
            if P.shape[1] == 2:
                ax.text(p[0], p[1], f' {t}', fontsize=9, color=color)
            else:
                ax.text(p[0], p[1], p[2], f' {t}', fontsize=9, color=color)
    return ax


@_backend
def draw_polygon(ax, P, color='goldenrod', alpha=0.35, edge=True):
    """꼭짓점 목록 P가 이루는 다각형을 색으로 채운다 (넓이·부피 표현용)."""
    P = np.asarray(P, dtype=float)
    if P.shape[1] == 2:
        ax.fill(P[:, 0], P[:, 1], color=color, alpha=alpha, zorder=1)
        if edge:
            loop = np.vstack([P, P[0]])         # 마지막 점을 처음과 이어 닫기
            ax.plot(loop[:, 0], loop[:, 1], color=color, lw=1.2, zorder=2)
    else:
        poly = Poly3DCollection([P], alpha=alpha, facecolor=color,
                                edgecolor=color if edge else 'none')
        ax.add_collection3d(poly)
    return ax


@_backend
def draw_line(ax, p1, p2, kind='segment', color='steelblue', alpha=0.9,
              scale=3.0, label=None, linestyle='-'):
    """두 점으로 정해지는 선을 그린다. kind='segment' | 'ray' | 'line'."""
    p1 = np.asarray(p1, dtype=float)
    p2 = np.asarray(p2, dtype=float)
    d = p2 - p1
    n = np.linalg.norm(d)
    if n < 1e-12:
        return ax
    u = d / n
    if kind == 'segment':
        a, b = p1, p2
    elif kind == 'ray':
        a, b = p1, p1 + d * scale
    else:                                       # 'line' — 양쪽으로 연장
        mid = (p1 + p2) / 2
        half = n * scale / 2
        a, b = mid - u * half, mid + u * half
    seg = np.vstack([a, b])
    if seg.shape[1] == 2:
        ax.plot(seg[:, 0], seg[:, 1], color=color, alpha=alpha,
                lw=1.6, ls=linestyle, zorder=2)
    else:
        ax.plot(seg[:, 0], seg[:, 1], seg[:, 2], color=color, alpha=alpha,
                lw=1.6, ls=linestyle)
    if label is not None:
        m = (p1 + p2) / 2
        (ax.text(m[0], m[1], f' {label}', color=color, fontsize=9)
         if len(m) == 2 else
         ax.text(m[0], m[1], m[2], f' {label}', color=color, fontsize=9))
    return ax


@_backend
def draw_circle(ax, center=(0, 0), radius=1.0, normal=None, color='steelblue',
                alpha=1.0, fill=False, n=100, linestyle='-'):
    """원을 그린다. 3차원에서는 normal에 수직인 평면 위의 원이 된다."""
    t = np.linspace(0, 2 * np.pi, n)
    center = np.asarray(center, dtype=float)
    if len(center) == 2:
        ring = center + np.column_stack([radius * np.cos(t), radius * np.sin(t)])
    else:
        nrm = np.asarray(normal if normal is not None else [0, 0, 1], float)
        nrm = nrm / np.linalg.norm(nrm)
        arb = np.array([1., 0., 0.]) if abs(nrm[0]) < 0.9 else np.array([0., 1., 0.])
        t1 = np.cross(nrm, arb); t1 /= np.linalg.norm(t1)   # 평면 위의 두 축
        t2 = np.cross(nrm, t1)
        ring = center + radius * (np.outer(np.cos(t), t1) + np.outer(np.sin(t), t2))
    if fill:
        draw_polygon(ax, ring, color=color, alpha=alpha * 0.3)
    if ring.shape[1] == 2:
        ax.plot(ring[:, 0], ring[:, 1], color=color, alpha=alpha,
                lw=1.4, ls=linestyle)
    else:
        ax.plot(ring[:, 0], ring[:, 1], ring[:, 2], color=color, alpha=alpha,
                lw=1.4, ls=linestyle)
    return ax


@_backend
def draw_plane(ax, p, normal, r=2.0, color='goldenrod', alpha=0.25,
               show_normal=True):
    """점 p를 지나고 normal에 수직인 평면을 반지름 r인 원판으로 그린다."""
    draw_circle(ax, center=p, radius=r, normal=normal, color=color,
                alpha=alpha, fill=True)
    if show_normal:
        n = np.asarray(normal, dtype=float)
        draw_vector(ax, n / np.linalg.norm(n), origin=p,
                    color='crimson', label='n')
    return ax


# ---------------------------------------------------------------- 격자·행렬

@_backend
def draw_grid(ax, A=None, n=4, color='steelblue', alpha=0.55, lw=0.7):
    """단위 격자를 그린다. 행렬 A를 주면 A로 변환된 격자를 그린다."""
    A = np.eye(2) if A is None else np.asarray(A, dtype=float)
    t = np.linspace(-n, n, 2 * n + 1)           # 격자선의 위치
    s = np.linspace(-n, n, 40)                  # 선 위의 표본점
    for k in t:
        horiz = np.vstack([s, np.full_like(s, k)])   # 가로선 (2, 40)
        vert = np.vstack([np.full_like(s, k), s])    # 세로선 (2, 40)
        for line in (horiz, vert):
            q = A @ line                             # 각 점에 A를 적용
            ax.plot(q[0], q[1], color=color, alpha=alpha, lw=lw, zorder=0)
    return ax


@_backend
def draw_matrix(ax, M, label=None, alpha=0.3, ghost=True):
    """행렬의 열벡터가 만드는 평행사변형(2x2) 또는 평행육면체(3x3)를 그린다.

    각 열벡터를 서로 다른 색의 화살표로, 그 벡터들이 이루는 도형을 옅은
    면으로 표시한다. 행렬식의 절댓값이 곧 이 도형의 넓이(부피)다.
    """
    M = np.asarray(M, dtype=float)
    cols = [M[:, j] for j in range(M.shape[1])]

    if M.shape == (2, 2):
        u, v = cols
        draw_polygon(ax, np.array([[0, 0], u, u + v, v]), alpha=alpha)
        draw_vector(ax, u, color='crimson')
        draw_vector(ax, v, color='seagreen')
        if ghost:                                   # 나머지 두 변
            draw_vector(ax, u, origin=v, color='gray', alpha=0.3, width=0.006)
            draw_vector(ax, v, origin=u, color='gray', alpha=0.3, width=0.006)
        corner = u + v
    elif M.shape == (3, 3):
        u, v, w = cols
        for vec, c in zip(cols, ['crimson', 'seagreen', 'royalblue']):
            draw_vector(ax, vec, color=c)
        for a, b in [(u, v), (u, w), (v, w),        # 평행육면체의 나머지 모서리
                     (u, v + w), (v, u + w), (w, u + v)]:
            draw_vector(ax, a, origin=b, color='gray', alpha=0.25, width=0.004)
        for f in [[np.zeros(3), u, u + v, v], [np.zeros(3), u, u + w, w],
                  [np.zeros(3), v, v + w, w], [w, u + w, u + v + w, v + w],
                  [v, u + v, u + v + w, v + w], [u, u + v, u + v + w, u + w]]:
            draw_polygon(ax, np.array(f), alpha=alpha * 0.5, edge=False)
        corner = u + v + w
    else:
        raise ValueError('draw_matrix는 2x2 또는 3x3 행렬만 지원한다')

    if label is not None:
        (ax.text(corner[0], corner[1], f' {label}', fontsize=10)
         if len(corner) == 2 else
         ax.text(corner[0], corner[1], corner[2], f' {label}', fontsize=10))
    return ax


def transform(A, P):
    """행마다 점 하나가 담긴 배열 P의 모든 점에 행렬 A를 적용한다."""
    A = np.asarray(A, dtype=float)
    P = np.asarray(P, dtype=float)
    return (A @ P.T).T


@_backend
def show_matrix(ax, A, fmt='{:.2f}', cmap='RdBu_r', title=None):
    """행렬을 색상 격자와 숫자로 함께 보여 준다."""
    A = np.asarray(A, dtype=float)
    lim = np.abs(A).max()
    lim = 1.0 if lim == 0 else lim
    ax.imshow(A, cmap=cmap, vmin=-lim, vmax=lim)
    if fmt:
        for i in range(A.shape[0]):
            for j in range(A.shape[1]):
                ax.text(j, i, fmt.format(A[i, j]),
                        ha='center', va='center', fontsize=9)
    ax.set_xticks(range(A.shape[1]))
    ax.set_yticks(range(A.shape[0]))
    ax.set_aspect('equal')
    if title:
        ax.set_title(title, fontsize=10)
    return ax
