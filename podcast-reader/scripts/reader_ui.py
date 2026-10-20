"""Self-contained presentation for the generated podcast reader.

These strings are embedded in reader.html; the delivered page needs no assets,
network requests, sibling files, or third-party browser libraries.
"""

STYLE = """
:root{color-scheme:dark;--bg:#0b0e13;--panel:#121720;--panel-soft:#10151c;--ink:#f0f0ed;--body:#c7ccd4;--muted:#989fac;--gold:#e8c66b;--gold-soft:#bfa86e;--line:#29303b;--focus:#f5d67e;--nav:rgba(11,14,19,.96)}
*{box-sizing:border-box}[hidden]{display:none!important}html{scroll-behavior:smooth;scroll-padding-top:90px}body{margin:0;background:var(--bg);color:var(--body);font:16px/1.85 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--gold);text-decoration:none}a:hover{text-decoration:underline}button,input,textarea{font:inherit}button{cursor:pointer}a,button,input,textarea,summary{-webkit-tap-highlight-color:transparent}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,summary:focus-visible,[tabindex="-1"]:focus-visible{outline:2px solid var(--focus);outline-offset:5px}
.skip{position:absolute;left:-9999px}.skip:focus{left:16px;top:16px;background:var(--panel);padding:10px;z-index:20}
.page{max-width:940px;margin:0 auto;padding:44px 40px 30px}.hero{text-align:center;padding:0 12px 24px}.eyebrow{display:inline-flex;align-items:center;gap:9px;color:var(--gold);font-size:11px;letter-spacing:.22em;font-weight:650}.eyebrow::before,.eyebrow::after{content:"";width:22px;height:1px;background:#705c30}
h1{font-size:clamp(29px,4vw,43px);line-height:1.4;font-weight:750;letter-spacing:.012em;color:var(--ink);margin:18px auto 14px;max-width:780px;text-wrap:balance;overflow-wrap:anywhere}
.episode-title{font-size:13px;color:var(--muted);margin:0 auto 12px;max-width:720px}.metadata{display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:6px 17px;font-size:12px;color:var(--muted)}.metadata span+span{position:relative}.metadata span+span::before{content:"";position:absolute;left:-9px;top:calc(50% - 1px);width:2px;height:2px;background:#555e6c;border-radius:50%}
.takeaway{margin:24px auto 0;max-width:780px;text-align:left;background:linear-gradient(115deg,rgba(232,198,107,.075),rgba(232,198,107,.015));border:1px solid #49412c;border-left:3px solid var(--gold);border-radius:2px 9px 9px 2px;padding:17px 22px}
.kicker{color:var(--gold);font-size:11px;letter-spacing:.12em;font-weight:650}.takeaway p{color:var(--ink);font-size:18px;margin:5px 0 0;line-height:1.85;font-weight:500}.takeaway .evidence{margin-top:11px}
.question-index{max-width:780px;margin:21px auto 0;text-align:left}.question-index-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:9px}.question-index h2{font-size:14px;line-height:1.5;color:var(--gold);font-weight:600}.question-index h2::before{display:none}.question-index-heading>span{font-size:11px;color:var(--muted)}.question-index ol{list-style:none;margin:0;padding:0;border-top:1px solid #3b3a30}.question-index li{border-bottom:1px solid var(--line)}.question-jump{display:grid;grid-template-columns:25px minmax(0,1fr) 16px;align-items:center;gap:10px;min-height:47px;padding:10px 2px;color:var(--ink);font-size:15px;line-height:1.7}.question-jump:hover{color:var(--gold);background:rgba(232,198,107,.035);text-decoration:none}.question-index-number{color:var(--gold-soft);font:11px/1.5 ui-monospace,monospace}.question-index-arrow{color:var(--gold-soft);font-size:15px}.question-index-text{overflow-wrap:anywhere}.index-answer-status{display:inline-block;margin-left:9px;padding:0 6px;border:1px solid #5b4c31;border-radius:3px;color:var(--gold-soft);font-size:10px;line-height:1.6;vertical-align:middle;white-space:nowrap}
.reading-stats{display:flex;justify-content:center;flex-wrap:wrap;gap:7px 17px;margin:18px 0 15px;color:var(--muted);font-size:12px}.reading-stats strong{font-weight:550;color:var(--ink)}.reading-stats .read-time{color:var(--gold)}
.toolbar{display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:9px}.button{min-height:44px;display:inline-flex;align-items:center;justify-content:center;gap:8px;background:var(--panel);border:1px solid #3b4351;color:var(--ink);border-radius:7px;padding:9px 16px;font-size:13px;line-height:1.5;font-weight:550;transition:background .15s,border-color .15s}.button:hover{background:#1a222e;border-color:#707b8d;text-decoration:none}.button.primary{background:var(--gold);color:#19170e;border-color:var(--gold)}.button.primary:hover{background:#f2d784}.button svg{width:16px;height:16px;flex:none}.button:disabled{cursor:default;opacity:.45}
.toolbar-feedback{font-size:12px;color:var(--gold);min-height:20px;margin:8px 0 0;line-height:1.6}.copy-fallback{text-align:left;margin:12px 0 0;padding:18px;border:1px solid var(--line);border-radius:8px;background:var(--panel)}.copy-fallback p{font-size:13px;margin:0 0 10px}.copy-fallback textarea{width:100%;height:160px;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:5px;padding:10px;font-size:13px;resize:vertical}.copy-fallback .button{margin-top:8px}
.section-nav{position:sticky;top:0;z-index:5;margin:0 -1px;background:var(--nav);backdrop-filter:blur(16px);border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.section-nav ul{display:flex;align-items:center;gap:25px;list-style:none;overflow-x:auto;overscroll-behavior-inline:contain;margin:0;padding:0 2px;scrollbar-width:none}.section-nav ul::-webkit-scrollbar{display:none}.section-nav li{flex:none}.section-nav a{display:flex;align-items:center;min-height:54px;padding:12px 0;border-bottom:2px solid transparent;color:var(--muted);font-size:13px;white-space:nowrap}.section-nav a:hover{color:var(--ink);text-decoration:none}.section-nav a[aria-current]{color:var(--gold);border-bottom-color:var(--gold)}
main{min-width:0}section{margin-top:42px;scroll-margin-top:88px}.section-heading{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:18px}h2{font-size:21px;letter-spacing:.015em;margin:0;color:var(--ink);line-height:1.5;font-weight:650}h2::before{content:"";display:inline-block;width:3px;height:.85em;margin-right:11px;background:var(--gold)}.section-count{color:var(--muted);font:11px/1.5 ui-monospace,monospace;letter-spacing:.08em}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:25px 25px;min-width:0;overflow-wrap:anywhere}.card h3{font-size:19px;line-height:1.65;color:var(--ink);margin:0 0 11px;font-weight:650}.card p{margin:8px 0;font-size:16px;line-height:1.85}.quick-card{display:flex;flex-direction:column}.quick-card .question{font-size:18px;color:var(--ink);font-weight:650;line-height:1.65;margin:0 0 12px}.quick-card .answer{font-size:15px;line-height:1.9;color:var(--body);font-weight:400;margin:0 0 16px}.quick-card .evidence{margin-top:auto;padding-top:0}
.question-cards{display:grid;gap:17px}.question-cards .quick-card{scroll-margin-top:85px;padding:27px 29px}.question-cards .question{font-size:21px;line-height:1.65;margin-bottom:11px}.question-number{display:inline-block;margin-right:12px;color:var(--gold-soft);font:13px/1.5 ui-monospace,monospace;vertical-align:2px}.question-meta{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin:0 0 14px}.question-status{font-size:11px;line-height:1.6;color:var(--body);border:1px solid #444c58;border-radius:4px;padding:2px 7px}.question-status[data-answer-status="partial"],.question-status[data-answer-status="unanswered"]{color:var(--gold-soft);border-color:#5b4c31}.question-origin{font-size:11px;color:var(--muted)}.field-label{display:block;font-size:11px;font-weight:550;letter-spacing:.035em;line-height:1.5;color:var(--muted);margin-bottom:6px}.quick-card .question-why{font-size:14px;color:var(--muted);margin:0 0 20px}.question-why .field-label{display:inline;margin-right:9px;color:var(--gold-soft)}.question-answer .field-label{color:var(--gold-soft)}.quick-card .question-answer .answer{font-size:16px;margin:0 0 17px}.question-gap{margin:0 0 18px;padding:10px 15px;border-left:2px solid #76613b;background:rgba(232,198,107,.035);border-radius:0 5px 5px 0}.question-gap .field-label{color:var(--gold-soft);margin:0 0 5px}.question-gap p{font-size:14px;margin:0;line-height:1.85}.question-cards .quick-card:target{border-color:#95804d;box-shadow:0 0 0 1px rgba(232,198,107,.1)}
.insight{margin-top:15px;padding:26px 28px}.insight:first-child{margin-top:0}.insight-heading{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}.insight-heading h3{flex:1;min-width:180px}.index{font:13px/1.5 ui-monospace,monospace;color:var(--gold-soft)}.kind{font-size:11px;color:var(--gold-soft);border:1px solid #49422f;padding:1px 8px;border-radius:4px;white-space:nowrap}.insight ul,.open-questions ul{margin:13px 0 0;padding-left:20px;font-size:15px}.insight li,.open-questions li{padding-left:4px;margin:7px 0}.insight li::marker,.open-questions li::marker{color:var(--gold)}
.evidence{display:flex;gap:7px;flex-wrap:wrap;margin-top:17px;font:11px/1.7 ui-monospace,monospace;color:var(--muted)}.evidence a,.evidence>span{display:inline-flex;align-items:center;gap:7px;min-height:34px;padding:5px 9px;border:1px solid #343d49;border-radius:5px}.evidence a{color:#c8b888;background:rgba(232,198,107,.025)}.evidence a:hover{border-color:#887644;background:rgba(232,198,107,.07);text-decoration:none}.evidence .evidence-action{font:11px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:var(--muted)}
.compact-reference{display:none}.metadata span{min-width:0;max-width:100%;overflow-wrap:anywhere}.episode-title,.limitations,.segment{overflow-wrap:anywhere}.segment>div{min-width:0}
blockquote{margin:0;padding:2px 0 2px 20px;border-left:2px solid var(--gold-soft)}blockquote p{font-size:20px!important;line-height:1.85!important;color:var(--ink)}blockquote cite{font-size:13px;color:var(--muted);font-style:normal;display:block;margin-top:13px}.quote+.quote,.action+.action{margin-top:15px}.action .context{color:var(--muted);font-size:14px}.participant h3{font-size:17px;margin-bottom:3px}.participant .role{font-size:12px;color:var(--gold-soft)}.participant p{font-size:14px;color:var(--muted)}.participant{background:var(--panel-soft)}
.limitations{color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding-top:25px}.limitations h2{font-size:16px;color:var(--muted)}.limitations ul{margin:0;padding-left:18px}.limitations li{margin:6px 0}.source-details{margin-top:32px;scroll-margin-top:82px;border:1px solid var(--line);border-radius:10px;background:var(--panel-soft)}.source-details>summary{min-height:64px;display:list-item;padding:19px 23px;cursor:pointer;color:var(--ink);font-size:15px;font-weight:550}.source-details>summary::marker{color:var(--gold)}.source-details[open]>summary{border-bottom:1px solid var(--line)}.source-content{padding:0 25px 24px}.source-content .section-heading{margin-bottom:16px}.source-content h2{font-size:18px}.source-content section{margin-top:28px}.source-return{display:flex;justify-content:flex-start;padding:16px 0 0}.return-summary{display:inline-flex;align-items:center;min-height:44px;font-size:13px;color:var(--gold);gap:8px}
.source-return:first-child{position:sticky;top:56px;z-index:4;padding:8px 0;background:var(--panel-soft);border-bottom:1px solid var(--line)}
.chapters{padding-left:21px;font-size:14px}.chapters li{margin:20px 0;padding-left:4px}.chapters p{color:var(--muted);margin:4px 0}.chapters .evidence{margin-top:9px}
label{display:block;color:var(--muted);font-size:13px;margin-bottom:8px}.search-controls{display:flex;align-items:center;gap:9px}input[type="search"]{min-width:0;width:100%;min-height:48px;font-size:16px;background:var(--bg);color:var(--ink);border:1px solid #3a4350;border-radius:7px;padding:10px 13px}.search-controls .button{white-space:nowrap;min-height:48px}#result-count{font-size:12px;color:var(--muted);margin:11px 0 16px}.search-empty{text-align:center;padding:35px 20px;border:1px dashed #39414f;border-radius:8px;margin:18px 0}.search-empty strong{color:var(--ink);font-size:16px}.search-empty p{font-size:14px;color:var(--muted);margin:8px 0 18px}
.segment{display:grid;grid-template-columns:92px 1fr;gap:16px;padding:20px 9px;border-top:1px solid var(--line);font-size:15px;scroll-margin-top:132px}.segment[hidden]{display:none}.stamp{font:11px/1.8 ui-monospace,monospace;color:var(--muted)}.stamp a{display:inline-flex;align-items:center;min-height:34px}.speaker{font-size:12px;color:var(--gold);display:block;margin-bottom:5px}.segment p{margin:0;white-space:pre-wrap}.segment:target,.segment.source-highlight{background:#242219;outline:1px solid #8b7643;border-radius:5px}
footer{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-top:35px;padding-top:22px;border-top:1px solid var(--line);color:var(--muted);font-size:11px}footer a{min-height:44px;display:inline-flex;align-items:center;color:var(--muted);white-space:nowrap}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(min-width:1150px){.page{max-width:980px;padding-left:55px;padding-right:55px}}
@media(max-width:600px){.page{padding:27px 20px 22px}.hero{padding:0 0 19px}.eyebrow{font-size:10px}h1{font-size:29px;line-height:1.45;margin-top:15px}.metadata{font-size:11px;gap:4px 13px}.metadata span+span::before{left:-7px}.episode-title{font-size:12px}.takeaway{margin-top:20px;padding:15px 17px}.takeaway p{font-size:16px;line-height:1.9}.reading-stats{font-size:11px;gap:5px 12px;margin:16px 0 13px}.toolbar{gap:8px}.toolbar .button{font-size:12px;padding:10px 12px;flex:1;white-space:nowrap}.toolbar .source-button{flex-basis:100%;background:transparent;border-color:transparent;min-height:36px;padding:4px}.toolbar-feedback{font-size:11px}.section-nav{margin:0 -20px;padding:0 20px}.section-nav ul{gap:23px}.section-nav a{min-height:53px;font-size:13px}.grid{grid-template-columns:1fr;gap:13px}.card{padding:22px 20px}.quick-card .question{font-size:18px;margin-bottom:11px}.quick-card .answer{font-size:16px;line-height:1.9;margin-bottom:17px}.card p{font-size:16px}.insight{padding:22px 20px}.insight-heading{gap:8px 10px}.insight-heading h3{font-size:18px;min-width:190px}.kind{margin-left:27px;margin-top:-5px;margin-bottom:8px}.takeaway .evidence{gap:6px}.evidence{font-size:11px;gap:7px}.evidence a{min-height:44px;padding:7px 10px}.evidence .evidence-action{font-size:11px}section{margin-top:33px}.section-heading{margin-bottom:16px}h2{font-size:20px;line-height:1.6}.section-count{display:none}blockquote{padding-left:17px}blockquote p{font-size:18px!important}.participant p{font-size:14px}.segment{grid-template-columns:1fr;gap:5px;padding:18px 8px;font-size:16px}.source-details>summary{font-size:14px;padding:18px 18px}.source-content{padding:0 16px 19px}.source-content h2{font-size:17px}.search-controls{gap:7px}.search-controls .button{padding:10px 12px}.chapters{padding-left:17px}.limitations{font-size:12px}footer{align-items:flex-start;font-size:10px;gap:12px}}
@media(max-width:600px){.compact-evidence .reference-time,.compact-evidence .evidence-action{display:none}.compact-evidence .compact-reference{display:inline}.compact-evidence a,.compact-evidence>span{min-height:36px;padding:6px 10px}.compact-evidence a{min-height:44px}}
@media(max-width:600px){.source-return:first-child{top:55px}}
@media(max-width:600px){.question-led h1{font-size:26px;line-height:1.45;margin:12px 0 10px}.question-led .episode-title{font-size:11px;line-height:1.65;margin-bottom:8px}.question-led .metadata{font-size:10px}.question-index{margin-top:17px}.question-index-heading{margin-bottom:7px}.question-index h2{font-size:13px}.question-index-heading>span{font-size:10px}.question-jump{grid-template-columns:22px minmax(0,1fr) 12px;gap:7px;min-height:44px;padding:10px 1px;font-size:14px;line-height:1.75}.question-index-number{font-size:10px}.index-answer-status{margin-left:6px;font-size:9px}.question-led .takeaway{margin-top:19px}.question-cards .quick-card{padding:22px 20px}.question-cards .question{font-size:19px;line-height:1.7}.question-number{font-size:12px;margin-right:9px}.question-meta{gap:7px;margin-bottom:12px}.question-why .field-label{display:block;margin-bottom:5px}.quick-card .question-why{font-size:14px;line-height:1.85;margin-bottom:17px}.quick-card .question-answer .answer{font-size:16px;line-height:1.9}.question-gap{padding:10px 12px}.question-gap p{font-size:14px}.question-cards .field-label{font-size:11px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}}
@media print{:root{color-scheme:light;--bg:#fff;--panel:#fff;--panel-soft:#fff;--ink:#171717;--body:#333;--muted:#555;--gold:#70521b;--gold-soft:#70521b;--line:#ddd}html{scroll-behavior:auto}body{font-size:11pt}.page{max-width:none;padding:0}.hero{padding-bottom:18px}h1{font-size:25pt}.takeaway{background:none;border-color:#c6b789;padding:13px 18px}.takeaway p{font-size:13pt}.card,blockquote,.takeaway{break-inside:avoid;box-shadow:none}.card{border-color:#ddd;padding:17px}.card p,.quick-card .answer{font-size:10pt;color:#333}.card h3,.quick-card .question{font-size:12pt;color:#111}section{margin-top:25px}.section-heading{margin-bottom:12px}h2{font-size:15pt;color:#111}.source-details,.section-nav,.toolbar,.toolbar-feedback,.copy-fallback,.skip,footer a{display:none!important}.evidence a,.evidence>span{min-height:0;padding:3px 6px;color:#70521b;border-color:#ddd;background:none}.evidence .evidence-action{color:#555}.kind{color:#70521b;border-color:#ddd}footer{color:#777}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.participant p{color:#555}}
@media print{.compact-evidence .reference-time,.compact-evidence .evidence-action{display:inline}.compact-reference{display:none!important}}
@media print{.question-index{break-inside:avoid;margin-top:15px}.question-index-heading>span,.question-index-arrow{display:none}.question-jump{min-height:0;padding:5px 0;font-size:10pt;grid-template-columns:25px 1fr}.question-status,.index-answer-status{color:#70521b;border-color:#c8b98f}.question-origin,.question-why{color:#555}.question-cards .quick-card{padding:17px}.question-cards .question{font-size:13pt}.question-gap{background:none;border-color:#baa673}.question-cards .question-answer .answer{font-size:10pt}}
"""


