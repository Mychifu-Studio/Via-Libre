
document.addEventListener('DOMContentLoaded', () => {
    // 1. Animations au scroll
    const observerOptions = {
        threshold: 0.15,
        rootMargin: "0px 0px -50px 0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, observerOptions);

    const elementsToReveal = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale, .reveal-up');
    elementsToReveal.forEach(el => observer.observe(el));

    // 2. Logique des onglets (Tabs)
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(target).classList.add('active');
        });
    });

    // 3. Logique du Menu Mobile (Hamburger)
    const mobileToggle = document.querySelector('.mobile-toggle');
    const sidebarNav = document.querySelector('.sidebar-nav');

    if (mobileToggle && sidebarNav) {
        mobileToggle.addEventListener('click', () => {
            mobileToggle.classList.toggle('active');
            sidebarNav.classList.toggle('active');
        });

        // Fermer le menu si on clique sur un lien
        const navLinks = sidebarNav.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                mobileToggle.classList.remove('active');
                sidebarNav.classList.remove('active');
            });
        });
    }
});
