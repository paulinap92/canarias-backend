const $ = (id) => document.getElementById(id);

const AREA_LABELS = {
  guide: "Guide",
  explore: "Explore",
  calendar: "Calendar",
  news: "News",
  live: "Live",
  media: "Media"
};

const RESOURCE_LABELS = {
  places: "Lugares",
  beaches: "Playas",
  routes: "Rutas",
  fauna: "Fauna",
  flora: "Flora",
  weather: "Weather",
  "air-quality": "Air quality",
  marine: "Marine",
  tides: "Tides",
  alerts: "Alerts",
  seismic: "Seismic",
  volcanic: "Volcanic",
  webcams: "Webcams"
};

const state = {area:"guide",items:[],selected:null,isNew:false,options:null};

function token(){return $("token").value.trim() || localStorage.getItem("canarias-editor-token") || "";}

async function api(url,options){
  options=options||{};
  const headers=new Headers(options.headers||{});
  const t=token();
  if(t) headers.set("Authorization","Bearer "+t);
  if(options.body && !headers.has("Content-Type")) headers.set("Content-Type","application/json");
  const response=await fetch(url,Object.assign({},options,{headers}));
  if(response.status===204) return null;
  const body=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(body.detail || ("HTTP "+response.status));
  return body;
}

function escapeHtml(value){
  return String(value==null?"":value).replace(/[&<>"']/g,(char)=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  })[char]);
}

function setStatus(message,error){
  $("status").textContent=message||"";
  $("status").classList.toggle("error",Boolean(error));
}
function setVisible(id,visible){$(id).classList.toggle("hidden",!visible);}
function fillSelect(el,values,labels){
  el.innerHTML="";
  values.forEach(value=>el.add(new Option((labels&&labels[value])||value,value)));
}

function renderTabs(){
  const root=$("area-tabs");
  root.innerHTML="";
  state.options.areas.forEach(area=>{
    const button=document.createElement("button");
    button.type="button";
    button.textContent=AREA_LABELS[area]||area;
    button.className=area===state.area?"active":"";
    button.addEventListener("click",()=>{
      state.area=area;
      renderTabs();
      configureArea();
      loadArea();
    });
    root.appendChild(button);
  });
}

function configureArea(){
  const area=state.area;
  fillSelect($("island"),state.options.islands);
  $("island").value=state.options.islands.includes("tenerife")?"tenerife":state.options.islands[0];
  setVisible("resource-row",["guide","explore","live"].includes(area));
  setVisible("month-row",area==="calendar");

  if(area==="guide") fillSelect($("resource"),state.options.sections);
  if(area==="explore") fillSelect($("resource"),state.options.explore_resources,RESOURCE_LABELS);
  if(area==="live") fillSelect($("resource"),state.options.live_resources,RESOURCE_LABELS);
  if(area==="calendar") $("month").value=state.options.current_month;

  $("new-item").classList.toggle("hidden",!["guide","explore","calendar"].includes(area));
  $("new-item").textContent=area==="calendar"?"+ Nuevo evento":"+ Nuevo";
  $("search").value="";
  state.items=[];
  state.selected=null;
  state.isNew=false;
  hideEditors();
}

function scopeQuery(){
  const params=new URLSearchParams();
  params.set("island",$("island").value);
  if(state.area==="guide") params.set("section",$("resource").value);
  if(state.area==="explore" || state.area==="live") params.set("resource",$("resource").value);
  if(state.area==="calendar") params.set("month",$("month").value);
  return params.toString();
}

function endpoint(){
  if(state.area==="guide") return "/api/editor/content";
  if(state.area==="explore") return "/api/editor/explore";
  if(state.area==="calendar") return "/api/editor/events";
  if(state.area==="news") return "/api/editor/news";
  if(state.area==="live") return "/api/editor/live";
  return "/api/editor/media";
}

function hideEditors(){
  $("form").classList.add("hidden");
  $("readonly-panel").classList.add("hidden");
  $("empty").classList.remove("hidden");
}

function itemName(item){
  return item.name || item.title || item.common_name || item.slug || item.id || item.key || "Sin nombre";
}
function itemSubtitle(item){
  if(state.area==="calendar") return item.start_date||"";
  if(state.area==="news") return item.source||item.published_at||"";
  if(state.area==="media") return (item.area||"")+" · "+(item.resource||"");
  return item.slug||item.category||item.id||"";
}

function renderList(){
  const root=$("items");
  const query=$("search").value.trim().toLowerCase();
  root.innerHTML="";
  let visible=0;
  state.items.forEach(item=>{
    const haystack=(itemName(item)+" "+itemSubtitle(item)).toLowerCase();
    if(query && !haystack.includes(query)) return;
    visible+=1;
    const button=document.createElement("button");
    button.type="button";
    const selectedKey=state.selected&&(state.selected._editor_key||state.selected.slug||state.selected.key);
    const key=item._editor_key||item.slug||item.key;
    button.className="item"+(selectedKey===key&&!state.isNew?" active":"");
    let badges="";
    if(item.hidden) badges+='<span class="badge warn">OCULTO</span>';
    if(item.missing) badges+='<span class="badge warn">SIN FOTO</span>';
    if(item.editorial_override) badges+='<span class="badge">EDITADO</span>';
    button.innerHTML="<strong>"+escapeHtml(itemName(item))+"</strong><small>"+escapeHtml(itemSubtitle(item))+"</small>"+(badges?'<span class="badges">'+badges+"</span>":"");
    button.addEventListener("click",()=>selectItem(item));
    root.appendChild(button);
  });
  $("summary").textContent=visible+" / "+state.items.length+" elementos";
}

function value(id,newValue){
  const el=$(id);
  if(arguments.length>1) el.value=newValue==null?"":newValue;
  return el.value;
}
function checked(id,newValue){
  const el=$(id);
  if(arguments.length>1) el.checked=Boolean(newValue);
  return el.checked;
}

function resetFormVisibility(){
  const area=state.area;
  setVisible("date-fields",area==="calendar");
  setVisible("order-row",area==="guide");
  setVisible("category-row",["guide","explore","calendar"].includes(area));
  setVisible("tags-row",["guide","explore"].includes(area));
  setVisible("featured-row",["guide","explore"].includes(area));
  setVisible("verified-row",area==="explore");
  setVisible("hidden-row",["explore","calendar","news"].includes(area));
  setVisible("lat-row",["explore","calendar"].includes(area));
  setVisible("lon-row",["explore","calendar"].includes(area));
  setVisible("media-box",["guide","explore","calendar","news"].includes(area));
  setVisible("source-row",["guide","explore","calendar","news"].includes(area));
  $("identity").disabled=!state.isNew||area!=="guide";
}

function selectItem(item){
  if(["live","media"].includes(state.area)){
    state.selected=item;
    showReadonly(itemName(item),item);
    renderList();
    return;
  }

  state.selected=JSON.parse(JSON.stringify(item));
  state.isNew=false;
  $("empty").classList.add("hidden");
  $("readonly-panel").classList.add("hidden");
  $("form").classList.remove("hidden");
  resetFormVisibility();

  $("mode").textContent=(AREA_LABELS[state.area]||state.area).toUpperCase();
  $("form-title").textContent=itemName(item);
  const identity=state.area==="guide"?item.slug:(item.id||item.url||item._identity||item._editor_key||"");
  value("identity",identity);
  value("name",item.name||item.title||item.common_name||"");
  value("category",item.category||"");
  value("order",item.order||"");
  value("description",item.description||item.summary||"");
  value("tags",Array.isArray(item.tags)?item.tags.join(", "):(Array.isArray(item.editorial_tags)?item.editorial_tags.join(", "):""));
  checked("featured",item.featured===true);
  checked("verified",item.verified===true);
  checked("hidden-item",item.hidden===true);
  value("latitude",item.latitude);
  value("longitude",item.longitude);
  value("start_date",item.start_date);
  value("end_date",item.end_date);
  value("location_name",item.location_name);
  checked("all_day",item.all_day!==false);
  value("image_url",item.image_url||item.image||"");
  value("image_credit",item.image_credit||"");
  value("image_license",item.image_license||"");
  value("image_origin",item.image_origin||"");
  value("image_source_url",item.image_source_url||"");
  value("image_license_url",item.image_license_url||"");
  value("source_url",item.source_url||item.website||item.url||"");
  value("raw-json",JSON.stringify(item,null,2));
  updateImagePreview();
  $("delete").classList.remove("hidden");
  setStatus("");
  renderList();
}

function newItem(){
  if(state.area==="explore" && $("resource").value==="routes"){
    alert("Las rutas necesitan geometría real. Puedes editar rutas existentes, pero no crear una línea desde este formulario.");
    return;
  }
  state.selected={};
  state.isNew=true;
  $("empty").classList.add("hidden");
  $("readonly-panel").classList.add("hidden");
  $("form").classList.remove("hidden");
  $("form").reset();
  resetFormVisibility();
  $("mode").textContent="NUEVO";
  $("form-title").textContent=state.area==="calendar"?"Nuevo evento":"Nuevo contenido";
  value("raw-json","{}");
  $("delete").classList.add("hidden");
  updateImagePreview();
  setStatus("");
}

function buildItem(){
  let base={};
  const raw=value("raw-json").trim();
  if(raw){
    try{base=JSON.parse(raw);}
    catch(error){throw new Error("JSON avanzado no es válido.");}
  }

  const assign=(key,val)=>{
    if(val===""||val==null) delete base[key];
    else base[key]=val;
  };
  const area=state.area;

  if(area==="guide"){
    assign("slug",value("identity").trim());
    assign("name",value("name").trim());
  }else if(area==="calendar"||area==="news"){
    assign("title",value("name").trim());
  }else{
    assign("name",value("name").trim());
  }

  assign("category",value("category").trim());
  if(area==="calendar"||area==="news") assign("summary",value("description").trim());
  else assign("description",value("description").trim());

  if(area==="guide"){
    const order=value("order").trim();
    if(order) base.order=Number(order); else delete base.order;
  }

  if(["guide","explore"].includes(area)){
    const tags=value("tags").split(",").map(v=>v.trim()).filter(Boolean);
    if(tags.length) base.tags=tags; else delete base.tags;
    base.featured=checked("featured");
  }
  if(area==="explore") base.verified=checked("verified");
  if(["explore","calendar","news"].includes(area)) base.hidden=checked("hidden-item");

  if(["explore","calendar"].includes(area)){
    const lat=value("latitude").trim();
    const lon=value("longitude").trim();
    if(lat) base.latitude=Number(lat); else delete base.latitude;
    if(lon) base.longitude=Number(lon); else delete base.longitude;
  }

  if(area==="calendar"){
    assign("start_date",value("start_date"));
    assign("end_date",value("end_date"));
    assign("location_name",value("location_name").trim());
    base.all_day=checked("all_day");
  }

  if(["guide","explore","calendar","news"].includes(area)){
    assign("image_url",value("image_url").trim());
    assign("image_credit",value("image_credit").trim());
    assign("image_license",value("image_license").trim());
    assign("image_origin",value("image_origin").trim());
    assign("image_source_url",value("image_source_url").trim());
    assign("image_license_url",value("image_license_url").trim());

    const source=value("source_url").trim();
    if(area==="explore") assign("website",source);
    else if(area==="calendar"||area==="news"){
      if(state.isNew&&area==="calendar") assign("url",source);
    }else assign("source_url",source);
  }

  return base;
}

function updateImagePreview(){
  const url=value("image_url").trim();
  const root=$("image-preview");
  root.innerHTML="";
  if(!url){root.textContent="Sin imagen";return;}
  const img=document.createElement("img");
  img.src=url;
  img.alt="";
  img.onerror=()=>{root.textContent="No se pudo cargar la imagen";};
  root.appendChild(img);
}

function showReadonly(title,payload){
  $("empty").classList.add("hidden");
  $("form").classList.add("hidden");
  $("readonly-panel").classList.remove("hidden");
  $("readonly-title").textContent=title;
  $("readonly-label").textContent=state.area==="live"?"LIVE · READ ONLY":"MEDIA";
  $("readonly-json").textContent=JSON.stringify(payload,null,2);
}

async function loadArea(){
  hideEditors();
  $("summary").textContent="Cargando…";
  try{
    const data=await api(endpoint()+"?"+scopeQuery());

    if(state.area==="live"){
      state.items=[{name:RESOURCE_LABELS[$("resource").value]||$("resource").value,snapshot:data.payload}];
      $("summary").textContent="Snapshot read-only";
      showReadonly(RESOURCE_LABELS[$("resource").value]||$("resource").value,data.payload);
      renderList();
      return;
    }

    state.items=data.items||[];
    state.selected=null;
    state.isNew=false;
    $("empty").classList.remove("hidden");
    $("readonly-panel").classList.add("hidden");
    $("form").classList.add("hidden");

    if(state.area==="media"){
      $("summary").textContent=data.with_image+" con foto · "+data.missing+" sin foto";
    }
    renderList();
  }catch(error){
    $("summary").textContent=error.message;
    $("empty").innerHTML="<h2>Error</h2><p>"+escapeHtml(error.message)+"</p>";
    $("empty").classList.remove("hidden");
  }
}

async function save(event){
  event.preventDefault();
  setStatus("Guardando…");
  try{
    const item=buildItem();
    let url=endpoint()+"?"+scopeQuery();
    let method="POST";

    if(!state.isNew){
      method="PUT";
      if(state.area==="guide") url=endpoint()+"/"+encodeURIComponent(state.selected.slug)+"?"+scopeQuery();
      else url=endpoint()+"/"+encodeURIComponent(state.selected._editor_key)+"?"+scopeQuery();
    }

    const result=await api(url,{method,body:JSON.stringify(item)});
    await loadArea();
    const saved=result&&result.saved;
    if(saved){
      const key=saved._editor_key||saved.slug;
      const found=state.items.find(x=>(x._editor_key||x.slug)===key);
      if(found) selectItem(found);
    }
    setStatus("Guardado ✓");
  }catch(error){
    setStatus(error.message,true);
  }
}

async function removeItem(){
  if(!state.selected||state.isNew) return;
  const verb=state.area==="guide"?"Eliminar":"Ocultar";
  if(!confirm(verb+' "'+itemName(state.selected)+'"?')) return;

  try{
    let url;
    if(state.area==="guide") url=endpoint()+"/"+encodeURIComponent(state.selected.slug)+"?"+scopeQuery();
    else url=endpoint()+"/"+encodeURIComponent(state.selected._editor_key)+"?"+scopeQuery();
    await api(url,{method:"DELETE"});
    await loadArea();
  }catch(error){
    setStatus(error.message,true);
  }
}

async function init(){
  $("token").value=localStorage.getItem("canarias-editor-token")||"";
  try{
    state.options=await api("/api/editor/options");
    renderTabs();
    configureArea();
    if(state.options.media_upload_enabled) $("upload-status").textContent="R2 configurado; falta conectar el endpoint de upload.";
    await loadArea();
  }catch(error){
    $("empty").innerHTML="<h2>No se pudo abrir el admin</h2><p>"+escapeHtml(error.message)+"</p>";
  }
}

$("token").addEventListener("change",()=>{localStorage.setItem("canarias-editor-token",$("token").value.trim());loadArea();});
$("reload").addEventListener("click",loadArea);
$("island").addEventListener("change",loadArea);
$("resource").addEventListener("change",()=>{
  $("new-item").classList.toggle("hidden",state.area==="explore"&&$("resource").value==="routes");
  loadArea();
});
$("month").addEventListener("change",loadArea);
$("search").addEventListener("input",renderList);
$("new-item").addEventListener("click",newItem);
$("delete").addEventListener("click",removeItem);
$("form").addEventListener("submit",save);
$("image_url").addEventListener("input",updateImagePreview);

init();
