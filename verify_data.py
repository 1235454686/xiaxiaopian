import urllib.request, json
from websocket import create_connection

with urllib.request.urlopen('http://localhost:9223/json', timeout=10) as resp:
    pages = json.loads(resp.read())

ws_url = None
for p in pages:
    if p['type']=='page' and '主播汇总' in p.get('title',''):
        ws_url = p['webSocketDebuggerUrl']; break

ws = create_connection(ws_url, timeout=10, header={'Origin':'http://localhost:9223'})

code = """(function(){
    var g = SpreadsheetApp.workbook.worksheetManager
        .getSheetBySheetId(SpreadsheetApp.workbook.activeSheetId).cellDataGrid;
    var rows = [];
    for(var i=0; i<10; i++){
        var row = [];
        for(var j=0; j<5; j++){
            var c = g.get(i,j);
            var v = '';
            if(c){
                if(typeof c === 'object' && c.value !== undefined) v = String(c.value);
                else if(typeof c === 'string') v = c;
            }
            row.push(v);
        }
        rows.push(i + ':' + row.join('|'));
    }
    return rows.join('\\n');
})()"""

ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':code,'returnByValue':True}}))
resp = json.loads(ws.recv())
val = resp.get('result',{}).get('result',{}).get('value')
if val: print(val)
else: print('ERR:', json.dumps(resp.get('result',{}), ensure_ascii=False)[:300])
ws.close()
