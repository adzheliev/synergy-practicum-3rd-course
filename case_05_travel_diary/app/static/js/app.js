const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (!prefersReducedMotion) {
  const notes = document.querySelectorAll(".field-note");
  notes.forEach((note, index) => {
    note.classList.add("is-reveal");
    note.style.transitionDelay = `${Math.min(index * 55, 330)}ms`;
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
    { threshold: 0.1, rootMargin: "0px 0px -30px 0px" }
  );

  notes.forEach((note) => observer.observe(note));
}
