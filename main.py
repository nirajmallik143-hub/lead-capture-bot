import http.server
import socketserver
import urllib.request
import json
import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-4.7")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quick Service Booking</title>
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: #eef2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 15px; }
        .card { background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.1); width: 100%; max-width: 420px; }
        .card h2 { margin-top: 0; color: #1e293b; text-align: center; font-size: 24px; }
        .card p { color: #64748b; font-size: 14px; text-align: center; margin-bottom: 20px; }
        label { font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 5px; display: block; }
        input, select { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 15px; outline: none; transition: border 0.2s; }
        input:focus, select:focus { border-color: #2563eb; }
        button { width: 100%; padding: 14px; background: #2563eb; color: #ffffff; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #1d4ed8; }
        .status-msg { display: none; margin-top: 15px; padding: 12px; border-radius: 8px; background: #dcfce7; color: #166534; font-size: 14px; text-align: center; font-weight: 600; }
        .wa-btn { display: none; margin-top: 10px; width: 100%; padding: 12px; background: #25d366; color: white; border-radius: 8px; text-decoration: none; text-align: center; font-weight: 600; box-sizing: border-box; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Book a Service</h2>
        <p>Fill out the form below for immediate dispatch.</p>
        
        <label>Full Name</label>
        <input type="text" id="name" placeholder="John Doe">
        
        <label>Phone Number</label>
        <input type="tel" id="phone" placeholder="+971 50 123 4567">
        
        <label>Service Required</label>
        <select id="service">
            <option value="AC Maintenance & Repair">AC Maintenance & Repair</option>
            <option value="Plumbing Service">Plumbing Service</option>
            <option value="Electrical Repair">Electrical Repair</option>
            <option value="Deep Cleaning">Deep Cleaning</option>
            <option value="General Inspection">General Inspection</option>
        </select>
        
        <button onclick="sendLead()">Submit Request</button>
        
        <div id="msg" class="status-msg">Inquiry submitted successfully!</div>
        <a id="wa" href="#" target="_blank" class="wa-btn">💬 Chat directly on WhatsApp</a>
    </div>

    <script>
        function sendLead() {
            const name = document.getElementById('name').value;
            const phone = document.getElementById('phone').value;
            const service = document.getElementById('service').value;

            if(!name || !phone) {
                alert("Please fill in both Name and Phone number.");
                return;
            }

            const data = {
                customer_name: name,
                phone: phone,
                service_requested: service,
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
                    document.getElementById('msg').style.display = "block";
                    const waBtn = document.getElementById('wa');
                    waBtn.href = "https://wa.me/" + phone.replace(/[^0-9]/g, '');
                    waBtn.style.display = "block";
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
    if lead_data.get("ai_follow_up_note"):
        message += f"\n\n🤖 *Suggested follow-up:* {lead_data['ai_follow_up_note']}"
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram alert skipped: Telegram credentials are not configured.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("Telegram error:", type(e).__name__)

def generate_grok_follow_up_note(lead_data):
    if not GROK_API_KEY:
        return None

    service = str(lead_data.get("service_requested", "service"))[:200]
    payload = json.dumps({
        "model": GROK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Write one concise, professional follow-up note for a home-services lead. Do not invent facts or claim a booking is confirmed.",
            },
            {
                "role": "user",
                "content": f"The customer requested: {service}",
            },
        ],
        "max_tokens": 100,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        GROK_API_URL,
        data=payload,
        headers={
            "Authorization": "Bearer " + GROK_API_KEY,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        note = result["choices"][0]["message"]["content"]
        return note.strip()[:500] if isinstance(note, str) and note.strip() else None
    except Exception as e:
        print("Grok error:", type(e).__name__)
        return None

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

            follow_up_note = generate_grok_follow_up_note(lead_data)
            if follow_up_note:
                lead_data["ai_follow_up_note"] = follow_up_note

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
    
