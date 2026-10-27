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

      const generationUrl =
        result.dataset.generationUrl;

      let isGenerating = false;

      console.log(
        "[PURPOSE FIT] Initialised",
        {
          generationUrl,
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

      function setPersonalityAreaSummary(area, text) {
        const element = container.querySelector(
          `[data-personality-area-summary="${area}"]`
        );
        if (!element) return;
        const value = String(text || "").trim();
        element.textContent = value;
        element.classList.toggle("d-none", !value);
        const placeholder = element
          .closest(".personality-overview-summary")
          ?.querySelector(".personality-overview-summary__placeholder");
        placeholder?.classList.toggle("d-none", Boolean(value));
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

        ["leadership", "organisation", "interaction"].forEach(
          (area) => setPersonalityAreaSummary(area, "")
        );

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

        const areaSummaries =
          data.personality_area_summaries || {};
        ["leadership", "organisation", "interaction"].forEach(
          (area) => setPersonalityAreaSummary(area, areaSummaries[area])
        );

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

      function applyCompletedResponse(responseData) {
        applySavedResult(
          responseData.data || {}
        );

        if (responseData.status === "outdated") {
          setStatus(
            getI18n(
              "needsUpdate",
              "Needs update"
            ),
            "warning"
          );
        } else {
          setHidden(statusBadge, true);
        }

        if (
          responseData.generated
          && typeof window.notifyCandidateAiContentUpdated === "function"
        ) {
          window.notifyCandidateAiContentUpdated(card);
        }
      }

      async function generatePurposeFit(url) {
        if (!url || isGenerating) {
          return;
        }

        isGenerating = true;
        resetPurposeFit();

        setHidden(loading, false);

        if (loadingText) {
          loadingText.textContent = getI18n(
            "creatingAiOverview",
            "Creating an overview from the available assessment results…"
          );
        }

        if (refreshButton) {
          refreshButton.disabled = true;
        }

        try {
          const response = await fetch(
            url,
            {
              method: "GET",
              headers: {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
              },
              credentials: "same-origin",
            }
          );

          let responseData = {};
          try {
            responseData = await response.json();
          } catch (parseError) {
            // The response may be a plain-text access or server error.
          }

          if (!response.ok) {
            throw new Error(
              responseData.error
              || responseData.message
              || getI18n(
                "couldNotGenerateAiOverview",
                "Could not generate AI overview."
              )
            );
          }

          if (
            !responseData.data
            || typeof responseData.data !== "object"
          ) {
            throw new Error(
              getI18n(
                "couldNotGenerateAiOverview",
                "Could not generate AI overview."
              )
            );
          }

          applyCompletedResponse(responseData);

        } catch (error) {
          console.error(
            "[PURPOSE FIT] Error:",
            error
          );

          setHidden(loading, true);
          setHidden(errorBox, false);

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
          isGenerating = false;

          if (refreshButton) {
            refreshButton.disabled = false;
          }

          refreshIcons();
        }
      }

      if (refreshButton) {
        refreshButton.addEventListener(
          "click",
          async () => {
            if (isGenerating) {
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

              await generatePurposeFit(
                data.generation_url
                || generationUrl
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

      const areaSummaryElements = [
        ...container.querySelectorAll(
          "[data-personality-area-summary]"
        )
      ];
      const needsPersonalityAreaSummaries =
        areaSummaryElements.length === 3
        && areaSummaryElements.some(
          (element) => !element.textContent.trim()
        );

      if (!hasFit) {
        await generatePurposeFit(
          generationUrl
        );
      } else if (needsPersonalityAreaSummaries) {
        const regenerateUrl =
          refreshButton?.dataset.regenerateUrl;

        if (regenerateUrl) {
          try {
            const response = await fetch(
              regenerateUrl,
              {
                method: "POST",
                headers: {
                  "X-CSRFToken": getCookie("csrftoken"),
                  "X-Requested-With": "XMLHttpRequest",
                },
                credentials: "same-origin",
              }
            );
            const data = await response.json();
            if (!response.ok) {
              throw new Error(
                data.error
                || getI18n(
                  "couldNotRegenerateAiOverview",
                  "Could not regenerate AI overview."
                )
              );
            }
            await generatePurposeFit(
              data.generation_url || generationUrl
            );
          } catch (error) {
            console.error(
              "[PURPOSE FIT] Could not add personality area summaries:",
              error
            );
          }
        }
      }

      refreshIcons();
    };
})();