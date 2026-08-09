"""tuvis.py — 『쓸모 있는 선형대수』 대화형 시각화 도구 (plotly 백엔드)

lautils.py와 **함수 이름과 인자 규약이 같다.** 캔버스를 만드는 첫 줄만 바꾸면
같은 코드가 정적 그림(matplotlib)과 대화형 그림(plotly) 양쪽에서 동작한다.

    from lautils import *      →  fig, ax = new_axes3d()   # 정적 (지면·저장용)
    from tuvis import *        →  fig, ax = new_axes3d()   # 대화형 (수업·코랩용)
    ...
    draw_matrix(ax, M); draw_vector(ax, v); draw_points(ax, P)

plotly는 마우스로 회전·확대할 수 있어 3차원 개념(외적, 평면, 평행육면체,
부분공간, 3차원 회전)을 설명할 때 특히 좋다. 다만 결과가 대화형 HTML이라
인쇄물에는 담을 수 없으므로, 이 책의 지면 도판은 모두 lautils.py로 그렸다.

설치:  pip install plotly

이 모듈은 원래 수업용으로 만든 tuvis의 API(figure2d, draw_vec3d, draw_mat22,
draw_space_mat22 ...)를 그대로 유지하면서, lautils와 공통인 이름을 덧붙인
것이다. 기존 수업 노트북은 수정 없이 그대로 동작한다.
"""
import numpy as np

try:
    import plotly.graph_objects as go
except ImportError as _e:                       # 친절한 안내
    raise ImportError(
        "tuvis는 plotly가 필요하다.  pip install plotly\n"
        "정적 그림만 필요하면 lautils를 쓰면 된다 (numpy + matplotlib)."
    ) from _e

# lautils와 공유하는 상수
PALETTE = ['crimson', 'royalblue', 'seagreen', 'darkorange',
           'purple', 'teal', 'saddlebrown', 'deeppink']
UNIT_SQUARE = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
UNIT_CUBE = np.array([[x, y, z] for x in (0., 1.)
                      for y in (0., 1.) for z in (0., 1.)])


# ================================================================ 캔버스

