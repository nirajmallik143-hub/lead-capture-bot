import http.server
import socketserver
import urllib.request
import json
import os

TELEGRAM_BOT_TOKEN = "8840603076:AAGQMONbsnWupYegm2dhzXYTkra3M_R7ICg"
TELEGRAM_CHAT_ID = "8798719105"

HTML_CONTENT = """<!DOCTYPE html>
<html>
<head>
    <title>Customer Inquiry</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #f4f4f4; }
        .form-box { background: white; padding: 20px; border-radius: 8px; max-width: 400px; margin: auto; }
        input, button { width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="form-box">
        <h2>Book a Service</h2>
        <input type="text" id="name" placeholder="Your Name">
        <input type="text" id="phone" placeholder="Phone Number">
        <input type="text" id="service" placeholder="Service Needed">
        <button onclick="sendLead()">Submit Inquiry</button>
        <p id="msg" style="color: green; font-weight: bold;"></p>
    </div>

    <script>
        function sendLead() {
            const data = {
                customer_name: document.getElementById('name').value,
                phone: document.getElementById('phone').value,
                service_requested: document.getElementById('service').value,
                timestamp: new Date().toLocaleString()
            };

            fetch('/submit-lead', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(result => {
                if(result.status === "success") {
                    document.getElementById('msg').innerText = "Inquiry sent! Saved to database & alert sent.";
                }
            });
        }
    </script>
</body>
</html>
"""

def send_telegram_alert(lead_data):
    message = (
        f"🚨 *NEW LEAD RECEIVED* 🚨\n\n"
        f"👤 *Name:* {lead_data.get('customer_name')}\n"
        f"📞 *Phone:* {lead_data.get('phone')}\n"
        f"🛠️ *Service:* {lead_data.get('service_requested')}\n"
        f"⏰ *Time:* {lead_data.get('timestamp')}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print("Telegram error:", e)

def save_to_firebase(lead_data):
    url = "https://clientleadautomation-default-rtdb.firebaseio.com/leads.json"
    payload = json.dumps(lead_data).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print("Firebase error:", e)

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode("utf-8"))

    def do_POST(self):
        if self.path == '/submit-lead':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            lead_data = json.loads(post_data.decode('utf-8'))
            
            save_to_firebase(lead_data)
            send_telegram_alert(lead_data)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))

PORT = int(os.environ.get("PORT", 8080))
with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    print(f"Server running on port {PORT}...")
    httpd.serve_forever()
