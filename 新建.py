"""
腾讯文档桌面版 - 一键新建（完整四步）
用法：python 新建.py [类型]
  类型: 表格(默认) 文档 幻灯片 PDF 收集表 智能文档 智能表格 思维导图 流程图 智能白板

四步流程：
  ① 激活桌面页
  ② JS点击「新建」→ 打开下拉菜单
  ③ JS事件+CDP点击类型按钮 → 打开模板面板(iframe)
  ④ 在iframe中CDP点击「空白XX」→ 创建新文档
"""
import json, time, subprocess, sys
from websocket import create_connection

CDP_PORT = 9223
ORIGIN = f"http://localhost:{CDP_PORT}"
TYPES = ['表格','文档','幻灯片','PDF','收集表','智能文档','智能表格','思维导图','流程图','智能白板']


def pages():
    r = subprocess.run(['curl','-s',f'http://localhost:{CDP_PORT}/json'], capture_output=True, text=True)
    return json.loads(r.stdout)


def desktop_ws():
    for p in pages():
        if p['type']=='page' and 'desktop' in p.get('url',''):
            return p['webSocketDebuggerUrl']


def main():
    t = sys.argv[1] if len(sys.argv)>1 else '表格'
    if t not in TYPES:
        print(f"❌ {t} 不支持，可选: {', '.join(TYPES)}"); return

    ws_url = desktop_ws()
    if not ws_url:
        print("❌ 未找到腾讯文档桌面页，请先打开腾讯文档"); return

    ws = create_connection(ws_url, timeout=10, header={"Origin": ORIGIN})
    before = {p['id'] for p in pages() if p['type']=='page'}

    # ① 激活桌面页
    print("① 激活桌面页...")
    ws.send(json.dumps({"id":0,"method":"Page.navigate",
        "params":{"url":"https://docs.qq.com/desktop"}}))
    json.loads(ws.recv())
    time.sleep(1)

    # ② 点击「新建」
    print(f"② 点击「新建」...")
    ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{
        "expression":"document.querySelectorAll('button').forEach(b=>{if(b.textContent.trim()==='新建')b.click()})",
        "returnByValue":True}}))
    json.loads(ws.recv())
    time.sleep(0.8)

    # ③ 在新建下拉菜单中点击目标类型（JS事件 + CDP双点）
    print(f"③ 点击「{t}」...")
    ws.send(json.dumps({"id":2,"method":"Runtime.evaluate","params":{
        "expression":f"""
        (function(){{
            const dd=document.querySelector('.rc-dropdown');
            if(!dd)return'NO_DROPDOWN';
            for(let el of dd.querySelectorAll('button')){{
                if(el.textContent.trim()==='{t}'){{
                    el.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,cancelable:true,view:window}}));
                    el.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,cancelable:true,view:window}}));
                    el.dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true,view:window}}));
                    el.click();
                    const r=el.getBoundingClientRect();
                    return JSON.stringify({{x:r.left+r.width/2,y:r.top+r.height/2}});
                }}
            }}
            return'NOT_FOUND';
        }})()
        """,
        "returnByValue":True}}))
    raw = json.loads(ws.recv()).get('result',{}).get('result',{}).get('value','null')
    if raw in ('NO_DROPDOWN', 'NOT_FOUND', 'null'):
        print(f"❌ 未找到「{t}」按钮（下拉菜单可能未弹出）"); ws.close(); return
    pos = json.loads(raw)

    ws.send(json.dumps({"id":3,"method":"Input.dispatchMouseEvent",
        "params":{"type":"mousePressed","x":pos['x'],"y":pos['y'],"button":"left","clickCount":1}}))
    json.loads(ws.recv())
    time.sleep(0.05)
    ws.send(json.dumps({"id":4,"method":"Input.dispatchMouseEvent",
        "params":{"type":"mouseReleased","x":pos['x'],"y":pos['y'],"button":"left","clickCount":1}}))
    json.loads(ws.recv())
    time.sleep(1)

    # ④ 在模板面板 iframe 中点击「空白XX」
    # 先检查模板面板是否出现（有些类型如"表格"会跳过面板直接创建，有些如"文档"会先创建empty_edit再显示面板）
    ws.send(json.dumps({"id":5,"method":"Runtime.evaluate","params":{
        "expression":"document.querySelector('iframe[src*=\"mall/panel\"]') ? 'EXISTS' : 'NO_IFRAME'",
        "returnByValue":True}}))
    has_panel = json.loads(ws.recv()).get('result',{}).get('result',{}).get('value','NO_IFRAME')
    
    if has_panel == 'NO_IFRAME':
        # 无模板面板，说明已自动创建
        ws.close()
        after_final = {p['id'] for p in pages() if p['type']=='page'}
        new_ids = after_final - before
        if new_ids:
            for p in pages():
                if p['id'] in new_ids:
                    print(f"✅ 空白{t}已创建\n   {p['url']}")
        else:
            print("⚠️ 未检测到新页面，请检查腾讯文档窗口")
        return

    print(f"④ 点击「空白{t}」...")
    ws.send(json.dumps({"id":6,"method":"Runtime.evaluate","params":{
        "expression":f"""
        (function(){{
            var iframe = document.querySelector('iframe[src*=\"mall/panel\"]');
            if(!iframe) return 'NO_IFRAME';
            var doc = iframe.contentDocument || iframe.contentWindow.document;
            if(!doc) return 'NO_DOC';
            
            // 找包含「空白{t}」的可点击元素
            var candidates = [];
            doc.querySelectorAll('*').forEach(function(el){{
                var txt = el.textContent.trim();
                if(txt.includes('空白') && txt.includes('{t}') && el.offsetParent !== null){{
                    var r = el.getBoundingClientRect();
                    candidates.push({{
                        tag: el.tagName,
                        text: txt.substring(0,40),
                        x: r.left + r.width/2,
                        y: r.top + r.height/2,
                        w: r.width,
                        h: r.height
                    }});
                }}
            }});
            
            if(candidates.length === 0) return 'NOT_FOUND';
            
            // 选最小的（最精确的）元素
            candidates.sort((a,b)=>a.w*a.h - b.w*b.h);
            var target = candidates[0];
            
            // JS点击
            doc.querySelectorAll('*').forEach(function(el){{
                var txt = el.textContent.trim();
                if(txt.includes('空白') && txt.includes('{t}') && el.offsetParent !== null){{
                    el.dispatchEvent(new MouseEvent('mousedown',{{bubbles:true,cancelable:true,view:window}}));
                    el.dispatchEvent(new MouseEvent('mouseup',{{bubbles:true,cancelable:true,view:window}}));
                    el.dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true,view:window}}));
                    el.click();
                }}
            }});
            
            return JSON.stringify({{x:target.x, y:target.y, text:target.text}});
        }})()
        """,
        "returnByValue":True}}))
    raw4 = json.loads(ws.recv()).get('result',{}).get('result',{}).get('value','NO_IFRAME')

    if raw4 == 'NO_IFRAME':
        print("⚠️ 未找到模板面板（表格可能已自动创建，跳过④）")
    elif raw4 == 'NO_DOC':
        print("❌ 无法访问iframe内容"); ws.close(); return
    elif raw4 == 'NOT_FOUND':
        print(f"❌ 模板面板中未找到「空白{t}」"); ws.close(); return
    else:
        pos4 = json.loads(raw4)
        print(f"   找到「{pos4['text']}」({pos4['x']:.0f},{pos4['y']:.0f})")
        ws.send(json.dumps({"id":8,"method":"Input.dispatchMouseEvent",
            "params":{"type":"mousePressed","x":pos4['x'],"y":pos4['y'],"button":"left","clickCount":1}}))
        json.loads(ws.recv())
        time.sleep(0.05)
        ws.send(json.dumps({"id":9,"method":"Input.dispatchMouseEvent",
            "params":{"type":"mouseReleased","x":pos4['x'],"y":pos4['y'],"button":"left","clickCount":1}}))
        json.loads(ws.recv())

    ws.close()
    time.sleep(2)

    # 检测结果
    after = {p['id'] for p in pages() if p['type']=='page'}
    new_ids = after - before
    if new_ids:
        for p in pages():
            if p['id'] in new_ids:
                print(f"✅ 空白{t}已创建\n   {p['url']}")
    else:
        print("⚠️ 未检测到新页面，请检查腾讯文档窗口")


if __name__=='__main__':
    main()