def figure2d(x=(-5, 5), y=(-5, 5), title='', width=600, height=600,
             bg_color='rgba(248, 250, 255, 0.3)'):
    """z=0 평면을 위에서 내려다보는 2차원 캔버스를 만든다."""
    fig = go.Figure()

    cx = [x[0], x[1], x[1], x[0]]
    cy = [y[0], y[0], y[1], y[1]]
    fig.add_trace(go.Mesh3d(x=cx, y=cy, z=[0, 0, 0, 0], i=[0, 0], j=[1, 2],
                            k=[2, 3], color=bg_color, opacity=1.0,
                            showlegend=False, hoverinfo='skip'))
    for a, b in [((x[0], x[1]), (0, 0)), ((0, 0), (y[0], y[1]))]:
        fig.add_trace(go.Scatter3d(x=list(a), y=list(b), z=[0, 0], mode='lines',
                                   line=dict(color='gray', width=3), opacity=0.4,
                                   showlegend=False, hoverinfo='skip'))
    for gx in range(int(np.ceil(x[0])), int(np.floor(x[1])) + 1):
        fig.add_trace(go.Scatter3d(x=[gx, gx], y=list(y), z=[0, 0], mode='lines',
                                   line=dict(color='lightgray', width=1), opacity=0.6,
                                   showlegend=False, hoverinfo='skip'))
    for gy in range(int(np.ceil(y[0])), int(np.floor(y[1])) + 1):
        fig.add_trace(go.Scatter3d(x=list(x), y=[gy, gy], z=[0, 0], mode='lines',
                                   line=dict(color='lightgray', width=1), opacity=0.6,
                                   showlegend=False, hoverinfo='skip'))

    zspan = max(x[1] - x[0], y[1] - y[0]) * 0.01
    fig.update_layout(
        title=title, width=width, height=height,
        scene=dict(
            xaxis=dict(range=list(x), title='x'),
            yaxis=dict(range=list(y), title='y'),
            zaxis=dict(range=[-zspan, zspan], visible=False),
            aspectmode='manual',
            aspectratio=dict(x=1, y=(y[1] - y[0]) / (x[1] - x[0]), z=0.001),
            camera=dict(eye=dict(x=0, y=0, z=2.0), center=dict(x=0, y=0, z=0),
                        up=dict(x=0, y=1, z=0),
                        projection=dict(type='orthographic')),
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def figure3d(x=(-1, 1), y=(-1, 1), z=(-1, 1), title='', width=600, height=600):
    """세 축의 비율이 같은 3차원 캔버스를 만든다."""
    fig = go.Figure()
    fig.update_layout(
        title=title, width=width, height=height,
        scene=dict(xaxis=dict(range=list(x), title='x'),
                   yaxis=dict(range=list(y), title='y'),
                   zaxis=dict(range=list(z), title='z'),
                   aspectmode='cube'),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def new_axes(xlim=(-5, 5), ylim=(-5, 5), figsize=None, grid=True, **kw):
    """lautils와 같은 이름·같은 반환 형태(fig, ax)의 2차원 캔버스."""
    fig = figure2d(x=xlim, y=ylim, **kw)
    return fig, fig                 # plotly에서는 fig가 곧 그리기 대상


def new_axes3d(xlim=(-2, 2), ylim=(-2, 2), zlim=(-2, 2), figsize=None, **kw):
    """lautils와 같은 이름·같은 반환 형태(fig, ax)의 3차원 캔버스."""
    fig = figure3d(x=xlim, y=ylim, z=zlim, **kw)
    return fig, fig


def setCam(fig, eye, target=(0, 0, 0), up=(0, 0, 1)):
    """카메라의 위치(eye), 바라보는 지점(target), 위 방향(up)을 지정한다."""
    fig.update_layout(scene_camera=dict(
        eye=dict(x=eye[0], y=eye[1], z=eye[2]),
        center=dict(x=target[0], y=target[1], z=target[2]),
        up=dict(x=up[0], y=up[1], z=up[2])))


# ================================================================ 내부 유틸

def _dash(style):
    """'-', '--', ':' 또는 'solid', 'dashed', 'dotted'를 plotly 표기로."""
    return {'-': 'solid', '--': 'dash', ':': 'dot', '-.': 'dashdot',
            'solid': 'solid', 'dashed': 'dash', 'dotted': 'dot'}.get(style, 'solid')


def _to3(v):
    """2차원 벡터를 z=0을 붙여 3차원으로 만든다."""
    v = np.asarray(v, dtype=float)
    return np.array([v[0], v[1], 0.0]) if v.shape == (2,) else v


def _cone(tip, base, radius=0.06, n=12):
    """화살촉으로 쓸 원뿔 메시를 만든다."""
    d = tip - base
    L = np.linalg.norm(d)
    if L < 1e-10:
        return (None,) * 6
    d = d / L
    arb = np.array([1., 0., 0.]) if abs(d @ np.array([1., 0., 0.])) < 0.9 \
        else np.array([0., 1., 0.])
    p1 = np.cross(d, arb); p1 /= np.linalg.norm(p1)
    p2 = np.cross(d, p1)
    th = np.linspace(0, 2 * np.pi, n + 1)[:-1]
    ring = np.array([base + radius * (np.cos(t) * p1 + np.sin(t) * p2) for t in th])
    verts = np.vstack([ring, [tip], [base]])
    i, j, k = [], [], []
    for a in range(n):
        b = (a + 1) % n
        i += [a, a]; j += [b, b]; k += [n, n + 1]
    return verts[:, 0], verts[:, 1], verts[:, 2], i, j, k


# ================================================================ 벡터

def draw_vec3d(fig, v, color='crimson', start_from=None, alpha=1.0, label=None,
               cone_ratio=0.12, cone_radius=0.06, lineType='solid'):
    """3차원 화살표(선분 + 원뿔 화살촉)를 그린다."""
    v = np.asarray(v, dtype=float)
    s = np.zeros(3) if start_from is None else np.asarray(start_from, dtype=float)
    end = s + v
    L = np.linalg.norm(v)
    if L < 1e-10:
        return fig
    base = end - (v / L) * (L * cone_ratio)

    fig.add_trace(go.Scatter3d(x=[s[0], base[0]], y=[s[1], base[1]],
                               z=[s[2], base[2]], mode='lines',
                               line=dict(color=color, width=4, dash=_dash(lineType)),
                               opacity=alpha, showlegend=False))
    if cone_radius > 0:
        cx, cy, cz, ci, cj, ck = _cone(end, base, radius=cone_radius)
        if cx is not None:
            fig.add_trace(go.Mesh3d(x=cx, y=cy, z=cz, i=ci, j=cj, k=ck,
                                    color=color, opacity=alpha, showlegend=False))
    if label is not None:
        m = s + v / 2
        fig.add_trace(go.Scatter3d(x=[m[0]], y=[m[1]], z=[m[2]], mode='text',
                                   text=[label], textfont=dict(size=12, color=color),
                                   showlegend=False))
    return fig


def draw_vec2d(fig, v, color='crimson', start_from=None, alpha=1.0, label=None,
               cone_ratio=0.12, cone_radius=0.04, lineType='solid'):
    """z=0 평면 위에 2차원 화살표를 그린다."""
    return draw_vec3d(fig, _to3(v), color=color,
                      start_from=None if start_from is None else _to3(start_from),
                      alpha=alpha, label=label, cone_ratio=cone_ratio,
                      cone_radius=cone_radius, lineType=lineType)


def draw_vector(fig, v, origin=None, color='crimson', label=None,
                width=0.012, alpha=1.0, linestyle='-'):
    """lautils와 같은 이름·같은 인자의 화살표. 2차원·3차원을 자동 판별한다."""
    v = np.asarray(v, dtype=float)
    radius = 0.04 if len(v) == 2 else 0.06
    return draw_vec3d(fig, _to3(v), color=color,
                      start_from=None if origin is None else _to3(origin),
                      alpha=alpha, label=label, cone_radius=radius,
                      lineType=_dash(linestyle))


def draw_vectors(fig, vs, origin=None, labels=None, alpha=1.0):
    """여러 벡터를 PALETTE 순서대로 색을 바꿔 가며 그린다."""
    for i, v in enumerate(np.asarray(vs, dtype=float)):
        draw_vector(fig, v, origin=origin, color=PALETTE[i % len(PALETTE)],
                    label=None if labels is None else labels[i], alpha=alpha)
    return fig


# ================================================================ 점·도형

def draw_points(fig, P, color='darkorange', size=4, label=None, labels=None,
                marker='o', s=None):
    """행마다 점 하나가 담긴 배열 P를 찍는다. 2차원은 z=0 평면 위에 놓인다."""
    pts = np.array([_to3(p) for p in np.atleast_2d(np.asarray(P, dtype=float))])
    size = size if s is None else max(s / 10, 2)     # matplotlib의 s와 눈금 맞춤
    fig.add_trace(go.Scatter3d(
        x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
        mode='markers+text' if labels else 'markers',
        marker=dict(size=size, color=color),
        text=labels, textposition='top center', textfont=dict(size=10),
        name=label or '', showlegend=False))
    return fig


def draw_points_in_matrix(fig, M, color='crimson', size=4):
    """열마다 점 하나가 담긴 행렬(2xN 또는 3xN)의 점들을 찍는다."""
    return draw_points(fig, np.asarray(M, dtype=float).T, color=color, size=size)


def draw_polygon(fig, P, color='goldenrod', alpha=0.35, edge=True):
    """꼭짓점 목록이 이루는 다각형을 색으로 채운다 (0번 꼭짓점 기준 부채꼴 분할)."""
    pts = np.array([_to3(p) for p in np.asarray(P, dtype=float)])
    n = len(pts)
    if n < 3:
        return fig
    i = [0] * (n - 2)
    j = list(range(1, n - 1))
    k = list(range(2, n))
    fig.add_trace(go.Mesh3d(x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
                            i=i, j=j, k=k, color=color, opacity=alpha,
                            showlegend=False))
    if edge:
        loop = np.vstack([pts, pts[0]])
        fig.add_trace(go.Scatter3d(x=loop[:, 0], y=loop[:, 1], z=loop[:, 2],
                                   mode='lines', line=dict(color=color, width=3),
                                   showlegend=False))
    return fig


def draw_polygons(fig, polygon_list, facecolors, alpha=0.8):
    """여러 개의 다각형을 한꺼번에 그린다 (수업용 원래 API)."""
    for poly, fc in zip(polygon_list, facecolors):
        draw_polygon(fig, poly, color=fc, alpha=alpha, edge=False)
    return fig


def draw_line(fig, p1, p2, kind='segment', color='steelblue', alpha=0.9,
              scale=3.0, label=None, linestyle='-', type=None, cone_radius=0.05):
    """두 점으로 정해지는 선을 그린다. kind='segment' | 'ray' | 'line'.

    수업용 원래 API의 type= 인자도 그대로 받는다.
    """
    kind = type or kind
    a = _to3(p1); b = _to3(p2)
    d = b - a
    L = np.linalg.norm(d)
    if L < 1e-12:
        return fig
    u = d / L
    if kind == 'segment':
        s, e = a, b
    elif kind == 'ray':
        s, e = a, a + d * scale
    else:
        mid = (a + b) / 2
        s, e = mid - u * (L * scale / 2), mid + u * (L * scale / 2)

    fig.add_trace(go.Scatter3d(x=[s[0], e[0]], y=[s[1], e[1]], z=[s[2], e[2]],
                               mode='lines',
                               line=dict(color=color, width=4, dash=_dash(linestyle)),
                               opacity=alpha, showlegend=False))
    heads = []
    if kind == 'ray':
        heads = [(e, e - u * L * 0.1)]
    elif kind == 'line':
        heads = [(e, e - u * L * 0.1), (s, s + u * L * 0.1)]
    for tip, base in heads:
        cx, cy, cz, ci, cj, ck = _cone(tip, base, radius=cone_radius)
        if cx is not None:
            fig.add_trace(go.Mesh3d(x=cx, y=cy, z=cz, i=ci, j=cj, k=ck,
                                    color=color, opacity=alpha, showlegend=False))
    if label is not None:
        m = (a + b) / 2
        fig.add_trace(go.Scatter3d(x=[m[0]], y=[m[1]], z=[m[2]], mode='text',
                                   text=[label], textfont=dict(size=12, color=color),
                                   showlegend=False))
    return fig


def draw_circle(fig, center=(0, 0), radius=1.0, normal=None, color='steelblue',
                alpha=0.5, fill=True, n=64, linestyle='-'):
    """원을 그린다. 3차원에서는 normal에 수직인 평면 위의 원이 된다."""
    c = _to3(center)
    nrm = np.asarray(normal if normal is not None else [0., 0., 1.], dtype=float)
    nrm = nrm / np.linalg.norm(nrm)
    arb = np.array([1., 0., 0.]) if abs(nrm @ np.array([1., 0., 0.])) < 0.9 \
        else np.array([0., 1., 0.])
    t1 = np.cross(nrm, arb); t1 /= np.linalg.norm(t1)
    t2 = np.cross(nrm, t1)
    th = np.linspace(0, 2 * np.pi, n + 1)[:-1]
    ring = np.array([c + radius * (np.cos(t) * t1 + np.sin(t) * t2) for t in th])

    if fill:
        verts = np.vstack([c.reshape(1, 3), ring])
        i = [0] * n
        j = list(range(1, n + 1))
        k = [(idx % n) + 1 for idx in range(1, n + 1)]
        fig.add_trace(go.Mesh3d(x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
                                i=i, j=j, k=k, color=color, opacity=alpha,
                                showlegend=False))
    loop = np.vstack([ring, ring[0:1]])
    fig.add_trace(go.Scatter3d(x=loop[:, 0], y=loop[:, 1], z=loop[:, 2],
                               mode='lines',
                               line=dict(color=color, width=3, dash=_dash(linestyle)),
                               opacity=min(alpha + 0.3, 1.0), showlegend=False))
    return fig


def draw_circle_3d(fig, center, normal, radius, color='steelblue', alpha=0.3,
                   n_segments=64, lineType='solid'):
    """수업용 원래 API — draw_circle의 인자 순서만 다른 형태."""
    return draw_circle(fig, center, radius, normal=normal, color=color,
                       alpha=alpha, n=n_segments, linestyle=lineType)


def draw_circle_2d(fig, center=(0, 0), radius=1.0, color='steelblue', alpha=0.5,
                   n_segments=64, lineType='solid'):
    """z=0 평면 위의 원."""
    return draw_circle(fig, center, radius, normal=[0, 0, 1], color=color,
                       alpha=alpha, n=n_segments, linestyle=lineType)


def draw_plane(fig, a, b, c=None, r=2.0, color='goldenrod', alpha=0.25,
               show_normal=True, **kw):
    """평면을 그린다. 두 가지 방식을 모두 받는다.

        draw_plane(fig, p, normal)        점 하나와 법선벡터
        draw_plane(fig, p1, p2, p3)       세 점 (수업용 원래 API)
    """
    if c is None:                                   # 점 + 법선
        p = np.asarray(a, dtype=float)
        n = np.asarray(b, dtype=float)
    else:                                           # 세 점
        p1, p2, p3 = (np.asarray(t, dtype=float) for t in (a, b, c))
        p = (p1 + p2 + p3) / 3.0
        n = np.cross(p2 - p1, p3 - p1)
        draw_polygon(fig, np.vstack([p1, p2, p3]), color='cyan', alpha=0.6)
    draw_circle(fig, p, r, normal=n, color=color, alpha=alpha)
    if show_normal:
        draw_vector(fig, n / np.linalg.norm(n), origin=p, color='crimson', label='n')
    return fig


def draw_plane_from_normal(fig, p, n, r=3, plane_color='goldenrod',
                           plane_alpha=0.2, lineType='solid'):
    """수업용 원래 API — 점과 법선으로 평면을 그린다."""
    return draw_plane(fig, p, n, r=r, color=plane_color, alpha=plane_alpha)


# ================================================================ 격자·행렬

def draw_grid(fig, A=None, n=4, color='steelblue', alpha=0.55, lw=1):
    """단위 격자를 그린다. 행렬 A를 주면 A로 변환된 격자를 그린다."""
    A = np.eye(2) if A is None else np.asarray(A, dtype=float)
    u = _to3(A[:, 0]); v = _to3(A[:, 1])
    for i in range(-n, n + 1):
        for base, along in ((u, v), (v, u)):
            s = base * i - along * n
            e = s + along * 2 * n
            fig.add_trace(go.Scatter3d(x=[s[0], e[0]], y=[s[1], e[1]],
                                       z=[s[2], e[2]], mode='lines',
                                       line=dict(color=color, width=lw),
                                       opacity=alpha, showlegend=False,
                                       hoverinfo='skip'))
    return fig


def draw_matrix(fig, M, label=None, alpha=0.3, ghost=True):
    """행렬의 열벡터가 만드는 평행사변형(2x2) 또는 평행육면체(3x3)를 그린다."""
    M = np.asarray(M, dtype=float)
    if M.shape == (2, 2):
        u, v = _to3(M[:, 0]), _to3(M[:, 1])
        draw_polygon(fig, np.vstack([np.zeros(3), u, u + v, v]), alpha=alpha)
        draw_vec3d(fig, u, color='crimson', cone_radius=0.04)
        draw_vec3d(fig, v, color='seagreen', cone_radius=0.04)
        if ghost:
            draw_vec3d(fig, u, color='gray', start_from=v, alpha=0.25,
                       cone_ratio=0, cone_radius=0)
            draw_vec3d(fig, v, color='gray', start_from=u, alpha=0.25,
                       cone_ratio=0, cone_radius=0)
        corner = u + v
    elif M.shape == (3, 3):
        u, v, w = M[:, 0], M[:, 1], M[:, 2]
        for vec, col in zip((u, v, w), ('crimson', 'seagreen', 'royalblue')):
            draw_vec3d(fig, vec, color=col)
        if ghost:
            for vec, org in [(u, v), (u, w), (u, v + w), (v, u), (v, w),
                             (v, u + w), (w, u), (w, v), (w, u + v)]:
                draw_vec3d(fig, vec, color='gray', start_from=org, alpha=0.25,
                           cone_ratio=0, cone_radius=0)
        corner = u + v + w
    else:
        raise ValueError('draw_matrix는 2x2 또는 3x3 행렬만 지원한다')

    if label is not None:
        fig.add_trace(go.Scatter3d(x=[corner[0]], y=[corner[1]], z=[corner[2]],
                                   mode='text', text=[label],
                                   textfont=dict(size=12), showlegend=False))
    return fig


def draw_mat22(fig, M, label=None):
    """수업용 원래 API — 2x2 행렬을 평행사변형으로."""
    return draw_matrix(fig, M, label=label)


def draw_mat33(fig, M, label=None):
    """수업용 원래 API — 3x3 행렬을 평행육면체로."""
    return draw_matrix(fig, M, label=label)


def draw_space_mat22(fig, M, label=None, color='gray', alpha=0.2):
    """수업용 원래 API — 2x2 행렬이 만드는 변환된 격자 공간."""
    draw_matrix(fig, M, label=label)
    return draw_grid(fig, M, n=10, color=color, alpha=alpha)


def transform(A, P):
    """행마다 점 하나가 담긴 배열 P의 모든 점에 행렬 A를 적용한다."""
    return (np.asarray(A, dtype=float) @ np.asarray(P, dtype=float).T).T


def show_matrix(fig, A, fmt='{:.2f}', cmap='RdBu_r', title=None):
    """행렬을 색상 격자로 보여 준다 (plotly 히트맵)."""
    A = np.asarray(A, dtype=float)
    lim = np.abs(A).max() or 1.0
    hm = go.Figure(go.Heatmap(z=A[::-1], zmin=-lim, zmax=lim, colorscale='RdBu_r',
                              text=[[fmt.format(v) for v in row] for row in A[::-1]]
                              if fmt else None,
                              texttemplate='%{text}' if fmt else None))
    hm.update_layout(title=title, width=420, height=400,
                     yaxis=dict(scaleanchor='x'))
    return hm


# ================================================================ 경계 볼륨

def draw_bounding_sphere(fig, center, radius, color='royalblue', alpha=0.3):
    """경계 구(bounding sphere)를 그린다."""
    c = np.asarray(center, dtype=float)
    u = np.linspace(0, 2 * np.pi, 40)
    v = np.linspace(0, np.pi, 20)
    fig.add_trace(go.Surface(
        x=c[0] + radius * np.outer(np.cos(u), np.sin(v)),
        y=c[1] + radius * np.outer(np.sin(u), np.sin(v)),
        z=c[2] + radius * np.outer(np.ones_like(u), np.cos(v)),
        colorscale=[[0, color], [1, color]], opacity=alpha, showscale=False))
    return fig


def _box_faces():
    faces = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4],
             [2, 3, 7, 6], [0, 3, 7, 4], [1, 2, 6, 5]]
    i, j, k = [], [], []
    for f in faces:
        i += [f[0], f[0]]; j += [f[1], f[2]]; k += [f[2], f[3]]
    return i, j, k


def draw_aabb(fig, min_pt, max_pt, color='seagreen', alpha=0.2):
    """축에 정렬된 경계 상자(AABB)를 그린다."""
    lo = np.asarray(min_pt, dtype=float)
    hi = np.asarray(max_pt, dtype=float)
    V = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]],
                  [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                  [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]],
                  [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]])
    i, j, k = _box_faces()
    fig.add_trace(go.Mesh3d(x=V[:, 0], y=V[:, 1], z=V[:, 2], i=i, j=j, k=k,
                            color=color, opacity=alpha, showlegend=False))
    return fig


def draw_obb(fig, center, half_extents, rotation, color='darkorange', alpha=0.2):
    """방향을 가진 경계 상자(OBB)를 그린다. rotation의 열이 상자의 축이다."""
    c = np.asarray(center, dtype=float)
    h = np.asarray(half_extents, dtype=float)
    R = np.asarray(rotation, dtype=float)
    signs = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]])
    V = np.array([c + R @ (s * h) for s in signs])
    i, j, k = _box_faces()
    fig.add_trace(go.Mesh3d(x=V[:, 0], y=V[:, 1], z=V[:, 2], i=i, j=j, k=k,
                            color=color, opacity=alpha, showlegend=False))
    for idx, col in enumerate(('crimson', 'seagreen', 'royalblue')):
        draw_vec3d(fig, R[:, idx] * h[idx], color=col, start_from=c,
                   cone_radius=0.03)
    return fig
