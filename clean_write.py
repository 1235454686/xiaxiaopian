import urllib.request, json
from websocket import create_connection
from datetime import datetime

with urllib.request.urlopen('http://localhost:9223/json', timeout=10) as resp:
    pages = json.loads(resp.read())

ws_url = None
for p in pages:
    if p['type']=='page' and '主播汇总' in p.get('title',''): ws_url = p['webSocketDebuggerUrl']; break

ws = create_connection(ws_url, timeout=10, header={'Origin':'http://localhost:9223'})
now = datetime.now().strftime('%m/%d %H:%M')

code = """(function(){
    var g = SpreadsheetApp.workbook.worksheetManager.getSheetBySheetId(SpreadsheetApp.workbook.activeSheetId).cellDataGrid;
    for(var r=0; r<100; r++) for(var c=0; c<20; c++) g.set(r, c, {value: ''});
    var h = ['日期','主播','今日音浪','直播时长','今日涨粉','曝光人数','观看人数','打赏人数','评论人数','点赞次数','更新时间'];
    for(var c=0; c<h.length; c++) g.set(0, c, {value: h[c]});
    var d = [
        ['07/02','冷冷♡','9,240','6.07h','+4','1,806','492','9','','','07/02 22:30'],
        ['07/02','雪.','244','1.49h','+0','948','66','3','','','07/02 22:30'],
        ['07/02','xyxx','219','1.59h','+2','2,484','90','6','','','07/02 22:30'],
        ['07/03','冷冷♡','1.6万','5小时','','','','','','','""" + now + """'],
        ['07/03','xyxx','372','','','','','','','','""" + now + """'],
        ['07/03','雪.','206','','','','','','','','""" + now + """'],
    ];
    for(var i=0; i<d.length; i++) for(var j=0; j<d[i].length; j++) if(d[i][j]) g.set(i+1, j, {value: d[i][j]});
    return 'ok';
})()"""

ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':code,'returnByValue':True}}))
resp = json.loads(ws.recv())
print('Result:', resp['result']['result']['value'])
ws.close()
