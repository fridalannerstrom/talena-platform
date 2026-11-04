/* #449: Lightweight progressive enhancement of the native Details menu.
 * Native <summary> keeps keyboard support even without JavaScript.
 * Existing download buttons and links keep their own handlers/routes.
 */
(() => {
  "use strict";

  function initTeamActionsMenu() {
    const page=document.querySelector(".talena-team-page[data-team-report-brand-primary]");
    const details=page?.querySelector("[data-team-actions-more]");
    if(!details||details.dataset.menuReady==="true")return;
    details.dataset.menuReady="true";

    const summary=details.querySelector("summary");
    const close=(restoreFocus=false)=>{
      if(!details.open)return;
      details.open=false;
      if(restoreFocus)summary?.focus();
    };

    // Close after selecting an action. The original button click/download
    // or anchor navigation still fires, and export feedback stays visible.
    details.addEventListener("click",event=>{
      const action=event.target.closest(".team-actions-more-menu a, .team-actions-more-menu button");
      // Buttons stay on the current page (downloads); restore the visible
      // menu trigger as focus target once their menu row is hidden.
      if(action&&!action.disabled)close(action.tagName==="BUTTON");
    });

    document.addEventListener("pointerdown",event=>{
      if(details.open&&!details.contains(event.target))close();
    });

    document.addEventListener("keydown",event=>{
      if(event.key==="Escape"&&details.open){
        event.preventDefault();
        close(true);
      }
    });

    // When tabbing away from the menu, don't leave a floating menu over
    // the team content (but allow tabbing between menu actions normally).
    details.addEventListener("focusout",event=>{
      if(details.open&&!details.contains(event.relatedTarget))close();
    });
  }

  if(document.readyState==="loading")
    document.addEventListener("DOMContentLoaded",initTeamActionsMenu,{once:true});
  else initTeamActionsMenu();
})();