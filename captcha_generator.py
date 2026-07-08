import os
import random
from typing import List, Tuple
from PIL import Image, ImageDraw


def create_sample_backgrounds(folder: str) -> List[Image.Image]:
    print(f"[INFO] Creating sample background images in: {folder}")
    os.makedirs(folder, exist_ok=True)

    colors = [(220, 220, 220), (200, 230, 255), (240, 220, 200)]
    images = []

    for idx, color in enumerate(colors, start=1):
        img = Image.new("RGB", (170, 170), color)
        path = os.path.join(folder, f"bg_{idx}.png")
        img.save(path)
        images.append(img)

    return images


def create_sample_objects(folder: str) -> List[Image.Image]:
    print(f"[INFO] Creating sample object images in: {folder}")
    os.makedirs(folder, exist_ok=True)

    colors = [(255, 0, 0), (0, 128, 0), (0, 0, 255)]
    images = []

    for idx, color in enumerate(colors, start=1):
        img = Image.new("RGB", (40, 40), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([8, 8, 32, 32], fill=color)
        path = os.path.join(folder, f"obj_{idx}.png")
        img.save(path)
        images.append(img)

    return images


def load_images_from_folder(folder: str, kind: str) -> List[Image.Image]:
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

    images = []
    for fname in os.listdir(folder):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(folder, fname)
            img = Image.open(path).convert("RGB")
            images.append(img)

    if not images:
        if kind == "background":
            images = create_sample_backgrounds(folder)
        else:
            images = create_sample_objects(folder)

    return images


def resize_image(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    return img.resize(size, Image.BILINEAR)


def overlay_object_cnn_style(
    background: Image.Image,
    obj: Image.Image,
    top_left: Tuple[int, int],
    white_threshold: int = 250,
) -> Image.Image:
    bg = background.copy()
    bg_pixels = bg.load()
    obj_pixels = obj.load()

    bg_w, bg_h = bg.size
    obj_w, obj_h = obj.size
    x0, y0 = top_left

    for i in range(obj_w):
        for j in range(obj_h):
            x = x0 + i
            y = y0 + j

            if x >= bg_w or y >= bg_h:
                continue

            r, g, b = obj_pixels[i, j]

            if (r >= white_threshold and g >= white_threshold and b >= white_threshold):
                continue

            bg_pixels[x, y] = (r, g, b)

    return bg


def generate_random_object_captcha(
    backgrounds_folder: str,
    objects_folder: str,
    bg_size: Tuple[int, int] = (170, 170),
    obj_size: Tuple[int, int] = (40, 40),
    min_objects: int = 2,
    max_objects: int = 6,
):
    background_images = load_images_from_folder(backgrounds_folder, kind="background")
    object_images = load_images_from_folder(objects_folder, kind="object")

    bg = resize_image(random.choice(background_images), bg_size)
    obj = resize_image(random.choice(object_images), obj_size)

    positions = []
    grid_rows, grid_cols = 4, 4
    step_x = (bg_size[0] - obj_size[0]) // (grid_cols - 1)
    step_y = (bg_size[1] - obj_size[1]) // (grid_rows - 1)

    for r in range(grid_rows):
        for c in range(grid_cols):
            x = c * step_x
            y = r * step_y
            positions.append((x, y))

    num_objects = random.randint(min_objects, max_objects)
    chosen_positions = random.sample(positions, num_objects)

    captcha_img = bg
    for pos in chosen_positions:
        captcha_img = overlay_object_cnn_style(captcha_img, obj, pos)

    question = f"How many objects are inserted in the image? Answer: {num_objects}"

    return captcha_img, question
