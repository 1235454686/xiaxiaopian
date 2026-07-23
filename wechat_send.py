"""微信发消息 v2 - 先验证联系人再发"""
import ctypes, time, pyperclip, keyboard, sys
from ctypes import wintypes
from PIL import ImageGrab
import easyocr, numpy as np

user32 = ctypes.windll.user32

contact = sys.argv[1] if len(sys.argv) > 1 else '妹妹'
message = sys.argv[2] if len(sys.argv) > 2 else '干嘛呢'

# Find WeChat
hwnd = None
def cb(h, _):
    global hwnd
    if user32.IsWindowVisible(h):
        l = user32.GetWindowTextLengthW(h)
        if l > 0:
            b = ctypes.create_unicode_buffer(l+1)
            user32.GetWindowTextW(h, b, l+1)
            if '微信' in b.value: hwnd = h; return False
    return True
user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(cb), 0)
if not hwnd: print('微信未运行'); sys.exit(1)

user32.ShowWindow(hwnd, 9); time.sleep(0.3)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

rect = wintypes.RECT(); user32.GetWindowRect(hwnd, ctypes.byref(rect))
w, h_win = rect.right - rect.left, rect.bottom - rect.top

def ocr():
    img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    reader = easyocr.Reader(['ch_sim'], gpu=False)
    return reader.readtext(np.array(img.convert('RGB')))

def click(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y)); time.sleep(0.05)
    user32.mouse_event(0x0002,0,0,0,0); time.sleep(0.03)
    user32.mouse_event(0x0004,0,0,0,0); time.sleep(0.2)

# 1. Find and click search box
results = ocr()
search_pos = None
for (bbox, text, conf) in results:
    if conf > 0.5 and '搜索' in text:
        x1, y1 = bbox[0]; x2, y2 = bbox[2]
        search_pos = (rect.left + (x1+x2)/2, rect.top + (y1+y2)/2)
        break
if not search_pos:
    search_pos = (rect.left + w*0.3, rect.top + h_win*0.06)

click(*search_pos)
time.sleep(0.3)

# 2. Clear search box and paste contact name
keyboard.press_and_release('ctrl+a')
time.sleep(0.1)
pyperclip.copy(contact); time.sleep(0.1)
keyboard.press_and_release('ctrl+v')
time.sleep(3)  # 等搜索结果加载

# 3. OCR verify the correct contact appears
results2 = ocr()
found_correct = False
contact_click_pos = None
for (bbox, text, conf) in results2:
    if contact in text and conf > 0.5:
        x1, y1 = bbox[0]; x2, y2 = bbox[2]
        contact_click_pos = (rect.left + (x1+x2)/2, rect.top + (y1+y2)/2)
        found_correct = True
        print(f'找到: \"{text}\" conf={conf:.2f}')
        break

if not found_correct:
    print(f'未找到联系人「{contact}」，请检查')
    sys.exit(1)

# 4. Click the correct contact
click(*contact_click_pos)
time.sleep(0.8)

# 5. Click input area and send
input_x = rect.left + w // 2
input_y = rect.top + int(h_win * 0.88)
click(input_x, input_y)
time.sleep(0.3)

pyperclip.copy(message); time.sleep(0.1)
keyboard.press_and_release('ctrl+v')
time.sleep(0.3)
keyboard.press_and_release('enter')
time.sleep(0.5)

# 6. Final verify
results3 = ocr()
h = h_win
sent = False
for (bbox, text, conf) in results3:
    y = (bbox[0][1] + bbox[2][1]) / 2
    if message[:2] in text and conf > 0.4 and 0.3*h < y < 0.85*h:
        print(f'✅ 已发送: [{conf:.2f}] \"{text}\"')
        sent = True
print(f'发送成功: {sent}')
