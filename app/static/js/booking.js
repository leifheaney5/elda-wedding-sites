document.addEventListener("DOMContentLoaded", () => {
  const weddingDate = document.getElementById("wedding_date");
  if (weddingDate && !weddingDate.min) {
    weddingDate.min = new Date().toISOString().split("T")[0];
  }
});
