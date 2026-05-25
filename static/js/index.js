/* 搜索功能 */
function searchMovie() {
    const searchText = document.getElementById('searchInput').value.trim();
    console.log(searchText);
    if (searchText) {
        // 可扩展：提交搜索请求到Django后端
        window.location.href = `/search/${searchText}/`;
    } else {
        alert("请输入要搜索的电影名称");
    }
}

/* 跳转电影详情 */
function goDetail(id) {
    // 可扩展：跳转到Django的电影详情页
    window.location.href = `/detail/${id}/`;
    console.log( id);
    // alert(`即将跳转到电影ID: ${id} 的详情页`);
}

/* 自动轮播逻辑 */
document.addEventListener('DOMContentLoaded', function() {
    let slideIndex = 0;
    const slides = document.querySelectorAll(".hero-slide");
    
    // 轮播核心函数
    function showSlides() {
        // 移除所有active类
        slides.forEach(slide => slide.classList.remove("active"));
        slideIndex++;
        // 重置索引
        if (slideIndex > slides.length) slideIndex = 1;
        // 给当前轮播图添加active类
        slides[slideIndex - 1].classList.add("active");
        // 4秒切换一次
        setTimeout(showSlides, 4000);
    }

    // 启动轮播
    showSlides();
});