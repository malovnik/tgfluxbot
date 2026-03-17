"""
Модуль генерации фотосессий.
Библиотеки локаций, стилей, поз, одежды, освещения.
Мета-промпт для Gemini, очередь fal.ai, сборка ZIP.
"""

import asyncio
import io
import random
import zipfile
from dataclasses import dataclass
from typing import List

import requests
import fal_client
from google import genai
from google.genai import types

from modules.config import (
    GEMINI_API_KEY, FAL_MODEL_ID, FAL_LORA_URL,
    TIMEOUT, logger
)

# ─────────────────────────────────────────────
# Библиотеки
# ─────────────────────────────────────────────

LOCATIONS = [
    # Outdoor
    "tropical Thai beach with turquoise water and longtail boats",
    "luxury yacht deck in open sea with sunset horizon",
    "rooftop bar overlooking Bangkok skyline at night",
    "narrow Hanoi old quarter alley with hanging lanterns",
    "Japanese zen garden with stone path and bamboo fence",
    "mountain trail in Bali rice terraces at sunrise",
    "seaside promenade in Busan with cherry blossoms",
    "night market in Chiang Mai with colorful food stalls",
    "infinity pool edge at luxury villa overlooking ocean",
    "street of Shibuya Tokyo with neon signs and crowds blurred",
    "ancient temple ruins in Angkor Wat with moss-covered stones",
    "coastal cliff edge with crashing waves below",
    "urban graffiti wall in creative district",
    "marina dock with luxury boats and calm water reflections",
    "desert dunes at golden hour with long shadows",
    # Indoor
    "modern minimalist coworking space with floor-to-ceiling windows",
    "upscale restaurant with dim moody lighting and dark wood interior",
    "luxury hotel lobby with marble floors and high ceilings",
    "industrial loft apartment with exposed brick and large windows",
    "professional photography studio with cyclorama wall",
    "vintage library with wooden bookshelves and warm lamp light",
    "modern gym with mirrored walls and professional equipment",
    "sleek elevator interior of a glass skyscraper",
    "boutique coffee shop with specialty equipment and warm tones",
    "art gallery with white walls and dramatic spotlight",
    "barbershop with leather chairs and vintage mirrors",
    "luxury car interior shot from passenger side",
    "high-end fashion store fitting room area",
    "penthouse apartment with panoramic city view at dusk",
    "train cabin window seat with blurred landscape outside",
]

