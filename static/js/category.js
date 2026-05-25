let currentPage = 1;
let currentGenre = 'Action'; // 初始分类

// 核心请求函数：同时处理分类切换和分页切换
async function fetchData(genre, page) {
    try {
        const response = await axios.get('/category/', {
            params: { genre: genre, page: page },
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        });

        const data = response.data;

        // 1. 更新电影列表
        const movieGrid = document.getElementById('movieGrid');
        movieGrid.innerHTML = data.movies.map(movie => `
            <div class="movie-card">
                <img src="${movie.poster_url}" alt="${movie.title}">
                <p style="text-align:center; padding:5px; font-size:12px;">${movie.title}</p>
            </div>
        `).join('');

        // 2. 更新分页按钮状态
        currentPage = data.current_page;
        document.getElementById('pageInfo').innerText = `第 ${data.current_page} / ${data.total_pages} 页`;
        document.getElementById('prevBtn').disabled = !data.has_previous;
        document.getElementById('nextBtn').disabled = !data.has_next;

    } catch (error) {
        console.error('加载失败:', error);
    }
}

// 分页点击事件
function changePage(action) {
    let targetPage = action === 'next' ? currentPage + 1 : currentPage - 1;
    fetchData(currentGenre, targetPage);
}
// 给所有 genre-item 绑定点击事件
document.querySelectorAll('.genre-item').forEach(item => {
  item.addEventListener('click', async function() {
    const genre = this.dataset.genre;

    // 1. 立即改变侧边栏颜色（UI反馈）
    document.querySelectorAll('.genre-item').forEach(li => li.style.color = 'white');
    this.style.color = 'red';

    try {
      // 2. 发送请求，注意添加 X-Requested-With 请求头
      const response = await axios.get('/category/', {
        params: { genre: genre },
        headers: {'X-Requested-With': 'XMLHttpRequest'}
      });

      const movies = response.data.movies;
      const movieGrid = document.getElementById('movieGrid');

      // 3. 清空旧电影，填充新电影
      movieGrid.innerHTML = '';

      movies.forEach(movie => {
        const card = `
          <div class="movie-card">
            <img src="${movie.poster_url}" alt="${movie.title}">
            <p style="text-align:center; padding:5px;">${movie.title}</p>
          </div>
        `;
        movieGrid.insertAdjacentHTML('beforeend', card);
      });

      console.log(`已切换至: ${response.data.current_genre}`);
    } catch (error) {
      console.error('加载失败:', error);
    }
  });
});
// 分类点击事件
document.querySelectorAll('.genre-item').forEach(item => {
    item.addEventListener('click', function() {
        // 样式切换
        document.querySelectorAll('.genre-item').forEach(li => li.style.color = 'white');
        this.style.color = 'red';

        // 数据请求：切换分类时重置为第1页
        currentGenre = this.dataset.genre;
        fetchData(currentGenre, 1);
    });
});