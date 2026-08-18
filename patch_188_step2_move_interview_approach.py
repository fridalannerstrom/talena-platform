from pathlib import Path

ROOT = Path(".")

PERSONALITY = ROOT / (
    "templates/customer/processes/partials/"
    "candidate_insights/personality/_results.html"
)

FINAL_OUTPUT = ROOT / (
    "templates/customer/processes/partials/"
    "candidate_insights/tabs/_final_output.html"
)

PROCESS_BASE = ROOT / "templates/customer/processes/process_base.html"
VIEWS = ROOT / "apps/processes/views.py"

for path in (PERSONALITY, FINAL_OUTPUT, PROCESS_BASE, VIEWS):
    if not path.exists():
        raise SystemExit(
            f"Could not find {path}. "
            "Run this script from the Talena repository root."
        )

final_output_original = FINAL_OUTPUT.read_text(encoding="utf-8")

if "data-response-style-interview-guidance" in final_output_original:
    raise SystemExit(
        "#188 step 2 appears to be applied already. No changes were made."
    )

# 1. Personality: remove Practical approach + Questions to explore.
personality_text = PERSONALITY.read_text(encoding="utf-8")

start_marker = "  <!-- PRACTICAL APPROACH -->"
end_marker = "\n</div>\n\n      </section>"

start = personality_text.find(start_marker)
end = personality_text.find(end_marker, start)

if start == -1 or end == -1 or end <= start:
    raise SystemExit(
        "Could not safely find the Personality interview-guidance block. "
        "No files were changed."
    )

personality_text_new = (
    personality_text[:start]
    + personality_text[end:]
)

# 2. Prepare for interview: replace the old general discussion guidance.
final_output_text = final_output_original

approach_start_marker = (
    "        <!-- HOW TO APPROACH THE CONVERSATION -->"
)
approach_end_marker = (
    "        {% if pre_interview_decision_support.context_note %}"
)

approach_start = final_output_text.find(approach_start_marker)
approach_end = final_output_text.find(
    approach_end_marker,
    approach_start,
)

if (
    approach_start == -1
    or approach_end == -1
    or approach_end <= approach_start
):
    raise SystemExit(
        "Could not safely find the old Prepare for interview "
        "conversation-guidance block. No files were changed."
    )

new_approach_block = r'''        <!-- RESPONSE-STYLE INTERVIEW APPROACH -->

        <section
          class="border-top pt-4 mt-4"
          data-response-style-interview-guidance
        >

          <div>

            <div class="insight-summary-kicker">
              ✨ {% trans "AI-generated insight" %}
            </div>

            <h3 class="insight-summary-title mb-1">
              {% trans "How to approach the conversation" %}
            </h3>

            <p class="text-muted small mb-0">
              {% blocktrans %}Practical interview guidance based on how the candidate used the personality questionnaire response scale.{% endblocktrans %}
            </p>

          </div>

          <div
            class="mt-3"
            data-response-style-interview-content
            {% if not response_style_guidance.recommended_approach and not response_style_guidance.questions %}
              hidden
            {% endif %}
          >

            <section
              class="purpose-fit-section"
              data-response-style-interview-approach-section
              {% if not response_style_guidance.recommended_approach %}
                hidden
              {% endif %}
            >

              <div class="purpose-fit-section-title mb-2">
                {% trans "Recommended approach" %}
              </div>

              <div
                class="purpose-fit-summary"
                data-response-style-interview-approach
              >{{ response_style_guidance.recommended_approach }}</div>

            </section>

            <section
              class="purpose-fit-list-card mt-3"
              data-response-style-interview-questions-section
              {% if not response_style_guidance.questions %}
                hidden
              {% endif %}
            >

              <div class="purpose-fit-section-title">
                {% trans "Questions to explore" %}
              </div>

              <ul
                class="purpose-fit-list"
                data-response-style-interview-questions
              >

                {% for question in response_style_guidance.questions %}
                  <li>
                    <span class="purpose-fit-list-icon">
                      <i data-feather="message-circle"></i>
                    </span>
                    <span>{{ question }}</span>
                  </li>
                {% endfor %}

              </ul>

            </section>

          </div>

          <div
            class="text-muted small mt-3"
            data-response-style-interview-empty
            {% if response_style_guidance.recommended_approach or response_style_guidance.questions %}
              hidden
            {% endif %}
          >
            {% trans "Response-style interview guidance is not available yet." %}
          </div>

        </section>


'''

