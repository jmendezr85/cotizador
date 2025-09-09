# utils.py
import math
from PIL import Image, ImageChops

try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:
    _HAS_NUMPY = False

DEFAULT_DPI = 300

PRINT_COSTS = {
    "pliego": {
        "display_name": "Pliego (70cm Ancho x Alto Flexible)",
        "dimensions_cm": (72, 102),
        "base_cost": 7000,
        "full_cost": 17500,
    },
    "medio_pliego": {
        "display_name": "Medio Pliego (70x50 cm)",
        "dimensions_cm": (73, 54),
        "base_cost": 4000,
        "full_cost": 9000,
    },
    "cuarto_pliego": {
        "display_name": "Cuarto Pliego (50x35 cm)",
        "dimensions_cm": (52, 36),
        "base_cost": 3000,
        "full_cost": 5000,
    },
    "extra_90": {
        "display_name": "Extra 90 cm (90cm Ancho x Alto Flexible)",
        "dimensions_cm": (90, 100),
        "base_cost": 9000,
        "full_cost": 23000,
    },
    "extra_100": {
        "display_name": "Extra 100 cm (100cm Ancho x Alto Flexible)",
        "dimensions_cm": (100, 100),
        "base_cost": 10000,
        "full_cost": 27000,
    },
    "large_format": {
        "display_name": "Formato Grande (Ancho > 100cm, Alto Flexible)",
        "dimensions_cm": (100, 100),
        "base_cost": 12000,
        "full_cost": 30000,
    }
}

LINE_COSTS = {
    "pliego": {"negra": 6000, "color": 7000},
    "medio_pliego": {"negra": 3500, "color": 4000},
    "cuarto_pliego": {"negra": 2500, "color": 3000}
}

LINE_DETECTION_CONFIG = {
    "black_threshold": 140,
    "white_threshold": 253,
    "min_black_ratio": 0.97
}


def cm_to_pixels(cm_value, dpi=DEFAULT_DPI):
    return int(cm_value * dpi / 2.54)


def pixels_to_cm(pixels_value, dpi=DEFAULT_DPI):
    return pixels_value * 2.54 / dpi


def _detect_line_type_numpy(arr, black_threshold, white_threshold, min_black_ratio):
    white_mask = (arr[:, :, 0] >= white_threshold) & (arr[:, :, 1] >= white_threshold) & (arr[:, :, 2] >= white_threshold)
    non_white_mask = ~white_mask
    non_white_count = int(non_white_mask.sum())

    if non_white_count == 0:
        return "color"

    black_mask = (arr[:, :, 0] <= black_threshold) & (arr[:, :, 1] <= black_threshold) & (arr[:, :, 2] <= black_threshold)
    black_and_nonwhite = black_mask & non_white_mask
    black_count = int(black_and_nonwhite.sum())

    black_ratio = black_count / non_white_count if non_white_count > 0 else 0.0

    return "negra" if black_ratio >= min_black_ratio else "color"


def _detect_line_type_pillow(image_pil, black_threshold, white_threshold, min_black_ratio):
    if not image_pil:
        return "color"

    rgb = image_pil.convert("RGB")
    pixels = rgb.getdata()

    non_white_count = 0
    black_count = 0

    for r, g, b in pixels:
        if r >= white_threshold and g >= white_threshold and b >= white_threshold:
            continue
        non_white_count += 1
        if r <= black_threshold and g <= black_threshold and b <= black_threshold:
            black_count += 1

    if non_white_count == 0:
        return "color"

    black_ratio = black_count / non_white_count
    return "negra" if black_ratio >= min_black_ratio else "color"


def detect_line_type(image_pil, black_threshold=None, white_threshold=None, min_black_ratio=None):
    if black_threshold is None:
        black_threshold = LINE_DETECTION_CONFIG["black_threshold"]
    if white_threshold is None:
        white_threshold = LINE_DETECTION_CONFIG["white_threshold"]
    if min_black_ratio is None:
        min_black_ratio = LINE_DETECTION_CONFIG["min_black_ratio"]

    if image_pil is None:
        return "color"

    if _HAS_NUMPY:
        try:
            rgb_image = image_pil.convert("RGB")
            arr = np.asarray(rgb_image)
            return _detect_line_type_numpy(arr, black_threshold, white_threshold, min_black_ratio)
        except Exception:
            return _detect_line_type_pillow(image_pil, black_threshold, white_threshold, min_black_ratio)
    else:
        return _detect_line_type_pillow(image_pil, black_threshold, white_threshold, min_black_ratio)


