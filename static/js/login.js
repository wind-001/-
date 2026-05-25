let mode = "login";

function switchTab(type) {
    mode = type;

    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    event.target.classList.add("active");

    if (type === "register") {
        document.getElementById("email").classList.remove("hidden");
    } else {
        document.getElementById("email").classList.add("hidden");
    }
}

function submitForm() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    if (mode === "login") {
        alert("登录：" + username);
    } else {
        const email = document.getElementById("email").value;
        alert("注册：" + username + " " + email);
    }

    // 后期接 Django API
}
