let step=0, answers=[], products=[], copy=null;
let resultGender='all', variantSelections={};
const view=document.querySelector('#view');
const finderConfig=window.SHOE_FINDER_CONFIG||{};
// Isti Measurement ID-jevi kao na statičkom sajtu. Tržište može da prosledi svoje preko SHOE_FINDER_CONFIG.
const GA_MEASUREMENT_IDS=(Array.isArray(finderConfig.gaIds)?finderConfig.gaIds:[]);
const LOCALE_VERSION='1';
const OFFER_CHECKED=finderConfig.offerChecked||'29.09.2026';
const stepNames=['podloga','prioritet','detalji','rezultat'];
const answerNames={road:'asfalt',trail:'suma',comfort:'udobnost',speed:'brzina',protection:'zastita',light:'lakoca',soft:'mekan_korak',support:'oslonac',training:'trening',race:'trka',technical:'neravan_teren',smooth:'prohodan_teren'};
const pathNames={road:'asfalt',trail:'trail',comfort:'udobnost',speed:'brzina',protection:'zastita',light:'lakoca',soft:'mekan',support:'oslonac',training:'trening',race:'trka',technical:'neravan',smooth:'prohodan'};
function startAnalytics(){
 const ids=GA_MEASUREMENT_IDS.filter(id=>/^G-[A-Z0-9]+$/.test(id));
 if(!ids.length)return;
 window.dataLayer=window.dataLayer||[];
 window.gtag=function(){dataLayer.push(arguments);};
 gtag('js',new Date());
 ids.forEach(id=>gtag('config',id));
 const script=document.createElement('script');
 script.async=true;
 script.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(ids[0]);
 document.head.appendChild(script);
}
function slug(value){return String(value).toLowerCase().replace(/đ/g,'dj').replace(/[čć]/g,'c').replace(/š/g,'s').replace(/ž/g,'z').replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'');}
function gaName(value){return slug(value).slice(0,40).replace(/_+$/,'');}
function track(eventName,opis){if(typeof window.gtag==='function')window.gtag('event',gaName(eventName),{a_opis:String(opis).slice(0,100)});}
function pathSlug(){return answers.map(value=>pathNames[value]||value).join('_');}
function pathText(){return answers.map((value,i)=>question(i).options.find(option=>option[0]===value)[1]).join(' → ');}
const stepShort={road:'Asfalt',trail:'Trail',comfort:'Udobnost',speed:'Brzina',protection:'Zaštita',light:'Lakoća',soft:'Mekan korak',support:'Oslonac',training:'Trening',race:'Trka',technical:'Neravan teren',smooth:'Prohodan teren'};
const stepCode={road:'asf',trail:'trl',comfort:'udo',speed:'brz',protection:'zas',light:'lak',soft:'mek',support:'osl',training:'tre',race:'trk',technical:'ner',smooth:'pro'};
const shoeCode={metaspeed:'meta','magic-speed':'magic',superblast:'super',novablast:'nova','gel-nimbus':'nimbus','gel-cumulus':'cumul','gel-kayano':'kayano','gt-2000':'gt2000','trabuco-max':'trabu',fujispeed:'fuji',blazeblast:'blaze','metafuji-trail':'mfuji','noosa-tri':'noosa',dynablast:'dyna',versablast:'versa'};
const genderCode={men:'m',women:'z',unisex:'u'};
const analyticsGender={men:'Muške',women:'Ženske',unisex:'Unisex'};
function quizCode(){return answers.map(value=>stepCode[value]||slug(value).slice(0,3)).join('_');}
function quizShort(){return answers.map(value=>stepShort[value]||value).join(' → ');}
function selectedVariant(key){const p=products.find(item=>item.key===key);if(!p)return null;const variants=variantsFor(p);return variants.find(item=>item.id===variantSelections[key])||variants[0]||null;}
function variantStory(key,variant){const p=products.find(item=>item.key===key);const name=p?.model_name||familyNames[key]||key;if(!variant)return quizShort()+' | '+name;return [quizShort(),name,analyticsGender[variant.gender]||variant.gender,variant.color,variant.sku].filter(Boolean).join(' | ');}
function variantEvent(prefix,key,variant){const shoe=shoeCode[key]||slug(key).slice(0,6);const head=(prefix?prefix+'_':'')+quizCode()+'_'+shoe;if(!variant)return head;const suffix=String(variant.sku||'').split('-').pop()||'0';const g=genderCode[variant.gender]||'x';const room=40-(head.length+g.length+suffix.length+3);const color=slug(variant.color||'boja').slice(0,Math.max(1,room));return head+'_'+g+'_'+color+'_'+suffix;}
function answerLabel(index,value){return question(index).options.find(option=>option[0]===value)?.[1]||value;}
const questionOptions={
 surface:['road','trail'],
 road:['comfort','speed'],
 trail:['protection','light'],
 comfort:['soft','support'],
 speed:['training','race'],
 terrain:['technical','smooth']
};
const recommendationModels={
 'road/comfort/soft':['gel-nimbus','gel-cumulus','dynablast'],
 'road/comfort/support':['gel-kayano','gt-2000'],
 'road/speed/training':['superblast','novablast','noosa-tri','dynablast','versablast'],
 'road/speed/race':['metaspeed','magic-speed','noosa-tri'],
 'trail/protection/technical':['trabuco-max'],
 'trail/protection/smooth':['trabuco-max'],
 'trail/light/technical':['fujispeed','metafuji-trail'],
 'trail/light/smooth':['fujispeed','metafuji-trail']
};
const familyNames={'metaspeed':'METASPEED™','magic-speed':'MAGIC SPEED™',superblast:'SUPERBLAST™',novablast:'NOVABLAST™','gel-nimbus':'GEL-NIMBUS™','gel-cumulus':'GEL-CUMULUS™','gel-kayano':'GEL-KAYANO™','gt-2000':'GT-2000™','trabuco-max':'TRABUCO MAX™',fujispeed:'FUJISPEED™',blazeblast:'BLAZEBLAST™','metafuji-trail':'METAFUJI TRAIL™','noosa-tri':'NOOSA TRI™',dynablast:'DYNABLAST™',versablast:'VERSABLAST™'};
function fill(template,vars){return String(template).replace(/\{(\w+)\}/g,(_,key)=>vars&&vars[key]!=null?String(vars[key]):'');}
function genderName(code){return copy.genders[code]||code;}
function colorName(color){return copy.colors[color]||color;}
function questionId(index=step,values=answers){return index===0?'surface':index===1?values[0]:values[0]==='trail'?'terrain':values[1];}
function question(index=step,values=answers){const id=questionId(index,values),src=copy.questions[id];return {title:src.title,intro:src.intro,options:questionOptions[id].map(key=>[key,src.options[key].label,src.options[key].description])};}
function options(){return question()?.options||[];}
function imageAsset(file){const base=finderConfig.assetBase||'assets/';return base+file;}
function familyName(key){const p=products.find(item=>item.key===key);return p?.family_name||familyNames[key]||key;}
function variantSrc(key,variant){if(variant?.image_src)return variant.image_src;if(variant?.filename)return imageAsset(variant.filename);const p=products.find(item=>item.key===key);if(p?.image_src)return p.image_src;if(p?.filename)return imageAsset(p.filename);return imageAsset(key+'.webp');}
function image(key,variant){const model=familyName(key);const alt=variant?fill(copy.product.altColor,{model,color:colorName(variant.color)}):fill(copy.product.alt,{model});return `<img src="${escapeText(variantSrc(key,variant))}" alt="${escapeText(alt)}" width="1200" height="1200">`;}
function recommendationSpec(){const path=answers.join('/');const server=finderConfig.recommendations||null;if(server&&Object.prototype.hasOwnProperty.call(server,path)){const spec=server[path]||{};return {shoes:spec.shoes||[],extras:spec.extras||[]};}return {shoes:recommendationModels[path]||[],extras:path.startsWith('trail/')?['blazeblast']:[]};}
function escapeText(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function applyChrome(){
 document.title=copy.meta.title;
 document.querySelector('meta[name="description"]')?.setAttribute('content',copy.meta.description);
 if(copy.meta.htmlLang)document.documentElement.lang=copy.meta.htmlLang;
 document.querySelector('.brand')?.setAttribute('aria-label',copy.header.home);
 const logo=document.querySelector('.brand-logo');
 if(logo)logo.alt=copy.header.logoAlt;
 const resetLabel=[...document.querySelector('#reset').childNodes].find(node=>node.nodeType===3);
 if(resetLabel)resetLabel.nodeValue=copy.header.reset+' ';
 const kicker=document.querySelector('.topline > span:first-child');
 if(kicker)kicker.textContent=copy.progress.kicker;
 const time=document.querySelector('.time');
 if(time)time.textContent=copy.progress.time;
 document.querySelector('.steps')?.setAttribute('aria-label',copy.progress.label);
 const stepKeys=['surface','priority','detail','result'];
 document.querySelectorAll('.steps li').forEach((li,index)=>{const text=[...li.childNodes].find(node=>node.nodeType===3);if(text)text.nodeValue=' '+copy.progress.steps[stepKeys[index]];});
}
function render(focus=false,trackView=false){
 document.querySelectorAll('.steps li').forEach((li,i)=>{li.className=i===step?'active':i<step?'done':'';if(i===step)li.setAttribute('aria-current','step');else li.removeAttribute('aria-current');});
 if(step===3){renderResult(trackView);}else{
  const q=question(),opts=q.options;
  view.innerHTML=`<section class="fade question-screen"><div class="intro"><div><p class="eyebrow">${escapeText(fill(copy.quiz.eyebrow,{current:String(step+1).padStart(2,'0'),total:'03'}))}</p><h1 tabindex="-1">${escapeText(q.title)}</h1></div><p>${escapeText(q.intro)}</p></div><div class="choices" style="--columns:${opts.length}">${opts.map((o,i)=>`<button class="choice ${answers[step]===o[0]?'selected':''}" data-value="${o[0]}" aria-pressed="${answers[step]===o[0]}"><span class="choice-top"><span>0${i+1}</span><span class="radio" aria-hidden="true"></span></span><span class="choice-copy"><span class="choice-title">${escapeText(o[1])}</span><span class="choice-description">${escapeText(o[2])}</span></span></button>`).join('')}</div><div class="controls">${step?`<button class="back" id="back">${escapeText(copy.quiz.back)}</button>`:`<span class="hint">${escapeText(copy.quiz.hint)}</span>`}<button class="primary" id="next" ${answers[step]?'':'disabled'}>${escapeText(step===2?copy.quiz.finish:copy.quiz.next)}</button></div></section>`;
  if(trackView)track('korak_'+(step+1)+'_'+stepNames[step],'Prikazano pitanje '+(step+1)+': '+stepNames[step]);
  view.querySelectorAll('.choice').forEach(el=>el.onclick=()=>select(el.dataset.value));
  document.querySelector('#next').onclick=next;
  if(step)document.querySelector('#back').onclick=()=>{track('nazad_sa_'+stepNames[step],'Vratio se sa pitanja: '+stepNames[step]);step--;render(true,true);window.scrollTo({top:0,behavior:'auto'});};
 }
 if(focus)view.querySelector('h1')?.focus({preventScroll:true});
}
function select(value){if(!options().some(o=>o[0]===value))throw new Error('Nepoznat odgovor');if(answers[step]!==value)answers=answers.slice(0,step);answers[step]=value;render();view.querySelector(`[data-value="${value}"]`).focus({preventScroll:true});}
function next(){if(!answers[step])return;track('odgovor_'+(step+1)+'_'+(answerNames[answers[step]]||answers[step]),'Odgovor '+(step+1)+': '+answerLabel(step,answers[step]));step++;render(true,true);window.scrollTo({top:0,behavior:'auto'});}
function reset(){if(!copy)return;track('pocni_ponovo','Počeo je anketu ispočetka');step=0;answers=[];resultGender='all';variantSelections={};render(true,true);window.scrollTo({top:0,behavior:'auto'});}
document.querySelector('#reset').onclick=reset;
function chosen(){return [...recommendationSpec().shoes];}
function extraKeys(){return [...recommendationSpec().extras];}
function variantsFor(p){return (p.variants||[]).filter(v=>resultGender==='all'||v.gender===resultGender||v.gender==='unisex');}
function stockNotice(p){if(p.variants?.length)return fill(copy.result.stockGender,{gender:resultGender==='women'?copy.result.stockWomen:copy.result.stockMen});return copy.result.stockNone;}
function productCard(key){
 const p=products.find(p=>p.key===key);if(!p)return '';
 const variants=variantsFor(p),selected=variants.find(v=>v.id===variantSelections[key])||variants[0];
 const groups=['men','women','unisex'].map(g=>({gender:g,variants:variants.filter(v=>v.gender===g)})).filter(g=>g.variants.length);
 const colors=groups.map(g=>`<div class="variant-group"><p class="variant-group-label">${escapeText(g.gender==='unisex'?fill(copy.genders.unisexGroup,{gender:genderName(g.gender)}):genderName(g.gender))}</p><div class="variant-options">${g.variants.map(v=>`<button class="variant-option ${v.id===selected.id?'selected':''}" data-model="${key}" data-variant="${v.id}" aria-pressed="${v.id===selected.id}" aria-label="${escapeText(fill(copy.product.variantAria,{gender:genderName(v.gender),color:colorName(v.color),sku:v.sku}))}"><img src="${escapeText(variantSrc(key,v))}" alt="" width="72" height="54"><span>${escapeText(colorName(v.color))}</span><small>${escapeText(v.sku.split('-').pop())}</small></button>`).join('')}</div></div>`).join('');
 return `<article class="product-card ${selected?'':'unavailable'}" data-product="${key}"><div class="product-photo">${image(key,selected)}</div><div class="product-copy"><h2>${escapeText(familyName(key))}</h2><p class="product-version">${escapeText(p.model_name)}</p>${selected?`${colors}<p class="selected-variant">${escapeText(genderName(selected.gender))} · ${escapeText(colorName(selected.color))} <span>${escapeText(selected.sku)}</span></p><a class="primary" href="${escapeText(selected.store_url)}" target="_blank" rel="noopener noreferrer">${escapeText(copy.product.store)}</a>`:`<p class="stock-notice">${escapeText(stockNotice(p))}</p>`}</div></article>`;
}
function bindVariantControls(){
 view.querySelectorAll('[data-gender]').forEach(el=>el.onclick=()=>{const gender=el.dataset.gender;if(gender===resultGender)return;resultGender=gender;const genderLabel=gender==='men'?'Muške':gender==='women'?'Ženske':'Sve';track('filter_'+(gender==='men'?'muske':gender==='women'?'zenske':'sve'),'Filter patika: '+genderLabel);renderResult(false);view.querySelector(`[data-gender="${resultGender}"]`).focus({preventScroll:true});});
 view.querySelectorAll('[data-variant]').forEach(el=>el.onclick=()=>{const key=el.dataset.model,id=el.dataset.variant;const variant=(products.find(item=>item.key===key)?.variants||[]).find(item=>item.id===id);variantSelections[key]=id;if(variant)track(variantEvent('boja',key,variant),variantStory(key,variant));const card=el.closest('.product-card');card.outerHTML=productCard(key);bindVariantControls();view.querySelector(`[data-model="${key}"][data-variant="${id}"]`).focus({preventScroll:true});});
 view.querySelectorAll('.product-card a.primary').forEach(el=>el.onclick=()=>{const key=el.closest('.product-card')?.dataset.product;const variant=selectedVariant(key);if(!variant)return;track(variantEvent('sv',key,variant),variantStory(key,variant));});
}

function renderResult(trackView=false){
 if(!products.length){view.innerHTML=`<h1 tabindex="-1">${escapeText(copy.result.loading)}</h1>`;return;}
 const result=copy.recommendations[answers.join('/')];
 const summary=answers.map((value,i)=>question(i).options.find(o=>o[0]===value)[1]);
 const filters=[['all',copy.result.filterAll],['men',copy.genders.men],['women',copy.genders.women]];
 const extras=extraKeys();
 view.innerHTML=`<section class="fade"><div class="result-top"><div><p class="eyebrow">${escapeText(copy.result.eyebrow)}</p><h1 tabindex="-1">${escapeText(result.title)}</h1></div><button class="back" id="edit">${escapeText(copy.result.edit)}</button></div><p class="result-reason">${escapeText(result.note)}</p><ul class="answer-summary" aria-label="${escapeText(copy.result.answersLabel)}">${summary.map(s=>`<li>${escapeText(s)}</li>`).join('')}</ul><div class="gender-filter" role="group" aria-label="${escapeText(copy.result.filterLabelText)}"><span>${escapeText(copy.result.filterPrefix)}</span>${filters.map(([value,label])=>`<button data-gender="${value}" aria-pressed="${resultGender===value}" class="${resultGender===value?'active':''}">${escapeText(label)}</button>`).join('')}</div><p class="variant-hint">${escapeText(copy.result.variantHint)}</p><div class="product-grid">${chosen().map(productCard).join('')}</div>${extras.length?`<section class="trail-extra"><h2>${escapeText(copy.result.trailExtra)}</h2><div class="product-grid">${extras.map(productCard).join('')}</div></section>`:''}<p class="availability-note">${escapeText(fill(copy.result.availability,{date:OFFER_CHECKED}))}</p></section>`;
 if(trackView){const models=chosen();track('rezultat_'+pathSlug(),'Rezultat: '+pathText());[...models,...extras].forEach(key=>{const variant=selectedVariant(key);track(variantEvent('',key,variant),variantStory(key,variant));});}
 bindVariantControls();
 document.querySelector('#edit').onclick=()=>{track('izmena_odgovora','Vratio se da izmeni odgovore');step=2;render(true,true);window.scrollTo({top:0,behavior:'auto'});};
}
function requestedLocale(){
 try{const code=(new URLSearchParams(location.search).get('lang')||'').toLowerCase();if(code==='sr'||code==='hr'||code==='sl')return code;}catch(e){}
 const html=(document.documentElement.lang||'').toLowerCase();
 if(html.startsWith('hr'))return 'hr';
 if(html.startsWith('sl'))return 'sl';
 return 'sr';
}
async function loadLocale(code){
 try{
  const res=await fetch('prevodi/'+code+'.json?v='+LOCALE_VERSION);
  if(!res.ok)return null;
  const data=await res.json();
  if(!data?.questions||!data.recommendations)return null;
  return data;
 }catch(e){return null;}
}
function registerFinderTool(){
 if(document.modelContext?.registerTool){try{Promise.resolve(document.modelContext.registerTool({name:'set_shoe_finder_answers',description:'Postavi tri odgovora i prikaži patike. road: comfort + soft/support ili speed + training/race. trail: protection/light + technical/smooth.',inputSchema:{type:'object',properties:{surface:{type:'string',enum:['road','trail']},priority:{type:'string',enum:['comfort','speed','protection','light']},detail:{type:'string',enum:['soft','support','training','race','technical','smooth']}},required:['surface','priority','detail'],additionalProperties:false},annotations:{readOnlyHint:false},execute(input){if(!input||Object.keys(input).some(k=>!['surface','priority','detail'].includes(k))||!recommendationModels[[input.surface,input.priority,input.detail].join('/')])throw new Error('Nevažeća kombinacija odgovora.');if(!products.length)throw new Error('Sačekaj da se modeli učitaju.');answers=[input.surface,input.priority,input.detail];step=3;render(true,true);return {models:chosen(),additional:extraKeys(),available:products.filter(p=>p.available&&[...chosen(),...extraKeys()].includes(p.key)).map(p=>p.key)};}})).catch(()=>{});}catch{}}
}
async function boot(){
 copy=window.SHOE_FINDER_COPY||null;
 if(!copy){
  const code=requestedLocale();
  copy=await loadLocale(code)||(code!=='sr'?await loadLocale('sr'):null)||window.SHOE_FINDER_I18N||null;
 }
 if(!copy){view.innerHTML='<h1>Probaj ponovo.</h1><p>Podaci o modelima trenutno nisu dostupni. Osveži stranicu.</p>';return;}
 applyChrome();
 if(Array.isArray(window.SHOE_FINDER_PRODUCTS)&&window.SHOE_FINDER_PRODUCTS.length){products=window.SHOE_FINDER_PRODUCTS;render(false,true);}
 else if(Array.isArray(window.PRODUCTS)&&window.PRODUCTS.length){products=window.PRODUCTS;render(false,true);}
 else view.innerHTML=`<h1>${escapeText(copy.errors.title)}</h1><p>${escapeText(copy.errors.body)}</p>`;
 registerFinderTool();
}
startAnalytics();
boot();
