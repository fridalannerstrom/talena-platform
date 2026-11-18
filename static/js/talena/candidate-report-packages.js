/* #360. Browser-only report packs for the currently authorised candidate. */
(() => {
  "use strict";
  if (window.TalenaReportPackages) return;
  const sv = (document.documentElement.lang || "").startsWith("sv");
  const t = sv ? {
    open:"Skapa rapportpaket",title:"Välj rapporter",description:"Välj färdiga rapporter och dra dem i önskad ordning. Du kan också använda pilarna.",
    incomplete:"Rapporter som ännu inte har genererats kan inte väljas.",all:"Välj alla",none:"Avmarkera alla",
    up:"Flytta upp",down:"Flytta ned",pdf:"En sammanslagen PDF",zip:"Separata PDF:er i ZIP",
    generate:"Ladda ner",close:"Stäng",count:"Valda rapporter",empty:"Inga färdiga rapporter.",
    toc:"Innehåll",cover:"Rapportpaket",progress:"Skapar rapport",preparing:"Sammanställer filer...",
    error:"Rapportpaketet kunde inte skapas.",stale:"Rapporterna har ändrats. Öppna väljaren igen.",
    large:"Rapportpaketet är för stort. Välj färre rapporter.",done:"Nedladdningen har startat.",
    reportError:"Det gick inte att skapa PDF för",reportHint:"Prova att ladda ner rapporten separat eller avmarkera den.",
    chartHint:"Ett diagram är inte färdigrenderat. Öppna rapporten och försök igen.",
    managerHint:"Chefsrapportens PDF-underlag kunde inte förberedas. Prova rapportens egen PDF-knapp.",
    combineError:"De enskilda rapporterna skapades, men paketet kunde inte sättas ihop."
  } : {
    open:"Create report package",title:"Select reports",description:"Select completed reports and drag to reorder, or use the arrow buttons.",
    incomplete:"Reports that have not been generated cannot be selected.",all:"Select all",none:"Deselect all",
    up:"Move up",down:"Move down",pdf:"One merged PDF",zip:"Separate PDFs in ZIP",
    generate:"Download",close:"Close",count:"Selected reports",empty:"No completed reports.",
    toc:"Contents",cover:"Report package",progress:"Creating report",preparing:"Combining files...",
    error:"Could not create the report package.",stale:"Reports changed. Reopen the picker.",
    large:"The package is too large. Select fewer reports.",done:"Download started.",
    reportError:"Could not create the PDF for",reportHint:"Try downloading that report separately or deselect it.",
    chartHint:"A chart is not ready. Open the report and try again.",
    managerHint:"Could not prepare the manager report PDF. Try its own PDF button.",
    combineError:"The individual PDFs were created, but the package could not be assembled."
  };
  const MAX_REPORTS = 20, MAX_BYTES = 100 * 1024 * 1024, MAX_PAGES = 450, ROWS = 17;
  let workspace=null, trigger=null, dialog=null, list=null, order=[], chosen=new Set(), busy=false, failedReportId=null;
  const element=(tag,cls,text)=>{
    const e=document.createElement(tag); if(cls)e.className=cls;
    if(text!==undefined)e.textContent=text; return e;
  };
  const api=()=>window.TalenaCandidateReports;
  const current=()=>workspace?.isConnected && document.querySelector("[data-candidate-insights-workspace]")===workspace;
  const available=()=>current()&&api()
    ? api().getAvailableReports().filter(r=>/^[a-z0-9-]+$/.test(r.id)).slice(0,MAX_REPORTS) : [];
  const status=(message,error=false)=>{
    const e=dialog?.querySelector("[data-package-status]");
    if(e){e.textContent=message;e.classList.toggle("is-error",error);}
  };
  function refresh(){
    if(!dialog)return;
    const count=order.filter(id=>chosen.has(id)).length;
    dialog.querySelector("[data-package-count]").textContent=t.count+": "+count;
    dialog.querySelector("[data-package-download]").disabled=busy||count===0;
  }
  function redraw(){
    if(!list)return;
    const reports=new Map(available().map(r=>[r.id,r]));
    order=order.filter(id=>reports.has(id));
    list.replaceChildren();
    const move=(id,direction)=>{
      const n=order.indexOf(id),other=n+direction;
      if(other<0||other>=order.length)return;
      [order[n],order[other]]=[order[other],order[n]];
      redraw();
      const row=[...list.children].find(r=>r.dataset.id===id);
      row?.querySelector(direction<0?"[data-move-up]":"[data-move-down]")?.focus();
    };
    order.forEach((id,index)=>{
      const report=reports.get(id),li=element("li","talena-package-row");
      li.dataset.id=id;li.draggable=true;
      li.classList.toggle("is-failed",failedReportId===id);
      const handle=element("span","talena-package-handle","⋮⋮");
      handle.setAttribute("aria-hidden","true");
      const checkbox=element("input","form-check-input");checkbox.type="checkbox";checkbox.checked=chosen.has(id);
      checkbox.setAttribute("aria-label",report.title);
      checkbox.addEventListener("change",()=>{checkbox.checked?chosen.add(id):chosen.delete(id);refresh();});
      const title=element("span","talena-package-report-title",report.title);
      const buttons=element("span","talena-package-order");
      [-1,1].forEach(direction=>{
        const b=element("button","talena-package-arrow",direction<0?"↑":"↓");
        b.type="button";b.disabled=direction<0?index===0:index===order.length-1;
        b.dataset[direction<0?"moveUp":"moveDown"]="";
        b.title=(direction<0?t.up:t.down)+": "+report.title;
        b.setAttribute("aria-label",b.title);
        b.addEventListener("click",()=>move(id,direction));
        buttons.append(b);
      });
      li.append(handle,checkbox,title,buttons);
      li.addEventListener("dragstart",e=>{
        if(busy){e.preventDefault();return;}
        e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",id);
      });
      li.addEventListener("dragover",e=>{if(!busy)e.preventDefault();});
      li.addEventListener("drop",e=>{
        e.preventDefault();if(busy)return;
        const dragged=e.dataTransfer.getData("text/plain");
        if(!order.includes(dragged)||dragged===id)return;
        order.splice(order.indexOf(dragged),1);
        order.splice(order.indexOf(id),0,dragged);redraw();
      });
      list.append(li);
    });
    refresh();
  }
  function close(){if(!busy)dialog?.close();}
  function discard(){
    if(!dialog)return;
    if(dialog.open)dialog.close();
    dialog.remove();dialog=null;list=null;order=[];chosen.clear();failedReportId=null;
  }
  function open(){
    if(!current()||busy)return;
    discard();
    const reports=available();
    order=reports.map(r=>r.id);chosen=new Set(order);
    dialog=element("dialog","talena-package-dialog");
    dialog.setAttribute("aria-labelledby","talenaPackageTitle");
    const head=element("header","talena-package-head");
    const h=element("h2","",t.title);h.id="talenaPackageTitle";
    const x=element("button","talena-package-x","×");x.type="button";
    x.setAttribute("aria-label",t.close);x.addEventListener("click",close);
    head.append(h,x);
    dialog.append(head,element("p","talena-package-description",t.description),
      element("p","talena-package-hint",t.incomplete));
    if(!reports.length)dialog.append(element("p","",t.empty));
    else{
      const buttons=element("div","talena-package-select");
      [[t.all,true],[t.none,false]].forEach(([title,on])=>{
        const b=element("button","talena-package-text-button",title);b.type="button";
        b.addEventListener("click",()=>{chosen=new Set(on?order:[]);redraw();});
        buttons.append(b);
      });
      list=element("ol","talena-package-list");list.setAttribute("aria-label",t.title);
      dialog.append(buttons,list);
    }
    const count=element("p","talena-package-count");count.dataset.packageCount="";
    const modes=element("fieldset","talena-package-modes");
    [["pdf",t.pdf],["zip",t.zip]].forEach(([value,label])=>{
      const wrapper=element("label","talena-package-mode");
      const radio=element("input");radio.type="radio";radio.name="talena-package-mode";
      radio.value=value;radio.checked=value==="pdf";
      wrapper.append(radio,element("span","",label));modes.append(wrapper);
    });
    const progress=element("p","talena-package-status");progress.dataset.packageStatus="";
    progress.setAttribute("role","status");progress.setAttribute("aria-live","polite");
    const foot=element("footer","talena-package-footer");
    const cancel=element("button","btn btn-light",t.close);cancel.type="button";cancel.addEventListener("click",close);
    const download=element("button","btn btn-dark",t.generate);download.type="button";
    download.dataset.packageDownload="";download.addEventListener("click",exportPackage);
    foot.append(cancel,download);
    dialog.append(count,modes,progress,foot);
    dialog.addEventListener("cancel",e=>{if(busy)e.preventDefault();});
    document.body.append(dialog);dialog.showModal();
    if(list)redraw();else refresh();
  }
  function accent(){
    const hex=workspace?.querySelector("[data-final-output-root]")
      ?.dataset.managerReportBrandPrimary||"#FF6F61";
    return /^#[0-9a-f]{6}$/i.test(hex)?hex:"#FF6F61";
  }
  function safeFailureHint(error) {
    // Only show allowlisted error categories, never raw server/renderer messages.
    // Those may include URLs or candidate-related data.
    const message=String(error?.message||"");
    if(message==="Chart not ready")return t.chartHint;
    if(message.startsWith("Manager report attribution")||
       message==="Missing verified PDF attribution")return t.managerHint;
    return t.reportHint;
  }
  async function exportPackage(){
    if(busy||!current())return;
    const ids=order.filter(id=>chosen.has(id)),registry=new Map(available().map(r=>[r.id,r]));
    if(!ids.length||ids.some(id=>!registry.has(id)))return status(t.stale,true);
    const original=workspace;
    const format=dialog.querySelector('input[name="talena-package-mode"]:checked')?.value||"pdf";
    // Resolve a safe filename from this candidate before asynchronous exports.
    // ZIP entries already get their names from getAvailableReports().
    const packageFilename=api().getPackageFilename(format);
    busy=true;failedReportId=null;refresh();
    list?.querySelectorAll(".talena-package-row").forEach(row=>row.classList.remove("is-failed"));
    dialog.querySelectorAll("button,input").forEach(e=>{e.disabled=true;});
    let failingReport=null,assembling=false;
    try{
      status(t.preparing);
      await window.TalenaReportPackageCore.ensure(format);
      let total=0;
      const entries=[];
      for(let i=0;i<ids.length;i++){
        const report=registry.get(ids[i]);
        if(!current()||workspace!==original||!available().some(r=>r.id===report.id))
          throw Error(t.stale);
        failingReport=report;
        status(t.progress+" "+(i+1)+"/"+ids.length+": "+report.title);
        // Let the browser paint the actual report number before html2canvas
        // starts its potentially long synchronous capture.
        await new Promise(resolve=>requestAnimationFrame(resolve));
        const blob=await api().exportReport(report.id,{returnBlob:true});
        if(blob?.type!=="application/pdf"||!blob.size)throw Error("Empty report PDF");
        total+=blob.size;if(total>MAX_BYTES)throw Error(t.large);
        entries.push({...report,blob});
        failingReport=null;
      }
      assembling=true;
      status(t.preparing);
      await new Promise(resolve=>requestAnimationFrame(resolve));
      const core=window.TalenaReportPackageCore;
      const output=format==="zip"?await core.zipFiles(entries):
        await core.merge(entries,await api().exportCover(t.cover),
          {title:t.cover,contentsTitle:t.toc,accent:accent()});
      if(!current()||workspace!==original)throw Error(t.stale);
      if(!output?.size||output.size>MAX_BYTES)throw Error(t.large);
      window.TalenaReportPackageCore.download(output,packageFilename);
      void window.TalenaReportExportActivity?.record?.(
        original?.dataset?.reportExportReceiptUrl, "candidate-package-"+format
      );
      status(t.done);
    }catch(err){
      if(err?.code==="REPORT_PACKAGE_TOO_LARGE"||err?.message===t.large) {
        status(t.large,true);
      } else if(err?.message===t.stale) {
        status(t.stale,true);
      } else if(failingReport) {
        failedReportId=failingReport.id;
        // Titles come from the authorised report picker; never print error
        // payloads or raw responses that might include candidate data.
        status(t.reportError+" “"+failingReport.title+"”. "+safeFailureHint(err),true);
        console.warn("Talena report package: individual PDF export failed",{reportId:failingReport.id});
      } else {
        status(assembling?t.combineError:t.error,true);
        console.warn("Talena report package: assembly failed",{format});
      }
    }finally{
      busy=false;
      dialog?.querySelectorAll("button,input").forEach(e=>{e.disabled=false;});
      if(dialog)redraw();
    }
  }
  function initialize(next){
    if(!next?.isConnected)return;
    if(workspace!==next){if(!busy)discard();workspace=next;}
    // The export action belongs to the candidate header (name/status row).
    // Never attach it to the Insights tabs: the button should stay in the
    // upper-right corner when a user changes report tabs.
    const sheet=workspace.closest(".candidate-sheet-layout");
    const headerActions=sheet?.querySelector(".candidate-profile-header .candidate-profile-actions");
    if(!headerActions)return;
    // The opener is OUTSIDE the insights workspace now. Checking closest()
    // against the workspace would add duplicates after each AJAX refresh.
    if(trigger?.isConnected&&trigger.parentElement===headerActions)return;
    trigger=element("button","btn btn-sm talena-package-open",t.open);
    trigger.type="button";
    trigger.setAttribute("data-candidate-report-package-open","");
    trigger.addEventListener("click",open);
    headerActions.append(trigger);
  }
  window.TalenaReportPackages=Object.freeze({initialize});
  initialize(document.querySelector("[data-candidate-insights-workspace]"));
})();