def compute_image_pixel_stats(image_pil, black_threshold=None, white_threshold=None):
    if black_threshold is None:
        black_threshold = LINE_DETECTION_CONFIG["black_threshold"]
    if white_threshold is None:
        white_threshold = LINE_DETECTION_CONFIG["white_threshold"]

    if image_pil is None:
        return {
            'total_pixels': 0,
            'white_count': 0,
            'non_white_count': 0,
            'black_count': 0,
            'non_white_percentage': 0.0
        }

    rgb_image = image_pil.convert("RGB")

    if _HAS_NUMPY:
        try:
            arr = np.asarray(rgb_image)
            h, w = arr.shape[0], arr.shape[1]
            total_pixels = h * w

            white_mask = (arr[:, :, 0] >= white_threshold) & (arr[:, :, 1] >= white_threshold) & (arr[:, :, 2] >= white_threshold)
            white_count = int(white_mask.sum())

            non_white_mask = ~white_mask
            non_white_count = int(non_white_mask.sum())

            black_mask = (arr[:, :, 0] <= black_threshold) & (arr[:, :, 1] <= black_threshold) & (arr[:, :, 2] <= black_threshold)
            black_and_nonwhite = black_mask & non_white_mask
            black_count = int(black_and_nonwhite.sum())

            non_white_percentage = (non_white_count / total_pixels) * 100 if total_pixels > 0 else 0.0

            return {
                'total_pixels': total_pixels,
                'white_count': white_count,
                'non_white_count': non_white_count,
                'black_count': black_count,
                'non_white_percentage': non_white_percentage
            }
        except Exception:
            pass

    pixels = rgb_image.getdata()
    total_pixels = 0
    white_count = 0
    non_white_count = 0
    black_count = 0

    for r, g, b in pixels:
        total_pixels += 1
        if r >= white_threshold and g >= white_threshold and b >= white_threshold:
            white_count += 1
            continue
        non_white_count += 1
        if r <= black_threshold and g <= black_threshold and b <= black_threshold:
            black_count += 1

    non_white_percentage = (non_white_count / total_pixels) * 100 if total_pixels > 0 else 0.0

    return {
        'total_pixels': total_pixels,
        'white_count': white_count,
        'non_white_count': non_white_count,
        'black_count': black_count,
        'non_white_percentage': non_white_percentage
    }


def is_color_image(image: Image.Image, tolerance: int = 10) -> bool:
    """
    Determina si un objeto de imagen PIL es a color o en blanco y negro,
    utilizando un método de comparación más robusto.

    Args:
        image: Un objeto de imagen de la biblioteca Pillow.
        tolerance: La tolerancia permitida para las diferencias de píxeles.

    Returns:
        True si la imagen es a color, False si es en blanco y negro.
    """
    if image.mode not in ['RGB', 'RGBA']:
        image = image.convert('RGB')

    # Convertir la imagen a escala de grises y luego de vuelta a RGB.
    # Si la imagen era realmente en blanco y negro, los píxeles no cambiarán.
    grayscale_image = image.convert('L').convert('RGB')
    
    # Calcular la diferencia de píxeles entre la imagen original y la versión en escala de grises.
    # ImageChops.difference devuelve una imagen con la diferencia absoluta de píxeles.
    diff_image = ImageChops.difference(image, grayscale_image)
    
    # Calcular la suma total de las diferencias de píxeles.
    # Si la suma es mayor que la tolerancia, la imagen es a color.
    if diff_image.getbbox():
        sum_of_differences = sum(diff_image.getdata())
        return sum_of_differences > tolerance
    else:
        # Si no hay diferencias, la imagen es en blanco y negro.
        return False


