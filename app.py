from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import openai
import os

# ========== INIT ==========
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

openai.api_key = os.getenv("OPENAI_API_KEY")


# ========== MODELS ==========

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    messages = db.relationship('ChatMessage', backref='user', lazy=True)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_text = db.Column(db.Text, nullable=False)
    bot_reply = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

# ========== ROLE PROMPTS ==========

role_prompts = {
    "default": {
        "prompt": "Kamu adalah asisten yang ramah.",
        "label": "🤖 Asisten Ramah"
    },
    "guru": {
        "prompt": "Kamu adalah seorang guru yang sabar dan suka menjelaskan konsep dengan jelas.",
        "label": "📘 Guru"
    },
    "dokter": {
        "prompt": "Kamu adalah seorang dokter profesional yang memberikan saran medis umum (bukan diagnosis).",
        "label": "🩺 Dokter"
    },
    "teman": {
        "prompt": "Kamu adalah teman akrab yang mendengarkan dan mendukung.",
        "label": "🧑‍🤝‍🧑 Teman"
    },
    "ahli_it": {
        "prompt": "Kamu adalah pakar IT yang menjawab pertanyaan teknis dengan detail.",
        "label": "💻 Ahli IT"
    }
}

# ========== LOGIN MANAGER ==========

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== ROUTES ==========

@app.route("/")
@login_required
def index():
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    return render_template("chat/index.html", history=chat_history, role_prompts=role_prompts)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email sudah terdaftar.")
            return redirect(url_for("register"))
        hashed_pw = generate_password_hash(password)
        new_user = User(email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Pendaftaran berhasil. Silakan login.")
        return redirect(url_for("login"))
    return render_template("login/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session["role"] = "default"
            return redirect(url_for("index"))
        flash("Email atau password salah.")
        return redirect(url_for("login"))
    return render_template("login/login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "Pesan kosong!"}), 400

    try:
        role = session.get("role", "default")
        system_prompt = role_prompts.get(role, role_prompts["default"])["prompt"]

        # Riwayat dari DB
        previous_messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
        messages = [{"role": "system", "content": system_prompt}]
        for msg in previous_messages:
            messages.append({"role": "user", "content": msg.user_text})
            messages.append({"role": "assistant", "content": msg.bot_reply})

        messages.append({"role": "user", "content": user_message})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # atau "gpt-3.5-turbo"
            messages=messages
        )

        bot_reply = response.choices[0].message["content"].strip()

        # Simpan ke database
        new_msg = ChatMessage(user_id=current_user.id, user_text=user_message, bot_reply=bot_reply)
        db.session.add(new_msg)
        db.session.commit()

        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/set-role", methods=["POST"])
@login_required
def set_role():
    selected_role = request.form.get("role")
    if selected_role in role_prompts:
        session["role"] = selected_role
    return redirect(url_for("index"))

@app.route("/download")
@login_required
def download_history():
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp).all()
    lines = []
    for msg in messages:
        ts = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"[{ts}] Kamu: {msg.user_text}")
        lines.append(f"[{ts}] Bot : {msg.bot_reply}")
        lines.append("")
    file_content = "\n".join(lines)
    return Response(
        file_content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=chat_history.txt"}
    )

if __name__ == "__main__":
    app.run(debug=True)
