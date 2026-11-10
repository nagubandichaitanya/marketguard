const statusElement = document.getElementById("api-status");
const checkButton = document.getElementById("check-api");

checkButton.addEventListener("click", async () => {
  statusElement.textContent = "API status: checking...";
  try {
    const response = await fetch("http://127.0.0.1:8000/health");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    statusElement.textContent = `API status: ${result.status} (${result.service})`;
  } catch (error) {
    statusElement.textContent = `API status: unavailable (${error.message})`;
  }
});
