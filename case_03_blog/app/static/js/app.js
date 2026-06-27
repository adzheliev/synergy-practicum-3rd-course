document.addEventListener("submit", (event) => {
  const deleteForm = event.target.closest("form[action$='/delete']");
  if (deleteForm && !window.confirm("Удалить пост без восстановления?")) {
    event.preventDefault();
  }
});

