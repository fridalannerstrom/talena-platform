(function () {
  "use strict";

  function getI18n(key, fallback) {
    return (
      window.TALENA_PROCESS_I18N?.[key]
      || fallback
    );
  }

  function getCookie(name) {
    const cookieValue = document.cookie
      .split("; ")
      .find((row) => row.startsWith(`${name}=`));

    return cookieValue
      ? decodeURIComponent(
          cookieValue.split("=")[1]
        )
      : null;
  }

  function refreshIcons() {
    if (!window.feather) {
      return;
    }

    try {
      window.feather.replace();
    } catch (error) {
      console.error(
        "[PURPOSE FIT] Feather error:",
        error
      );
    }
  }

  window.initCandidatePurposeFitStream =
    async function (
      container = document
    ) {
      const card = container.querySelector(
        "#purposeFitCard"
      );

      const result = container.querySelector(
        "#purposeFitResult"
      );

      if (!card || !result) {
        return;
      }

      if (
        card.dataset.purposeFitInitialized
        === "true"
      ) {
        return;
      }

      card.dataset.purposeFitInitialized =
        "true";

      const loading = container.querySelector(
        "#purposeFitLoading"
      );

      const loadingText =
        container.querySelector(
          "#purposeFitLoadingText"
        );

      const errorBox = container.querySelector(
        "#purposeFitError"
      );

      const statusBadge =
        container.querySelector(
          "#purposeFitStatusBadge"
        );

      const outdatedWarning =
        container.querySelector(
          "#purposeFitOutdatedWarning"
        );

      const title = container.querySelector(
        "#purposeFitTitle"
      );

      const summary = container.querySelector(
        "#purposeFitSummary"
      );

      const alignmentList =
        container.querySelector(
          "#purposeFitAlignment"
        );

      const verifyList =
        container.querySelector(
          "#purposeFitVerify"
        );

      const nextStep =
        container.querySelector(
          "#purposeFitNextStep"
        );

      const contextNote =
        container.querySelector(
          "#purposeFitContextNote"
        );

      const refreshButton =
        card.querySelector(
          ".js-regenerate-purpose-fit"
        );

      const streamUrl =
        result.dataset.streamUrl;

      let isStreaming = false;

      console.log(
        "[PURPOSE FIT] Initialised",
        {
          streamUrl,
        }
      );

      function setHidden(
        element,
        hidden
      ) {
        if (!element) {
          return;
        }

        element.classList.toggle(
          "d-none",
          hidden
        );
      }

      function setStatus(
        text,
        type = "neutral"
      ) {
        if (!statusBadge) {
          return;
        }

        statusBadge.textContent =
          text || "";

        statusBadge.className =
          "badge rounded-pill";

        if (type === "warning") {
          statusBadge.classList.add(
            "bg-warning-subtle",
            "text-warning-emphasis"
          );
        } else if (type === "danger") {
          statusBadge.classList.add(
            "bg-danger-subtle",
            "text-danger-emphasis"
          );
        } else if (type === "success") {
          statusBadge.classList.add(
            "bg-success-subtle",
            "text-success-emphasis"
          );
        } else {
          statusBadge.classList.add(
            "bg-light",
            "text-muted"
          );
        }
      }

      function renderList(
        element,
        items,
        iconName
      ) {
        if (!element) {
          return;
        }

        element.replaceChildren();

        const validItems =
          Array.isArray(items)
            ? items.filter(Boolean)
            : [];

        validItems.forEach((item) => {
          const li =
            document.createElement("li");

          const icon =
            document.createElement("span");

          icon.className =
            "purpose-fit-list-icon";

          icon.innerHTML =
            `<i data-feather="${iconName}"></i>`;

          const text =
            document.createElement("span");

          text.textContent =
            String(item);

          li.appendChild(icon);
          li.appendChild(text);

          element.appendChild(li);
        });

        refreshIcons();
      }

      function resetPurposeFit() {
        if (title) {
          title.textContent =
            getI18n(
              "aiOverview",
              "AI Summary"
            );
        }

        if (summary) {
          summary.textContent = "";
        }

        alignmentList?.replaceChildren();
        verifyList?.replaceChildren();

        if (nextStep) {
          nextStep.textContent = "";
        }

        if (contextNote) {
          contextNote.textContent = "";
        }

        setHidden(
          result,
          true
        );

        setHidden(
          errorBox,
          true
        );

        setHidden(
          outdatedWarning,
          true
        );
      }

      function applySavedResult(data) {
        if (title) {
          title.textContent =
            data.title
            || getI18n(
              "aiOverview",
              "AI Summary"
            );
        }

        if (summary) {
          summary.textContent =
            data.summary || "";
        }

        renderList(
          alignmentList,
          data.key_alignment || [],
          "check"
        );

        renderList(
          verifyList,
          data.areas_to_verify || [],
          "search"
        );

        if (nextStep) {
          nextStep.textContent =
            data.suggested_next_step
            || "";
        }

        if (contextNote) {
          contextNote.textContent =
            data.context_note
            || "";
        }

        setHidden(
          loading,
          true
        );

        setHidden(
          result,
          false
        );
      }

      function applyStreamEvent(event) {
        if (!event) {
          return;
        }

        switch (event.type) {
          case "saved_result":
            applySavedResult(
              event.data || {}
            );

            if (
              event.status === "outdated"
            ) {
              setStatus(
                getI18n(
                  "needsUpdate",
                  "Needs update"
                ),
                "warning"
              );
            } else {
              setHidden(
                statusBadge,
                true
              );
            }

            break;

          case "meta":
            setHidden(
              loading,
              true
            );

            setHidden(
              result,
              false
            );

            break;

          case "summary_delta":
            if (summary) {
              summary.textContent +=
                event.text || "";
            }

            break;

          case "key_alignment":
            renderList(
              alignmentList,
              event.items || [],
              "check"
            );

            break;

          case "areas_to_verify":
            renderList(
              verifyList,
              event.items || [],
              "search"
            );

            break;

          case "suggested_next_step":
            if (nextStep) {
              nextStep.textContent =
                event.text || "";
            }

            break;

          case "context_note":
            if (contextNote) {
              contextNote.textContent =
                event.text || "";
            }

            break;

          case "done":
            setHidden(
              loading,
              true
            );

            setHidden(
              result,
              false
            );

            setHidden(
              statusBadge,
              true
            );

            if (
              typeof window
                .notifyCandidateAiContentUpdated
              === "function"
            ) {
              window
                .notifyCandidateAiContentUpdated(
                  card
                );
            }

            break;

          case "error":
            throw new Error(
              event.message
              || "AI Overview generation failed."
            );

          default:
            break;
        }
      }

      async function streamPurposeFit(
        url
      ) {
        if (
          !url
          || isStreaming
        ) {
          return;
        }

        isStreaming = true;

        resetPurposeFit();

        setHidden(
          loading,
          false
        );

        if (loadingText) {
          loadingText.textContent =
            getI18n(
              "creatingAiOverview",
              "Creating an overview from the available assessment results…"
            );
        }

        if (refreshButton) {
          refreshButton.disabled =
            true;
        }

        try {
          console.log(
            "[PURPOSE FIT] Fetching:",
            url
          );

          const response =
            await fetch(
              url,
              {
                method: "GET",

                headers: {
                  "Accept":
                    "application/x-ndjson",

                  "X-Requested-With":
                    "XMLHttpRequest",
                },

                credentials:
                  "same-origin",
              }
            );

          if (!response.ok) {
            let message =
              getI18n(
                "couldNotGenerateAiOverview",
                "Could not generate AI overview."
              );

            try {
              const data =
                await response.json();

              message =
                data.error
                || data.message
                || message;
            } catch (
              parseError
            ) {
              // Use fallback message.
            }

            throw new Error(
              message
            );
          }

          if (!response.body) {
            throw new Error(
              "The browser did not receive a response stream."
            );
          }

          const reader =
            response.body.getReader();

          const decoder =
            new TextDecoder(
              "utf-8"
            );

          let buffer = "";

          while (true) {
            const {
              value,
              done,
            } =
              await reader.read();

            if (done) {
              break;
            }

            buffer +=
              decoder.decode(
                value,
                {
                  stream: true,
                }
              );

            const lines =
              buffer.split("\n");

            buffer =
              lines.pop() || "";

            for (
              const rawLine
              of lines
            ) {
              const line =
                rawLine.trim();

              if (!line) {
                continue;
              }

              const event =
                JSON.parse(line);

              console.log(
                "[PURPOSE FIT] Event:",
                event
              );

              applyStreamEvent(
                event
              );
            }
          }

          buffer +=
            decoder.decode();

          if (buffer.trim()) {
            const event =
              JSON.parse(
                buffer.trim()
              );

            applyStreamEvent(
              event
            );
          }

        } catch (error) {
          console.error(
            "[PURPOSE FIT] Error:",
            error
          );

          setHidden(
            loading,
            true
          );

          setHidden(
            errorBox,
            false
          );

          if (errorBox) {
            errorBox.textContent =
              error.message
              || "Could not generate AI overview.";
          }

          setStatus(
            getI18n(
              "failed",
              "Failed"
            ),
            "danger"
          );

        } finally {
          isStreaming = false;

          if (refreshButton) {
            refreshButton.disabled =
              false;
          }

          refreshIcons();
        }
      }

      if (refreshButton) {
        refreshButton.addEventListener(
          "click",
          async () => {
            if (isStreaming) {
              return;
            }

            const regenerateUrl =
              refreshButton.dataset
                .regenerateUrl;

            if (!regenerateUrl) {
              return;
            }

            refreshButton.disabled =
              true;

            try {
              const response =
                await fetch(
                  regenerateUrl,
                  {
                    method: "POST",

                    headers: {
                      "X-CSRFToken":
                        getCookie(
                          "csrftoken"
                        ),

                      "X-Requested-With":
                        "XMLHttpRequest",
                    },

                    credentials:
                      "same-origin",
                  }
                );

              const data =
                await response.json();

              if (!response.ok) {
                throw new Error(
                  data.error
                  || data.message
                  || getI18n(
                    "couldNotRegenerateAiOverview",
                    "Could not regenerate AI overview."
                  )
                );
              }

              await streamPurposeFit(
                data.stream_url
                || streamUrl
              );

            } catch (error) {
              console.error(
                "[PURPOSE FIT] Regeneration error:",
                error
              );

              setHidden(
                loading,
                true
              );

              setHidden(
                errorBox,
                false
              );

              if (errorBox) {
                errorBox.textContent =
                  error.message
                  || "Could not regenerate AI overview.";
              }

              setStatus(
                getI18n(
                  "failed",
                  "Failed"
                ),
                "danger"
              );

            } finally {
              refreshButton.disabled =
                false;

              refreshIcons();
            }
          }
        );
      }

      const hasFit =
        result.dataset.hasFit
        === "true";

      if (!hasFit) {
        await streamPurposeFit(
          streamUrl
        );
      }

      refreshIcons();
    };
})();