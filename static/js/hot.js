async function loadHot(sort="rating") {
    const res = await fetch(`/api/hot/?sort=${sort}`);
    const movies = await res.json();

    document.getElementById("hotList").innerHTML =
        movies.map(m => `
        <div class="movie-card">
            <img src="${m.poster}">
            <div class="movie-info">
                <h3>${m.title}</h3>
                <p>⭐ ${m.rating}</p>
            </div>
        </div>
    `).join("");
}

window.onload = function() {
    loadHot();
}