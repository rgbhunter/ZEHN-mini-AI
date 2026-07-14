import subprocess
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# Start bot in a background process
subprocess.Popen(["python", "main.py"])

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"<h1>ZEHN mini Bot is running!</h1><p>Bu server botni Render'da bepul va o'chmasdan ishlashi uchun ochilgan.</p>")

def run_server():
    # Render o'z portini beradi, agar yo'q bo'lsa 8080 ishlatamiz
    port = int(os.environ.get('PORT', 8080))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Starting web server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