final_output_text_new = (
    final_output_text[:approach_start]
    + new_approach_block
    + final_output_text[approach_end:]
)

# 3. Final-output refresh view: include saved response-style guidance.
views_text = VIEWS.read_text(encoding="utf-8")

function_start_marker = "def process_candidate_final_output(\n"
next_function_marker = (
    "\n\n@login_required\n"
    "def process_candidate_combined_questions(\n"
)

function_start = views_text.find(function_start_marker)
function_end = views_text.find(
    next_function_marker,
    function_start,
)

if function_start == -1 or function_end == -1:
    raise SystemExit(
        "Could not isolate process_candidate_final_output(). "
        "No files were changed."
    )

function_block = views_text[function_start:function_end]

if '"response_style_guidance"' in function_block:
    raise SystemExit(
        "process_candidate_final_output() already appears to contain "
        "response-style guidance context. No files were changed."
    )

pre_assignment = '''    pre_interview_decision_support = (
        invitation.ai_pre_interview_decision_support
        or {}
    )
'''

replacement_assignment = '''    pre_interview_decision_support = (
        invitation.ai_pre_interview_decision_support
        or {}
    )

    # #188: Prepare for interview uses the saved response-style
    # interview approach from the same one-call response-style result.
    response_style_guidance = (
        invitation.ai_response_style_guidance
        or {}
    )
'''

if pre_assignment not in function_block:
    raise SystemExit(
        "Could not find the expected pre-interview assignment. "
        "No files were changed."
    )

function_block = function_block.replace(
    pre_assignment,
    replacement_assignment,
    1,
)

context_anchor = '''            "combined_questions_refresh_url": (
                combined_questions_refresh_url
            ),

            "pre_interview_decision_support": (
'''

context_replacement = '''            "combined_questions_refresh_url": (
                combined_questions_refresh_url
            ),

            "response_style_guidance": (
                response_style_guidance
            ),

            "pre_interview_decision_support": (
'''

if context_anchor not in function_block:
    raise SystemExit(
        "Could not find the expected final-output render context. "
        "No files were changed."
    )

function_block = function_block.replace(
    context_anchor,
    context_replacement,
    1,
)

views_text_new = (
    views_text[:function_start]
    + function_block
    + views_text[function_end:]
)

# 4. Response-style JS: mirror interview-owned fields across tabs.
process_base_text = PROCESS_BASE.read_text(encoding="utf-8")

if "function renderInterviewGuidance(" in process_base_text:
    raise SystemExit(
        "Response-style interview mirroring already appears to exist. "
        "No files were changed."
    )

render_guidance_marker = (
    "\n\n\n  function renderGuidance(root, guidance) {"
)

render_guidance_pos = process_base_text.find(
    render_guidance_marker
)

if render_guidance_pos == -1:
    raise SystemExit(
        "Could not find the response-style renderGuidance() function. "
        "No files were changed."
    )

