"""Shared candidate insight content for active and historical candidates."""

from __future__ import annotations

from typing import Any, Literal

InsightMode = Literal["general", "context"]


def build_candidate_insights(
    *,
    mode: InsightMode = "general",
    general_insight_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the candidate insight structure used by the candidate sheet.

    ``general_insight_input`` is accepted now so both active and historical
    candidate flows use the same API. The current implementation still returns
    the deterministic content that previously lived in views.py.
    """
    _ = general_insight_input
    candidate_insights_mode: InsightMode = (
        "context" if mode == "context" else "general"
    )

    if candidate_insights_mode == "context":
        candidate_insights = {
            "summary": {
                "headline": "Potential fit for a structured Business Controller role",
                "body": (
                    "The candidate shows a profile that may support structured analysis, reliable delivery and careful business follow-up. "
                    "For this Business Controller context, the strongest signal is the combination of analytical thinking, planning and quality focus. "
                    "The main areas to validate are stakeholder communication, pace when priorities change and the ability to turn analysis into practical recommendations."
                ),
                "bullets": [
                    {
                        "label": "Most important interpretation",
                        "text": "The candidate appears well aligned with work that requires structure, accuracy and thoughtful analysis, but the interview should validate how this translates into stakeholder-facing business support.",
                    },
                    {
                        "label": "Confidence / context level",
                        "text": "Medium confidence. The interpretation uses completed assessment data and the added Business Controller role context, but should be combined with interview evidence.",
                    },
                    {
                        "label": "What this report is based on",
                        "text": "Assessment results, personality and motivation indicators, cognitive reasoning data, and the added role context covering requirements, priorities and interview focus.",
                    },
                ],
            },
            "fit": {
                "title": "Role match verdict",
                "label": "Potential match",
                "confidence": "Medium",
                "summary": (
                    "Talena sees a promising match for the Business Controller role, mainly because the candidate shows strong "
                    "indicators for structure, analytical thinking and reliable delivery."
                ),
                "body": (
                    "Talena sees a promising match for the Business Controller role, mainly because the candidate shows strong "
                    "indicators for structure, analytical thinking and reliable delivery."
                ),
                "reasoning": [
                    "The role requires structured analysis and careful follow-up, which appears aligned with the candidate’s strengths in planning, quality focus and analytical thinking.",
                    "The candidate may be well suited to work that requires accuracy, ownership and thoughtful decision support.",
                    "The match is not yet strong enough to confirm without interview validation, especially around stakeholder-facing business support.",
                ],
                "watch_points": [
                    "Stakeholder communication",
                    "Pace under ambiguity",
                    "Commercial judgement",
                ],
                "suggested_next_step": "Proceed with a structured interview focused on stakeholder communication, changing priorities and business impact.",
                "decision_note": (
                    "This is a decision-support recommendation, not a final hiring decision. Combine it with interview evidence, experience and role requirements."
                ),
            },
            "key_strengths": [
                {
                    "title": "Structured business analysis",
                    "body": "The candidate appears likely to bring structure and clarity to analytical work.",
                    "how_it_may_show": "May organise information, compare alternatives and create a clear basis for business decisions.",
                    "why_it_matters": "This is relevant for a Business Controller role where managers need clear financial insights and practical recommendations.",
                    "evidence": ["Analytical Thinking", "Planning", "Quality Focus"],
                },
                {
                    "title": "Reliable delivery",
                    "body": "The profile suggests a preference for accuracy, follow-through and doing work properly.",
                    "how_it_may_show": "May take deadlines and reporting quality seriously, especially when expectations are clear.",
                    "why_it_matters": "This can support recurring financial follow-up, reporting cycles and dependable stakeholder support.",
                    "evidence": ["Reliability", "Quality Focus", "Self-discipline"],
                },
                {
                    "title": "Thoughtful decision support",
                    "body": "The candidate may be comfortable working with information before reaching conclusions.",
                    "how_it_may_show": "May ask clarifying questions, analyse patterns and avoid rushing into unsupported recommendations.",
                    "why_it_matters": "This is useful when the role requires sound judgement and the ability to translate data into business insight.",
                    "evidence": ["Analytical Thinking", "Logical reasoning"],
                },
                {
                    "title": "Ownership with clarity",
                    "body": "The candidate may perform well when given clear goals and responsibility for defined tasks.",
                    "how_it_may_show": "May take ownership of agreed deliverables and work independently when priorities are understood.",
                    "why_it_matters": "This can support a role where the person needs to manage recurring analysis, deadlines and stakeholder requests.",
                    "evidence": ["Autonomy", "Achievement", "Planning"],
                },
            ],
            "areas_to_explore": [
                {
                    "title": "Stakeholder influence",
                    "body": "It may be useful to understand how the candidate communicates financial insights and gains buy-in from non-finance stakeholders.",
                    "explore_through": "Ask about a time when they had to explain complex information to a manager or influence a business decision.",
                    "what_to_listen_for": "Look for clarity, confidence, ability to adapt the message and understanding of the stakeholder’s perspective.",
                    "evidence": ["Influencing", "Communication"],
                },
                {
                    "title": "Pace under ambiguity",
                    "body": "It may be useful to explore how the candidate handles changing priorities, incomplete information or urgent deadlines.",
                    "explore_through": "Ask about a situation where they had to deliver analysis despite unclear or changing requirements.",
                    "what_to_listen_for": "Look for how they balance accuracy with practical progress and whether they can prioritise effectively.",
                    "evidence": ["Adaptability", "Decision-making"],
                },
                {
                    "title": "Commercial confidence",
                    "body": "It may be useful to understand how confidently the candidate connects analysis to business impact.",
                    "explore_through": "Ask for an example where their analysis led to a recommendation, decision or improvement.",
                    "what_to_listen_for": "Look for business understanding, practical judgement and ability to move from numbers to action.",
                    "evidence": ["Business understanding", "Analytical Thinking"],
                },
                {
                    "title": "Collaboration with managers",
                    "body": "It may be useful to explore how the candidate builds working relationships with managers and stakeholders.",
                    "explore_through": "Ask what helps them collaborate well with people who have different priorities or limited finance knowledge.",
                    "what_to_listen_for": "Look for patience, service mindset, clarity and ability to create trust over time.",
                    "evidence": ["Teamwork", "Listening"],
                },
            ],
            "questions": [
                {
                    "category": "strengths",
                    "category_label": "Strengths",
                    "question": "Tell me about a time when you used financial or business analysis to support an important decision.",
                    "why": "Helps validate analytical problem-solving and ability to turn data into practical recommendations.",
                    "listen_for": "Look for clear reasoning, business understanding, accuracy and impact on the decision.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Can you describe a situation where you had to explain complex financial information to someone without a finance background?",
                    "why": "Explores stakeholder communication and ability to make analysis understandable.",
                    "listen_for": "Look for clarity, adaptation to the audience and ability to connect numbers to business reality.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Tell me about a time when priorities changed close to a deadline. How did you handle it?",
                    "why": "Helps understand pace, flexibility and prioritisation under pressure.",
                    "listen_for": "Look for structure, calmness, communication and practical decision-making.",
                },
                {
                    "category": "motivation",
                    "category_label": "Motivation",
                    "question": "What type of financial or analytical work gives you the most energy?",
                    "why": "Explores motivation fit with the role’s recurring tasks and stakeholder support.",
                    "listen_for": "Look for alignment with analysis, quality, ownership and business impact.",
                },
                {
                    "category": "work_style",
                    "category_label": "Work style",
                    "question": "How do you prefer to work with managers who need support but may not know exactly what analysis they need?",
                    "why": "Explores consulting style, communication and ability to clarify needs.",
                    "listen_for": "Look for curiosity, structure, patience and ability to guide stakeholders.",
                },
            ],
            "motivation_environment": {
                "summary": (
                    "In this Business Controller context, the candidate’s likely motivation for quality, autonomy and meaningful contribution "
                    "may support independent delivery and careful analysis. Engagement may be strongest when expectations are clear and the work "
                    "has visible business value."
                ),
                "top_motivators": [
                    {
                        "title": "Quality",
                        "body": "May be motivated by accurate, reliable work and high standards.",
                    },
                    {
                        "title": "Autonomy",
                        "body": "May value ownership over tasks and freedom to decide how to approach analysis.",
                    },
                    {
                        "title": "Making a difference",
                        "body": "May gain energy from seeing that their work improves decisions or creates business value.",
                    },
                ],
                "possible_demotivators": [
                    {
                        "title": "Unclear priorities",
                        "body": "May lose energy if goals, responsibilities or decision-making authority remain vague.",
                    },
                    {
                        "title": "Low-quality shortcuts",
                        "body": "May become frustrated if speed is repeatedly prioritised over accuracy.",
                    },
                    {
                        "title": "Limited ownership",
                        "body": "May find it less engaging if there is little room to influence how work is done.",
                    },
                ],
                "best_environment": [
                    {
                        "title": "Clear expectations",
                        "body": "Clear priorities and success criteria may help the candidate focus effectively.",
                    },
                    {
                        "title": "Trust and responsibility",
                        "body": "The candidate may perform well when trusted to own analysis and follow through.",
                    },
                    {
                        "title": "Business-oriented dialogue",
                        "body": "Regular dialogue with managers can help connect analysis to practical decisions.",
                    },
                    {
                        "title": "Constructive feedback",
                        "body": "Feedback on usefulness and business impact may help maintain motivation.",
                    },
                ],
                "manager_tips": [
                    {
                        "title": "Clarify the business question",
                        "body": "Explain what decision the analysis should support before asking for numbers or reports.",
                    },
                    {
                        "title": "Agree on priorities",
                        "body": "Be clear about what is urgent, what can wait and what level of detail is needed.",
                    },
                    {
                        "title": "Give ownership",
                        "body": "Let the candidate own recurring analysis while agreeing on checkpoints and deadlines.",
                    },
                    {
                        "title": "Connect work to impact",
                        "body": "Show how their analysis contributes to decisions, improvements or financial control.",
                    },
                ],
                "context_implications": (
                    "For this role, the motivation profile may support careful and independent delivery. "
                    "The main thing to watch is whether the role provides enough clarity, ownership and connection to business impact."
                ),
            },
            "work_style": {
                "summary": (
                    "The candidate appears likely to work best with clarity, structure and enough space to think things through. "
                    "In this role context, that may support reliable analysis, careful financial follow-up and considered business recommendations."
                ),
                "items": [
                    {
                        "title": "How they work",
                        "subtitle": "Structure, pace and task approach",
                        "body": "May prefer clear expectations, organised work and time to understand the task before moving into action.",
                        "practical_tip": "Provide clear priorities and agree on what good delivery looks like early in the process.",
                        "evidence": ["Planning", "Reliability", "Quality Focus"],
                        "icon": "work",
                        "icon_class": "",
                    },
                    {
                        "title": "How they communicate",
                        "subtitle": "Information sharing and stakeholder dialogue",
                        "body": "May communicate most effectively when there is a clear purpose and enough context to form a considered view.",
                        "practical_tip": "Invite them to explain their reasoning and connect analysis to practical business consequences.",
                        "evidence": ["Communication", "Analytical Thinking"],
                        "icon": "communicate",
                        "icon_class": "is-blue",
                    },
                    {
                        "title": "How they handle change",
                        "subtitle": "Changing priorities and business needs",
                        "body": "May adapt well when changes are explained clearly, but may need clarity around priorities if several things change at once.",
                        "practical_tip": "When priorities shift, clarify what changed, what stays the same and what should be handled first.",
                        "evidence": ["Adaptability", "Decision-making"],
                        "icon": "change",
                        "icon_class": "is-green",
                    },
                    {
                        "title": "How they handle pressure",
                        "subtitle": "Deadlines and workload",
                        "body": "May perform best when pressure is paired with structure, realistic priorities and clear expectations.",
                        "practical_tip": "Use short check-ins during intense reporting periods to remove blockers and keep priorities visible.",
                        "evidence": ["Resilience", "Emotional Control"],
                        "icon": "pressure",
                        "icon_class": "is-orange",
                    },
                    {
                        "title": "How they prefer to be managed",
                        "subtitle": "Support, autonomy and feedback",
                        "body": "May respond well to a management style that combines trust and autonomy with clear goals and constructive feedback.",
                        "practical_tip": "Give ownership, but agree on checkpoints and make expectations explicit.",
                        "evidence": ["Autonomy", "Quality", "Achievement"],
                        "icon": "managed",
                        "icon_class": "is-pink",
                    },
                ],
                "footer_note": (
                    "This section translates personality and motivation indicators into practical behaviours for the current role context. "
                    "Full trait-level results can be reviewed further down as evidence."
                ),
            },
            "next_steps": [
                {
                    "label": "Recommended action",
                    "title": "Proceed with a structured interview",
                    "body": "Use the report to guide a focused interview rather than as a standalone decision.",
                    "focus": "Validate stakeholder communication, commercial judgement and pace under ambiguity.",
                },
                {
                    "label": "Interview focus",
                    "title": "Ask evidence-based follow-up questions",
                    "body": "Use behavioural questions to understand how the candidate applies analysis and structure in real work situations.",
                    "focus": "Ask for examples involving financial analysis, deadlines, prioritisation and influencing decisions.",
                },
                {
                    "label": "Decision support",
                    "title": "Combine assessment insights with interview evidence",
                    "body": "Use the assessment results together with interview notes, experience and role requirements.",
                    "focus": "Avoid making a decision from assessment data alone.",
                },
            ],
        }

    else:
        candidate_insights = {
            "summary": {
                "headline": (
                    "General assessment summary"
                    if candidate_insights_mode == "general"
                    else "Contextual candidate insight summary"
                ),
                "body": (
                    "The candidate’s assessment profile suggests a structured and analytical work style, with strong indicators around planning, quality focus and working with complex information. "
                    "This may support roles or situations where careful follow-up, accuracy and thoughtful problem-solving are important. "
                    "At the same time, the results should be explored further through conversation, especially around stakeholder influence, decision-making pace and how the candidate handles changing priorities. "
                    "Add role or process context to make this interpretation more specific."
                ),
            },
            "fit": {
                "label": (
                    "Insufficient context"
                    if candidate_insights_mode == "general"
                    else "Potential fit"
                ),
                "confidence": (
                    "Low"
                    if candidate_insights_mode == "general"
                    else "Medium"
                ),
                "suggested_next_step": (
                    "Add context"
                    if candidate_insights_mode == "general"
                    else "Structured follow-up"
                ),
                "body": (
                    "No process context has been added yet, so this section does not assess "
                    "fit for a specific role, team, leadership situation or development goal."
                    if candidate_insights_mode == "general"
                    else
                    "Based on the added context, the candidate appears to show several relevant "
                    "indicators. Some areas should be explored further before making a decision."
                ),
            },
                "key_strengths": [
                    {
                        "title": "Structured approach",
                        "body": "Likely to value clarity, order and follow-through in work situations.",
                        "how_it_may_show": "May create structure, keep track of details and prefer clear expectations before moving into action.",
                        "why_it_matters": "This can support consistency, planning and dependable delivery in day-to-day work.",
                        "evidence": ["Reliability", "Planning", "Task focus"],
                    },
                    {
                        "title": "Analytical problem solving",
                        "body": "May be comfortable working with information, patterns and conclusions.",
                        "how_it_may_show": "May identify patterns, compare options and use information to support decisions.",
                        "why_it_matters": "This can support work that requires prioritisation, judgement and problem-solving.",
                        "evidence": ["Analytical Thinking", "Logical reasoning"],
                    },
                    {
                        "title": "Reliable ownership",
                        "body": "May take commitments seriously and show a preference for doing things properly.",
                        "how_it_may_show": "May follow through on agreed responsibilities and aim to deliver work to a consistent standard.",
                        "why_it_matters": "This can be useful where trust, accountability and reliable execution are important.",
                        "evidence": ["Quality Focus", "Self-discipline"],
                    },
                    {
                        "title": "Thoughtful decision-making",
                        "body": "May prefer to consider information carefully before reaching conclusions.",
                        "how_it_may_show": "May ask clarifying questions, weigh alternatives and avoid rushing decisions without enough information.",
                        "why_it_matters": "This can support sound judgement, especially in situations where decisions have practical consequences.",
                        "evidence": ["Analytical Thinking", "Complex Thinking"],
                    },
                ],
            "areas_to_explore": [
                {
                    "title": "Stakeholder influence",
                    "body": "It may be useful to understand how the candidate communicates ideas, gains buy-in and handles situations where others have different views.",
                    "explore_through": "Ask about a time when they needed to influence a decision or create agreement without having full authority.",
                    "what_to_listen_for": "Look for clarity, confidence, listening, adaptability and ability to connect their message to others’ needs.",
                    "evidence": ["Influencing", "Communication"],
                },
                {
                    "title": "Pace under ambiguity",
                    "body": "It may be useful to explore how the candidate handles situations where information is incomplete, priorities change or decisions need to be made quickly.",
                    "explore_through": "Ask about a situation where they had to move forward without having all the information they wanted.",
                    "what_to_listen_for": "Look for how they balance careful thinking with practical action, and whether they can adjust when conditions change.",
                    "evidence": ["Adaptability", "Decision-making"],
                },
                {
                    "title": "Collaboration style",
                    "body": "It may be useful to understand what type of collaboration helps the candidate perform at their best, especially in teams with different working styles.",
                    "explore_through": "Ask what they need from colleagues and managers to collaborate well, and what others usually appreciate about working with them.",
                    "what_to_listen_for": "Look for self-awareness, openness to feedback and ability to adapt communication to different people.",
                    "evidence": ["Teamwork", "Listening"],
                },
                {
                    "title": "Energy and motivation fit",
                    "body": "It may be useful to explore what gives the candidate energy at work and which conditions may reduce engagement over time.",
                    "explore_through": "Ask what types of tasks, environments or goals tend to bring out their best contribution.",
                    "what_to_listen_for": "Look for alignment between the person’s drivers and the realities of the role, team or development context.",
                    "evidence": ["Motivation", "Work preferences"],
                },
            ],
            "questions": [
                {
                    "question": "Tell me about a time when you used analysis to influence a decision.",
                    "why": "Validates analytical thinking and communication in a practical situation.",
                },
                {
                    "question": "How do you handle situations where priorities change quickly?",
                    "why": "Explores adaptability, structure and decision-making under pressure.",
                },
                {
                    "question": "What type of work environment helps you perform at your best?",
                    "why": "Connects motivation and work style to the candidate’s preferred conditions.",
                },
            ],
            "motivation_environment": {
                "summary": (
                    "The candidate appears likely to be energised by quality, autonomy and meaningful contribution. "
                    "They may perform best in an environment with clear expectations, room for ownership and opportunities to do work properly."
                ),
                "top_motivators": [
                    {
                        "title": "Quality",
                        "body": "May be motivated by doing work to a high standard and feeling that the result is accurate and reliable.",
                    },
                    {
                        "title": "Autonomy",
                        "body": "May value having ownership over tasks and enough freedom to decide how work should be approached.",
                    },
                    {
                        "title": "Making a difference",
                        "body": "May gain energy from seeing that their work contributes to something meaningful or useful.",
                    },
                ],
                "possible_demotivators": [
                    {
                        "title": "Unclear expectations",
                        "body": "May lose energy if goals, responsibilities or decision-making authority are vague for too long.",
                    },
                    {
                        "title": "Low-quality shortcuts",
                        "body": "May become frustrated if speed is consistently prioritised over accuracy or thoughtful delivery.",
                    },
                    {
                        "title": "Limited ownership",
                        "body": "May find it less engaging if there is little room to take responsibility or influence how work is done.",
                    },
                ],
                "best_environment": [
                    {
                        "title": "Clear goals",
                        "body": "An environment with clear priorities and expectations may help the candidate focus their energy effectively.",
                    },
                    {
                        "title": "Trust and ownership",
                        "body": "They may perform well when trusted to take responsibility and manage tasks with a degree of independence.",
                    },
                    {
                        "title": "Quality-focused culture",
                        "body": "A culture that values accuracy, improvement and thoughtful work may support engagement.",
                    },
                    {
                        "title": "Constructive feedback",
                        "body": "Regular feedback and clear dialogue may help maintain motivation and alignment.",
                    },
                ],
                "manager_tips": [
                    {
                        "title": "Clarify expectations early",
                        "body": "Be clear about what success looks like and which priorities matter most.",
                    },
                    {
                        "title": "Give ownership with boundaries",
                        "body": "Allow independence while agreeing on checkpoints, timelines and decision areas.",
                    },
                    {
                        "title": "Connect work to purpose",
                        "body": "Explain why tasks matter and how they contribute to wider goals or customer value.",
                    },
                    {
                        "title": "Avoid unnecessary ambiguity",
                        "body": "When things are changing, communicate what is known, what is uncertain and when decisions will be made.",
                    },
                ],
                "context_implications": (
                    "Without added process context, these insights should be read as general motivation themes. "
                    "If this report is used for a specific role, onboarding plan or development purpose, the motivation profile should be interpreted against that situation."
                ),
            },
            "work_style": {
                "summary": (
                    "The candidate appears likely to work best with clarity, structure and enough space to think things through. "
                    "Their profile may suggest a thoughtful and reliable working style, with a preference for quality and considered decisions."
                ),
                "items": [
                    {
                        "title": "How they work",
                        "subtitle": "Structure, pace and task approach",
                        "body": "The candidate may prefer clear expectations, organised work and time to understand the task before moving into action.",
                        "practical_tip": "Provide clear priorities and agree on what good delivery looks like early in the process.",
                        "evidence": ["Planning", "Reliability", "Quality Focus"],
                        "icon": "work",
                        "icon_class": "",
                    },
                    {
                        "title": "How they communicate",
                        "subtitle": "Information sharing and collaboration",
                        "body": "They may communicate most effectively when there is a clear purpose and enough context to form a considered view.",
                        "practical_tip": "Invite them to explain their reasoning and give space for questions, especially in complex discussions.",
                        "evidence": ["Communication", "Analytical Thinking"],
                        "icon": "communicate",
                        "icon_class": "is-blue",
                    },
                    {
                        "title": "How they handle change",
                        "subtitle": "Adaptability and shifting priorities",
                        "body": "They may adapt well when changes are explained clearly, but may need clarity around priorities if several things change at once.",
                        "practical_tip": "When priorities shift, clarify what has changed, what stays the same and what should be handled first.",
                        "evidence": ["Adaptability", "Decision-making"],
                        "icon": "change",
                        "icon_class": "is-green",
                    },
                    {
                        "title": "How they handle pressure",
                        "subtitle": "Pressure response and workload",
                        "body": "The candidate may perform best when pressure is paired with structure, realistic priorities and clear expectations.",
                        "practical_tip": "Use regular check-ins during intense periods to remove blockers and keep priorities visible.",
                        "evidence": ["Resilience", "Emotional Control"],
                        "icon": "pressure",
                        "icon_class": "is-orange",
                    },
                    {
                        "title": "How they prefer to be managed",
                        "subtitle": "Support, autonomy and feedback",
                        "body": "They may respond well to a management style that combines trust and autonomy with clear goals and constructive feedback.",
                        "practical_tip": "Give ownership, but agree on checkpoints and make expectations explicit.",
                        "evidence": ["Autonomy", "Quality", "Achievement"],
                        "icon": "managed",
                        "icon_class": "is-pink",
                    },
                ],
                "footer_note": (
                    "This section translates personality and work style indicators into practical behaviours. "
                    "Full trait-level results can be reviewed further down as evidence."
                ),
            },
            "next_steps": [
                {
                    "label": "Recommended action",
                    "title": "Use a structured follow-up conversation",
                    "body": "Use the insights as a starting point for a structured conversation rather than as a final conclusion.",
                    "focus": "Focus on examples from real work situations, especially where the candidate had to apply their strengths in practice.",
                },
                {
                    "label": "Validate through examples",
                    "title": "Explore the most relevant follow-up themes",
                    "body": "Ask targeted questions around the areas that would benefit from more context before making decisions or recommendations.",
                    "focus": "Prioritise stakeholder influence, pace under ambiguity and collaboration style.",
                },
                {
                    "label": "Connect insights to context",
                    "title": "Add process context for sharper recommendations",
                    "body": "If this report will be used for a specific role, team, onboarding plan or development purpose, add context to make the next steps more precise.",
                    "focus": "Add role, team, leadership or onboarding context to tailor the interpretation.",
                },
            ],

            "questions": [
                {
                    "category": "strengths",
                    "category_label": "Strengths",
                    "question": "Tell me about a situation where you used structure or analysis to solve a work-related problem.",
                    "why": "Helps validate how the candidate applies analytical and structured strengths in real situations.",
                    "listen_for": "Look for clear reasoning, practical action, follow-through and ability to explain the outcome.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Can you describe a time when you needed to influence someone who had a different opinion from you?",
                    "why": "Explores how the candidate gains buy-in and handles different perspectives.",
                    "listen_for": "Look for listening, clarity, adaptability, confidence and respect for other viewpoints.",
                },
                {
                    "category": "explore",
                    "category_label": "Explore",
                    "question": "Tell me about a situation where you had to make progress without having all the information you wanted.",
                    "why": "Helps understand how the candidate handles ambiguity and changing priorities.",
                    "listen_for": "Look for balance between careful thinking and practical action.",
                },
                {
                    "category": "motivation",
                    "category_label": "Motivation",
                    "question": "What type of work tends to give you the most energy, and what tends to drain your energy over time?",
                    "why": "Explores motivation fit and the conditions that may support sustained performance.",
                    "listen_for": "Look for alignment between the candidate’s drivers and the realities of the role or context.",
                },
                {
                    "category": "work_style",
                    "category_label": "Work style",
                    "question": "How do you prefer to receive goals, feedback and follow-up from a manager?",
                    "why": "Helps understand what management style may support the candidate’s performance.",
                    "listen_for": "Look for self-awareness, clarity around support needs and ability to work with expectations.",
                },
            ],

        }


    return candidate_insights
