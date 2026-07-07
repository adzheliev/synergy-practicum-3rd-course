const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!prefersReducedMotion) {
  const rows = document.querySelectorAll(".book-row");
  rows.forEach((row, index) => {
    row.classList.add("is-reveal");
    row.style.transitionDelay = `${Math.min(index * 50, 300)}ms`;
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
    { threshold: 0.15 }
  );

  rows.forEach((row) => observer.observe(row));
}
