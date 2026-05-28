"""
HTML → PNG 렌더
- 1순위: Playwright (Windows/Mac/Linux, GTK 의존성 없음)
- 2순위: weasyprint (Linux, fallback)
"""
import sys, os, subprocess, glob
from pathlib import Path
from PIL import Image, ImageChops

OUTPUT_DIR = Path(__file__).resolve().parent


def _trim_and_resize(img, target_width=1080):
    bg_color = img.getpixel((0, 0))
    bg = Image.new(img.mode, img.size, bg_color)
    bbox = ImageChops.difference(img, bg).getbbox()
    if bbox:
        pad = 24
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(img.width, bbox[2] + pad)
        bottom = min(img.height, bbox[3] + pad)
        img = img.crop((left, top, right, bottom))
    if img.width != target_width:
        ratio = target_width / img.width
        img = img.resize((target_width, int(img.height * ratio)), Image.LANCZOS)
    return img


def _try_playwright(html_path, png_path, target_width):
    from playwright.sync_api import sync_playwright
    html_path = Path(html_path).resolve()
    png_path = Path(png_path)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={'width': target_width, 'height': 800},
            device_scale_factor=2,
        )
        page = ctx.new_page()
        page.goto(f'file:///{html_path.as_posix()}')
        page.wait_for_load_state('networkidle')
        height = page.evaluate('Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)')
        page.set_viewport_size({'width': target_width, 'height': int(height) + 40})
        png_bytes = page.screenshot(full_page=True, type='png')
        browser.close()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(png_bytes)
    img = Image.open(png_path).convert('RGB')
    img = _trim_and_resize(img, target_width)
    img.save(str(png_path), 'PNG', optimize=True)
    return png_path


def _try_weasyprint(html_path, png_path, target_width):
    import time
    from weasyprint import HTML
    html_path = Path(html_path).resolve()
    png_path = Path(png_path)
    ts = str(int(time.time() * 1000))
    pdf_path = OUTPUT_DIR / f"_tmp_{html_path.stem}_{ts}.pdf"
    tmp_prefix = OUTPUT_DIR / f"_tmp_{html_path.stem}_{ts}_p"
    HTML(str(html_path)).write_pdf(str(pdf_path))
    for old in glob.glob(f"{tmp_prefix}-*.png"):
        try: os.remove(old)
        except: pass
    subprocess.run(['pdftoppm', '-r', '144', '-png', str(pdf_path), str(tmp_prefix)], check=True)
    pngs = sorted(glob.glob(f"{tmp_prefix}-*.png"))
    imgs = [Image.open(p).convert('RGB') for p in pngs]
    if len(imgs) == 1:
        img = imgs[0]
    else:
        w = max(i.width for i in imgs)
        h = sum(i.height for i in imgs)
        img = Image.new('RGB', (w, h), 'white')
        y = 0
        for im in imgs:
            img.paste(im, (0, y)); y += im.height
    img = _trim_and_resize(img, target_width)
    img.save(str(png_path), 'PNG', optimize=True)
    return png_path


def html_to_png(html_path, png_path, target_width=1080):
    """HTML → PNG. Playwright 우선, 실패 시 weasyprint fallback"""
    try:
        result = _try_playwright(html_path, png_path, target_width)
        print(f"saved (playwright): {result}")
        return result
    except Exception as e:
        print(f"[Playwright 실패: {e}]")
        try:
            result = _try_weasyprint(html_path, png_path, target_width)
            print(f"saved (weasyprint): {result}")
            return result
        except Exception as e2:
            print(f"[weasyprint도 실패: {e2}]")
            raise


if __name__ == '__main__':
    html = sys.argv[1] if len(sys.argv) > 1 else str(OUTPUT_DIR / 'preview_이길범.html')
    out = sys.argv[2] if len(sys.argv) > 2 else str(OUTPUT_DIR / 'preview_test.png')
    html_to_png(html, out)