PHOTO_STYLES = [
    {
        "name": "Hasselblad Medium Format",
        "camera": "Hasselblad X2D 100C with XCD 80mm f/1.9 lens",
        "settings": "f/2.0, 1/250sec, ISO 64",
        "look": "medium format shallow depth of field, creamy bokeh, exceptional detail and dynamic range, natural color science",
    },
    {
        "name": "Kodak Portra 400",
        "camera": "Contax T2 with Carl Zeiss Sonnar 38mm f/2.8",
        "settings": "f/2.8, 1/125sec",
        "look": "Kodak Portra 400 film stock, warm pastel tones, soft grain, slightly lifted shadows, organic skin tones with subtle peach undertones",
    },
    {
        "name": "Black & White Grain",
        "camera": "Leica M11 Monochrom with 50mm Summilux f/1.4",
        "settings": "f/2.0, 1/500sec, ISO 400",
        "look": "high contrast black and white, visible film grain like Kodak Tri-X 400, deep blacks, rich midtones, dramatic tonal range",
    },
    {
        "name": "CineStill 800T Night",
        "camera": "Canon AE-1 with 50mm f/1.4",
        "settings": "f/1.4, 1/60sec",
        "look": "CineStill 800T tungsten-balanced film, characteristic red halation around highlights, warm amber street lights, teal shadows, cinematic night mood",
    },
    {
        "name": "Vogue Editorial",
        "camera": "Phase One IQ4 150MP with 110mm LS f/2.8",
        "settings": "f/4.0, 1/160sec, ISO 50",
        "look": "high fashion editorial look, perfectly controlled studio-quality lighting even outdoors, retouched skin with visible texture, Vogue magazine aesthetic",
    },
    {
        "name": "Street Candid 35mm",
        "camera": "Ricoh GR IIIx with 40mm f/2.8",
        "settings": "f/4.0, 1/250sec, ISO 800",
        "look": "authentic street photography, slightly imperfect framing, documentary feel, urban grit, available light only, snapshot aesthetic with artistic intent",
    },
    {
        "name": "Cinematic Anamorphic",
        "camera": "ARRI ALEXA Mini LF with Atlas Mercury anamorphic 40mm T2.2",
        "settings": "T2.2, 1/48sec, 800 ASA",
        "look": "2.39:1 cinematic aspect ratio, horizontal lens flares, oval bokeh, characteristic anamorphic breathing, film-like highlight rolloff, teal and orange color grade",
    },
    {
        "name": "Fuji Velvia Vivid",
        "camera": "Nikon F3 with Nikkor 85mm f/1.4",
        "settings": "f/2.0, 1/500sec",
        "look": "Fuji Velvia 50 slide film, extremely saturated colors, punchy contrast, vivid greens and blues, deep reds, landscape photography aesthetic",
    },
    {
        "name": "iPhone Casual",
        "camera": "iPhone 16 Pro main camera 24mm f/1.78",
        "settings": "auto exposure, computational photography",
        "look": "natural smartphone photography, Smart HDR processing, slight computational sharpening, authentic casual selfie or friend-taken photo feel, social media ready",
    },
    {
        "name": "Richard Avedon Fashion",
        "camera": "Mamiya RZ67 with 110mm f/2.8",
        "settings": "f/8, 1/125sec, ISO 100",
        "look": "clean white seamless background, flat even lighting from large softboxes, sharp focus across entire frame, minimal shadows, stark high-key fashion portrait",
    },
    {
        "name": "Scandinavian Minimalism",
        "camera": "Sony A7R V with 35mm GM f/1.4",
        "settings": "f/2.8, 1/200sec, ISO 100",
        "look": "muted desaturated palette, soft diffused window light, clean negative space, subtle earth tones, hygge aesthetic, calm contemplative mood",
    },
    {
        "name": "Golden Hour Warm",
        "camera": "Canon R5 with RF 85mm f/1.2L",
        "settings": "f/1.2, 1/1000sec, ISO 100",
        "look": "perfect golden hour backlight with warm rim lighting, lens flares, honeyed skin tones, dreamy atmosphere, shallow depth of field, magical warm glow",
    },
    {
        "name": "Neon Cyberpunk",
        "camera": "Sony A7S III with 35mm f/1.4 GM",
        "settings": "f/1.4, 1/100sec, ISO 3200",
        "look": "neon-lit urban night scene, pink and blue color cast from neon signs, wet reflective surfaces, cyberpunk aesthetic, high ISO grain, moody atmospheric",
    },
    {
        "name": "Vintage Polaroid",
        "camera": "Polaroid SX-70 with 116mm f/8",
        "settings": "auto exposure",
        "look": "classic Polaroid instant film look, slightly washed out colors, soft focus, characteristic white border frame, warm vintage color shift, nostalgic imperfect charm",
    },
    {
        "name": "90s Film Nostalgia",
        "camera": "Olympus Mju II with 35mm f/2.8",
        "settings": "f/2.8, auto exposure",
        "look": "90s point-and-shoot aesthetic, Fuji Superia 400 color palette, on-camera flash with harsh direct light, red-eye possibility, casual snapshot composition, era-authentic processing",
    },
]