def coty_calculate_price_logic(print_type_key, non_white_percentage, largo_cm):
    data = PRINT_COSTS.get(print_type_key)
    if not data:
        return 0.0

    base_cost = data["base_cost"]
    full_cost = data["full_cost"]

    porcentaje_clamped = max(0, min(100, non_white_percentage))

    if print_type_key == "extra_90":
        if porcentaje_clamped < 6:
            return 10000
        elif 6 <= porcentaje_clamped < 15:
            return 12000
        elif 15 <= porcentaje_clamped < 25:
            return 14000
        elif 25 <= porcentaje_clamped < 35:
            return 16000
        elif 35 <= porcentaje_clamped < 45:
            return 18000
        elif 45 <= porcentaje_clamped < 55:
            return 20000
        elif 55 <= porcentaje_clamped < 65:
            return 22000
        elif 65 <= porcentaje_clamped < 75:
            return 24000
        elif 75 <= porcentaje_clamped < 85:
            return 26000
        elif 85 <= porcentaje_clamped < 95:
            return 28000
        else:
            return 30000

    factor = 0.0
    if porcentaje_clamped < 6:
        factor = 0.0
    elif porcentaje_clamped < 15:
        factor = 0.1
    elif porcentaje_clamped < 25:
        factor = 0.2
    elif porcentaje_clamped < 35:
        factor = 0.3
    elif porcentaje_clamped < 45:
        factor = 0.4
    elif porcentaje_clamped < 55:
        factor = 0.5
    elif porcentaje_clamped < 65:
        factor = 0.6
    elif porcentaje_clamped < 75:
        factor = 0.7
    elif porcentaje_clamped < 85:
        factor = 0.8
    elif porcentaje_clamped < 95:
        factor = 0.9
    else:
        factor = 1.0

    largo_factor = 1.0
    if print_type_key in ["pliego", "extra_90", "extra_100", "large_format"]:
        ref_height = data["dimensions_cm"][1]
        if ref_height > 0 and largo_cm > ref_height:
            largo_factor = largo_cm / ref_height
        else:
            largo_factor = 1.0

    total_cost = base_cost + (full_cost - base_cost) * factor
    total_cost *= largo_factor

    if print_type_key == "medio_pliego":
        pass
    elif print_type_key == "cuarto_pliego":
        total_cost = round(total_cost / 500) * 500
    elif print_type_key in ["pliego", "extra_90", "extra_100", "large_format"]:
        total_cost = round(total_cost / 1000) * 1000

    return total_cost


def calculate_print_cost(print_type_key, non_white_percentage, canvas_height_cm):
    try:
        data = PRINT_COSTS[print_type_key]
    except KeyError:
        return 0

    porcentaje_clamped = max(0, min(100, non_white_percentage))
    
    factor = 0.0
    if porcentaje_clamped < 6:
        factor = 0.0
    elif porcentaje_clamped < 15:
        factor = 0.1
    elif porcentaje_clamped < 25:
        factor = 0.2
    elif porcentaje_clamped < 35:
        factor = 0.3
    elif porcentaje_clamped < 45:
        factor = 0.4
    elif porcentaje_clamped < 55:
        factor = 0.5
    elif porcentaje_clamped < 65:
        factor = 0.6
    elif porcentaje_clamped < 75:
        factor = 0.7
    elif porcentaje_clamped < 85:
        factor = 0.8
    elif porcentaje_clamped < 95:
        factor = 0.9
    else:
        factor = 1.0

    largo_factor = 1.0
    if print_type_key in ["pliego", "extra_90", "extra_100", "large_format"]:
        ref_height = data["dimensions_cm"][1]
        if ref_height > 0:
            largo_factor = canvas_height_cm / ref_height
    
    print(largo_factor)
    
    
    total_cost = data["base_cost"] + (data["full_cost"] - data["base_cost"]) * factor
    total_cost *= largo_factor

    if print_type_key == "cuarto_pliego":
        total_cost = round(total_cost / 500) * 500
    elif print_type_key in ["pliego", "extra_90", "extra_100", "large_format"]:
        total_cost = round(total_cost / 1000) * 1000

    return total_cost