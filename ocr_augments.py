import cv2
try:
    import pytesseract
except Exception:
    pytesseract = None
import numpy as np
from PIL import Image
import shutil
import os
import tempfile

# Template/cropping defaults
GRID_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'grid_template.png')
# relative crop: left, top, width, height (fractions of image size)
RELATIVE_CROP = (0.55, 0.45, 0.35, 0.12)
TEMPLATE_MATCH_THRESHOLD = 0.6

if pytesseract is not None:
    # Try to locate tesseract executable on Windows if not on PATH
    if shutil.which('tesseract') is None:
        possible = [
            r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
            r'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe'
        ]
        for p in possible:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break

def preprocess_image_cv(img):
    # img: numpy array BGR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # increase contrast / apply blur
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    # adaptive threshold
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 11, 2)
    return th

def ocr_image_path(path, lang=None):
    """Run OCR on an image path and return list of text items with bounding boxes.

    Returns: {
      'text_items': [ {'text': str, 'conf': int, 'left': int, 'top': int, 'width': int, 'height': int}, ... ],
      'raw_text': str
    }
    """
    try:
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            # fallback to PIL
            pil = Image.open(path).convert('RGB')
            img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    except Exception:
        pil = Image.open(path).convert('RGB')
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    if pytesseract is None:
        raise RuntimeError('pytesseract package not installed in this Python environment')

    proc = preprocess_image_cv(img)

    # pytesseract expects RGB PIL image
    pil_proc = Image.fromarray(cv2.cvtColor(proc, cv2.COLOR_GRAY2RGB))

    config = r'--psm 6'
    if lang:
        raw = pytesseract.image_to_string(pil_proc, lang=lang, config=config)
    else:
        raw = pytesseract.image_to_string(pil_proc, config=config)

    data = pytesseract.image_to_data(pil_proc, output_type=pytesseract.Output.DICT, config=config)

    items = []
    n = len(data['text'])
    for i in range(n):
        txt = data['text'][i].strip()
        if not txt:
            continue
        try:
            conf = int(data['conf'][i])
        except Exception:
            conf = -1
        items.append({
            'text': txt,
            'conf': conf,
            'left': int(data['left'][i]),
            'top': int(data['top'][i]),
            'width': int(data['width'][i]),
            'height': int(data['height'][i])
        })

    return {
        'text_items': items,
        'raw_text': raw
    }


def ocr_image_array(img, lang=None):
    """Run OCR on an image provided as a BGR numpy array."""
    if pytesseract is None:
        raise RuntimeError('pytesseract package not installed in this Python environment')
    proc = preprocess_image_cv(img)
    pil_proc = Image.fromarray(cv2.cvtColor(proc, cv2.COLOR_GRAY2RGB))
    config = r'--psm 6'
    if lang:
        raw = pytesseract.image_to_string(pil_proc, lang=lang, config=config)
    else:
        raw = pytesseract.image_to_string(pil_proc, config=config)
    data = pytesseract.image_to_data(pil_proc, output_type=pytesseract.Output.DICT, config=config)
    items = []
    n = len(data['text'])
    for i in range(n):
        txt = data['text'][i].strip()
        if not txt:
            continue
        try:
            conf = int(data['conf'][i])
        except Exception:
            conf = -1
        items.append({
            'text': txt,
            'conf': conf,
            'left': int(data['left'][i]),
            'top': int(data['top'][i]),
            'width': int(data['width'][i]),
            'height': int(data['height'][i])
        })
    return {'text_items': items, 'raw_text': raw}


def find_template_in_image(img, template_path, threshold=TEMPLATE_MATCH_THRESHOLD):
    """Try to locate template in image. img is BGR numpy array. Returns (x,y,w,h) or None."""
    if not os.path.exists(template_path):
        return None
    tpl = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if tpl is None:
        try:
            tpl = cv2.cvtColor(np.array(Image.open(template_path).convert('RGB')), cv2.COLOR_RGB2BGR)
        except Exception:
            return None
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(img_gray, tpl_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        top_left = max_loc
        h, w = tpl_gray.shape
        return (top_left[0], top_left[1], w, h)
    return None


def crop_by_relative(img, rel_box):
    """Crop image by relative box (left, top, width, height) in fractions."""
    h, w = img.shape[:2]
    l = int(rel_box[0] * w)
    t = int(rel_box[1] * h)
    ww = int(rel_box[2] * w)
    hh = int(rel_box[3] * h)
    # clamp
    l = max(0, min(l, w-1))
    t = max(0, min(t, h-1))
    ww = max(1, min(ww, w - l))
    hh = max(1, min(hh, h - t))
    return img[t:t+hh, l:l+ww]


def extract_grid_cells_from_items(items, expected_cols=6, y_tolerance=12):
    """Group OCR items by approximate row (y coordinate) and return first row's texts sorted by x.

    items: list of {'text','conf','left','top','width','height'}
    Returns: list of cell texts (length <= expected_cols)
    """
    if not items:
        return []
    # compute center y
    for it in items:
        it['cy'] = it['top'] + it['height'] / 2
        it['cx'] = it['left'] + it['width'] / 2

    # group by y using simple clustering: build rows dict keyed by rounded cy
    rows = []
    for it in sorted(items, key=lambda x: x['cy']):
        placed = False
        for row in rows:
            if abs(row['cy'] - it['cy']) <= y_tolerance:
                row['items'].append(it)
                # update row cy average
                row['cy'] = (row['cy'] * (len(row['items'])-1) + it['cy']) / len(row['items'])
                placed = True
                break
        if not placed:
            rows.append({'cy': it['cy'], 'items': [it]})

    # pick the row with the most items (likely the augments row)
    rows.sort(key=lambda r: len(r['items']), reverse=True)
    if not rows:
        return []
    best = rows[0]['items']
    # sort by cx and take expected_cols
    best_sorted = sorted(best, key=lambda x: x['cx'])
    texts = [x['text'] for x in best_sorted][:expected_cols]
    # pad with empty strings if fewer than expected
    while len(texts) < expected_cols:
        texts.append("")
    return texts


def process_folder_for_augments(folder_path, expected_cols=6):
    """Process all image files in folder_path and return detected grid texts per image.

    Returns: { filename: { 'cells': [...], 'raw_text': str } }
    """
    import os
    out = {}
    if not os.path.isdir(folder_path):
        return out
    for fn in sorted(os.listdir(folder_path)):
        if not fn.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            continue
        full = os.path.join(folder_path, fn)
        try:
            # load full image as BGR
            img = cv2.imdecode(np.fromfile(full, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                pil = Image.open(full).convert('RGB')
                img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

            # try template matching first
            tpl_rect = find_template_in_image(img, GRID_TEMPLATE_PATH)
            if tpl_rect:
                x, y, w_box, h_box = tpl_rect
                crop = img[y:y+h_box, x:x+w_box]
            else:
                # use relative crop fallback
                crop = crop_by_relative(img, RELATIVE_CROP)

            res = ocr_image_array(crop)
            cells = extract_grid_cells_from_items(res.get('text_items', []), expected_cols=expected_cols)
            out[fn] = {'cells': cells, 'raw_text': res.get('raw_text', '')}
        except Exception as e:
            out[fn] = {'error': str(e)}
    return out

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python ocr_augments.py <image_path>')
        sys.exit(1)
    out = ocr_image_path(sys.argv[1])
    print('Raw text:\n', out['raw_text'])
    print('Items:')
    for it in out['text_items']:
        print(it)
