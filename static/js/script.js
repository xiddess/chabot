async function sendMessage() {
    const messageInput = document.getElementById("message");
    const chatbox = document.getElementById("chatbox");
    const userMessage = messageInput.value.trim();
    if (!userMessage) return;

    // Tampilkan pesan pengguna langsung
    chatbox.innerHTML += `<div class="user"><strong>Kamu:</strong> ${userMessage}</div>`;
    messageInput.value = "";
    messageInput.focus();

    // Kirim ke server
    const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage })
    });

    const data = await response.json();

    // Tampilkan respons
    if (data.reply) {
        chatbox.innerHTML += `<div class="bot"><strong>Bot:</strong> ${data.reply}</div>`;
    } else {
        chatbox.innerHTML += `<div class="bot"><strong>Bot:</strong> Terjadi kesalahan.</div>`;
    }

    // Scroll ke bawah
    chatbox.scrollTop = chatbox.scrollHeight;
}
