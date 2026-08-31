from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.processes.models import (
    Candidate,
    HistoricalAssessmentResult,
    HistoricalAssessmentScore,
    HistoricalProcessCandidate,
    TestProcess,
)
from apps.teams.models import Team, TeamMembership


SEED_SOURCE = "talena_dev_team_seed"
PRODUCTION_ENVIRONMENTS = {"prod", "production"}
SAFE_NON_DEBUG_ENVIRONMENTS = {"local", "dev", "development", "test", "testing"}

TEAM_STYLE_ORDER = (
    "Connector",
    "Catalyst",
    "Director",
    "Energiser",
    "Architect",
    "Harmoniser",
    "Analyst",
    "Auditor",
)

PERSONALITY_TRAITS = (
    "Cooperative",
    "Empathy",
    "Supporting",
    "Connecting",
    "Dynamic",
    "Influential",
    "Goal-focused",
    "Structured",
    "Analytical",
    "Complex Thinking",
    "Creativity",
    "Adaptability",
    "Straightforward",
    "Status Avoidance",
    "Modesty",
    "Resilience",
    "Emotional Control",
    "Independence",
)

MOTIVATION_FACTORS = (
    "Attachment",
    "Customer Service",
    "Work Life Balance",
    "People Development",
    "Stability",
    "Authority",
    "Acquisition",
    "Independence",
    "Recognition",
    "Making a Difference",
    "Achievement",
    "Quality",
    "Learning",
    "Ethics",
    "Commercial Focus",
)

DEMO_PROFILES = (
    {
        "key": "analytical",
        "first_name": "Demo Ada",
        "last_name": "Analys",
        "team_styles": {
            "Connector": 3,
            "Catalyst": 4,
            "Director": 6,
            "Energiser": 4,
            "Architect": 9,
            "Harmoniser": 5,
            "Analyst": 10,
            "Auditor": 9,
        },
        "personality": {
            "Cooperative": 5,
            "Empathy": 4,
            "Supporting": 4,
            "Connecting": 3,
            "Dynamic": 5,
            "Influential": 5,
            "Goal-focused": 8,
            "Structured": 9,
            "Analytical": 10,
            "Complex Thinking": 9,
            "Creativity": 6,
            "Adaptability": 5,
            "Straightforward": 8,
            "Status Avoidance": 6,
            "Modesty": 7,
            "Resilience": 8,
            "Emotional Control": 8,
            "Independence": 9,
        },
        "motivation": {
            "Attachment": 2.5,
            "Customer Service": 3,
            "Work Life Balance": 3.5,
            "People Development": 2.5,
            "Stability": 3,
            "Authority": 3.5,
            "Acquisition": 3,
            "Independence": 5,
            "Recognition": 2.5,
            "Making a Difference": 3.5,
            "Achievement": 4.5,
            "Quality": 5,
            "Learning": 5,
            "Ethics": 4,
            "Commercial Focus": 4.5,
        },
        "abilities": {"verbal": 62, "logical": 88, "numerical": 91},
    },
    {
        "key": "energetic",
        "first_name": "Demo Leo",
        "last_name": "Energi",
        "team_styles": {
            "Connector": 10,
            "Catalyst": 9,
            "Director": 8,
            "Energiser": 10,
            "Architect": 4,
            "Harmoniser": 7,
            "Analyst": 4,
            "Auditor": 3,
        },
        "personality": {
            "Cooperative": 7,
            "Empathy": 7,
            "Supporting": 6,
            "Connecting": 10,
            "Dynamic": 10,
            "Influential": 9,
            "Goal-focused": 9,
            "Structured": 5,
            "Analytical": 5,
            "Complex Thinking": 7,
            "Creativity": 9,
            "Adaptability": 9,
            "Straightforward": 5,
            "Status Avoidance": 3,
            "Modesty": 3,
            "Resilience": 8,
            "Emotional Control": 6,
            "Independence": 7,
        },
        "motivation": {
            "Attachment": 4.5,
            "Customer Service": 4.5,
            "Work Life Balance": 2.5,
            "People Development": 4,
            "Stability": 2,
            "Authority": 4.5,
            "Acquisition": 4,
            "Independence": 4.5,
            "Recognition": 5,
            "Making a Difference": 3.5,
            "Achievement": 5,
            "Quality": 3,
            "Learning": 4.5,
            "Ethics": 3.5,
            "Commercial Focus": 5,
        },
        "abilities": {"verbal": 86, "logical": 58, "numerical": 44},
    },
    {
        "key": "balanced",
        "first_name": "Demo Mira",
        "last_name": "Balans",
        "team_styles": {
            "Connector": 7,
            "Catalyst": 6,
            "Director": 5,
            "Energiser": 6,
            "Architect": 7,
            "Harmoniser": 9,
            "Analyst": 7,
            "Auditor": 8,
        },
        "personality": {
            "Cooperative": 9,
            "Empathy": 9,
            "Supporting": 9,
            "Connecting": 7,
            "Dynamic": 6,
            "Influential": 5,
            "Goal-focused": 6,
            "Structured": 7,
            "Analytical": 7,
            "Complex Thinking": 6,
            "Creativity": 6,
            "Adaptability": 7,
            "Straightforward": 7,
            "Status Avoidance": 8,
            "Modesty": 8,
            "Resilience": 7,
            "Emotional Control": 8,
            "Independence": 6,
        },
        "motivation": {
            "Attachment": 5,
            "Customer Service": 4,
            "Work Life Balance": 4,
            "People Development": 5,
            "Stability": 4,
            "Authority": 2.5,
            "Acquisition": 2.5,
            "Independence": 3.5,
            "Recognition": 3,
            "Making a Difference": 5,
            "Achievement": 3.5,
            "Quality": 4,
            "Learning": 4,
            "Ethics": 5,
            "Commercial Focus": 3,
        },
        "abilities": {"verbal": 72, "logical": 71, "numerical": 66},
    },
)


