document.addEventListener("submit", (event) => {
  const deleteForm = event.target.closest("form[action$='/delete']");
  if (deleteForm && !window.confirm("Удалить пост без восстановления?")) {
    event.preventDefault();
  }
});

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!prefersReducedMotion) {
  const posts = document.querySelectorAll(".post");
  posts.forEach((post, index) => {
    post.classList.add("is-reveal");
    post.style.transitionDelay = `${Math.min(index * 45, 270)}ms`;
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );

  posts.forEach((post) => observer.observe(post));
}