TOOLBAR_SCRIPT = """
(() => {
  'use strict';
  const copyButton=document.getElementById('copy-summary');
  const downloadButton=document.getElementById('download-summary');
  const markdownNode=document.getElementById('summary-markdown');
  const status=document.getElementById('toolbar-status');
  const fallback=document.getElementById('copy-fallback');
  const fallbackText=document.getElementById('copy-text');
  const announce=text=>{status.textContent=text};
  const manualCopy=()=>{
    fallback.hidden=false;
    fallbackText.value=markdownNode.textContent;
    announce(copyButton.dataset.manual);
    fallbackText.focus();
    fallbackText.select();
  };
  if(copyButton&&downloadButton&&markdownNode){
  copyButton.addEventListener('click',async()=>{
    copyButton.disabled=true;
    try{
      if(!navigator.clipboard||!navigator.clipboard.writeText)throw new Error('clipboard unavailable');
      await navigator.clipboard.writeText(markdownNode.textContent);
      fallback.hidden=true;
      announce(copyButton.dataset.success);
    }catch(_error){manualCopy()}
    finally{copyButton.disabled=false}
  });
  document.getElementById('close-copy').addEventListener('click',()=>{
    fallback.hidden=true;announce('');copyButton.focus();
  });
  downloadButton.addEventListener('click',()=>{
    let url;
    try{
      const blob=new Blob(['\\ufeff',markdownNode.textContent],{type:'text/markdown;charset=utf-8'});
      url=URL.createObjectURL(blob);
      const link=document.createElement('a');
      link.href=url;link.download=downloadButton.dataset.filename;
      document.body.append(link);link.click();link.remove();
      announce(downloadButton.dataset.success);
      window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(_error){
      if(url)URL.revokeObjectURL(url);
      manualCopy();announce(downloadButton.dataset.failure);
    }
  });
  }
  document.querySelectorAll('.question-jump').forEach(link=>link.addEventListener('click',event=>{
    const target=document.getElementById(link.hash.slice(1));
    if(!target)return;
    event.preventDefault();
    history.pushState(null,'',link.getAttribute('href'));
    target.focus({preventScroll:true});
    target.scrollIntoView({block:'start',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  }));
  const nav=document.querySelector('.section-nav');
  if(nav){
    const links=[...nav.querySelectorAll('a[href^="#"]')];
    const targets=links.map(link=>document.getElementById(link.hash.slice(1)));
    let scheduled=false,currentIndex=-1;
    const update=()=>{
      scheduled=false;let active=0;
      targets.forEach((target,index)=>{if(target&&target.getBoundingClientRect().top<=115)active=index});
      links.forEach((link,index)=>{if(index===active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current')});
      if(active!==currentIndex){
        const strip=nav.querySelector('ul'),item=links[active];
        if(strip&&item){
          const container=strip.getBoundingClientRect(),bounds=item.getBoundingClientRect();
          if(bounds.left<container.left)strip.scrollLeft-=container.left-bounds.left+8;
          else if(bounds.right>container.right)strip.scrollLeft+=bounds.right-container.right+8;
        }
        currentIndex=active;
      }
    };
    window.addEventListener('scroll',()=>{if(!scheduled){scheduled=true;requestAnimationFrame(update)}},{passive:true});
    window.addEventListener('resize',update);
    links.forEach(link=>link.addEventListener('click',()=>{
      const target=document.getElementById(link.hash.slice(1));
      if(target&&target.tagName==='DETAILS')target.open=true;
      links.forEach(item=>item.removeAttribute('aria-current'));
      link.setAttribute('aria-current','location');
    }));
    update();
  }
})();
"""


