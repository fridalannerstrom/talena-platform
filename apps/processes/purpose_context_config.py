from django.utils.translation import gettext_lazy as _

# Talena process context i18n batch 1
PURPOSE_CONTEXT_CONFIG = {
    "recruitment": {
        "tab_label": _("Role context"),
        "context_title": _("Role context"),
        "context_intro": _("Add role information to tailor candidate insights, questions and recommendations to this hiring process."),

        "title_label": _("Role title"),
        "fit_label": _("Role fit"),
        "title_help": _("Example: Business Controller, Sales Manager, Customer Support Specialist."),

        "job_advertisement_label": _("Job advertisement or role description"),
        "job_advertisement_help": _("Paste the job ad or describe the role in your own words."),

        "requirements_profile_label": _("Requirement profile"),
        "requirements_profile_help": _("Describe the key requirements, expectations or selection criteria."),

        "competency_profile_label": _("Competency profile"),
        "competency_profile_help": _("List the behaviours or competencies that matter most in this role."),

        "must_haves_label": _("Must-have requirements"),
        "must_haves_help": _("Add non-negotiable skills, experience, behaviours or conditions."),

        "nice_to_haves_label": _("Nice-to-have requirements"),
        "nice_to_haves_help": _("Add helpful but non-critical requirements."),

        "priorities_label": _("Hiring priorities"),
        "priorities_help": _("What matters most in this hiring decision?"),

        "interview_notes_label": _("Interview focus or notes"),
        "interview_notes_help": _("Add areas you want to validate during interview."),

        "save_button": _("Save role context"),
        "empty_state_title": _("No role context added yet"),
        "empty_state_text": _("Add role context to tailor the candidate insights to this hiring process."),
    },

    "role_match": {
        "tab_label": _("Role match"),
        "context_title": _("Role match context"),
        "context_intro": _("Add information about the target role to assess how the person may match the role."),

        "title_label": _("Target role"),
        "title_help": _("Example: Senior Analyst, Team Lead, Internal Consultant."),

        "job_advertisement_label": _("Role description"),
        "job_advertisement_help": _("Describe the role, team or internal position."),

        "requirements_profile_label": _("Role expectations"),
        "requirements_profile_help": _("Describe what the person needs to handle in this role."),

        "competency_profile_label": _("Important behaviours"),
        "competency_profile_help": _("List behaviours that are important for success in this role."),

        "must_haves_label": _("Critical requirements"),
        "must_haves_help": _("Add the requirements that are most important to validate."),

        "nice_to_haves_label": _("Helpful requirements"),
        "nice_to_haves_help": _("Add additional strengths that would be beneficial."),

        "priorities_label": _("Role match priorities"),
        "priorities_help": _("What should the analysis focus on?"),

        "interview_notes_label": _("Notes or concerns"),
        "interview_notes_help": _("Add anything you want the AI to consider."),

        "save_button": _("Save role match context"),
        "empty_state_title": _("No role match context added yet"),
        "empty_state_text": _("Add target role context to tailor the insights to this role match."),
    },

    "leadership_potential": {
        "tab_label": _("Leadership context"),
        "context_title": _("Leadership potential context"),
        "context_intro": _("Add information about the leadership opportunity, expectations or future role."),

        "title_label": _("Leadership opportunity or future role"),
        "title_help": _("Example: Future team lead, first-time manager, succession candidate."),

        "job_advertisement_label": _("Leadership situation"),
        "job_advertisement_help": _("Describe the leadership situation or opportunity."),

        "requirements_profile_label": _("Leadership expectations"),
        "requirements_profile_help": _("Describe what leadership behaviours are expected."),

        "competency_profile_label": _("Important leadership competencies"),
        "competency_profile_help": _("List the competencies you want to explore."),

        "must_haves_label": _("Critical leadership behaviours"),
        "must_haves_help": _("Add behaviours that are especially important."),

        "nice_to_haves_label": _("Helpful leadership behaviours"),
        "nice_to_haves_help": _("Add behaviours that would be valuable but not critical."),

        "priorities_label": _("Assessment priorities"),
        "priorities_help": _("What should the leadership potential analysis focus on?"),

        "interview_notes_label": _("Reflection or interview notes"),
        "interview_notes_help": _("Add questions, observations or concerns."),

        "save_button": _("Save leadership context"),
        "empty_state_title": _("No leadership context added yet"),
        "empty_state_text": _("Add leadership context to tailor insights to this leadership potential assessment."),
    },

    "leader_development": {
        "tab_label": _("Leadership context"),
        "context_title": _("Leadership development context"),
        "context_intro": _("Add leadership information to tailor the insights to this development situation."),

        "title_label": _("Leadership role or situation"),
        "title_help": _("Example: New manager, senior leader, team lead in change."),

        "job_advertisement_label": _("Leadership context"),
        "job_advertisement_help": _("Describe the current leadership situation."),

        "requirements_profile_label": _("Leadership expectations"),
        "requirements_profile_help": _("Describe what good leadership looks like in this context."),

        "competency_profile_label": _("Important leadership behaviours"),
        "competency_profile_help": _("List leadership behaviours that matter most."),

        "must_haves_label": _("Critical leadership behaviours"),
        "must_haves_help": _("Add behaviours that are essential in this context."),

        "nice_to_haves_label": _("Helpful leadership behaviours"),
        "nice_to_haves_help": _("Add behaviours that would strengthen the person’s leadership."),

        "priorities_label": _("Development goals"),
        "priorities_help": _("What should the person develop or focus on?"),

        "interview_notes_label": _("Coaching or reflection notes"),
        "interview_notes_help": _("Add observations, questions or coaching focus areas."),

        "save_button": _("Save leadership context"),
        "empty_state_title": _("No leadership context added yet"),
        "empty_state_text": _("Add leadership context to tailor the insights to this development situation."),
    },

    "employee_development": {
        "tab_label": _("Development context"),
        "context_title": _("Employee development context"),
        "context_intro": _("Add development information to tailor the insights to this person’s growth situation."),

        "title_label": _("Development situation"),
        "title_help": _("Example: Growth plan, new responsibilities, performance development."),

        "job_advertisement_label": _("Current role or situation"),
        "job_advertisement_help": _("Describe the current role, situation or development need."),

        "requirements_profile_label": _("Current expectations"),
        "requirements_profile_help": _("Describe expectations, responsibilities or performance goals."),

        "competency_profile_label": _("Relevant behaviours"),
        "competency_profile_help": _("List behaviours that are important for development."),

        "must_haves_label": _("Important development areas"),
        "must_haves_help": _("Add the most important areas to work on."),

        "nice_to_haves_label": _("Additional development areas"),
        "nice_to_haves_help": _("Add secondary or longer-term development areas."),

        "priorities_label": _("Development priorities"),
        "priorities_help": _("What should the development conversation focus on?"),

        "interview_notes_label": _("Manager or coaching notes"),
        "interview_notes_help": _("Add notes, observations or questions."),

        "save_button": _("Save development context"),
        "empty_state_title": _("No development context added yet"),
        "empty_state_text": _("Add development context to tailor the insights to this employee’s situation."),
    },

    "career_path": {
        "tab_label": _("Career context"),
        "context_title": _("Career path context"),
        "context_intro": _("Add career information to tailor the insights to possible future paths or development directions."),

        "title_label": _("Career direction or question"),
        "title_help": _("Example: Specialist track, manager track, internal mobility."),

        "job_advertisement_label": _("Career situation"),
        "job_advertisement_help": _("Describe the person’s current career situation or question."),

        "requirements_profile_label": _("Possible future paths"),
        "requirements_profile_help": _("Describe roles, paths or opportunities being considered."),

        "competency_profile_label": _("Relevant strengths or behaviours"),
        "competency_profile_help": _("List behaviours or strengths to explore in relation to career direction."),

        "must_haves_label": _("Important career factors"),
        "must_haves_help": _("Add factors that are important for future fit or satisfaction."),

        "nice_to_haves_label": _("Additional career factors"),
        "nice_to_haves_help": _("Add secondary factors that may influence the path."),

        "priorities_label": _("Career priorities"),
        "priorities_help": _("What should the career guidance focus on?"),

        "interview_notes_label": _("Reflection notes"),
        "interview_notes_help": _("Add notes, questions or career reflections."),

        "save_button": _("Save career context"),
        "empty_state_title": _("No career context added yet"),
        "empty_state_text": _("Add career context to tailor the insights to possible future paths."),
    },

    "onboarding": {
        "tab_label": _("Onboarding context"),
        "context_title": _("Onboarding context"),
        "context_intro": _("Add onboarding information to tailor the insights to the person’s first period in the role."),

        "title_label": _("New role"),
        "title_help": _("Example: Account Manager, Product Owner, Finance Assistant."),

        "job_advertisement_label": _("Role and team context"),
        "job_advertisement_help": _("Describe the new role, team and working environment."),

        "requirements_profile_label": _("Expectations during onboarding"),
        "requirements_profile_help": _("Describe what the person needs to understand or deliver early on."),

        "competency_profile_label": _("Important behaviours during onboarding"),
        "competency_profile_help": _("List behaviours that will help the person settle in successfully."),

        "must_haves_label": _("Critical onboarding needs"),
        "must_haves_help": _("Add support needs or conditions that are especially important."),

        "nice_to_haves_label": _("Helpful onboarding support"),
        "nice_to_haves_help": _("Add helpful support, introductions or resources."),

        "priorities_label": _("First 30–90 day priorities"),
        "priorities_help": _("What should the person focus on during the first period?"),

        "interview_notes_label": _("Handover or onboarding notes"),
        "interview_notes_help": _("Add notes from hiring, manager handover or team context."),

        "save_button": _("Save onboarding context"),
        "empty_state_title": _("No onboarding context added yet"),
        "empty_state_text": _("Add onboarding context to tailor the insights to the first 30–90 days."),
    },

    "team_development": {
        "tab_label": _("Team context"),
        "context_title": _("Team development context"),
        "context_intro": _("Add team information to tailor the insights to collaboration, dynamics and development needs."),

        "title_label": _("Team or group"),
        "title_help": _("Example: Sales team, leadership team, project group."),

        "job_advertisement_label": _("Team context"),
        "job_advertisement_help": _("Describe the team, its purpose and current situation."),

        "requirements_profile_label": _("Team goals or expectations"),
        "requirements_profile_help": _("Describe what the team needs to achieve or improve."),

        "competency_profile_label": _("Important team behaviours"),
        "competency_profile_help": _("List behaviours that matter for collaboration and team performance."),

        "must_haves_label": _("Critical collaboration needs"),
        "must_haves_help": _("Add behaviours or conditions that are especially important."),

        "nice_to_haves_label": _("Helpful team behaviours"),
        "nice_to_haves_help": _("Add behaviours that would strengthen the team."),

        "priorities_label": _("Team development priorities"),
        "priorities_help": _("What should the team development focus on?"),

        "interview_notes_label": _("Notes about team dynamics"),
        "interview_notes_help": _("Add observations, challenges or questions."),

        "save_button": _("Save team context"),
        "empty_state_title": _("No team context added yet"),
        "empty_state_text": _("Add team context to tailor the insights to collaboration and team development."),
    },

    "reorganisation": {
        "tab_label": _("Change context"),
        "context_title": _("Reorganisation context"),
        "context_intro": _("Add information about the change situation to tailor insights to transition, adaptability and future needs."),

        "title_label": _("Change or reorganisation situation"),
        "title_help": _("Example: New structure, changed responsibilities, team merger."),

        "job_advertisement_label": _("Change context"),
        "job_advertisement_help": _("Describe what is changing and why."),

        "requirements_profile_label": _("Future expectations"),
        "requirements_profile_help": _("Describe what the person or team will need to handle after the change."),

        "competency_profile_label": _("Important behaviours in change"),
        "competency_profile_help": _("List behaviours such as adaptability, resilience, communication or structure."),

        "must_haves_label": _("Critical change needs"),
        "must_haves_help": _("Add the most important behaviours or support needs."),

        "nice_to_haves_label": _("Helpful change behaviours"),
        "nice_to_haves_help": _("Add behaviours that would support the transition."),

        "priorities_label": _("Change priorities"),
        "priorities_help": _("What should the reorganisation insight focus on?"),

        "interview_notes_label": _("Change notes"),
        "interview_notes_help": _("Add observations, risks or questions."),

        "save_button": _("Save change context"),
        "empty_state_title": _("No reorganisation context added yet"),
        "empty_state_text": _("Add change context to tailor the insights to this reorganisation."),
    },

    "flexible": {
        "tab_label": _("Process context"),
        "context_title": _("Process context"),
        "context_intro": _("Add context to tailor the candidate insights to this process."),

        "title_label": _("Context title"),
        "title_help": _("Give this context a short title."),

        "job_advertisement_label": _("Main context"),
        "job_advertisement_help": _("Describe the process, situation or purpose."),

        "requirements_profile_label": _("Expectations or criteria"),
        "requirements_profile_help": _("Describe what should be considered in the interpretation."),

        "competency_profile_label": _("Relevant behaviours"),
        "competency_profile_help": _("List behaviours or competencies that matter."),

        "must_haves_label": _("Important factors"),
        "must_haves_help": _("Add factors that are especially important."),

        "nice_to_haves_label": _("Additional factors"),
        "nice_to_haves_help": _("Add helpful but less critical factors."),

        "priorities_label": _("Priorities"),
        "priorities_help": _("What should the interpretation focus on?"),

        "interview_notes_label": _("Notes"),
        "interview_notes_help": _("Add any extra notes or questions."),

        "save_button": _("Save context"),
        "empty_state_title": _("No context added yet"),
        "empty_state_text": _("Add context to tailor the candidate insights to this process."),
    },
}