POSES = [
    "standing with hands in pockets, relaxed confident posture",
    "leaning against a wall with one shoulder, arms crossed loosely",
    "walking confidently toward camera, mid-stride",
    "sitting on stone steps, elbows on knees, looking up",
    "looking out a large window, contemplative profile view",
    "holding a coffee cup casually, slight smile",
    "working on a laptop at a table, focused expression",
    "standing with arms crossed, direct eye contact",
    "leaning on a metal railing, looking into the distance",
    "three-quarter view, thoughtful expression, hand on chin",
    "standing next to a car, one hand on the roof",
    "sitting in a leather armchair, relaxed power pose",
    "adjusting shirt sleeve, looking down, candid moment",
    "standing with back partially to camera, looking over shoulder",
    "crouching low, forearms on knees, intense eye contact",
    "stretching arms overhead, casual morning wake-up feel",
    "reading a book while sitting on a bench",
    "standing in a doorway, silhouette framing",
    "walking up stairs, shot from below, dynamic angle",
    "sitting on the edge of a rooftop, legs dangling",
    "standing with one foot on a ledge, overlooking scenery",
    "caught mid-laugh, genuine happy expression",
    "putting on sunglasses, mid-motion candid",
    "standing at a bar counter, one elbow resting on it",
    "looking at phone while walking, natural urban moment",
    "standing with hands behind back, formal posture",
    "sitting cross-legged on the floor, casual relaxed",
    "leaning forward on a table, intense engaged expression",
    "standing in rain, face tilted up slightly, peaceful",
    "running hand through hair, casual natural gesture",
    "standing with one hand in pocket, other holding jacket over shoulder",
    "sitting sideways on a chair, arm over the backrest",
    "walking away from camera, looking back with a smirk",
    "standing between two columns or pillars, symmetrical framing",
    "holding a camera, photographing something off-frame",
    "sitting on a motorcycle, hands on handlebars",
    "standing at the edge of a pool, towel over shoulder",
    "leaning on a window frame, soft natural light on face",
    "standing in an elevator, pressing a button, candid",
    "sitting on a high stool at a counter, relaxed posture",
    "walking through a crowd, motion blur around, sharp subject",
    "standing in front of a mirror, reflection visible",
    "stretching after a workout, athletic pose, slight sweat",
    "pointing at something off-camera, engaged expression",
    "hands clasped behind head, relaxed backward lean",
    "squinting slightly against bright sunlight, natural",
    "standing near a bonfire, warm light on face, night setting",
    "sitting on a low wall, one leg up, casual urban",
    "walking with a backpack, traveler explorer vibe",
    "standing with feet apart, power stance, low angle shot",
]

OUTFITS = [
    "tailored dark navy suit with white shirt, no tie, top button open",
    "casual white crew-neck t-shirt with dark blue jeans and white sneakers",
    "light linen beach shirt unbuttoned over swim shorts, barefoot",
    "smart casual polo shirt in olive green with chino pants and loafers",
    "athletic dry-fit black t-shirt with running shorts and sports shoes",
    "cream oversized knit sweater with dark slim pants",
    "black leather jacket over a plain gray t-shirt with dark jeans and boots",
    "crisp button-down shirt with rolled sleeves and dress pants with suspenders",
    "relaxed-fit linen suit in light beige with espadrilles, resort wear",
    "black hoodie with jogger pants and chunky sneakers, streetwear",
    "denim jacket over a white henley with khaki cargo pants",
    "fitted black turtleneck with charcoal slacks, minimalist elegant",
    "tropical print short-sleeve shirt with white shorts and sandals",
    "dark brown suede bomber jacket with plain tee and dark jeans",
    "all-black outfit: black shirt, black pants, black shoes, monochrome",
    "light blue Oxford shirt tucked into navy chinos with brown belt",
    "vintage band t-shirt with ripped jeans and Converse sneakers",
    "tailored gray blazer over a black crewneck with dark trousers",
    "white long-sleeve sweatshirt with black crossbody bag and dark pants",
    "gym tank top showing athletic build, training shorts, wrist wraps",
]