TRANSCRIPT_SCRIPT = """
(() => {
  'use strict';
  const input=document.getElementById('search'),rows=[...document.querySelectorAll('.segment')];
  const count=document.getElementById('result-count'),empty=document.getElementById('search-empty');
  const clear=document.getElementById('clear-search'),details=document.getElementById('source-details');
  let lastCitation=null,openedByReference=false;
  const motion=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';
  const filter=()=>{
    const q=input.value.trim().toLowerCase();let visible=0;
    for(const row of rows){const show=!q||row.dataset.search.includes(q);row.hidden=!show;if(show)visible++}
    count.textContent=(q?count.dataset.match:count.dataset.all).replace('{n}',q?visible:rows.length);
    empty.hidden=visible!==0;clear.disabled=!input.value;
  };
  const reset=()=>{input.value='';filter();input.focus()};
  input.addEventListener('input',filter);
  clear.addEventListener('click',reset);
  document.getElementById('reset-search').addEventListener('click',reset);
  const revealSource=()=>{
    if(!location.hash.startsWith('#segment-'))return;
    const target=document.getElementById(location.hash.slice(1));
    if(!target||!details)return;
    if(!details.open)openedByReference=true;
    details.open=true;input.value='';filter();
    rows.forEach(row=>row.classList.toggle('source-highlight',row===target));
    target.focus({preventScroll:true});
    target.scrollIntoView({block:'start',behavior:motion()});
  };
  document.querySelectorAll('.segment-reference').forEach(link=>link.addEventListener('click',event=>{
    event.preventDefault();lastCitation=link;
    history.pushState(null,'',link.getAttribute('href'));
    revealSource();
  }));
  document.querySelectorAll('.return-summary').forEach(link=>link.addEventListener('click',event=>{
    event.preventDefault();
    const target=lastCitation||document.getElementById('summary');
    if(openedByReference){details.open=false;openedByReference=false}
    rows.forEach(row=>row.classList.remove('source-highlight'));
    history.pushState(null,'','#'+target.id);
    target.focus({preventScroll:true});target.scrollIntoView({block:lastCitation?'center':'start',behavior:motion()});
  }));
  window.addEventListener('hashchange',revealSource);
  window.addEventListener('popstate',revealSource);
  filter();revealSource();
})();
"""


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print("Presentation library; use render_reader.py to generate a standalone reader.")
