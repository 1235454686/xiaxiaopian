"""终极填表：API写全量数据 + keyboard导航触发渲染"""
import urllib.request, json, time, ctypes, keyboard
from websocket import create_connection
from ctypes import wintypes
from datetime import datetime

# ====== API Write ======
with urllib.request.urlopen('http://localhost:9223/json', timeout=10) as resp:
    pages = json.loads(resp.read())

ws_url = None
for p in pages:
    if p['type']=='page' and '主播汇总' in p.get('title',''): ws_url = p['webSocketDebuggerUrl']; break

ws = create_connection(ws_url, timeout=10, header={'Origin':'http://localhost:9223'})
now = datetime.now().strftime('%m/%d %H:%M')

code = """(function(){
    var g = SpreadsheetApp.workbook.worksheetManager
        .getSheetBySheetId(SpreadsheetApp.workbook.activeSheetId).cellDataGrid;
    
    // Clear
    for(var r=0; r<20; r++) for(var c=0; c<11; c++) g.set(r, c, {value: ''});
    
    // Headers
    var h = ['日期','主播','今日音浪','直播时长','今日涨粉','曝光人数','观看人数','打赏人数','评论人数','点赞次数','更新时间'];
    for(var c=0; c<h.length; c++) g.set(0, c, {value: h[c]});
    
    // Data
    var d = [
        ['07/02','冷冷♡','9,240','6.07h','+4','1,806','492','9','','','07/02 22:30'],
        ['07/02','雪.','244','1.49h','+0','948','66','3','','','07/02 22:30'],
        ['07/02','xyxx','219','1.59h','+2','2,484','90','6','','','07/02 22:30'],
        ['07/03','冷冷♡','1.6万','5小时','','','','','','','""" + now + """'],
        ['07/03','xyxx','372','','','','','','','','""" + now + """'],
        ['07/03','雪.','206','','','','','','','','""" + now + """'],
    ];
    for(var i=0; i<d.length; i++)
        for(var j=0; j<d[i].length; j++)
            if(d[i][j]) g.set(i+1, j, {value: d[i][j]});
    
    return JSON.stringify({rows: d.length});
})()"""

ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':code,'returnByValue':True}}))
resp = json.loads(ws.recv())
val = resp.get('result',{}).get('result',{}).get('value')
print('API write:', val)
ws.close()

# ====== Keyboard navigation ======
user32 = ctypes.windll.user32
hwnd = None
def cb(h, _):
    global hwnd
    if user32.IsWindowVisible(h):
        l = user32.GetWindowTextLengthW(h)
        if l > 0:
            b = ctypes.create_unicode_buffer(l+1)
            user32.GetWindowTextW(h, b, l+1)
            if '主播汇总' in b.value: hwnd = h; return False
    return True
user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(cb), 0)

if hwnd:
    user32.SetForegroundWindow(hwnd); time.sleep(0.3)
    rect = wintypes.RECT(); user32.GetWindowRect(hwnd, ctypes.byref(rect))
    
    # Click A1
    ctypes.windll.user32.SetCursorPos(rect.left+260, rect.top+210); time.sleep(0.1)
    user32.mouse_event(0x0002,0,0,0,0); time.sleep(0.05)
    user32.mouse_event(0x0004,0,0,0,0); time.sleep(0.3)
    
    # Navigate down through all rows (forces render)
    for i in range(7):
        keyboard.press_and_release('down'); time.sleep(0.1)
    for i in range(7):
        keyboard.press_and_release('up'); time.sleep(0.1)
    
    keyboard.press_and_release('ctrl+s')
    print('Navigated + Ctrl+S')
else:
    print('Window not found')
