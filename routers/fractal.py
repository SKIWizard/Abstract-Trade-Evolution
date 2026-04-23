from flask import Blueprint, jsonify
import numpy as np
import random
import base64
from io import BytesIO
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

fractal_bp = Blueprint('fractal', __name__, url_prefix='/fractal')

params = {
    "res": 600,
    "max_iter": 40,
    "escape_radius": 4,
    "formula_complexity": (5, 20)
}


def safe_eval(formula_str, z, c):
    try:
        z = np.clip(z.real, -1e10, 1e10) + 1j * np.clip(z.imag, -1e10, 1e10)
        result = eval(formula_str)
        if np.any(np.isinf(result)) or np.any(np.isnan(result)):
            return np.zeros_like(c)
        return result
    except:
        return np.zeros_like(c)


def get_random_formula():
    ops = ['+', '-', '*']
    funcs = [
        'np.sin', 'np.cos', 'np.abs', 'np.exp',
        'np.sinh', 'np.cosh'
    ]

    safe_formulas = [
        "z**2 + c",
        "z**3 + c",
        "z**2 + c**2",
        "np.sin(z) + c",
        "np.cos(z) + c",
        "z * z + c",
        "z**2 + np.sin(c)",
        "z**3 - c",
        "np.exp(z) + c",
        "z**2 + np.exp(c)"
    ]

    if random.random() < 0.3:
        return random.choice(safe_formulas)

    formula = "z"
    complexity = random.randint(3, params["formula_complexity"][1])

    for _ in range(complexity):
        op = random.choice(ops)
        if op == '*':
            term = random.choice(['z', 'c', '0.5', '2.0'])
            formula = f"({formula})*({term})"
        elif op == '+':
            term = random.choice(['z', 'c', '0.5', '2.0', 'np.sin(z)', 'np.cos(c)'])
            formula = f"({formula})+({term})"
        elif op == '-':
            term = random.choice(['z', 'c', '0.5', '2.0'])
            formula = f"({formula})-({term})"

        if random.random() > 0.7 and len(funcs) > 0:
            formula = f"{random.choice(funcs)}({formula})"

    return formula + " + c"


def generate_fractal_data(formula_str, x_range=[-2, -2], y_range=[2, 2], res=600):
    x = np.linspace(x_range[0], x_range[1], res)
    y = np.linspace(y_range[0], y_range[1], res)
    X, Y = np.meshgrid(x, y)
    c = X + 1j * Y
    z = np.zeros_like(c)
    fractal_map = np.zeros(c.shape)

    for i in range(params["max_iter"]):
        try:
            z_new = safe_eval(formula_str, z, c)
            mask = np.abs(z_new) < params["escape_radius"]
            fractal_map[mask] += 1
            z = z_new
            if not np.any(mask):
                break
        except Exception:
            break

    fractal_map = np.log1p(fractal_map)
    fractal_map = fractal_map / fractal_map.max() if fractal_map.max() > 0 else fractal_map

    return fractal_map


def fractal_to_base64(fractal_data, formula):
    try:
        fig = plt.figure(figsize=(10, 10), facecolor='black', dpi=80)
        ax = fig.add_subplot(111)
        ax.set_facecolor('black')
        ax.set_axis_off()

        cmap_name = random.choice(['plasma', 'inferno', 'magma', 'viridis', 'coolwarm', 'twilight'])
        cmap = plt.get_cmap(cmap_name)

        extent = [-2, 2, -2, 2]
        ax.imshow(fractal_data, cmap=cmap, extent=extent, origin='lower', aspect='auto')

        formula_display = formula if len(formula) <= 60 else formula[:57] + "..."
        ax.set_title(formula_display, color='white', fontsize=10, pad=20, fontfamily='monospace')

        buffer = BytesIO()
        plt.tight_layout(pad=0)
        plt.savefig(buffer, format='png', bbox_inches='tight', facecolor='black', dpi=90)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        plt.close('all')

        return image_base64
    except Exception:
        return create_placeholder_image()


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
        formula = get_random_formula()
        fractal_data = generate_fractal_data(formula, [-2, -2], [2, 2], res=params["res"])
        image_base64 = fractal_to_base64(fractal_data, formula)

        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{image_base64}",
            "formula": formula
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500