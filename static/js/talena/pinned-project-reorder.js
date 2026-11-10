(function () {
  const list = document.querySelector(".talena-pinned-projects[data-reorder-url]");
  if (!list) return;

  const status = list.querySelector("[data-pinned-order-status]");
  const handlesSelector = "[data-pinned-reorder-handle]";
  let activeRow = null;
  let activeHandle = null;
  let initialOrder = null;
  let activePointerId = null;
  let moved = false;
  let saving = false;

  function rows() {
    return Array.from(list.querySelectorAll(".talena-pinned-project"));
  }

  function order() {
    return rows().map(function (row) {
      return Number(row.dataset.pinnedProjectId);
    });
  }

  function announce(message) {
    if (status) status.textContent = message || "";
  }

  function saveOrder(previousOrder) {
    const nextOrder = order();
    if (nextOrder.length < 2 || nextOrder.every(function (id, index) {
      return id === previousOrder[index];
    })) {
      return;
    }

    const csrfInput = list.querySelector("input[name='csrfmiddlewaretoken']");
    if (!csrfInput) {
      announce(list.dataset.orderFailed);
      return;
    }

    saving = true;
    list.querySelectorAll(handlesSelector).forEach(function (handle) {
      handle.disabled = true;
    });

    fetch(list.dataset.reorderUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfInput.value,
        "X-Requested-With": "XMLHttpRequest"
      },
      body: JSON.stringify({ order: nextOrder })
    }).then(function (response) {
      if (!response.ok) throw new Error("Could not save pinned project order.");
      announce(list.dataset.orderSaved);
    }).catch(function () {
      const byId = new Map(rows().map(function (row) {
        return [Number(row.dataset.pinnedProjectId), row];
      }));
      previousOrder.forEach(function (id) {
        const row = byId.get(id);
        if (row) list.insertBefore(row, status || null);
      });
      announce(list.dataset.orderFailed);
    }).finally(function () {
      saving = false;
      list.querySelectorAll(handlesSelector).forEach(function (handle) {
        handle.disabled = false;
      });
    });
  }

  function clearDragState() {
    rows().forEach(function (row) {
      row.classList.remove("is-reordering", "is-drop-target");
    });
    activeRow = null;
    activeHandle = null;
    activePointerId = null;
  }

  list.addEventListener("pointerdown", function (event) {
    const handle = event.target.closest(handlesSelector);
    if (!handle || saving || event.button !== 0) return;

    const row = handle.closest(".talena-pinned-project");
    if (!row) return;

    event.preventDefault();
    activeRow = row;
    activeHandle = handle;
    activePointerId = event.pointerId;
    initialOrder = order();
    moved = false;
    row.classList.add("is-reordering");
    handle.setPointerCapture(event.pointerId);
  });

  list.addEventListener("pointermove", function (event) {
    if (!activeRow || event.pointerId !== activePointerId) return;
    if (Math.abs(event.movementX) + Math.abs(event.movementY) > 2) moved = true;

    const target = document.elementFromPoint(event.clientX, event.clientY)
      ?.closest(".talena-pinned-project");
    if (!target || target === activeRow) return;

    rows().forEach(function (row) {
      row.classList.remove("is-drop-target");
    });
    target.classList.add("is-drop-target");

    const midpoint = target.getBoundingClientRect().top + target.offsetHeight / 2;
    list.insertBefore(activeRow, event.clientY < midpoint ? target : target.nextElementSibling);
  });

  function finishPointerReorder(event) {
    if (!activeRow || event.pointerId !== activePointerId) return;
    const previousOrder = initialOrder || [];
    const shouldSave = moved;
    clearDragState();
    if (shouldSave) saveOrder(previousOrder);
  }

  list.addEventListener("pointerup", finishPointerReorder);
  list.addEventListener("pointercancel", finishPointerReorder);

  list.addEventListener("keydown", function (event) {
    const handle = event.target.closest(handlesSelector);
    if (!handle || saving || (event.key !== "ArrowUp" && event.key !== "ArrowDown")) return;

    const row = handle.closest(".talena-pinned-project");
    const currentRows = rows();
    const index = currentRows.indexOf(row);
    const previousOrder = order();

    if (event.key === "ArrowUp" && index > 0) {
      event.preventDefault();
      list.insertBefore(row, currentRows[index - 1]);
    } else if (event.key === "ArrowDown" && index < currentRows.length - 1) {
      event.preventDefault();
      list.insertBefore(currentRows[index + 1], row);
    } else {
      return;
    }

    handle.focus();
    saveOrder(previousOrder);
  });
})();