DEFAULT_PURPOSE_CONTEXT_CONFIG = PURPOSE_CONTEXT_CONFIG["flexible"]


PURPOSE_ALIASES = {
    "hiring": "recruitment",
    "recruiting": "recruitment",
    "recruitment": "recruitment",
    "selection": "recruitment",

    "role_match": "role_match",
    "role match": "role_match",

    "leadership_potential": "leadership_potential",
    "leadership potential": "leadership_potential",

    "leader_development": "leader_development",
    "leader development": "leader_development",
    "leadership_development": "leader_development",
    "leadership development": "leader_development",

    "employee_development": "employee_development",
    "employee development": "employee_development",
    "development": "employee_development",

    "career_path": "career_path",
    "career path": "career_path",

    "onboarding": "onboarding",

    "team_development": "team_development",
    "team development": "team_development",

    "reorganisation": "reorganisation",
    "reorganization": "reorganisation",

    "flexible": "flexible",
    "flexible_process": "flexible",
    "flexible process": "flexible",
}


def normalize_purpose_key(purpose):
    if not purpose:
        return "flexible"

    key = str(purpose).strip().lower()
    key = key.replace("-", "_")

    return PURPOSE_ALIASES.get(key, key)


def get_purpose_context_config(purpose):
    key = normalize_purpose_key(purpose)
    return PURPOSE_CONTEXT_CONFIG.get(key, DEFAULT_PURPOSE_CONTEXT_CONFIG)