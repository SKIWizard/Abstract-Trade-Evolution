from flask import Blueprint, jsonify
import numpy as np
import random
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
from mpmath import mp
from models import db, Fractal

warnings.filterwarnings('ignore')

fractal_bp = Blueprint('fractal', __name__, url_prefix='/fractal')

params = {
    "res_high": 1000,
    "res_low": 150,
    "max_iter": 60,
    "escape_radius": 100,
    "initial_dps": 20,
    "dps_step": 5,
    "dps_threshold": 1e-12,
    "formula_complexity": (10, 40),
    "rare_cmap_chance": 0.01
}

mp.dps = params["initial_dps"]

trash_cmaps = [
    'BrBG', 'YlOrBr', 'copper', 'bone', 'Grays',
    'Greys', 'binary', 'gist_yarg', 'gist_earth',
    'OrRd', 'PuRd', 'BuPu', 'Oranges', 'Reds',
    'autumn', 'summer', 'Wistia', 'hot', 'afmhot',
    'brown', 'tab10', 'tab20', 'tab20b', 'tab20c',
    'Pastel1', 'Pastel2', 'Set3', 'flag', 'prism',
    'ocean', 'terrain', 'gnuplot', 'gnuplot2',
    'CMRmap', 'cubehelix', 'pink', 'gray'
]

rare_cmaps = [
    'plasma', 'inferno', 'magma', 'viridis',
    'coolwarm', 'twilight', 'turbo', 'jet',
    'Spectral', 'RdYlBu', 'RdYlGn', 'PuOr',
    'BrBG_r', 'PiYG', 'PRGn', 'nipy_spectral',
    'rainbow', 'hsv', 'seismic', 'spring',
    'winter', 'cool'
]


def get_random_cmap():
    if random.random() < params["rare_cmap_chance"]:
        return random.choice(rare_cmaps)
    else:
        return random.choice(trash_cmaps)


def get_random_formula():
    ops = ['+', '-', '*', '/', '**']
    funcs = [
        'np.sin', 'np.cos', 'np.tan', 'np.abs', 'np.exp', 'np.conj',
        'np.sqrt', 'np.log', 'np.sinh', 'np.cosh', 'np.tanh',
        'np.arcsin', 'np.arccos', 'np.arctan', 'np.arcsinh', 'np.arccosh', 'np.arctanh'
    ]
    formula = "z"
    for _ in range(random.randint(*params["formula_complexity"])):
        op = random.choice(ops)
        if op == '**':
            formula = f"({formula})**{random.randint(2, 3)}"
        else:
            term = random.choice(['z', 'c', str(round(random.random(), 2))])
            formula = f"({formula}){op}({term})"

        if random.random() > 0.5:
            formula = f"{random.choice(funcs)}({formula})"

    return formula + " + c"


def generate_fractal_data(formula_str, x_range, y_range, res):
    x = np.linspace(float(x_range[0]), float(x_range[1]), res)
    y = np.linspace(float(y_range[0]), float(y_range[1]), res)
    X, Y = np.meshgrid(x, y)
    c = X + 1j * Y
    z = np.zeros_like(c)
    fractal_map = np.zeros(c.shape)

    for i in range(params["max_iter"]):
        try:
            z_new = eval(formula_str)
            mask = np.abs(z_new) < params["escape_radius"]
            fractal_map[mask] += 1
            z = z_new
            if not np.any(mask):
                break
        except:
            break

    if fractal_map.max() > 0:
        fractal_map = np.log1p(fractal_map)
        fractal_map = fractal_map / fractal_map.max()

    return fractal_map


def find_good_fractal():
    attempts = 0
    while attempts < 30:
        attempts += 1
        try:
            f = get_random_formula()
            data = generate_fractal_data(f, [mp.mpf(-2), mp.mpf(2)], [mp.mpf(-2), mp.mpf(2)], res=params["res_low"])
            unique_vals = len(np.unique(data))
            if 5 < unique_vals < 45:
                return f
        except:
            continue
    return "z**2 + c"


def fractal_to_base64(fractal_data):
    try:
        fig = plt.figure(figsize=(10, 10), facecolor='black', dpi=80)
        ax = fig.add_subplot(111)
        ax.set_facecolor('black')
        ax.set_axis_off()

        cmap_name = get_random_cmap()
        cmap = plt.get_cmap(cmap_name)

        ax.imshow(fractal_data, cmap=cmap, extent=[-2, 2, -2, 2], origin='lower', aspect='auto')

        buffer = BytesIO()
        plt.tight_layout(pad=0)
        plt.savefig(buffer, format='png', bbox_inches='tight', facecolor='black', dpi=90)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        plt.close('all')

        return image_base64, cmap_name
    except Exception:
        return create_placeholder_image(), 'gray'


def create_placeholder_image():
    fig = plt.figure(figsize=(10, 10), facecolor='black')
    ax = fig.add_subplot(111)
    ax.set_facecolor('#0b0e14')
    ax.text(0.5, 0.5, 'Ошибка генерации\nПопробуйте еще раз',
            ha='center', va='center', color='white', fontsize=16, transform=ax.transAxes)
    ax.set_axis_off()

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', facecolor='black')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close(fig)
    return image_base64


@fractal_bp.route("/generate", methods=["POST"])
def generate_fractal():
    try:
        mp.dps = params["initial_dps"]
        formula = find_good_fractal()
        x_range = [mp.mpf(-2), mp.mpf(2)]
        y_range = [mp.mpf(-2), mp.mpf(2)]
        fractal_data = generate_fractal_data(
            formula,
            x_range,
            y_range,
            res=params["res_high"]
        )
        image_base64, cmap_name = fractal_to_base64(fractal_data)

        fractal_record = Fractal(
            formula=formula,
            cmap=cmap_name,
            x_min=str(x_range[0]),
            x_max=str(x_range[1]),
            y_min=str(y_range[0]),
            y_max=str(y_range[1]),
            res=params["res_high"],
            max_iter=params["max_iter"],
            escape_radius=params["escape_radius"]
        )
        db.session.add(fractal_record)
        db.session.commit()

        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{image_base64}",
            "formula": formula,
            "fractal_id": fractal_record.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500