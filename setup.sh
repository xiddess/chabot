#!/bin/bash

echo "📦 Membuat virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "⬇️ Menginstal requirements..."
pip install -r requirements.txt

echo "✅ Setup selesai. Menjalankan aplikasi
python3 app.py