class Command(BaseCommand):
    help = (
        "Create three synthetic candidates with complete assessment data for "
        "testing team reports. No Sova requests or emails are sent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--process-id",
            type=int,
            required=True,
            help="TestProcess id that should own the synthetic candidates.",
        )
        parser.add_argument(
            "--team-id",
            type=int,
            help="Optional Team id. When supplied, demo candidates are added to it.",
        )
        parser.add_argument(
            "--allow-non-debug",
            action="store_true",
            help=(
                "Allow the command in a recognised non-production environment "
                "when DEBUG is false. Production is always blocked."
            ),
        )

    def handle(self, *args, **options):
        self._assert_safe_environment(options["allow_non_debug"])

        try:
            process = TestProcess.objects.select_related("company").get(
                pk=options["process_id"]
            )
        except TestProcess.DoesNotExist as exc:
            raise CommandError(
                f"No test process exists with id {options['process_id']}."
            ) from exc

        team = self._get_team(options.get("team_id"), process)
        now = timezone.now()
        created_candidates = 0
        updated_candidates = 0

        with transaction.atomic():
            for profile in DEMO_PROFILES:
                candidate, was_created = self._upsert_candidate(process, profile)
                if was_created:
                    created_candidates += 1
                else:
                    updated_candidates += 1

                historical_candidate = self._upsert_process_candidate(
                    process=process,
                    candidate=candidate,
                    profile=profile,
                    completed_at=now,
                )
                self._write_assessment_data(
                    process=process,
                    candidate=candidate,
                    historical_candidate=historical_candidate,
                    profile=profile,
                    completed_at=now,
                )

                if team is not None:
                    TeamMembership.objects.update_or_create(
                        team=team,
                        candidate=candidate,
                        defaults={
                            "role": "Demo profile",
                            "source": SEED_SOURCE,
                        },
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Synthetic team-report data ready for process {process.id} "
            f"({process.name})."
        ))
        self.stdout.write(
            f"Candidates: {created_candidates} created, "
            f"{updated_candidates} refreshed."
        )
        if team is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All three demo candidates are members of team {team.id} "
                    f"({team.name})."
                )
            )
        else:
            self.stdout.write(
                "No --team-id supplied. Add the demo candidates to a team in "
                "Talena, or rerun this command with --team-id."
            )

    def _assert_safe_environment(self, allow_non_debug):
        environment = str(getattr(settings, "ENVIRONMENT", "local") or "local")
        environment = environment.strip().lower()

        if environment in PRODUCTION_ENVIRONMENTS:
            raise CommandError(
                "Refusing to create synthetic candidate data in production."
            )

        if settings.DEBUG:
            return

        if environment in SAFE_NON_DEBUG_ENVIRONMENTS and allow_non_debug:
            return

        raise CommandError(
            "DEBUG is false. If this is an isolated dev environment, rerun "
            "with --allow-non-debug. Production remains blocked."
        )

    def _get_team(self, team_id, process):
        if not team_id:
            return None

        try:
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist as exc:
            raise CommandError(f"No team exists with id {team_id}.") from exc

        if process.company_id and team.company_id != process.company_id:
            raise CommandError(
                "The selected team belongs to a different company than the process."
            )

        return team

    def _upsert_candidate(self, process, profile):
        email = (
            f"talena.demo.team.{process.id}.{profile['key']}@example.invalid"
        )
        return Candidate.objects.update_or_create(
            email=email,
            defaults={
                "first_name": profile["first_name"],
                "last_name": profile["last_name"],
            },
        )

    def _upsert_process_candidate(
        self,
        *,
        process,
        candidate,
        profile,
        completed_at,
    ):
        sova_candidate_id = (
            f"talena-dev-demo-{process.id}-{profile['key']}"
        )
        historical_candidate, _ = HistoricalProcessCandidate.objects.update_or_create(
            process=process,
            candidate=candidate,
            sova_candidate_id=sova_candidate_id,
            defaults={
                "status": "completed",
                "completed_at": completed_at,
                "notes": (
                    "[DEV DEMO] Synthetic assessment data generated by "
                    "seed_team_report_demo. Not a real candidate or Sova result."
                ),
            },
        )
        return historical_candidate

    def _write_assessment_data(
        self,
        *,
        process,
        candidate,
        historical_candidate,
        profile,
        completed_at,
    ):
        personality_scores = []
        for name in TEAM_STYLE_ORDER:
            personality_scores.append(
                {
                    "name": name,
                    "category": "team_style",
                    "score": profile["team_styles"][name],
                }
            )
        for name in PERSONALITY_TRAITS:
            personality_scores.append(
                {
                    "name": name,
                    "category": "personality",
                    "score": profile["personality"][name],
                }
            )

        self._replace_result(
            process=process,
            candidate=candidate,
            historical_candidate=historical_candidate,
            profile_key=profile["key"],
            assessment_type="personality",
            scale="sten",
            scores=personality_scores,
            completed_at=completed_at,
        )

        self._replace_result(
            process=process,
            candidate=candidate,
            historical_candidate=historical_candidate,
            profile_key=profile["key"],
            assessment_type="motivation",
            scale="one_to_five",
            scores=[
                {
                    "name": name,
                    "category": "motivation",
                    "score": profile["motivation"][name],
                }
                for name in MOTIVATION_FACTORS
            ],
            completed_at=completed_at,
        )

        for ability, percentile in profile["abilities"].items():
            self._replace_result(
                process=process,
                candidate=candidate,
                historical_candidate=historical_candidate,
                profile_key=profile["key"],
                assessment_type=ability,
                scale="percentile",
                scores=[
                    {
                        "name": f"{ability.title()} Percentile",
                        "category": "ability",
                        "percentile": percentile,
                    }
                ],
                completed_at=completed_at,
            )

    def _replace_result(
        self,
        *,
        process,
        candidate,
        historical_candidate,
        profile_key,
        assessment_type,
        scale,
        scores,
        completed_at,
    ):
        result_id = (
            f"talena-dev-demo-{process.id}-{profile_key}-{assessment_type}"
        )
        result, _ = HistoricalAssessmentResult.objects.update_or_create(
            process=process,
            candidate=candidate,
            assessment_type=assessment_type,
            scale=scale,
            sova_result_id=result_id,
            defaults={
                "historical_candidate": historical_candidate,
                "sova_candidate_id": historical_candidate.sova_candidate_id,
                "status": "completed",
                "language": "en",
                "time_added": completed_at,
                "time_completed": completed_at,
                "raw_data": {
                    "synthetic": True,
                    "source": SEED_SOURCE,
                    "profile": profile_key,
                },
            },
        )

        # This result id is owned exclusively by this seed command. Replacing
        # its score rows keeps reruns deterministic when demo profiles evolve.
        result.scores.all().delete()

        HistoricalAssessmentScore.objects.bulk_create(
            [
                HistoricalAssessmentScore(
                    result=result,
                    name=item["name"],
                    category=item["category"],
                    scale=scale,
                    score=item.get("score"),
                    percentile=item.get("percentile"),
                    raw_value=str(
                        item.get("percentile")
                        if item.get("percentile") is not None
                        else item.get("score")
                    ),
                )
                for item in scores
            ]
        )
