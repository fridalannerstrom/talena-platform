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
    large:"Rapportpaketet är för stort. Välj färre rapporter.",done:"Nedladdningen har startat."
  } : {
    open:"Create report package",title:"Select reports",description:"Select completed reports and drag to reorder, or use the arrow buttons.",
    incomplete:"Reports that have not been generated cannot be selected.",all:"Select all",none:"Deselect all",
    up:"Move up",down:"Move down",pdf:"One merged PDF",zip:"Separate PDFs in ZIP",
    generate:"Download",close:"Close",count:"Selected reports",empty:"No completed reports.",
    toc:"Contents",cover:"Report package",progress:"Creating report",preparing:"Combining files...",
    error:"Could not create the report package.",stale:"Reports changed. Reopen the picker.",
    large:"The package is too large. Select fewer reports.",done:"Download started."
  };
  const MAX_REPORTS = 20, MAX_BYTES = 100 * 1024 * 1024, MAX_PAGES = 450, ROWS = 17;
  let workspace=null, trigger=null, dialog=null, list=null, order=[], chosen=new Set(), busy=false;
  const libs={};
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
    dialog.remove();dialog=null;list=null;order=[];chosen.clear();
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
  function load(name,url,ready){
    if(ready())return Promise.resolve();
    if(!libs[name]){
      libs[name]=new Promise((resolve,reject)=>{
        const script=element("script");script.src=url;script.crossOrigin="anonymous";
        script.referrerPolicy="no-referrer";
        script.addEventListener("load",()=>ready()?resolve():reject(Error(t.error)),{once:true});
        script.addEventListener("error",()=>reject(Error(t.error)),{once:true});
        document.head.append(script);
      }).catch(e=>{delete libs[name];throw e;});
    }
    return libs[name];
  }
  function download(blob,name){
    const url=URL.createObjectURL(blob);
    const a=element("a");a.href=url;a.download=name;document.body.append(a);
    try{a.click();}finally{a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),30000);}
  }
  function accent(){
    const hex=workspace?.querySelector("[data-final-output-root]")?.dataset.managerReportBrandPrimary||"#FF6F61";
    return /^#[0-9a-f]{6}$/i.test(hex)?hex:"#FF6F61";
  }
  function makeLink(pdf,target,rect){
    const {PDFName}=window.PDFLib;
    const obj=pdf.context.obj({
      Type:PDFName.of("Annot"),Subtype:PDFName.of("Link"),
      Rect:rect,Border:[0,0,0],Dest:pdf.context.obj([target.ref,PDFName.of("Fit")])
    });
    return pdf.context.register(obj);
  }
  async function merge(entries,coverBlob){
    const {PDFDocument,StandardFonts,PDFName,rgb}=window.PDFLib;
    const pdf=await PDFDocument.create();
    pdf.setTitle(t.cover);pdf.setAuthor("Talena");
    const cover=await PDFDocument.load(await coverBlob.arrayBuffer());
    const importedCover=await pdf.copyPages(cover,cover.getPageIndices());
    importedCover.forEach(page=>pdf.addPage(page));
    const tocPages=Array.from({length:Math.ceil(entries.length/ROWS)},
      ()=>pdf.addPage([595.28,841.89]));
    const targets=[];
    for(const entry of entries){
      const src=await PDFDocument.load(await entry.blob.arrayBuffer());
      if(!src.getPageCount()||pdf.getPageCount()+src.getPageCount()>MAX_PAGES)throw Error(t.large);
      const index=pdf.getPageCount(),pages=await pdf.copyPages(src,src.getPageIndices());
      pages.forEach(page=>pdf.addPage(page));
      targets.push({title:entry.title,start:index});
    }
    const font=await pdf.embedFont(StandardFonts.Helvetica),hex=accent();
    const color=rgb(...[1,3,5].map(n=>parseInt(hex.slice(n,n+2),16)/255));
    tocPages.forEach((page,pageIndex)=>{
      page.drawText(t.toc,{x:52,y:780,size:25,font,color});
      page.drawLine({start:{x:52,y:757},end:{x:544,y:757},thickness:1,color});
      const links=[];
      targets.slice(pageIndex*ROWS,(pageIndex+1)*ROWS).forEach((entry,i)=>{
        const y=710-i*37;
        const title=entry.title.length>59?entry.title.slice(0,56)+"...":entry.title;
        page.drawText(title,{x:56,y,size:12,font});
        page.drawText(String(entry.start+1),{x:510,y,size:11,font,color});
        links.push(makeLink(pdf,pdf.getPage(entry.start),[48,y-12,546,y+24]));
      });
      if(links.length)page.node.set(PDFName.of("Annots"),pdf.context.obj(links));
    });
    return new Blob([await pdf.save()],{type:"application/pdf"});
  }
  async function zipFiles(entries){
    const zip=new window.JSZip();
    entries.forEach(e=>zip.file(e.filename,e.blob));
    return zip.generateAsync({type:"blob",compression:"DEFLATE",compressionOptions:{level:3}});
  }
  async function exportPackage(){
    if(busy||!current())return;
    const ids=order.filter(id=>chosen.has(id)),registry=new Map(available().map(r=>[r.id,r]));
    if(!ids.length||ids.some(id=>!registry.has(id)))return status(t.stale,true);
    const original=workspace;
    const format=dialog.querySelector('input[name="talena-package-mode"]:checked')?.value||"pdf";
    busy=true;refresh();
    dialog.querySelectorAll("button,input").forEach(e=>{e.disabled=true;});
    try{
      status(t.preparing);
      if(format==="zip")
        await load("zip","https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js",
          ()=>typeof window.JSZip==="function");
      else
        await load("pdf","https://cdn.jsdelivr.net/npm/pdf-lib@1.17.1/dist/pdf-lib.min.js",
          ()=>!!window.PDFLib?.PDFDocument);
      let total=0;
      const entries=[];
      for(let i=0;i<ids.length;i++){
        const report=registry.get(ids[i]);
        if(!current()||workspace!==original||!available().some(r=>r.id===report.id))
          throw Error(t.stale);
        status(t.progress+" "+(i+1)+"/"+ids.length+": "+report.title);
        const blob=await api().exportReport(report.id,{returnBlob:true});
        if(blob?.type!=="application/pdf")throw Error(t.error);
        total+=blob.size;if(total>MAX_BYTES)throw Error(t.large);
        entries.push({...report,blob});
      }
      status(t.preparing);
      const output=format==="zip"?await zipFiles(entries):
        await merge(entries,await api().exportCover(t.cover));
      if(!current()||workspace!==original)throw Error(t.stale);
      if(!output?.size||output.size>MAX_BYTES)throw Error(t.large);
      download(output,format==="zip"?"talena-rapporter.zip":"talena-rapportpaket.pdf");
      status(t.done);
    }catch(err){
      status([t.stale,t.large].includes(err?.message)?err.message:t.error,true);
    }finally{
      busy=false;
      dialog?.querySelectorAll("button,input").forEach(e=>{e.disabled=false;});
      if(dialog)redraw();
    }
  }
  function initialize(next){
    if(!next?.isConnected)return;
    if(workspace!==next){if(!busy)discard();workspace=next;}
    if(trigger?.isConnected&&trigger.closest("[data-candidate-insights-workspace]")===workspace)return;
    const nav=workspace.querySelector(".candidate-insights-navigation");
    if(!nav)return;
    trigger=element("button","btn btn-sm talena-package-open",t.open);
    trigger.type="button";trigger.addEventListener("click",open);nav.append(trigger);
  }
  window.TalenaReportPackages=Object.freeze({initialize});
  initialize(document.querySelector("[data-candidate-insights-workspace]"));
})();