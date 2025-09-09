from PIL import Image
from utils import LINE_DETECTION_CONFIG

# Umbrales que usa detect_line_type
black_threshold = LINE_DETECTION_CONFIG["black_threshold"]
white_threshold = LINE_DETECTION_CONFIG["white_threshold"]

img = Image.open(
    r"C:\Users\JORGE-PC\Desktop\Cotizador ya funcional\Cotizador ya funcional\CotizadorApp\resource\mejora_1.png"
).convert("RGB")

total_pixels = 0
white_like = 0
black_like = 0
color_like = 0

for r, g, b in img.getdata():
    total_pixels += 1
    if r >= white_threshold and g >= white_threshold and b >= white_threshold:
        white_like += 1
    elif r <= black_threshold and g <= black_threshold and b <= black_threshold:
        black_like += 1
    else:
        color_like += 1

print(f"Total píxeles: {total_pixels}")
print(f"Blancos (>= {white_threshold}): {white_like}")
print(f"Negros (<= {black_threshold}): {black_like}")
print(f"Colores intermedios: {color_like}")