LIGHTING = [
    {
        "name": "golden_hour",
        "time": "sunset golden hour, 5:30 PM",
        "desc": "warm amber directional sunlight from low angle, long soft shadows, rim lighting on hair and shoulders, 3200K warm color temperature",
    },
    {
        "name": "harsh_midday",
        "time": "high noon, clear sky",
        "desc": "direct overhead sunlight creating strong defined shadows under brow and chin, high contrast, 5600K neutral daylight",
    },
    {
        "name": "overcast_soft",
        "time": "daytime overcast sky",
        "desc": "soft diffused light from cloud cover acting as giant softbox, minimal shadows, even illumination, flattering for portraits, 6500K cool daylight",
    },
    {
        "name": "night_warm_artificial",
        "time": "nighttime, urban setting",
        "desc": "warm artificial street lamps and interior lights, pools of warm light against dark surroundings, 2700K tungsten warmth, atmospheric",
    },
    {
        "name": "neon_night",
        "time": "late night, neon district",
        "desc": "colorful neon signs casting pink, blue, and green light on face, wet surfaces reflecting colors, mixed color temperatures creating vibrant mood",
    },
    {
        "name": "sunrise_dawn",
        "time": "early morning sunrise, 6:00 AM",
        "desc": "soft pink and orange dawn light, delicate and ethereal, gentle side lighting, 3800K warm with pink undertones, fresh dewy atmosphere",
    },
    {
        "name": "candlelight",
        "time": "evening, indoor intimate setting",
        "desc": "warm flickering candlelight as primary source, deep warm shadows, intimate atmosphere, 1800K ultra-warm, dramatic chiaroscuro",
    },
    {
        "name": "studio_rembrandt",
        "time": "controlled studio environment",
        "desc": "classic Rembrandt lighting with 45-degree key light, characteristic triangle of light under eye on shadow side, 1:3 lighting ratio, dramatic and sculptural",
    },
    {
        "name": "window_light",
        "time": "daytime, near large window",
        "desc": "soft directional window light from one side, gentle gradient from light to shadow across face, natural and intimate, Vermeer-like quality",
    },
    {
        "name": "backlight_rim",
        "time": "late afternoon, strong backlight",
        "desc": "strong backlight creating glowing rim around subject, face in partial shadow, dramatic silhouette edge, lens flare possibility, ethereal mood",
    },
]

# Совместимость локаций и одежды (индексы)
LOCATION_OUTFIT_COMPAT = {
    # beach/pool/yacht → пляжная/casual одежда
    0: [2, 1, 9, 12, 16],
    1: [2, 3, 8, 12],
    8: [2, 1, 12, 19],
    # office/coworking → деловая/smart casual
    15: [0, 3, 5, 15, 17],
    # restaurant/hotel → элегантная
    16: [0, 3, 8, 11, 17],
    17: [0, 3, 8, 11, 15, 17],
}

# ─────────────────────────────────────────────
# Мета-промпт для Gemini
# ─────────────────────────────────────────────

PHOTOSHOOT_META_PROMPT = """You are an expert photography director creating a cohesive photoshoot of 10 images.

PHOTOSHOOT PARAMETERS:
- Location: {location}
- Photo style: {style_name}
- Camera: {camera}
- Camera settings: {settings}
- Visual look: {look}
- Lighting: {lighting_desc} ({lighting_time})
- Subject trigger word: MLVNK

POSES (one per image, in this order):
{poses_list}

OUTFITS (one per image, in this order):
{outfits_list}

ORIENTATIONS (per image):
{orientations_list}

RULES:
1. Generate exactly 10 prompts, one per line, separated by |||
2. Every prompt MUST start with "MLVNK, a man in his mid-30s with short dark brown hair, light stubble, green-blue eyes"
3. Every prompt MUST end with "solo man, only one person in the scene, no other people visible, anatomically correct hands with five fingers"
4. Each prompt should be 100-200 words, comma-separated continuous flow
5. Include the camera, settings, and visual look in every prompt
6. Keep the location and lighting consistent across all 10 but vary the exact position and angle
7. For portrait orientation images, describe vertical composition. For landscape, describe horizontal composition
8. Add unique environmental micro-details to each image (different foreground objects, background elements, atmospheric touches)
9. Do NOT use markdown, numbering, or any formatting — just raw prompts separated by |||
10. English only, no meta-commentary"""


# ─────────────────────────────────────────────
# Dataclass
# ─────────────────────────────────────────────

