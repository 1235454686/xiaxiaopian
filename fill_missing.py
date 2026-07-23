import urllib.request, json
from websocket import create_connection
from datetime import datetime

with urllib.request.urlopen('http://localhost:9223/json', timeout=10) as resp:
    pages = json.loads(resp.read())

ws_url = None
for p in pages:
    if p['type']=='page' and '主播汇总' in p.get('title',''):
        ws_url = p['webSocketDebuggerUrl']; break

ws = create_connection(ws_url, timeout=10, header={'Origin':'http://localhost:9223'})

now = datetime.now().strftime('%m/%d %H:%M')

# Write xyxx row 5, 雪. row 6
code = """(function(){
    var g = SpreadsheetApp.workbook.worksheetManager
        .getSheetBySheetId(SpreadsheetApp.workbook.activeSheetId).cellDataGrid;
    
    // xyxx today
    g.set(5, 0, {value: '07/03'}); g.set(5, 1, {value: 'xyxx'});
    g.set(5, 2, {value: '372'}); g.set(5, 10, {value: '""" + now + """'});
    
    // 雪. today
    g.set(6, 0, {value: '07/03'}); g.set(6, 1, {value: '雪.'});
    g.set(6, 2, {value: '206'}); g.set(6, 10, {value: '""" + now + """'});
    
    try{ SpreadsheetApp.view.sheetStatus._Fm._AXM.updateDocData(); } catch(e){}
    return 'ok';
})()"""

ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':code,'returnByValue':True}}))
resp = json.loads(ws.recv())
print('补写:', resp['result']['result']['value'])

# Reload to refresh canvas
ws.send(json.dumps({'id':2,'method':'Page.reload'}))
json.loads(ws.recv())
ws.close()
print('Done')
