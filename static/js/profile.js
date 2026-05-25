async function loadProfile() {
    const info = await fetch("/api/user/info/").then(r => r.json());
    document.getElementById("userInfo").innerHTML =
        `<h2>${info.username}</h2>
         <p>NFC标签ID: ${info.nfc_id}</p>`;
}

async function loadRecommend() {
    const data = await fetch("/api/user/recommend/").then(r => r.json());
    document.getElementById("recommendList").innerHTML =
        data.map(m => `<div class="movie-card"><img src="${m.poster}"></div>`).join("");
}

async function loadFavorites() {
    const data = await fetch("/api/user/favorites/").then(r => r.json());
    document.getElementById("favoriteList").innerHTML =
        data.map(m => `<div class="movie-card"><img src="${m.poster}"></div>`).join("");
}

async function loadHistory() {
    const data = await fetch("/api/user/history/").then(r => r.json());
    document.getElementById("historyList").innerHTML =
        data.map(h => `<p>${h.title} ⭐${h.rating}</p>`).join("");
}

window.onload = function() {
    loadProfile();
    loadRecommend();
    loadFavorites();
    loadHistory();
}