@dataclass
class PhotoshootConfig:
    """Конфигурация одной фотосессии."""
    location: str
    style: dict
    lighting: dict
    poses: List[str]
    outfits: List[str]
    orientations: List[str]  # "portrait" | "landscape"
    num_photos: int = 10


# ─────────────────────────────────────────────
# Генерация конфигурации
# ─────────────────────────────────────────────

def generate_photoshoot_config(num_photos: int = 10) -> PhotoshootConfig:
    """Создаёт рандомную конфигурацию фотосессии."""
    location = random.choice(LOCATIONS)
    style = random.choice(PHOTO_STYLES)
    lighting = random.choice(LIGHTING)

    # Выбираем num_photos разных поз
    poses = random.sample(POSES, min(num_photos, len(POSES)))

    # Выбираем одежду — для фотосессии используем 2-3 варианта, чередуя
    outfit_pool = random.sample(OUTFITS, min(3, len(OUTFITS)))
    outfits = [outfit_pool[i % len(outfit_pool)] for i in range(num_photos)]

    # Ориентации: ~60% portrait, ~40% landscape, перемешанные
    num_portrait = int(num_photos * 0.6)
    num_landscape = num_photos - num_portrait
    orientations = (["portrait_4_3"] * num_portrait +
                    ["landscape_4_3"] * num_landscape)
    random.shuffle(orientations)

    return PhotoshootConfig(
        location=location,
        style=style,
        lighting=lighting,
        poses=poses,
        outfits=outfits,
        orientations=orientations,
        num_photos=num_photos,
    )


# ─────────────────────────────────────────────
# Генерация промптов через Gemini
# ─────────────────────────────────────────────

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


async def generate_photoshoot_prompts(config: PhotoshootConfig) -> List[str]:
    """Генерирует 10 детальных промптов через Gemini за 1 запрос."""

    poses_str = "\n".join(
        f"Image {i+1}: {pose}" for i, pose in enumerate(config.poses)
    )
    outfits_str = "\n".join(
        f"Image {i+1}: {outfit}" for i, outfit in enumerate(config.outfits)
    )
    orientations_str = "\n".join(
        f"Image {i+1}: {'portrait (vertical)' if 'portrait' in o else 'landscape (horizontal)'}"
        for i, o in enumerate(config.orientations)
    )

    meta_prompt = PHOTOSHOOT_META_PROMPT.format(
        location=config.location,
        style_name=config.style["name"],
        camera=config.style["camera"],
        settings=config.style["settings"],
        look=config.style["look"],
        lighting_desc=config.lighting["desc"],
        lighting_time=config.lighting["time"],
        poses_list=poses_str,
        outfits_list=outfits_str,
        orientations_list=orientations_str,
    )

    logger.info(f"Генерация {config.num_photos} промптов через Gemini")

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            temperature=0.8,
            max_output_tokens=16384,
        ),
        contents=meta_prompt,
    )

    raw = response.text.strip()
    prompts = [p.strip() for p in raw.split("|||") if p.strip()]

    # Если Gemini вернул меньше промптов — дополняем дубликатами
    while len(prompts) < config.num_photos:
        prompts.append(prompts[-1])

    return prompts[:config.num_photos]


# ─────────────────────────────────────────────
# Генерация изображений через fal.ai
# ─────────────────────────────────────────────

async def generate_photoshoot_images(
    prompts: List[str],
    orientations: List[str],
    progress_callback=None,
) -> List[dict]:
    """
    Генерирует все изображения фотосессии с rate limiting.
    Батчами по 2 (concurrent limit fal.ai для нового аккаунта).
    """
    all_results = []
    batch_size = 2
    total = len(prompts)

    for i in range(0, total, batch_size):
        batch_prompts = prompts[i:i + batch_size]
        batch_orientations = orientations[i:i + batch_size]

        if progress_callback:
            await progress_callback(i, total)

        # Запускаем batch_size запросов параллельно
        tasks = []
        for p, o in zip(batch_prompts, batch_orientations):
            tasks.append(_generate_single(p, o))

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in batch_results:
            if isinstance(r, dict):
                all_results.append(r)
            elif isinstance(r, Exception):
                logger.error(f"Ошибка генерации в batch: {r}")

        # Пауза между батчами чтобы не упереться в лимит
        if i + batch_size < total:
            await asyncio.sleep(2)

    if progress_callback:
        await progress_callback(total, total)

    return all_results


