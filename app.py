"""
AI-Generated Image Detector - Web Server
Ultra-clean, lightweight server connecting the frontend, trained model, and database.
"""

import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import random
import sys
import tempfile
import webbrowser

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils import load_config
from src.predict import DetectorPredictor
from src.add_images import get_current_counts

HOST = "127.0.0.1"
PORT = 5000

# 1. Connect to Config and Database
config = load_config("config.yaml")
db_counts = get_current_counts("database")
total_db_images = sum(db_counts[s][c] for s in db_counts for c in db_counts[s])
print(f"[DATABASE] Connected to database: {total_db_images:,} images across train/valid/test.")

# 2. Connect to Trained Model Checkpoint
weights_path = config["paths"].get("best_model_path", "models/best_model.pth")
try:
    predictor = DetectorPredictor(config=config, weights_path=weights_path)
    print(f"[MODEL] Connected to trained model: {weights_path}")
except Exception as e:
    print(f"[MODEL] Warning: Could not load model ({e})")
    predictor = None


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Serve Frontend and static assets
        if self.path == "/" or self.path == "/index.html":
            html_path = os.path.join(os.path.dirname(__file__), "index.html")
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
            return

        # Serve CSS and JS files
        if self.path.endswith((".css", ".js")):
            filename = self.path.lstrip('/')
            file_path = os.path.join(os.path.dirname(__file__), filename)
            if not os.path.isfile(file_path):
                self.send_response(404)
                self.end_headers()
                return
            with open(file_path, "rb") as f:
                content = f.read()
            mime_type = "text/css" if filename.endswith('.css') else "application/javascript"
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.end_headers()
            self.wfile.write(content)
            return

        # API: Database & Server Stats
        elif self.path == "/api/stats":
            self._send_json({
                "status": "online",
                "model": config["model"].get("backbone", "ResNet50"),
                "database": {
                    "train": db_counts.get("train", {}),
                    "valid": db_counts.get("valid", {}),
                    "test": db_counts.get("test", {}),
                    "total_images": total_db_images,
                }
            })

        # API: Fetch Sample Image from Database
        elif self.path.startswith("/api/sample"):
            cls_type = "REAL" if "type=real" in self.path else "FAKE"
            folder = os.path.join("database", "test", cls_type)
            if not os.path.exists(folder):
                folder = os.path.join("database", "train", cls_type)

            files = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".png", ".webp"))]
            if not files:
                self._send_json({"error": "No sample images in database"}, status=404)
                return

            sample_file = os.path.join(folder, random.choice(files))
            with open(sample_file, "rb") as img_f:
                b64_data = base64.b64encode(img_f.read()).decode("utf-8")

            self._send_json({
                "filename": os.path.basename(sample_file),
                "type": cls_type,
                "image_b64": f"data:image/jpeg;base64,{b64_data}"
            })

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # API: Predict Image
        if self.path == "/api/predict":
            if predictor is None:
                self._send_json({"error": "Model not loaded. Train the model first."}, status=500)
                return

            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)

            tmp_path = None
            try:
                content_type = self.headers.get("Content-Type", "")

                # Handle multipart/form-data
                if "multipart/form-data" in content_type:
                    boundary = content_type.split("boundary=")[1].strip()
                    parts = body.split(f"--{boundary}".encode())
                    img_bytes = None
                    for part in parts:
                        if b"name=\"image_b64\"" in part and b"\r\n\r\n" in part:
                            _, data = part.split(b"\r\n\r\n", 1)
                            raw_b64 = data.rstrip(b"\r\n--").decode("utf-8").split(",")[-1]
                            img_bytes = base64.b64decode(raw_b64)
                            break
                        elif b"filename=" in part and b"\r\n\r\n" in part:
                            _, data = part.split(b"\r\n\r\n", 1)
                            img_bytes = data.rstrip(b"\r\n--")
                            break
                else:
                    img_bytes = body

                if not img_bytes:
                    raise ValueError("No image received in request.")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(img_bytes)
                    tmp_path = tmp.name

                result = predictor.predict(tmp_path)
                self._send_json(result)

            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        # Compact access log
        print(f"[HTTP] {args[0]} {args[1]}")


def main():
    server = HTTPServer((HOST, PORT), RequestHandler)
    url = f"http://{HOST}:{PORT}"
    print("\n" + "=" * 55)
    print(f" 🚀 AI Image Detector Web App Connected & Live")
    print(f" 🔗 URL: {url}")
    print(f" 📁 Database Images: {total_db_images:,}")
    print("=" * 55 + "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped.")


if __name__ == "__main__":
    main()
