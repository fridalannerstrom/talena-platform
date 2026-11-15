"use strict";
// Guard the contract between candidate chart technology and PDF export.
// Static template checks complement the functional hidden-Motivation test.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const read=p=>fs.readFileSync(p,"utf8");
const base="templates/customer/processes/partials/";
const team=read(base+"candidate_insights/tabs/_team_styles.html");
const sharedTeam=read(base+"_team_styles.html");
const leadership=read(base+"candidate_insights/tabs/_leadership_report.html");
const derailment=read(base+"candidate_insights/tabs/_derailment_report.html");
const motivation=read(base+"candidate_insights/motivation/_results.html");
const registry=read("static/js/talena/candidate-report-export.js");
const teamProfileExport=read("static/js/talena/team-profile-export.js");

assert.ok(team.includes("team_style_use_svg=True"),
  "Candidate team report must use server-rendered SVG; canvas needs explicit export fallback");
assert.ok(sharedTeam.includes("{% if team_style_use_svg %}")&&
  sharedTeam.includes("team_style_profile.chart_svg|safe"),
  "Team report SVG option and SVG content must stay available");
assert.ok(leadership.includes("leadership_report_content.chart_svg|safe")&&
  !leadership.includes("<canvas"),
  "Leadership PDF uses a server-rendered SVG, not a lazy canvas");
assert.ok(!derailment.includes("<canvas"),
  "Derailment scales should not introduce an unhandled canvas");
assert.ok(motivation.includes("data-motivation-rose-chart")&&
  registry.includes('window.TalenaPdfMotivationRose.render(source)'),
  "Lazy Motivation canvas must have an offscreen PDF renderer");
assert.ok(teamProfileExport.includes("TalenaTeamProfileCharts?.render(profile)")&&
  teamProfileExport.includes("chart.resize()"),
  "Separate team member PDF exporter must initialise its canvas before capture");
console.log("Candidate chart coverage: Team/Leadership SVG, Derailment HTML, Motivation canvas fallback, team-member PDF preparation OK");
