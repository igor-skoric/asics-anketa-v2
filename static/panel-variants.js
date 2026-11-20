(() => {
  const root = document.querySelector("[data-variant-editor]");
  if (!root) return;

  const editor = root.querySelector("[data-variant-list]");
  const addBtn = root.querySelector("[data-variant-add]");
  const totalInput = root.querySelector('input[name$="-TOTAL_FORMS"]');
  const template = document.getElementById("variant-empty-template");
  const max = Number(root.dataset.max || "10");

  if (!editor || !addBtn || !totalInput || !template) return;

  const visibleCount = () =>
    [...editor.querySelectorAll(".variant-card")].filter((card) => !card.classList.contains("is-removing")).length;

  const syncAddState = () => {
    const atMax = visibleCount() >= max;
    addBtn.disabled = atMax;
    addBtn.setAttribute("aria-disabled", atMax ? "true" : "false");
  };

  const bindCard = (card) => {
    const removeBtn = card.querySelector("[data-variant-remove]");
    const undoBtn = card.querySelector("[data-variant-undo]");
    const deleteInput = card.querySelector('input[name$="-DELETE"]');
    if (!removeBtn || !deleteInput) return;

    const setRemoving = (on) => {
      deleteInput.checked = on;
      card.classList.toggle("is-removing", on);
      if (undoBtn) undoBtn.hidden = !on;
      removeBtn.hidden = on;
      syncAddState();
    };

    removeBtn.addEventListener("click", () => setRemoving(true));
    if (undoBtn) undoBtn.addEventListener("click", () => setRemoving(false));
    if (deleteInput.checked) setRemoving(true);
  };

  const addCard = () => {
    if (visibleCount() >= max) return;
    const index = Number(totalInput.value || "0");
    const html = template.innerHTML.replace(/__prefix__/g, String(index));
    editor.insertAdjacentHTML("beforeend", html);
    totalInput.value = String(index + 1);
    const card = editor.lastElementChild;
    if (card) {
      bindCard(card);
      if (window.PanelPhotos) window.PanelPhotos.bindAll(card);
      const focus = card.querySelector("select, input:not([type=hidden]):not([type=checkbox])");
      if (focus) focus.focus();
    }
    syncAddState();
  };

  editor.querySelectorAll(".variant-card").forEach(bindCard);
  addBtn.addEventListener("click", addCard);

  if (!editor.querySelector(".variant-card")) addCard();
  syncAddState();
})();
