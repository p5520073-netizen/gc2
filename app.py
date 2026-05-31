from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import secrets
import json
import uvicorn

app = FastAPI()
rooms = {}

html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Ghost Chat</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            background: #000;
            color: #0f0;
            font-family: monospace;
            padding: 20px;
            width: 100%;
            overflow-x: auto;
        }
        
        button, input {
            background: #111;
            border: 1px solid #0f0;
            color: #0f0;
            padding: 10px;
            margin: 5px;
            cursor: pointer;
            font-family: monospace;
        }
        
        #chat {
            display: none;
        }
        
        #messages {
            border: 1px solid #0f0;
            height: 300px;
            overflow-x: auto;
            overflow-y: auto;
            margin: 10px 0;
            padding: 10px;
            word-wrap: break-word;
            word-break: break-all;
            white-space: normal;
        }
        
        .message {
            margin: 5px 0;
            padding: 5px;
            border-bottom: 1px solid #0f033;
            word-wrap: break-word;
            word-break: break-word;
            white-space: normal;
            overflow-wrap: break-word;
        }
        
        .input-area {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 5px;
        }
        
        #msg {
            flex: 3;
            min-width: 150px;
            padding: 10px;
        }
        
        .input-area button {
            flex: 1;
            min-width: 80px;
        }
        
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }
            .input-area {
                flex-direction: column;
            }
            #msg {
                width: 100%;
            }
            .input-area button {
                width: 100%;
            }
        }
    </style>
</head>
<body>
<div id="menu">
    <h2>GHOST CHAT - Zero Trace</h2>
    <button onclick="create()">+ BUAT ROOM BARU</button><br><br>
    <input id="code" placeholder="KODE ROOM" style="width:200px">
    <button onclick="join()">MASUK ROOM</button>
</div>
<div id="chat">
    <div>ROOM: <b id="roomCode"></b></div>
    <div id="messages"></div>
    <div class="input-area">
        <input id="msg" placeholder="Tulis pesan...">
        <button onclick="send()">KIRIM</button>
        <button onclick="leave()">KELUAR & HAPUS</button>
    </div>
</div>
<script>
let ws=null,roomCode=null;
function create(){fetch('/create').then(r=>r.json()).then(d=>{roomCode=d.code;connect()})}
function join(){let c=document.getElementById('code').value.toUpperCase();if(c){roomCode=c;connect()}}
function connect(){
    let protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws=new WebSocket(`${protocol}//${location.host}/ws/${roomCode}`);
    ws.onmessage=e=>{
        let d=JSON.parse(e.data);
        if(d.type=='msg'){
            let messagesDiv = document.getElementById('messages');
            let msgDiv = document.createElement('div');
            msgDiv.className = 'message';
            msgDiv.innerHTML = '> ' + d.msg;
            messagesDiv.appendChild(msgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    };
    ws.onopen=()=>{
        document.getElementById('menu').style.display='none';
        document.getElementById('chat').style.display='block';
        document.getElementById('roomCode').innerText=roomCode;
        document.getElementById('messages').innerHTML = '';
    };
    ws.onclose=()=>{
        alert('Room closed or disconnected');
        location.reload();
    };
}
function send(){
    let i=document.getElementById('msg');
    if(i.value&&ws&&ws.readyState===WebSocket.OPEN){
        ws.send(JSON.stringify({type:'msg',content:i.value}));
        i.value='';
        i.focus();
    }
}
function leave(){
    if(ws) ws.close();
    fetch(`/wipe/${roomCode}`,{method:'DELETE'}).finally(()=>location.reload());
}
</script>
</body>
</html>
"""

@app.get("/")
async def home():
    return HTMLResponse(html)

@app.get("/create")
async def create_room():
    code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ0123456789') for _ in range(6))
    rooms[code] = {"clients": []}
    return {"code": code}

@app.websocket("/ws/{code}")
async def ws_endpoint(ws: WebSocket, code: str):
    await ws.accept()
    if code not in rooms:
        await ws.close()
        return
    rooms[code]["clients"].append(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg['type'] == 'msg':
                for c in rooms[code]["clients"]:
                    await c.send_json({"type": "msg", "msg": msg['content']})
    except:
        if code in rooms:
            rooms[code]["clients"].remove(ws)
            if len(rooms[code]["clients"]) == 0:
                del rooms[code]

@app.delete("/wipe/{code}")
async def wipe(code: str):
    if code in rooms:
        del rooms[code]
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)