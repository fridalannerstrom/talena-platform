(function () {
  const root = document.querySelector("[data-chat-root]");

  if (!root) {
    return;
  }

  const messagesDiv = root.querySelector("#chat-messages");
  const input = root.querySelector("#chat-input");
  const button = root.querySelector("#send-btn");
  const emptyState = root.querySelector("[data-chat-empty]");
  const streamUrl = root.dataset.streamUrl || "";

  if (!messagesDiv || !input || !button || !streamUrl) {
    return;
  }

  function getCsrfToken() {
    const el = root.querySelector("input[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function hideEmptyState() {
    if (emptyState) {
      emptyState.classList.add("is-hidden");
    }
  }

  function scrollToLatest() {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function addMessage(role, text) {
    hideEmptyState();

    const row = document.createElement("div");
    row.className = `chat-row ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.dataset.raw = text || "";
    bubble.textContent = text || "";

    row.appendChild(bubble);
    messagesDiv.appendChild(row);
    scrollToLatest();

    return row;
  }

  function renderMarkdownInBubble(bubbleEl) {
    const raw = bubbleEl.dataset.raw || "";

    if (!raw.trim()) {
      bubbleEl.innerHTML = "";
      return;
    }

    if (!window.marked || !window.DOMPurify) {
      bubbleEl.textContent = raw;
      return;
    }

    const html = window.marked.parse(raw, {
      gfm: true,
      breaks: true,
    });

    bubbleEl.innerHTML = window.DOMPurify.sanitize(html);
  }

  async function sendToBackendStream(message) {
    const response = await fetch(streamUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const data = await response.json().catch(function () {
        return {};
      });

      throw new Error(
        data.error
        || root.dataset.requestError
        || "Request failed"
      );
    }

    if (!response.body) {
      throw new Error(
        root.dataset.streamError
        || "Streaming is not supported in this browser."
      );
    }

    return {
      reader: response.body.getReader(),
      decoder: new TextDecoder("utf-8"),
    };
  }

  function setBusy(isBusy) {
    button.disabled = isBusy;
    input.disabled = isBusy;
    button.setAttribute("aria-busy", isBusy ? "true" : "false");
  }

  async function handleSend() {
    const text = input.value.trim();

    if (!text || button.disabled) {
      return;
    }

    setBusy(true);
    addMessage("user", text);
    input.value = "";

    const assistantRow = addMessage("assistant", "");
    const assistantBubble = assistantRow.querySelector(".chat-bubble");
    assistantBubble.classList.add("is-typing");
    assistantBubble.dataset.raw = "";

    try {
      const stream = await sendToBackendStream(text);

      while (true) {
        const chunkResult = await stream.reader.read();

        if (chunkResult.done) {
          break;
        }

        const chunk = stream.decoder.decode(
          chunkResult.value,
          { stream: true }
        );

        assistantBubble.dataset.raw += chunk;
        assistantBubble.textContent += chunk;
        scrollToLatest();
      }

      renderMarkdownInBubble(assistantBubble);
    } catch (error) {
      const prefix = root.dataset.errorPrefix || "Error";
      const fallback = root.dataset.unknownError || "Unknown error";
      const message = `${prefix}: ${error && error.message ? error.message : fallback}`;

      assistantBubble.dataset.raw = message;
      assistantBubble.textContent = message;
    } finally {
      assistantBubble.classList.remove("is-typing");
      setBusy(false);
      input.focus();
      scrollToLatest();
    }
  }

  button.addEventListener("click", function (event) {
    event.preventDefault();
    handleSend();
  });

  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  });

  if (window.feather) {
    window.feather.replace();
  }
})();
