import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

# Start bot in a background process
subprocess.Popen(["python", "main.py"])

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"<h1>ZEHN mini Bot is running!</h1><p>Bu oyna faqat serverni faol ushlab turish uchun ochilgan. Bot bemalol Telegramda ishlayveradi.</p>")

def run_server():
    server_address = ('0.0.0.0', 7860)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print("Starting dummy web server on port 7860")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
