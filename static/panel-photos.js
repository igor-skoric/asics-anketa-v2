(() => {
  const IMAGE_TYPE = /^image\//;

  const fileInput = (root) => root.querySelector('input[type="file"]');
  const clearInput = (root) => root.querySelector('input[name$="clear_photo"], input[name="clear_photo"]');
  const preview = (root) => root.querySelector("[data-photo-preview]");
  const empty = (root) => root.querySelector("[data-photo-empty]");
  const overlay = (root) => root.querySelector("[data-photo-overlay]");

  const setEditing = (root, on) => {
    root.classList.toggle("is-editing", on);
    const layer = overlay(root);
    if (layer) layer.hidden = !on;
  };

  const setHasImage = (root, on) => {
    root.classList.toggle("has-image", on);
    const img = preview(root);
    const hint = empty(root);
    if (img) img.hidden = !on;
    if (hint) hint.hidden = on;
    if (!on) setEditing(root, false);
  };

  const revokePreview = (img) => {
    if (img && img.dataset.objectUrl) {
      URL.revokeObjectURL(img.dataset.objectUrl);
      delete img.dataset.objectUrl;
    }
  };

  const showFile = (root, file) => {
    if (!file || !IMAGE_TYPE.test(file.type || "")) return;
    const img = preview(root);
    const clear = clearInput(root);
    if (clear) clear.checked = false;
    revokePreview(img);
    const url = URL.createObjectURL(file);
    if (img) {
      img.src = url;
      img.dataset.objectUrl = url;
    }
    setHasImage(root, true);
    setEditing(root, false);
  };

  const assignFiles = (input, file) => {
    if (!input || !file) return;
    try {
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
    } catch (_error) {
      // Some environments block DataTransfer; change still needs a user gesture via click.
    }
  };

  const clearImage = (root) => {
    const input = fileInput(root);
    const clear = clearInput(root);
    const img = preview(root);
    if (input) input.value = "";
    if (clear) clear.checked = true;
    revokePreview(img);
    if (img) {
      img.removeAttribute("src");
      img.hidden = true;
    }
    setHasImage(root, false);
  };

  const bind = (root) => {
    if (!root || root.dataset.photoBound === "1") return;
    const input = fileInput(root);
    if (!input) return;
    root.dataset.photoBound = "1";
    input.classList.add("visually-hidden");
    input.setAttribute("accept", input.getAttribute("accept") || "image/*");

    const surface = root.querySelector(".photo-drop-surface");
    const replaceBtn = root.querySelector("[data-photo-replace]");
    const removeBtn = root.querySelector("[data-photo-remove]");
    const cancelBtn = root.querySelector("[data-photo-cancel]");

    const openPicker = () => input.click();

    surface?.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      if (!root.classList.contains("has-image")) {
        openPicker();
        return;
      }
      setEditing(root, !root.classList.contains("is-editing"));
    });

    surface?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      surface.click();
    });

    replaceBtn?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openPicker();
    });

    removeBtn?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      clearImage(root);
    });

    cancelBtn?.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      setEditing(root, false);
    });

    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (file) showFile(root, file);
    });

    ["dragenter", "dragover"].forEach((name) => {
      surface?.addEventListener(name, (event) => {
        event.preventDefault();
        event.stopPropagation();
        root.classList.add("is-drag");
      });
    });

    ["dragleave", "drop"].forEach((name) => {
      surface?.addEventListener(name, (event) => {
        event.preventDefault();
        event.stopPropagation();
        root.classList.remove("is-drag");
      });
    });

    surface?.addEventListener("drop", (event) => {
      const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
      if (!file || !IMAGE_TYPE.test(file.type || "")) return;
      assignFiles(input, file);
      if (input.files && input.files[0]) {
        showFile(root, input.files[0]);
      } else {
        showFile(root, file);
      }
    });

    document.addEventListener("click", (event) => {
      if (!root.classList.contains("is-editing")) return;
      if (root.contains(event.target)) return;
      setEditing(root, false);
    });
  };

  const bindAll = (scope) => {
    (scope || document).querySelectorAll("[data-photo-drop]").forEach(bind);
  };

  window.PanelPhotos = { bind, bindAll };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => bindAll(document));
  } else {
    bindAll(document);
  }
})();
