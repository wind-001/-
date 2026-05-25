// 1. 模拟后端返回的电影数据 (JSON格式)
const mockMovieData = {
    id: 101,
    title: "星际穿越 (Interstellar)",
    rating: 9.3,
    year: "2014",
    duration: "2小时 49分钟",
    genre: "科幻 / 冒险",
    // 这里使用网络图作为背景和海报
    poster: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500&auto=format&fit=crop&q=60", 
    backdrop: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1600&auto=format&fit=crop&q=80",
    description: "在不远的未来，地球气候已经不适合粮食生长，水资源枯竭，人类面临灭绝。一组探险者利用他们发现的一个虫洞，进行了一次超越人类限制的太空旅行，试图为人类寻找新的家园。",
    cast: [
        { name: "马修·麦康纳", role: "Cooper", img: "https://randomuser.me/api/portraits/men/32.jpg" },
        { name: "安妮·海瑟薇", role: "Brand", img: "https://randomuser.me/api/portraits/women/44.jpg" },
        { name: "杰西卡·查斯坦", role: "Murph", img: "https://randomuser.me/api/portraits/women/65.jpg" },
        { name: "迈克尔·凯恩", role: "Prof. Brand", img: "https://randomuser.me/api/portraits/men/85.jpg" },
        { name: "马特·达蒙", role: "Mann", img: "https://randomuser.me/api/portraits/men/22.jpg" }
    ]
};

// 2. 页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    renderMovieInfo(mockMovieData);
    setupEventListeners();
});

// 3. 渲染电影信息的函数
function renderMovieInfo(movie) {
    // 设置背景图
    const heroBg = document.getElementById('hero-bg');
    heroBg.style.backgroundImage = `url('${movie.backdrop}')`;

    // 填充文本信息
    document.getElementById('movie-poster').src = movie.poster;
    document.getElementById('movie-title').textContent = movie.title;
    document.getElementById('movie-rating').textContent = movie.rating;
    document.getElementById('movie-year').textContent = movie.year;
    document.getElementById('movie-duration').textContent = movie.duration;
    document.getElementById('movie-genre').textContent = movie.genre;
    document.getElementById('movie-desc').textContent = movie.description;

    // 渲染演员列表
    const castContainer = document.getElementById('cast-list');
    let castHTML = '';
    
    movie.cast.forEach(actor => {
        castHTML += `
            <div class="cast-card">
                <img src="${actor.img}" alt="${actor.name}">
                <span class="cast-name">${actor.name}</span>
                <span class="cast-role">${actor.role}</span>
            </div>
        `;
    });
    
    castContainer.innerHTML = castHTML;
}

// 4. 设置交互事件
function setupEventListeners() {
    const favBtn = document.getElementById('fav-btn');
    
    favBtn.addEventListener('click', function() {
        const icon = this.querySelector('i');
        
        // 切换类名来改变图标样式 (空心心 -> 实心心)
        if (icon.classList.contains('far')) {
            icon.classList.remove('far');
            icon.classList.add('fas');
            icon.style.color = '#e50914'; // 变红
            this.innerHTML = '<i class="fas fa-heart" style="color:#e50914"></i> 已收藏';
        } else {
            icon.classList.remove('fas');
            icon.classList.add('far');
            icon.style.color = 'white';
            this.innerHTML = '<i class="far fa-heart"></i> 收藏';
        }
    });
}