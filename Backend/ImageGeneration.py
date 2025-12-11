import asyncio
from random import randint
from PIL import Image
import requests
from dotenv import load_dotenv, get_key
import os
from time import sleep
from huggingface_hub import InferenceClient
import io

# ======================
# CONFIG & CONSTANTS
# ======================

load_dotenv()

HF_TOKEN = get_key('.env', 'HuggingFaceAPIKey')
if not HF_TOKEN:
    raise RuntimeError("HuggingFaceAPIKey not found in .env")

# Choose a model that supports Inference Providers for text-to-image
# See HF docs: FLUX.1-dev / FLUX.1-Krea-dev, etc. 
MODEL_ID = "black-forest-labs/FLUX.1-dev"

# Let HF choose/route providers for you (or set provider="hf-inference" / "fal-ai")
client = InferenceClient(
    api_key=HF_TOKEN,
    provider="auto",   # or "hf-inference", "fal-ai", etc.
)

DATA_FOLDER = "Data"
IMAGE_GEN_FILE = os.path.join("Frontend", "Files", "ImageGeneration.data")


# ======================
# IMAGE DISPLAY
# ======================

def open_images(prompt: str):
    """Open up to 4 images based on the prompt name."""
    folder_path = DATA_FOLDER
    safe_prompt = prompt.replace(" ", "_")
    files = [f"{safe_prompt}{i}.jpg" for i in range(1, 5)]

    for jpg_file in files:
        image_path = os.path.join(folder_path, jpg_file)
        if not os.path.exists(image_path):
            print(f"File does not exist: {image_path}")
            continue
        try:
            img = Image.open(image_path)
            print(f"Opening image: {image_path}")
            img.show()
            sleep(1)
        except IOError:
            print(f"Unable to open {image_path}")


# ======================
# HUGGING FACE REQUEST
# ======================

async def query(prompt: str) -> bytes:
    """
    Run text-to-image for a single prompt and return raw image bytes.
    This is executed in a thread so it doesn't block asyncio.
    """
    def _run():
        # output is a PIL.Image object according to HF docs 
        img = client.text_to_image(
            prompt,
            model=MODEL_ID,
            # You can also pass extra params:
            # guidance_scale=7.5,
            # num_inference_steps=30,
            # negative_prompt="ugly, distorted",
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")  # or "JPEG"
        return buf.getvalue()

    return await asyncio.to_thread(_run)


async def generate_images(prompt: str) -> bool:
    tasks = []
    safe_prompt = prompt.replace(" ", "_")

    os.makedirs(DATA_FOLDER, exist_ok=True)

    for _ in range(4):
        full_prompt = (
            f"{prompt}, quality 4K, sharpness maximum, Ultra High details, high resolution, "
            f"seed {randint(0, 1_000_000)}"
        )
        tasks.append(asyncio.create_task(query(full_prompt)))

    try:
        image_bytes_list = await asyncio.gather(*tasks)
    except Exception as e:
        print("Failed to generate images:", repr(e))
        return False

    for i, image_bytes in enumerate(image_bytes_list, start=1):
        filename = os.path.join(DATA_FOLDER, f"{safe_prompt}{i}.jpg")
        with open(filename, "wb") as f:
            f.write(image_bytes)

    print("Images generated and saved.")
    return True


# --------- THIS is the wrapper you were missing ---------
def generate_and_open(prompt: str):
    """Sync wrapper: run the async generator, then open images."""
    success = asyncio.run(generate_images(prompt))
    if success:
        open_images(prompt)
    else:
        print("Skipping opening images because generation failed.")
# --------------------------------------------------------


# ======================
# MAIN LOOP
# ======================

def main_loop():
    print(f"Watching for image generation requests in: {IMAGE_GEN_FILE}")

    while True:
        try:
            with open(IMAGE_GEN_FILE, "r") as f:
                data: str = f.read().strip()

            if not data:
                sleep(1)
                continue

            try:
                prompt, status = [x.strip() for x in data.split(",", 1)]
            except ValueError:
                print(f"Invalid data format in {IMAGE_GEN_FILE}: {data!r}")
                sleep(1)
                continue

            if status.lower() == "true":
                print("Generating Images ...")
                # ✅ call the sync wrapper, NOT the coroutine directly
                generate_and_open(prompt=prompt)

                with open(IMAGE_GEN_FILE, "w") as f:
                    f.write(f"{prompt},False")

                break  # or 'continue' if you want it to keep watching
            else:
                sleep(1)

        except FileNotFoundError:
            print(f"{IMAGE_GEN_FILE} not found. Waiting...")
            sleep(2)
        except Exception as e:
            print("Error in main loop:", repr(e))
            try:
                with open(IMAGE_GEN_FILE, "w") as f:
                    f.write(f"{prompt},False")
            except Exception:
                pass
            sleep(2)


if __name__ == "__main__":
    main_loop()
