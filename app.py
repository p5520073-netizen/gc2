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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Ghost Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #000;
            color: #0f0;
            font-family: monospace;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            width: 100%;
            max-width: 350px;
            margin: 0 auto;
            text-align: center;
        }
        button, input {
            background: #111;
            border: 1px solid #0f0;
            color: #0f0;
            padding: 12px;
            margin: 10px 0;
            cursor: pointer;
            font-family: monospace;
            font-size: 14px;
            width: 100%;
        }
        button:active { background: #0f0; color: #000; }
        #chat { display: none; }
        #messages {
            border: 1px solid #0f0;
            height: 50vh;
            overflow-y: auto;
            margin: 15px 0;
            padding: 10px;
            text-align: left;
            word-wrap: break-word;
        }
        .message {
            margin: 5px 0;
            padding: 5px 0;
            border-bottom: 1px solid #0f033;
        }
        h1 { font-size: 1.5rem; margin-bottom: 5px; }
        .sub { margin-bottom: 20px; font-size: 0.7rem; }
        .or { margin: 5px 0; font-size: 0.7rem; }
        .warning { font-size: 0.6rem; margin-top: 20px; }
        .ghost { font-size: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>
<div class="container">
    <div id="menu">
        <div class="ghost">
        .-""-.<br>
       .'     '.<br>
      /   .--.   \\<br>
     :   :##:    :<br>
     |   :##:    |<br>
     :   '--'    ;<br>
      \\   ::::  /<br>
       '.____.'<br>
        </div>
        <h1>GHOST CHAT</h1>
        <div class="sub">ZERO TRACE. EPHEMERAL COMMS.</div>
        <button onclick="createRoom()">> INITIALIZE ROOM</button>
        <div class="or">OR CONNECT</div>
        <div class="enter-label">ENTER 6-CHAR CODE</div>
        <input type="text" id="joinCode" placeholder="______" maxlength="6" style="text-transform:uppercase; text-align:center; letter-spacing:4px;">
        <button onclick="joinRoom()">ACCESS ROOM</button>
        <div class="warning">WARNING: ALL DATA DESTROYED UPON EXIT.</div>
    </div>
    <div id="chat">
        <div class="ghost">
        .-""-.<br>
       .'     '.<br>
      /   .--.   \\<br>
     :   :##:    :<br>
     |   :##:    |<br>
     :   '--'    ;<br>
      \\   ::::  /<br>
       '.____.'<br>
        </div>
        <h1>GHOST CHAT</h1>
        <div class="room-header">ROOM: <b id="roomCodeDisplay"></b></div>
        <div id="messages"></div>
        <input type="text" id="msgInput" placeholder="TYPE MESSAGE...">
        <button onclick="sendMessage()">SEND</button>
        <button onclick="leaveRoom()" style="border-color:#ff4444; color:#ff4444;">WIPE & EXIT</button>
    </div>
</div>
<script>
let ws = null;
let currentRoomCode = null;

function createRoom() {
    fetch('/create')
        .then(r => r.json())
        .then(data => {
            currentRoomCode = data.code;
            connectWebSocket();
        });
}

function joinRoom() {
    let code = document.getElementById('joinCode').value.toUpperCase().trim();
    if (code.length === 6) {
        currentRoomCode = code;
        connectWebSocket();
    } else {
        alert('ENTER 6-CHAR CODE');
    }
}

function connectWebSocket() {
    let protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/${currentRoomCode}`);
    
    ws.onopen = function() {
        document.getElementById('menu').style.display = 'none';
        document.getElementById('chat').style.display = 'block';
        document.getElementById('roomCodeDisplay').innerText = currentRoomCode;
        document.getElementById('messages').innerHTML = '';
    };
    
    ws.onmessage = function(e) {
        let data = JSON.parse(e.data);
        if (data.type === 'msg') {
            let msgDiv = document.createElement('div');
            msgDiv.className = 'message';
            msgDiv.innerHTML = '> ' + data.msg;
            document.getElementById('messages').appendChild(msgDiv);
            msgBox.scrollTop = msgBox.scrollHeight;
        }
    };
    
    ws.onclose = function() {
        alert('ROOM CLOSED');
        location.reload();
    };
}

function sendMessage() {
    let input = document.getElementById('msgInput');
    if (input.value.trim() && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type: 'msg', content: input.value}));
        input.value = '';
        input.focus();
    }
}

function leaveRoom() {
    if (ws) ws.close();
    fetch(`/wipe/${currentRoomCode}`, {method: 'DELETE'})
        .finally(() => location.reload());
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
            if msg.get('type') == 'msg':
                for client in rooms[code]["clients"]:
                    await client.send_json({"type": "msg", "msg": msg['content']})
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
