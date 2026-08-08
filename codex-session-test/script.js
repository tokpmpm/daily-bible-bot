const promptElement = document.querySelector("#promptText");
const toast = document.querySelector("#toast");
const copyButtons = document.querySelectorAll("[data-copy-prompt]");
const downloadButton = document.querySelector("#downloadButton");

const promptText = promptElement.textContent.trim();
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2200);
}

async function copyPrompt() {
  try {
    await navigator.clipboard.writeText(promptText);
  } catch (error) {
    const textarea = document.createElement("textarea");
    textarea.value = promptText;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  showToast("Prompt 已複製到剪貼簿");
}

copyButtons.forEach((button) => {
  button.addEventListener("click", copyPrompt);
});

downloadButton.addEventListener("click", () => {
  const file = new Blob([promptText], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = "codex-multi-session-test-prompt.txt";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showToast("文字檔已開始下載");
});
