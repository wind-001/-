document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('movieGrid');
    const btns = document.querySelectorAll('.sort-btn');

    btns.forEach(btn => {
        btn.addEventListener('click', function() {
            btns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            const type = this.getAttribute('data-type'); // 'year' 或 'rating'
            const cards = Array.from(grid.querySelectorAll('.card-wrapper'));

           cards.sort((a, b) => {
                const valA = parseFloat(a.querySelector('.movie-card').dataset[type]) || 0;
                const valB = parseFloat(b.querySelector('.movie-card').dataset[type]) || 0;
                return valB - valA;
            });

            // 清空并重新按顺序添加
            cards.forEach(card => grid.appendChild(card));
        });
    });
});

function searchMovie() {
    const searchText = document.getElementById('searchInput').value.trim();
    console.log(searchText);
    if (searchText) {
        // 可扩展：提交搜索请求到Django后端
        window.location.href = `/search/${searchText}/`;
    } else {
        alert("请输入要搜索的电影名称");
    }
      // 阻止按钮默认提交表单导致页面刷新（可选，但推荐加上）
    return false;
}