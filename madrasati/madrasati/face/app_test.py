from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
import websockets
import json
import asyncio

app = FastAPI()

# WebSocket URL for Node.js backend
WEBSOCKET_URL = "ws://localhost:3001/ws"

# HTML form for sending fake attendance data
@app.get("/", response_class=HTMLResponse)
async def get_form():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fake Attendance Sender</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 20px auto; }
            form { display: flex; flex-direction: column; gap: 10px; }
            input, button { padding: 10px; font-size: 16px; }
            button { background-color: #4CAF50; color: white; border: none; cursor: pointer; }
            button:hover { background-color: #45a049; }
            #status { color: green; }
            #error { color: red; }
        </style>
    </head>
    <body>
        <h1>Fake Attendance Sender</h1>
        <form action="/send-attendance" method="post">
            <label for="studentId">Student Matricule:</label>
            <input type="text" id="studentId" name="studentId" required placeholder="e.g., S001">
            <label for="timestamp">Timestamp (YYYY-MM-DD HH:MM):</label>
            <input type="text" id="timestamp" name="timestamp" required placeholder="e.g., 2025-08-08 14:30">
            <button type="submit">Send Attendance</button>
        </form>
        <p id="status"></p>
        <p id="error"></p>
        <script>
            async function sendAttendance(event) {
                event.preventDefault();
                const studentId = document.getElementById('studentId').value;
                const timestamp = document.getElementById('timestamp').value;
                const status = document.getElementById('status');
                const error = document.getElementById('error');
                status.textContent = '';
                error.textContent = '';

                try {
                    const response = await fetch('/send-attendance', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: new URLSearchParams({ studentId, timestamp })
                    });
                    const result = await response.json();
                    if (response.ok) {
                        status.textContent = result.message;
                    } else {
                        error.textContent = result.error;
                    }
                } catch (err) {
                    error.textContent = 'Error: ' + err.message;
                }
            }
            document.querySelector('form').addEventListener('submit', sendAttendance);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

# Send attendance data via WebSocket
@app.post("/send-attendance")
async def send_attendance(studentId: str = Form(...), timestamp: str = Form(...)):
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            await websocket.send(json.dumps({"studentId": studentId, "timestamp": timestamp}))
            response = await websocket.recv()
            return json.loads(response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WebSocket error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
