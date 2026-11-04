/* #449: report picker for ONE authorised team. Report PDFs are created only
 * by the existing #180 / #181 exports, assembled by #360's shared core.
 * Names and member IDs are never exposed while anonymisation is enabled.
 */
(() => {
  "use strict";
  const page=document.querySelector(".talena-team-page[data-team-report-brand-primary]");
  const trigger=page?.querySelector("[data-team-package-open]");
  const outsideStatus=page?.querySelector("[data-team-package-status]");
  if(!page||!trigger||!outsideStatus)return;
  const sv=(document.documentElement.lang||"").toLowerCase().startsWith("sv");
  const t=sv?{
    open:"Skapa teamrapportpaket",title:"Välj teamrapporter",
    description:"Välj vilka rapporter som ska ingå. Dra för att ändra ordning eller använd pilarna.",
    incomplete:"individuella teamprofiler saknas eller är inte färdiga och kan därför inte väljas.",
    summary:"Sammansatt teamrapport",individual:"Individuell teamprofil",
    all:"Välj alla",none:"Avmarkera alla",up:"Flytta upp",down:"Flytta ned",
    pdf:"En sammanslagen PDF",zip:"Separata PDF:er i ZIP",
    count:"Valda rapporter",close:"Stäng",download:"Ladda ner rapportpaket",
    empty:"Det finns inga färdiga teamrapporter att välja.",
    unavailable:"Rapportexporten kunde inte läsas in. Uppdatera sidan och försök igen.",
    anonymous:"Stäng av anonymisering innan du skapar ett identifierande teamrapportpaket.",
    stale:"Teamets rapporter har ändrats. Öppna väljaren igen.",progress:"Skapar rapport",
    preparing:"Sammanställer rapportpaketet…",done:"Nedladdningen har startat.",
    failed:"Rapportpaketet kunde inte skapas.",large:"Rapportpaketet är för stort. Välj färre rapporter.",
    package:"Teamrapportpaket",contents:"Innehåll"
  }:{
    open:"Create team report package",title:"Select team reports",
    description:"Select the reports to include. Drag to reorder or use the arrow buttons.",
    incomplete:"individual team profiles are missing or incomplete and cannot be selected.",
    summary:"Composite team report",individual:"Individual team profile",
    all:"Select all",none:"Deselect all",up:"Move up",down:"Move down",
    pdf:"One merged PDF",zip:"Separate PDFs in ZIP",
    count:"Selected reports",close:"Close",download:"Download report package",
    empty:"No completed team reports are available.",
    unavailable:"Report export could not be loaded. Refresh the page and try again.",
    anonymous:"Turn off anonymisation before creating an identifiable team report package.",
    stale:"Team reports changed. Reopen the picker.",progress:"Creating report",
    preparing:"Assembling report package…",done:"Download started.",
    failed:"Could not create team report package.",large:"The report package is too large. Select fewer reports.",
    package:"Team report package",contents:"Contents"
  };
  const node=(tag,css,text)=>{const x=document.createElement(tag);
    if(css)x.className=css;if(text!==undefined)x.textContent=text;return x;};
  const profileApi=()=>window.TalenaTeamProfilesExport;
  const teamApi=()=>window.TalenaTeamReportExport;
  const pack=()=>window.TalenaReportPackageCore;
  // Distinguish an unavailable client PDF adapter (often an old cached JS
  // file) from a genuinely empty team. Never report zero available reports
  // when the picker was not connected to the existing exporters.
  const adaptersReady=()=>
    typeof profileApi()?.getAvailableProfiles==="function" &&
    typeof teamApi()?.getAvailable==="function" &&
    typeof pack()?.safeFilenamePart==="function";
  // Fail closed if the team anonymity switch is missing or not initialised.
  const isAnon=()=>page.querySelector("#teamAnonymityToggle")?.getAttribute("aria-checked")!=="false";
  const isCurrent=()=>page.isConnected &&
    document.querySelector(".talena-team-page[data-team-report-brand-primary]")===page;
  let dialog=null,list=null,order=[],chosen=new Set(),busy=false,cancelled=false;
  const reportName=()=>pack().safeFilenamePart(page.dataset.teamReportName)||"talena-team";
  function options() {
    if(!isCurrent()||isAnon())return [];
    const entries=[];
    if(teamApi()?.getAvailable())entries.push({
      id:"team-report",type:"shared",title:t.summary,
      filename:reportName()+" - "+t.summary+".pdf"
    });
    const profiles=profileApi()?.getAvailableProfiles()||[];
    profiles.forEach(p=>entries.push({
      id:"member-"+p.id,type:"member",memberId:p.id,
      title:t.individual+": "+p.title,filename:p.filename
    }));
    return entries;
  }
  function status(text,error=false,outer=false) {
    const el=outer?outsideStatus:dialog?.querySelector("[data-package-status]");
    if(!el)return;
    el.textContent=text;el.classList.toggle("is-error",error);
  }
  function refresh() {
    if(!dialog)return;
    const amount=order.filter(id=>chosen.has(id)).length;
    const label=dialog.querySelector("[data-package-count]");
    const action=dialog.querySelector("[data-package-download]");
    label.textContent=t.count+": "+amount;
    action.disabled=busy||amount===0;
  }
  function draw() {
    if(!dialog||!list)return;
    const allowed=new Map(options().map(r=>[r.id,r]));
    order=order.filter(id=>allowed.has(id));
    list.replaceChildren();
    const move=(id,delta)=>{
      const i=order.indexOf(id),dest=i+delta;
      if(dest<0||dest>=order.length)return;
      [order[i],order[dest]]=[order[dest],order[i]];
      draw();
      [...list.children].find(row=>row.dataset.id===id)
        ?.querySelector(delta<0?"[data-up]":"[data-down]")?.focus();
    };
    order.forEach((id,i)=>{
      const entry=allowed.get(id);
      const row=node("li","talena-package-row");row.dataset.id=id;row.draggable=true;
      const grip=node("span","talena-package-handle","⋮⋮");grip.setAttribute("aria-hidden","true");
      const checkbox=node("input","form-check-input");checkbox.type="checkbox";
      checkbox.checked=chosen.has(id);checkbox.setAttribute("aria-label",entry.title);
      checkbox.addEventListener("change",()=>{checkbox.checked?chosen.add(id):chosen.delete(id);refresh();});
      const title=node("span","talena-package-report-title",entry.title);
      const actions=node("span","talena-package-order");
      [-1,1].forEach(direction=>{
        const button=node("button","talena-package-arrow",direction<0?"↑":"↓");
        button.type="button";button.disabled=direction<0?i===0:i===order.length-1;
        button.dataset[direction<0?"up":"down"]="";
        button.title=(direction<0?t.up:t.down)+": "+entry.title;
        button.setAttribute("aria-label",button.title);
        button.addEventListener("click",()=>move(id,direction));
        actions.append(button);
      });
      row.append(grip,checkbox,title,actions);
      row.addEventListener("dragstart",e=>{
        if(busy){e.preventDefault();return;}
        e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",id);
      });
      row.addEventListener("dragover",e=>{if(!busy)e.preventDefault();});
      row.addEventListener("drop",e=>{
        e.preventDefault();if(busy)return;
        const source=e.dataTransfer.getData("text/plain");
        if(!order.includes(source)||source===id)return;
        order.splice(order.indexOf(source),1);
        order.splice(order.indexOf(id),0,source);draw();
      });
      list.append(row);
    });
    refresh();
  }
  function discard() {
    if(!dialog)return;
    dialog.close();dialog.remove();dialog=null;list=null;order=[];chosen.clear();
  }
  function close(){if(!busy)discard();}
  function open() {
    if(busy||!isCurrent())return;
    if(isAnon()){status(t.anonymous,true,true);return;}
    if(!adaptersReady()){status(t.unavailable,true,true);return;}
    const data=options();
    discard();order=data.map(x=>x.id);chosen=new Set(order);
    dialog=node("dialog","talena-package-dialog talena-team-package-dialog");
    dialog.setAttribute("aria-labelledby","talenaTeamPackageTitle");
    const head=node("header","talena-package-head");
    const title=node("h2","",t.title);title.id="talenaTeamPackageTitle";
    const x=node("button","talena-package-x","×");x.type="button";
    x.setAttribute("aria-label",t.close);x.addEventListener("click",close);
    head.append(title,x);
    dialog.append(head,node("p","talena-package-description",t.description));
    const missing=profileApi()?.getMissingCount()||0;
    if(missing)dialog.append(node("p","talena-package-hint",missing+" "+t.incomplete));
    if(data.length){
      const controls=node("div","talena-package-select");
      [[t.all,true],[t.none,false]].forEach(([label,on])=>{
        const button=node("button","talena-package-text-button",label);button.type="button";
        button.addEventListener("click",()=>{chosen=new Set(on?order:[]);draw();});
        controls.append(button);
      });
      list=node("ol","talena-package-list");list.setAttribute("aria-label",t.title);
      dialog.append(controls,list);
    } else dialog.append(node("p","talena-package-description",t.empty));
    const count=node("p","talena-package-count");count.dataset.packageCount="";
    const formats=node("fieldset","talena-package-modes");
    [["pdf",t.pdf],["zip",t.zip]].forEach(([value,label])=>{
      const wrap=node("label","talena-package-mode"),radio=node("input");
      radio.type="radio";radio.name="talena-team-package-format";
      radio.value=value;radio.checked=value==="pdf";
      wrap.append(radio,node("span","",label));formats.append(wrap);
    });
    const message=node("p","talena-package-status");
    message.dataset.packageStatus="";message.setAttribute("role","status");
    message.setAttribute("aria-live","polite");
    const footer=node("footer","talena-package-footer");
    const cancel=node("button","btn btn-light",t.close);
    cancel.type="button";cancel.addEventListener("click",close);
    const action=node("button","btn btn-dark",t.download);
    action.type="button";action.dataset.packageDownload="";action.addEventListener("click",exportPackage);
    footer.append(cancel,action);
    dialog.append(count,formats,message,footer);
    dialog.addEventListener("cancel",e=>{e.preventDefault();close();});
    document.body.append(dialog);dialog.showModal();
    if(list)draw();else refresh();
  }
  function requireCurrent() {
    if(cancelled||!adaptersReady()||!isCurrent()||isAnon()||!profileApi()?.isCurrent()||
      !teamApi()?.isCurrent())throw Error(isAnon()?t.anonymous:t.stale);
  }
  async function exportPackage() {
    if(busy||!dialog||!chosen.size)return;
    requireCurrent();
    const ids=order.filter(id=>chosen.has(id));
    const registry=new Map(options().map(x=>[x.id,x]));
    if(!ids.length||ids.some(id=>!registry.has(id)))return status(t.stale,true);
    const format=dialog.querySelector('input[name="talena-team-package-format"]:checked')?.value||"pdf";
    const filename=reportName()+" - "+t.package+"."+(format==="zip"?"zip":"pdf");
    // Acquire both existing export adapters to block simultaneous legacy
    // downloads and prevent snapshot races with live team charts.
    if(!profileApi().beginPackage())return status(t.stale,true);
    if(!teamApi().beginPackage()){profileApi().endPackage();return status(t.stale,true);}
    cancelled=false;
    busy=true;refresh();
    dialog.querySelectorAll("button,input").forEach(control=>{control.disabled=true;});
    try {
      status(t.preparing);
      await pack().ensure(format);
      requireCurrent();
      let total=0;
      const entries=[];
      for(let i=0;i<ids.length;i++){
        requireCurrent();
        const entry=registry.get(ids[i]);
        if(!options().some(item=>item.id===entry.id))throw Error(t.stale);
        status(t.progress+" "+(i+1)+"/"+ids.length+": "+entry.title);
        const blob=entry.type==="shared"
          ?await teamApi().exportReportForPackage()
          :await profileApi().exportProfileForPackage(entry.memberId);
        requireCurrent();
        if(blob?.type!=="application/pdf")throw Error(t.failed);
        total+=blob.size;
        if(total>pack().MAX_BYTES)throw Error(t.large);
        entries.push({...entry,blob});
      }
      status(t.preparing);
      const output=format==="zip"
        ?await pack().zipFiles(entries)
        :await pack().merge(entries,await teamApi().exportCoverForPackage(t.package),{
          title:t.package,contentsTitle:t.contents,accent:page.dataset.teamReportBrandPrimary
        });
      requireCurrent();
      if(!output?.size||output.size>pack().MAX_BYTES)throw Error(t.large);
      pack().download(output,filename);
      status(t.done);
      status(t.done,false,true);
    }catch(err) {
      const message=err?.code==="REPORT_PACKAGE_TOO_LARGE"?t.large:
        [t.anonymous,t.stale,t.large].includes(err?.message)?err.message:t.failed;
      status(message,true);status(message,true,true);
    }finally {
      busy=false;
      teamApi()?.endPackage();profileApi()?.endPackage();
      if(dialog){dialog.querySelectorAll("button,input").forEach(control=>{control.disabled=false;});draw();}
    }
  }
  function anonymityChanged() {
    const anonymous=isAnon();
    trigger.disabled=anonymous;
    trigger.title=anonymous?t.anonymous:t.open;
    if(anonymous){
      // A privacy toggle permanently cancels the in-flight package, even
      // if names are shown again before its slow PDF rendering finishes.
      if(busy)cancelled=true;
      // Tear down identifying report labels immediately.
      if(dialog)discard();
      status(t.anonymous,true,true);
    }else status("",false,true);
  }
  trigger.addEventListener("click",open);
  const toggle=page.querySelector("#teamAnonymityToggle");
  if(toggle&&typeof MutationObserver!=="undefined"){
    new MutationObserver(anonymityChanged).observe(toggle,{attributes:true,attributeFilter:["aria-checked"]});
  }
  // The template restores the anonymity switch from sessionStorage during
  // DOMContentLoaded. Only reveal the package control once that restoration
  // has run, preventing a one-frame leak of an enabled identifying action.
  const activate=()=>{trigger.hidden=false;anonymityChanged();};
  if(document.readyState==="loading") {
    document.addEventListener("DOMContentLoaded",()=>Promise.resolve().then(activate),{once:true});
  } else activate();
})();