mirror_function = r'''

  function renderInterviewGuidance(root, guidance) {
    if (!guidance) {
      return;
    }

    const workspace = root.closest(
      "[data-candidate-insights-workspace]"
    );

    const scope = workspace || document;

    const targets = scope.querySelectorAll(
      "[data-response-style-interview-guidance]"
    );

    if (!targets.length) {
      return;
    }

    const approachText = String(
      guidance.recommended_approach || ""
    ).trim();

    const validQuestions = Array.isArray(
      guidance.questions
    )
      ? guidance.questions
          .map(function (question) {
            return String(question || "").trim();
          })
          .filter(Boolean)
      : [];

    targets.forEach(function (target) {
      const content = target.querySelector(
        "[data-response-style-interview-content]"
      );

      const empty = target.querySelector(
        "[data-response-style-interview-empty]"
      );

      const approachSection = target.querySelector(
        "[data-response-style-interview-approach-section]"
      );

      const approach = target.querySelector(
        "[data-response-style-interview-approach]"
      );

      const questionsSection = target.querySelector(
        "[data-response-style-interview-questions-section]"
      );

      const questionsList = target.querySelector(
        "[data-response-style-interview-questions]"
      );

      setText(approach, approachText);

      setHidden(
        approachSection,
        !approachText
      );

      if (questionsList) {
        questionsList.replaceChildren();

        validQuestions.forEach(function (question) {
          const item = document.createElement("li");

          const icon = document.createElement("span");
          icon.className = "purpose-fit-list-icon";
          icon.innerHTML =
            '<i data-feather="message-circle"></i>';

          const text = document.createElement("span");
          text.textContent = question;

          item.appendChild(icon);
          item.appendChild(text);

          questionsList.appendChild(item);
        });
      }

      setHidden(
        questionsSection,
        validQuestions.length === 0
      );

      const hasInterviewGuidance = Boolean(
        approachText || validQuestions.length
      );

      setHidden(
        content,
        !hasInterviewGuidance
      );

      setHidden(
        empty,
        hasInterviewGuidance
      );
    });

    if (window.feather) {
      window.feather.replace();
    }
  }
'''

process_base_text_new = (
    process_base_text[:render_guidance_pos]
    + mirror_function
    + process_base_text[render_guidance_pos:]
)

old_render_questions_call = '''    renderQuestions(
      root,
      guidance.questions
    );

    const combinationSection = find(
'''

new_render_questions_call = '''    renderQuestions(
      root,
      guidance.questions
    );

    renderInterviewGuidance(
      root,
      guidance
    );

    const combinationSection = find(
'''

if old_render_questions_call not in process_base_text_new:
    raise SystemExit(
        "Could not find the response-style renderQuestions() call. "
        "No files were changed."
    )

process_base_text_new = process_base_text_new.replace(
    old_render_questions_call,
    new_render_questions_call,
    1,
)

# Validate Python before writing anything.
compile(
    views_text_new,
    str(VIEWS),
    "exec",
)

for marker in (
    "data-response-style-interview-guidance",
    "data-response-style-interview-approach",
    "data-response-style-interview-questions",
):
    if marker not in final_output_text_new:
        raise SystemExit(
            f"Validation failed: missing {marker}."
        )

if "data-guidance-approach-section" in personality_text_new:
    raise SystemExit(
        "Validation failed: old Personality approach is still present."
    )

if "data-guidance-questions-section" in personality_text_new:
    raise SystemExit(
        "Validation failed: old Personality questions are still present."
    )

# Write only after every validation passed.
PERSONALITY.write_text(
    personality_text_new,
    encoding="utf-8",
)

FINAL_OUTPUT.write_text(
    final_output_text_new,
    encoding="utf-8",
)

VIEWS.write_text(
    views_text_new,
    encoding="utf-8",
)

PROCESS_BASE.write_text(
    process_base_text_new,
    encoding="utf-8",
)

print("Updated:")
print("✓ Personality response-style UI")
print("✓ Prepare for interview response-style UI")
print("✓ Final-output refresh context")
print("✓ Response-style live JS mirroring")
print()
print("#188 step 2 complete:")
print("✓ Personality now keeps interpretation only")
print("✓ Interview approach moved to Prepare for interview")
print("✓ Response-style questions moved with it")
print("✓ One OpenAI call retained")
