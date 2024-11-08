document.addEventListener('DOMContentLoaded', function() {
    const wrapper = document.querySelector('.related-spots-wrapper');
    const list = document.querySelector('.related-spot-list');
    const btnLeft = document.getElementById('scrollLeft');
    const btnRight = document.getElementById('scrollRight');

    // 초기 스크롤 버튼 상태 설정
    checkScrollButtons();

    // 왼쪽 스크롤
    btnLeft.addEventListener('click', () => {
        const scrollAmount = wrapper.offsetWidth * 0.8;
        wrapper.scrollBy({
            left: -scrollAmount,
            behavior: 'smooth'
        });
    });

    // 오른쪽 스크롤
    btnRight.addEventListener('click', () => {
        const scrollAmount = wrapper.offsetWidth * 0.8;
        wrapper.scrollBy({
            left: scrollAmount,
            behavior: 'smooth'
        });
    });

    // 스크롤 이벤트 감지하여 버튼 상태 업데이트
    wrapper.addEventListener('scroll', checkScrollButtons);

    // 버튼 상태 체크 함수
    function checkScrollButtons() {
        const isAtStart = wrapper.scrollLeft === 0;
        const isAtEnd = wrapper.scrollLeft >= (list.scrollWidth - wrapper.offsetWidth);

        btnLeft.style.display = isAtStart ? 'none' : 'flex';
        btnRight.style.display = isAtEnd ? 'none' : 'flex';
    }
});