async def _generate_single(prompt: str, orientation: str) -> dict:
    """Генерирует одно изображение."""
    loras = []
    if FAL_LORA_URL:
        loras.append({"path": FAL_LORA_URL, "scale": 1.0})

    arguments = {
        "prompt": prompt,
        "image_size": orientation,
        "num_images": 1,
        "num_inference_steps": 28,
        "guidance_scale": 3.0,
        "output_format": "jpeg",
        "enable_safety_checker": False,
        "loras": loras,
    }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: fal_client.subscribe(
            FAL_MODEL_ID,
            arguments=arguments,
            with_logs=True,
            on_queue_update=lambda u: None,
        ),
    )

    images = result.get("images", [])
    if images:
        return {"url": images[0]["url"], "orientation": orientation}
    raise RuntimeError("fal.ai вернул пустой результат")


# ─────────────────────────────────────────────
# Скачивание и сборка ZIP
# ─────────────────────────────────────────────

async def download_images(image_results: List[dict]) -> List[bytes]:
    """Скачивает все изображения по URL, возвращает байты."""
    loop = asyncio.get_event_loop()
    downloaded = []

    for i, img in enumerate(image_results):
        url = img["url"]
        try:
            data = await loop.run_in_executor(
                None,
                lambda u=url: requests.get(u, timeout=TIMEOUT).content,
            )
            downloaded.append(data)
            logger.info(f"Скачано изображение {i+1}/{len(image_results)}")
        except Exception as e:
            logger.error(f"Ошибка скачивания {url}: {e}")

    return downloaded


def build_zip(image_bytes_list: List[bytes], session_name: str) -> bytes:
    """Собирает ZIP-архив из списка изображений."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, data in enumerate(image_bytes_list, 1):
            zf.writestr(f"{session_name}/{session_name}_{i:02d}.jpg", data)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────
# Главный оркестратор
# ─────────────────────────────────────────────

async def run_photoshoot(
    num_photos: int = 10,
    progress_callback=None,
) -> dict:
    """
    Полный pipeline фотосессии:
    1. Генерация конфигурации
    2. Gemini → 10 промптов
    3. fal.ai → 10 изображений (батчами по 2)
    4. Скачивание + ZIP

    Returns:
        {
            "config": PhotoshootConfig,
            "image_bytes": [bytes, ...],
            "zip_bytes": bytes,
            "session_name": str,
            "theme": str,
        }
    """
    # 1. Конфигурация
    config = generate_photoshoot_config(num_photos)
    session_name = f"photoshoot_{config.style['name'].lower().replace(' ', '_')}"
    theme = f"{config.style['name']} | {config.location[:50]}"

    logger.info(f"Фотосессия: {theme}")

    if progress_callback:
        await progress_callback(-1, num_photos, "Генерация промптов...")

    # 2. Промпты через Gemini
    prompts = await generate_photoshoot_prompts(config)
    logger.info(f"Получено {len(prompts)} промптов")

    # 3. Генерация изображений
    async def img_progress(current, total):
        if progress_callback:
            await progress_callback(current, total, f"Генерация фото {current}/{total}...")

    image_results = await generate_photoshoot_images(
        prompts, config.orientations, progress_callback=img_progress
    )

    if not image_results:
        raise RuntimeError("Не удалось сгенерировать ни одного изображения")

    # 4. Скачивание
    if progress_callback:
        await progress_callback(-1, num_photos, "Скачивание изображений...")

    image_bytes = await download_images(image_results)

    # 5. ZIP
    zip_bytes = build_zip(image_bytes, session_name)

    return {
        "config": config,
        "image_bytes": image_bytes,
        "zip_bytes": zip_bytes,
        "session_name": session_name,
        "theme": theme,
    }
