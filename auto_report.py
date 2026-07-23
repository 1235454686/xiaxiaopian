"""
马伶薯 - 自动采集 v5
动态查找空行追加，同天同人覆盖
"""
import urllib.request, json, time, sys
from datetime import datetime
from websocket import create_connection

EDGE_PORT, TDOC_PORT = 9222, 9223
HEADERS = ['日期','主播','今日音浪','直播时长','今日涨粉','曝光人数','观看人数','打赏人数','评论人数','点赞次数','更新时间']

def get_ws(port, filt):
    try:
        with urllib.request.urlopen(f'http://localhost:{port}/json', timeout=10) as resp:
            pages = json.loads(resp.read())
        for p in pages:
            if p['type']=='page' and filt in p.get('url',''): return p['webSocketDebuggerUrl']
    except: pass
    return None

def cdp(ws, expr):
    ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':expr,'returnByValue':True}}))
    return json.loads(ws.recv()).get('result',{}).get('result',{}).get('value')

print(f'=== 马伶薯 {datetime.now().strftime("%m/%d %H:%M")} ===')

# ====== 数据采集 ======
ws_url = get_ws(EDGE_PORT, 'union.bytedance.com')
if not ws_url: print('Edge未运行'); sys.exit(1)
ws = create_connection(ws_url, timeout=30, header={'Origin':f'http://localhost:{EDGE_PORT}'})

cdp(ws, "window.location.href='https://union.bytedance.com/open/portal/index?appId=3000'")
time.sleep(5)

dash = cdp(ws, """(function(){var t=document.body.innerText;var idx=t.indexOf('主播今日音浪');if(idx<0)return'[]';var s=t.substring(idx,idx+1000);var lines=s.split('\\n');var r=[];for(var i=0;i<lines.length-1;i++){if(/^\\d+$/.test(lines[i].trim())&&parseInt(lines[i])<=50){var name=lines[i+1].trim();var yl=lines[i+2].trim();if(name&&name.length>=2&&!/^\\d+$/.test(name)&&name.indexOf('积分')<0&&name.indexOf('得分')<0&&name.indexOf('违规')<0&&name.indexOf('跟进')<0&&name.indexOf('审批')<0&&name.indexOf('变更')<0&&name!=='/'&&/^[\\d.,]+万?$/.test(yl)){r.push({name:name,yinlang:yl});i+=2}}}return JSON.stringify(r)})()""")
today_data = json.loads(dash) if dash else []
print(f'今日开播: {[(d["name"],d["yinlang"]) for d in today_data]}')

# 点列表补时长
if today_data:
    cdp(ws, """var a=document.querySelectorAll('*');for(var i=0;i<a.length;i++){if(a[i].textContent.trim()==='主播列表'&&a[i].children.length<=2&&a[i].offsetParent!==null){var r=a[i].getBoundingClientRect();if(r.x<300){a[i].click();break;}}}""")
    time.sleep(4)
    known = [d['name'] for d in today_data]
    list_js = """(function(){var t=document.body.innerText;var hosts=""" + json.dumps(known) + """;var r={};for(var h=0;h<hosts.length;h++){var n=hosts[h],idx=t.indexOf(n);if(idx<0)continue;var dur=(t.substring(idx,idx+300).match(/(\\d[\\d,.]*分钟|\\d[\\d.]*小时)/)||[''])[0];r[n]={duration:dur}}return JSON.stringify(r)})()"""
    detail = json.loads(cdp(ws, list_js)) if cdp(ws, list_js) else {}
else:
    detail = {}
ws.close()

if not today_data: print('无人开播'); sys.exit(0)

# ====== 填表：找空行 + 同天覆盖 ======
ws2_url = get_ws(TDOC_PORT, '主播汇总')
if not ws2_url:
    # try title match
    with urllib.request.urlopen(f'http://localhost:{TDOC_PORT}/json', timeout=10) as resp:
        for p in json.loads(resp.read()):
            if p['type']=='page' and '主播汇总' in p.get('title',''): 
                ws2_url = p['webSocketDebuggerUrl']; break
if not ws2_url: print('腾讯文档未运行'); sys.exit(1)
ws2 = create_connection(ws2_url, timeout=10, header={'Origin':f'http://localhost:{TDOC_PORT}'})

today = datetime.now().strftime('%m/%d')
now_time = datetime.now().strftime('%m/%d %H:%M')

# 读取现有数据，找最后一行和今天已有的行
month_no_zero = str(int(today.split('/')[0]))
day_no_zero = str(int(today.split('/')[1]))
alt_date = f'{month_no_zero}月{day_no_zero}日'
scan_js = f"""(function(){{
    var g = SpreadsheetApp.workbook.worksheetManager
        .getSheetBySheetId(SpreadsheetApp.workbook.activeSheetId).cellDataGrid;
    var lastRow = 0;
    var todayRows = {{}};
    var patterns = ['{today}', '{today.replace("/","月")}日', '{alt_date}'];
    
    for(var r = 1; r < 1000; r++){{
        var dateCell = g.get(r, 0);
        var nameCell = g.get(r, 1);
        var dateVal = String((dateCell && dateCell.value) || (typeof dateCell === 'string' ? dateCell : ''));
        var nameVal = String((nameCell && nameCell.value) || (typeof nameCell === 'string' ? nameCell : ''));
        
        if(!dateVal && !nameVal) break;
        lastRow = r;
        
        var isToday = false;
        for(var p=0; p<patterns.length; p++){{
            if(dateVal.indexOf(patterns[p]) >= 0){{ isToday = true; break; }}
        }}
        if(isToday){{ todayRows[nameVal] = r; }}
    }}
    
    return JSON.stringify({{lastRow: lastRow, todayRows: todayRows}});
}})()"""

scan_result = json.loads(cdp(ws2, scan_js))
last_row = scan_result['lastRow']
today_rows = scan_result['todayRows']
print(f'已有 {last_row} 行数据，今日已写: {list(today_rows.keys())}')

# 构建写入数据
results = []
for d in today_data:
    results.append({
        'name': d['name'],
        'yinlang': d['yinlang'],
        'duration': detail.get(d['name'], {}).get('duration', ''),
    })

# 写入
updated = 0
added = 0
for d in results:
    name = d['name']
    row_data = [today, name, d['yinlang'], d['duration'], '', '', '', '', '', '', now_time]
    
    if name in today_rows:
        target_row = today_rows[name]
        updated += 1
    else:
        last_row += 1
        target_row = last_row
        added += 1
    
    # Write each cell
    for c, val in enumerate(row_data):
        if val:
            write_js = f"""(function(){{
                var g = SpreadsheetApp.workbook.worksheetManager
                    .getSheetBySheetId(SpreadsheetApp.workbook.activeSheetId).cellDataGrid;
                g.set({target_row}, {c}, {{value: {json.dumps(val)}}});
                return 'ok';
            }})()"""
            cdp(ws2, write_js)
    
    # Mark that this name now has a row
    today_rows[name] = target_row

ws2.close()

# 写本地备份
backup_path = r'C:\Users\小念\Desktop\Hermes\直播数据.txt'
with open(backup_path, 'w', encoding='utf-8') as f:
    f.write(f'马伶薯公会 - 直播数据汇总\n更新: {now_time}\n{"="*40}\n\n')
    f.write(f'{today}:\n')
    for d in results:
        f.write(f'  {d["name"]:<6} 音浪 {d["yinlang"]:<8} 时长 {d["duration"]:<8}\n')

print(f'✅ 更新 {updated} 人，新增 {added} 人')
print(f'数据: {[(d["name"], d["yinlang"]) for d in results]}')
