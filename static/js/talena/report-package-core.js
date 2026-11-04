/* Shared, in-browser ZIP and PDF package assembler for candidate/team reports.
 * Only consumes existing PDF Blobs from authorised page export adapters.
 * No candidate API requests, AI calls, server writes or remote PDF uploads.
 */
(() => {
  "use strict";
  if (window.TalenaReportPackageCore) return;
  const MAX_REPORTS=40, MAX_BYTES=100*1024*1024, MAX_PAGES=450, ROWS=17;
  const loading={};
  function load(name,url,ready) {
    if(ready())return Promise.resolve();
    if(!loading[name]){
      loading[name]=new Promise((resolve,reject)=>{
        const script=document.createElement("script");
        script.src=url;script.crossOrigin="anonymous";script.referrerPolicy="no-referrer";
        script.addEventListener("load",()=>ready()?resolve():reject(Error("PDF package library unavailable")),{once:true});
        script.addEventListener("error",()=>reject(Error("PDF package library unavailable")),{once:true});
        document.head.append(script);
      }).catch(err=>{delete loading[name];throw err;});
    }
    return loading[name];
  }
  async function ensure(format) {
    if(format==="zip")return load("jszip",
      "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js",
      ()=>typeof window.JSZip==="function");
    if(format==="pdf")return load("pdf-lib",
      "https://cdn.jsdelivr.net/npm/pdf-lib@1.17.1/dist/pdf-lib.min.js",
      ()=>!!window.PDFLib?.PDFDocument);
    throw Error("Unsupported report package type");
  }
  function safeFilenamePart(value) {
    return Array.from(String(value||"").normalize("NFC")
      .replace(/[\u0000-\u001F\u007F-\u009F\u200B-\u200F\u202A-\u202E\u2066-\u2069<>:"/\\|?*]/g," ")
      .replace(/\s+/g," ").trim()).slice(0,90).join("")
      .replace(/[.\s-]+$/g,"");
  }
  function color(hex) {
    const value=/^#[\da-f]{6}$/i.test(hex||"")?hex:"#FF6F61";
    const values=[1,3,5].map(i=>parseInt(value.slice(i,i+2),16)/255);
    return window.PDFLib.rgb(...values);
  }
  function link(pdf,target,rectangle){
    const {PDFName}=window.PDFLib;
    return pdf.context.register(pdf.context.obj({
      Type:PDFName.of("Annot"),Subtype:PDFName.of("Link"),
      Rect:rectangle,Border:[0,0,0],
      Dest:pdf.context.obj([target.ref,PDFName.of("Fit")])
    }));
  }
  function validateEntries(entries) {
    if(!Array.isArray(entries)||!entries.length||entries.length>MAX_REPORTS)
      throw Error("Invalid report package selection");
    let total=0;
    for(const entry of entries){
      if(!entry||typeof entry.title!=="string"||entry.blob?.type!=="application/pdf"||
        !entry.filename||!safeFilenamePart(entry.filename))throw Error("Invalid report PDF");
      total+=entry.blob.size;
      if(total>MAX_BYTES)throw Error("Report package too large");
    }
  }
  async function merge(entries,coverBlob,options={}) {
    validateEntries(entries);
    if(coverBlob?.type!=="application/pdf")throw Error("Package cover unavailable");
    await ensure("pdf");
    const {PDFDocument,StandardFonts,PDFName}=window.PDFLib;
    const pdf=await PDFDocument.create();
    pdf.setTitle(options.title||"Talena report package");
    pdf.setAuthor("Talena");
    const cover=await PDFDocument.load(await coverBlob.arrayBuffer());
    const covers=await pdf.copyPages(cover,cover.getPageIndices());
    covers.forEach(page=>pdf.addPage(page));
    const tocPages=Array.from({length:Math.ceil(entries.length/ROWS)},
      ()=>pdf.addPage([595.28,841.89]));
    const targets=[];
    for(const entry of entries){
      const source=await PDFDocument.load(await entry.blob.arrayBuffer());
      const count=source.getPageCount();
      if(!count||pdf.getPageCount()+count>MAX_PAGES)throw Error("Report package too large");
      const start=pdf.getPageCount();
      const pages=await pdf.copyPages(source,source.getPageIndices());
      pages.forEach(page=>pdf.addPage(page));
      targets.push({title:entry.title,start});
    }
    const font=await pdf.embedFont(StandardFonts.Helvetica);
    const accent=color(options.accent);
    tocPages.forEach((page,i)=>{
      page.drawText(options.contentsTitle||"Contents",{x:52,y:780,size:25,font,color:accent});
      page.drawLine({start:{x:52,y:757},end:{x:544,y:757},thickness:1,color:accent});
      const links=[];
      targets.slice(i*ROWS,(i+1)*ROWS).forEach((entry,j)=>{
        const y=710-j*37;
        const title=entry.title.length>59?entry.title.slice(0,56)+"...":entry.title;
        page.drawText(title,{x:56,y,size:12,font});
        page.drawText(String(entry.start+1),{x:510,y,size:11,font,color:accent});
        links.push(link(pdf,pdf.getPage(entry.start),[48,y-12,546,y+24]));
      });
      if(links.length)page.node.set(PDFName.of("Annots"),pdf.context.obj(links));
    });
    const data=await pdf.save();
    if(data.byteLength>MAX_BYTES)throw Error("Report package too large");
    return new Blob([data],{type:"application/pdf"});
  }
  async function zipFiles(entries) {
    validateEntries(entries);
    await ensure("zip");
    const zip=new window.JSZip();
    // ZIP viewers often sort names alphabetically; prefix selected order.
    const digits=String(entries.length).length;
    entries.forEach((entry,i)=>{
      const prefix=String(i+1).padStart(Math.max(digits,2),"0")+" - ";
      zip.file(prefix+safeFilenamePart(entry.filename.replace(/\.pdf$/i,""))+".pdf",entry.blob);
    });
    const blob=await zip.generateAsync({type:"blob",compression:"DEFLATE",
      compressionOptions:{level:3}});
    if(!blob.size||blob.size>MAX_BYTES)throw Error("Report package too large");
    return blob;
  }
  function download(blob,filename) {
    if(!blob?.size)throw Error("Empty download");
    const name=safeFilenamePart(filename.replace(/\.(pdf|zip)$/i,""))+
      (filename.toLowerCase().endsWith(".zip")?".zip":".pdf");
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url;a.download=name;document.body.append(a);
    try{a.click()}finally{
      a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),30000);
    }
  }
  window.TalenaReportPackageCore=Object.freeze({
    ensure,merge,zipFiles,download,safeFilenamePart,
    MAX_REPORTS,MAX_BYTES,MAX_PAGES
  });
})();