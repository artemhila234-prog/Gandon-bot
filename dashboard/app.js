const pageNames={dashboard:"Главная",players:"Игроки",requests:"Заявки",shop:"Магазин",messages:"Сообщения",logs:"Логи",console:"Консоль",settings:"Настройки"};
const content=document.getElementById("pageContent");
const breadcrumb=document.getElementById("breadcrumb");
const sidebar=document.getElementById("sidebar");
const overlay=document.getElementById("overlay");
function showPage(page){
  if(!pageNames[page]) return;
  document.querySelectorAll(".nav-item").forEach(button=>button.classList.toggle("active",button.dataset.page===page));
  breadcrumb.textContent=pageNames[page];
  if(page!=="dashboard"){
    const descriptions={players:"Управление участниками, балансами, варнами и ролями.",requests:"Проверка заявок на вступление и получение баллов.",shop:"Настройка товаров, наборов, донатов и стоимости.",messages:"Отправка сообщений и Embed-панелей в Discord.",logs:"Просмотр latest.log и audit.log.",console:"Мониторинг и безопасное управление ботом.",settings:"Подключения, роли, каналы и параметры панели."};
    const existing=document.getElementById("comingPage");
    if(existing) existing.remove();
    const section=document.createElement("section");
    section.id="comingPage";section.className="panel coming-page";
    section.innerHTML='<div class="empty-state"><div class="empty-icon">✦</div><strong>'+pageNames[page]+'</strong><p>'+descriptions[page]+'</p><span class="pill pending">Будет реализовано на следующем этапе</span></div>';
    const old=document.getElementById("dashboardBody");
    if(old) old.hidden=true;
    if(page==="players"){
      section.innerHTML='<div class="panel-heading"><div><h2>Игроки</h2><p>Баланс и варны из базы бота</p></div><button class="text-button" id="refreshPlayers">Обновить</button></div><input id="playerSearch" class="panel-search" placeholder="⌕  Поиск по Discord ID"><div id="playersResult" class="empty-state">Загрузка игроков…</div>';
      loadPlayers(section);
    } else if(page==="requests"){
      section.innerHTML='<div class="panel-heading"><div><h2>Заявки</h2><p>Очередь заявок из базы бота · только просмотр</p></div><button class="text-button" id="refreshRequests">Обновить</button></div><div id="requestsResult" class="empty-state">Загрузка заявок…</div>';
      loadRequests(section);
    } else if(page==="shop"){
      section.innerHTML='<div class="panel-heading"><div><h2>Магазин</h2><p>Каталог, доступный в API · только просмотр</p></div><button class="text-button" id="refreshShop">Обновить</button></div><div id="shopResult" class="empty-state">Загрузка каталога…</div>';
      loadShop(section);
    }
    content.appendChild(section);
  }else{
    const old=document.getElementById("comingPage");if(old)old.remove();
    const oldBody=document.getElementById("dashboardBody");if(oldBody)oldBody.hidden=false;
  }
  closeMenu();
}
function closeMenu(){sidebar.classList.remove("open");overlay.classList.remove("show")}
document.querySelectorAll("[data-page]").forEach(button=>button.addEventListener("click",()=>showPage(button.dataset.page)));
document.querySelectorAll("[data-go]").forEach(button=>button.addEventListener("click",()=>showPage(button.dataset.go)));
document.getElementById("menuButton").addEventListener("click",()=>{sidebar.classList.toggle("open");overlay.classList.toggle("show")});
overlay.addEventListener("click",closeMenu);
// The dashboard is a static first-stage shell. No fake metrics or live bot actions are exposed.


// Discord session and access display. Authorization decisions are made by the backend.
const loginButton=document.getElementById("loginButton");
const logoutButton=document.getElementById("logoutButton");
const authBadge=document.getElementById("authBadge");
const sideUserName=document.getElementById("sideUserName");
const sideUserAccess=document.getElementById("sideUserAccess");
const topAvatar=document.getElementById("topAvatar");
const sideAvatar=document.getElementById("sideAvatar");
let currentAccessLevel="none";
const accessLabels={none:"Нет доступа",media:"Media",co_adm:"Co.Adm — управление персоналом",adm:"Adm — управление ботом",full:"Full — полный доступ"};
function avatarLetter(name){return (name||"?").trim().slice(0,1).toUpperCase()}
async function loadSession(){
  try{
    const response=await fetch("/api/me",{credentials:"same-origin"});
    const data=await response.json();
    if(!data.authenticated){
      authBadge.textContent="НЕ АВТОРИЗОВАН";
      sideUserName.textContent="Гость";
      sideUserAccess.textContent="Вход не выполнен";
      return;
    }
    const user=data.user;
    currentAccessLevel=user.access_level||"none";
    const letter=avatarLetter(user.username);
    authBadge.textContent="DISCORD ПОДКЛЮЧЁН";
    authBadge.classList.add("authenticated");
    loginButton.hidden=true;
    logoutButton.hidden=false;
    sideUserName.textContent=user.username;
    sideUserAccess.textContent=accessLabels[user.access_level]||"Нет доступа";
    topAvatar.textContent=letter;
    sideAvatar.textContent=letter;
    const mediaText=user.access_level==="none"?"доступ не выдан":"доступ подтверждён";
    const setupTag=document.getElementById("setupTag");
    if(setupTag)setupTag.textContent=user.access_level==="none"?"NO ACCESS":"ACCESS VERIFIED";
    const notice=document.querySelector(".notice p");
    if(notice){
      const roleText=(user.role_names||[]).length?(user.role_names.join(", ")):"Ролей не найдено";
      notice.textContent="Discord: "+user.discord_username+" · "+mediaText+". Ваш класс доступа: "+(accessLabels[user.access_level]||"не назначен")+". Роли: "+roleText+".";
    }
  }catch(error){
    authBadge.textContent="API НЕДОСТУПЕН";
  }
}
if(logoutButton){
  logoutButton.addEventListener("click",async()=>{
    await fetch("/auth/logout",{method:"POST",credentials:"same-origin"});
    window.location.href="/";
  });
}
loadSession();


function makeCell(value){
  const cell=document.createElement("td");
  cell.textContent=String(value??"—");
  return cell;
}
async function apiGet(url){
  const response=await fetch(url,{credentials:"same-origin"});
  const data=await response.json();
  if(!response.ok)throw new Error(data.detail||"Ошибка запроса.");
  return data;
}
async function loadPlayers(section){
  const result=section.querySelector("#playersResult"),refresh=section.querySelector("#refreshPlayers"),search=section.querySelector("#playerSearch");
  if(!result)return;let players=[];
  const render=()=>{
    const term=(search?.value||"").trim().toLowerCase();
    const filtered=players.filter(p=>(String(p.user_id)+" "+(p.username||"")+" "+(p.discord_username||"")).toLowerCase().includes(term));
    if(!filtered.length){result.className="empty-state";result.textContent=players.length?"Ничего не найдено.":"Активных участников в базе не найдено.";return;}
    const list=document.createElement("div");list.className="discord-member-list";
    for(const p of filtered){
      const warns=Math.max(0,Math.min(2,Number(p.warns)||0));
      const row=document.createElement("article");row.className="discord-member-row";
      const avatar=document.createElement("div");avatar.className="discord-member-avatar";
      if(p.avatar_url){const img=document.createElement("img");img.src=p.avatar_url;img.alt="";img.loading="lazy";img.onerror=()=>{avatar.textContent=(p.username||"?").slice(0,1).toUpperCase();};avatar.append(img);}else avatar.textContent=(p.username||"?").slice(0,1).toUpperCase();
      const identity=document.createElement("div");identity.className="discord-member-identity";
      const name=document.createElement("strong");name.textContent=p.username||"Участник WhiteGrief";
      const sub=document.createElement("span");sub.textContent=(p.discord_username?"@"+p.discord_username+" · ":"")+"ID: "+p.user_id;identity.append(name,sub);
      const balance=document.createElement("div");balance.className="discord-member-balance";balance.innerHTML="<small>БАЛАНС</small>";
      const balanceValue=document.createElement("strong");balanceValue.textContent=Number(p.balance||0).toLocaleString("ru-RU")+" ✧";balance.append(balanceValue);
      const warn=document.createElement("div");warn.className="discord-member-warns";
      const warnLabel=document.createElement("small");warnLabel.textContent="ВАРНЫ";
      const warnText=document.createElement("strong");warnText.textContent=warns+"/3";
      const bars=document.createElement("span");bars.className="discord-warn-bars";
      for(let i=0;i<3;i++){const bar=document.createElement("i");if(i<warns)bar.classList.add("on");bars.append(bar);}warn.append(warnLabel,warnText,bars);
      const actions=document.createElement("div");actions.className="discord-member-actions";
      if(["co_adm","adm","full"].includes(currentAccessLevel)){
        const add=document.createElement("button");add.className="member-action give-warn";add.textContent="+ Варн";add.disabled=warns>=2;add.title=warns>=2?"Лимит достигнут: при следующем нарушении участника кикают с Discord-сервера.":"Выдать варн";add.addEventListener("click",()=>changePlayerWarn(p.user_id,"warn"));
        const remove=document.createElement("button");remove.className="member-action remove-warn";remove.textContent="−";remove.disabled=warns===0;remove.title="Снять варн";remove.addEventListener("click",()=>changePlayerWarn(p.user_id,"remove-warn"));actions.append(add,remove);
      }
      row.append(avatar,identity,balance,warn,actions);list.append(row);
    }
    result.className="players-result";result.replaceChildren(list);
  };
  const load=async()=>{result.className="empty-state";result.textContent="Загружаем участников…";try{const data=await apiGet("/api/players");players=data.players||[];render();}catch(e){result.className="empty-state";result.textContent=e.message;}};
  search?.addEventListener("input",render);refresh?.addEventListener("click",load);await load();
}
function openWarnDialog(userId,action){
  const existing=document.getElementById("warnActionModal");if(existing)existing.remove();
  const isAdd=action==="warn";
  const modal=document.createElement("div");modal.id="warnActionModal";modal.className="warn-modal";
  const dialog=document.createElement("form");dialog.className="warn-modal-card";dialog.setAttribute("role","dialog");dialog.setAttribute("aria-modal","true");
  const close=document.createElement("button");close.type="button";close.className="warn-modal-close";close.textContent="×";close.setAttribute("aria-label","Закрыть");
  const eyebrow=document.createElement("span");eyebrow.className="warn-modal-eyebrow";eyebrow.textContent="WHITEGRIEF • MODERATION";
  const title=document.createElement("h2");title.textContent=isAdd?"Выдать предупреждение":"Снять предупреждение";
  const description=document.createElement("p");description.className="warn-modal-description";description.textContent="Игрок Discord ID: "+userId+". Укажи причину действия.";
  const label=document.createElement("label");label.className="warn-modal-label";label.textContent="Причина";
  const textarea=document.createElement("textarea");textarea.className="warn-modal-reason";textarea.rows=4;textarea.maxLength=500;textarea.placeholder="Опиши нарушение или причину снятия…";textarea.required=true;
  const footer=document.createElement("div");footer.className="warn-modal-footer";
  const cancel=document.createElement("button");cancel.type="button";cancel.className="warn-modal-cancel";cancel.textContent="Отмена";
  const submit=document.createElement("button");submit.type="submit";submit.className="warn-modal-submit"+(isAdd?" danger":"");submit.textContent=isAdd?"Выдать варн":"Снять варн";
  const error=document.createElement("p");error.className="warn-modal-error";error.hidden=true;
  const dismiss=()=>modal.remove();close.addEventListener("click",dismiss);cancel.addEventListener("click",dismiss);
  modal.addEventListener("click",e=>{if(e.target===modal)dismiss();});
  dialog.addEventListener("submit",async e=>{
    e.preventDefault();const reason=textarea.value.trim();if(!reason){error.textContent="Укажи причину.";error.hidden=false;return;}
    submit.disabled=true;submit.textContent="Обработка…";error.hidden=true;
    try{
      const response=await fetch("/api/players/"+encodeURIComponent(userId)+"/"+action,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({reason})});
      const raw=await response.text();let data={};try{data=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ (HTTP "+response.status+"). Проверь логи первого хостинга.");}if(!response.ok)throw new Error(data.detail||"Не удалось изменить варны.");
      dismiss();const section=document.getElementById("comingPage");if(section)await loadPlayers(section);
      showToast(isAdd?"Варн успешно выдан.":"Варн успешно снят.");
    }catch(err){error.textContent=err.message||"Произошла ошибка.";error.hidden=false;submit.disabled=false;submit.textContent=isAdd?"Выдать варн":"Снять варн";}
  });
  footer.append(cancel,submit);label.append(textarea);dialog.append(close,eyebrow,title,description,label,error,footer);modal.append(dialog);document.body.append(modal);textarea.focus();
}
function showToast(message){
  const old=document.getElementById("panelToast");if(old)old.remove();
  const toast=document.createElement("div");toast.id="panelToast";toast.className="panel-toast";toast.textContent=message;document.body.append(toast);
  window.setTimeout(()=>toast.remove(),2600);
}
async function changePlayerWarn(userId,action){openWarnDialog(userId,action);}

async function loadRequests(section){
  const result=section.querySelector("#requestsResult"),refresh=section.querySelector("#refreshRequests");
  let requests=[];
  const load=async()=>{
    result.className="requests-loading";result.textContent="Загружаем очередь заявок…";
    if(refresh){refresh.disabled=true;refresh.textContent="Загрузка…";}
    try{
      const data=await apiGet("/api/requests");requests=data.requests||[];
      const wrap=document.createElement("div");wrap.className="requests-workspace";
      const hero=document.createElement("div");hero.className="requests-hero";
      hero.innerHTML='<div class="requests-hero-copy"><span class="requests-kicker">WHITEGRIEF • APPLICATION CENTER</span><h2>Центр заявок</h2><p>Все обращения сообщества собраны в одном месте.</p></div><div class="requests-hero-symbol" aria-hidden="true">▤</div>';
      const stats=document.createElement("div");stats.className="requests-stats";
      const stat=document.createElement("div");stat.className="requests-stat";stat.innerHTML='<span>ВСЕГО В ОЧЕРЕДИ</span><strong>'+requests.length+'</strong><small>заявок загружено</small>';stats.append(stat);
      const toolbar=document.createElement("div");toolbar.className="requests-toolbar";
      const heading=document.createElement("div");heading.innerHTML="<strong>Последние обращения</strong><span>Просмотр заявок из базы бота</span>";
      const search=document.createElement("input");search.className="requests-search";search.placeholder="⌕  Поиск по ID или типу…";search.setAttribute("aria-label","Поиск заявок");
      toolbar.append(heading,search);
      const list=document.createElement("div");list.className="request-list";
      const typeInfo={join:{name:"Заявка на вступление",icon:"♙",tone:"join"},points:{name:"Заявка на баллы",icon:"✧",tone:"points"}};
      const render=()=>{
        const term=search.value.trim().toLowerCase();
        const visible=requests.filter(item=>(String(item.user_id)+" "+String(item.message_id)+" "+String(item.type)+" "+JSON.stringify(item.data||{})).toLowerCase().includes(term));
        list.replaceChildren();
        if(!visible.length){const empty=document.createElement("div");empty.className="requests-empty";empty.innerHTML='<span>✦</span><strong>'+(requests.length?"Ничего не найдено":"Пока нет заявок")+'</strong><p>'+(requests.length?"Попробуй изменить поисковый запрос.":"Когда появятся новые обращения, они отобразятся здесь.")+'</p>';list.append(empty);return;}
        visible.forEach((item,index)=>{
          const info=typeInfo[item.type]||{name:"Заявка: "+item.type,icon:"✦",tone:"other"};
          const card=document.createElement("article");card.className="request-card request-card-"+info.tone;card.style.animationDelay=Math.min(index,10)*35+"ms";
          const top=document.createElement("div");top.className="request-card-top";
          const type=document.createElement("span");type.className="request-type "+info.tone;type.textContent=info.icon+"  "+info.name;
          const number=document.createElement("span");number.className="request-number";number.textContent="#"+String(index+1).padStart(2,"0");top.append(type,number);
          const user=document.createElement("div");user.className="request-user";user.innerHTML='<span class="request-user-avatar">♙</span><div><strong>Участник Discord</strong><small>ID: '+String(item.user_id??"—")+'</small></div>';
          const payload=document.createElement("div");payload.className="request-payload";
          const values=item.data&&typeof item.data==="object"?Object.entries(item.data):[];
          if(values.length){values.forEach(([key,value])=>{const field=document.createElement("div");field.className="request-field";const label=document.createElement("small");label.textContent=key.replace(/[_-]/g," ");const val=document.createElement("strong");val.textContent=typeof value==="object"?JSON.stringify(value):String(value??"—");field.append(label,val);payload.append(field);});}
          else {const message=document.createElement("p");message.className="request-message";message.textContent=typeof item.data==="string"?item.data:"Дополнительные сведения не указаны.";payload.append(message);}
          const meta=document.createElement("div");meta.className="request-meta";
          const date=document.createElement("span");date.textContent="◷  "+String(item.created_at||"Дата не указана");
          const msg=document.createElement("span");msg.textContent="Сообщение · "+String(item.message_id??"—");meta.append(date,msg);
          const actions=document.createElement("div");actions.className="request-card-actions";
          if(item.type==="join"){
            const approve=document.createElement("button");approve.type="button";approve.className="request-approve-button";approve.textContent="✓  Одобрить заявку";
            approve.addEventListener("click",()=>approveJoinRequest(item.user_id,approve));
            const reject=document.createElement("button");reject.type="button";reject.className="request-reject-button";reject.textContent="✕  Отклонить";
            reject.addEventListener("click",()=>rejectJoinRequest(item.user_id,reject));
            actions.append(approve,reject);
          }
          card.append(top,user,payload,meta,actions);list.append(card);
        });
      };
      search.addEventListener("input",render);render();wrap.append(hero,stats,toolbar,list);result.className="requests-view";result.replaceChildren(wrap);
    }catch(e){result.className="empty-state";result.textContent=e.message;}
    finally{if(refresh){refresh.disabled=false;refresh.textContent="↻  Обновить";}}
  };
  if(refresh)refresh.textContent="↻  Обновить";
  refresh?.addEventListener("click",load);await load();
}
function openApproveDialog(userId,onApprove){
  const old=document.getElementById("approveActionModal");if(old)old.remove();
  const modal=document.createElement("div");modal.id="approveActionModal";modal.className="action-modal";
  const card=document.createElement("section");card.className="action-modal-card";card.setAttribute("role","dialog");card.setAttribute("aria-modal","true");card.setAttribute("aria-labelledby","approveDialogTitle");
  const close=document.createElement("button");close.type="button";close.className="action-modal-close";close.textContent="×";close.setAttribute("aria-label","Закрыть");
  const icon=document.createElement("div");icon.className="action-modal-icon";icon.textContent="✦";
  const eyebrow=document.createElement("span");eyebrow.className="action-modal-eyebrow";eyebrow.textContent="WHITEGRIEF • APPLICATION CENTER";
  const title=document.createElement("h2");title.id="approveDialogTitle";title.textContent="Одобрить заявку?";
  const description=document.createElement("p");description.className="action-modal-description";description.textContent="Пользователь Discord ID: "+userId;
  const note=document.createElement("div");note.className="action-modal-note";note.textContent="Будут выданы роли, изменён ник и создан личный канал. Это действие изменит данные на Discord-сервере.";
  const footer=document.createElement("div");footer.className="action-modal-footer";
  const cancel=document.createElement("button");cancel.type="button";cancel.className="action-modal-cancel";cancel.textContent="Отмена";
  const approve=document.createElement("button");approve.type="button";approve.className="action-modal-confirm";approve.textContent="✓  Одобрить";
  const dismiss=()=>modal.remove();close.addEventListener("click",dismiss);cancel.addEventListener("click",dismiss);
  modal.addEventListener("click",e=>{if(e.target===modal)dismiss();});
  approve.addEventListener("click",async()=>{approve.disabled=true;approve.textContent="Обрабатываем…";cancel.disabled=true;try{await onApprove();dismiss();}catch(error){note.textContent=error.message||"Не удалось одобрить заявку.";note.classList.add("error");approve.disabled=false;approve.textContent="Повторить";cancel.disabled=false;}});
  footer.append(cancel,approve);card.append(close,icon,eyebrow,title,description,note,footer);modal.append(card);document.body.append(modal);approve.focus();
}
async function approveJoinRequest(userId,button){
  openApproveDialog(userId,async()=>{
    button.disabled=true;button.textContent="Обрабатываем…";
    try{
      const response=await fetch("/api/requests/"+encodeURIComponent(userId)+"/approve",{method:"POST",credentials:"same-origin"});
      const raw=await response.text();let data={};
      try{data=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ (HTTP "+response.status+"). Проверь логи обоих хостингов.");}
      if(!response.ok)throw new Error(data.detail||("Ошибка одобрения (HTTP "+response.status+")."));
      showToast("Заявка одобрена. Сообщение отправлено в Discord.");
      const section=document.getElementById("comingPage");if(section)await loadRequests(section);
    }catch(error){button.disabled=false;button.textContent="✓  Одобрить заявку";throw error;}
  });
}

function openRejectDialog(userId,onReject){
  const old=document.getElementById("rejectActionModal");if(old)old.remove();
  const modal=document.createElement("div");modal.id="rejectActionModal";modal.className="action-modal";
  const card=document.createElement("section");card.className="action-modal-card";card.setAttribute("role","dialog");card.setAttribute("aria-modal","true");
  const close=document.createElement("button");close.type="button";close.className="action-modal-close";close.textContent="×";
  const eyebrow=document.createElement("span");eyebrow.className="action-modal-eyebrow";eyebrow.textContent="WHITEGRIEF • APPLICATION CENTER";
  const title=document.createElement("h2");title.textContent="Отклонить заявку?";
  const description=document.createElement("p");description.className="action-modal-description";description.textContent="Discord ID: "+userId;
  const note=document.createElement("div");note.className="action-modal-note";note.textContent="Заявка будет отклонена, роль «Ожидание верификации» будет снята, а пользователю придёт уведомление в личные сообщения. С сервера он исключён не будет.";
  const footer=document.createElement("div");footer.className="action-modal-footer";
  const cancel=document.createElement("button");cancel.type="button";cancel.className="action-modal-cancel";cancel.textContent="Отмена";
  const reject=document.createElement("button");reject.type="button";reject.className="action-modal-confirm";reject.textContent="✕  Отклонить";
  const dismiss=()=>modal.remove();close.addEventListener("click",dismiss);cancel.addEventListener("click",dismiss);
  modal.addEventListener("click",e=>{if(e.target===modal)dismiss();});
  reject.addEventListener("click",async()=>{reject.disabled=true;reject.textContent="Обрабатываем…";cancel.disabled=true;try{await onReject();dismiss();}catch(error){note.textContent=error.message||"Не удалось отклонить заявку.";note.classList.add("error");reject.disabled=false;reject.textContent="Повторить";cancel.disabled=false;}});
  footer.append(cancel,reject);card.append(close,eyebrow,title,description,note,footer);modal.append(card);document.body.append(modal);reject.focus();
}
async function rejectJoinRequest(userId,button){
  openRejectDialog(userId,async()=>{
    button.disabled=true;button.textContent="Обрабатываем…";
    try{
      const response=await fetch("/api/requests/"+encodeURIComponent(userId)+"/reject",{method:"POST",credentials:"same-origin"});
      const raw=await response.text();let data={};
      try{data=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ (HTTP "+response.status+").");}
      if(!response.ok)throw new Error(data.detail||("Ошибка отклонения (HTTP "+response.status+")."));
      showToast("Заявка отклонена. Роль ожидания снята, пользователь остался на сервере.");
      const section=document.getElementById("comingPage");if(section)await loadRequests(section);
    }catch(error){button.disabled=false;button.textContent="✕  Отклонить";throw error;}
  });
}

async function loadShop(section){
  const result=section.querySelector("#shopResult"),refresh=section.querySelector("#refreshShop");
  const load=async()=>{
    result.className="shop-loading";
    result.textContent="Загружаем товары…";
    try{
      const data=await apiGet("/api/shop"),items=data.items||[];
      if(!items.length){result.className="empty-state";result.textContent="Каталог пуст.";return;}
      const icons={kit:"⚔️",донат:"👑",кейс:"🎁",услуга:"📜"};
      const categoryNames={kit:"Наборы",донат:"Привилегии",кейс:"Кейсы",услуга:"Услуги"};
      const hero=document.createElement("div");hero.className="shop-hero";
      hero.innerHTML='<div class="shop-hero-copy"><span class="shop-kicker">WHITEGRIEF • REWARDS</span><h2>Магазин</h2><p>Выбирай награды, наборы и привилегии за баллы.</p><span class="shop-hero-note">✦ Твой прогресс — твои преимущества</span></div><div class="shop-hero-art" aria-hidden="true"><span class="hero-orbit orbit-one">✦</span><span class="hero-crown">👑</span><span class="hero-orbit orbit-two">✧</span></div>';
      const tools=document.createElement("div");tools.className="shop-toolbar";
      const filters=document.createElement("div");filters.className="shop-filters";
      const search=document.createElement("input");search.className="shop-search";search.placeholder="⌕  Найти товар…";search.setAttribute("aria-label","Поиск товара");
      const grid=document.createElement("div");grid.className="shop-grid";
      const cats=["Все","kit","донат","кейс","услуга"];let active="Все";
      for(const cat of cats){const b=document.createElement("button");b.className="shop-filter"+(cat==="Все"?" active":"");b.textContent=cat==="Все"?"Все товары":categoryNames[cat];b.addEventListener("click",()=>{active=cat;filters.querySelectorAll("button").forEach(x=>x.classList.toggle("active",x===b));render();});filters.append(b);}
      tools.append(filters,search);
      const render=()=>{
        const term=search.value.trim().toLowerCase();
        const visible=items.filter(item=>(active==="Все"||item.type===active)&&String(item.name).toLowerCase().includes(term));
        grid.replaceChildren();
        if(!visible.length){const empty=document.createElement("div");empty.className="shop-empty";empty.textContent="Ничего не найдено. Попробуй изменить поиск.";grid.append(empty);return;}
        visible.forEach((item,index)=>{
          const card=document.createElement("article");card.className="shop-product-card";card.style.animationDelay=Math.min(index,12)*35+"ms";
          const visual=document.createElement("div");visual.className="shop-product-visual type-"+item.type;
          const glow=document.createElement("span");glow.className="shop-product-glow";
          const icon=document.createElement("span");icon.className="shop-product-icon";icon.textContent=icons[item.type]||"✦";
          visual.append(glow,icon);
          const category=document.createElement("span");category.className="shop-category";category.textContent=categoryNames[item.type]||item.type;
          const name=document.createElement("h3");name.textContent=item.name;
          const price=document.createElement("div");price.className="shop-price";price.innerHTML='<span aria-hidden="true">◈</span> '+Number(item.price).toLocaleString("ru-RU")+' <small>баллов</small>';
          const button=document.createElement("button");button.className="shop-buy-button";button.type="button";button.textContent="Подробнее";
          button.addEventListener("click",()=>showShopDetails(item,icons[item.type]||"✦",categoryNames[item.type]||item.type));
          card.append(visual,category,name,price,button);grid.append(card);
        });
      };
      search.addEventListener("input",render);
      render();result.className="shop-catalog";result.replaceChildren(hero,tools,grid);
    }catch(e){result.className="empty-state";result.textContent=e.message;}
  };
  refresh?.addEventListener("click",load);await load();
}
function showShopDetails(item,icon,category){
  const old=document.getElementById("shopDetailsModal");if(old)old.remove();
  const modal=document.createElement("div");modal.id="shopDetailsModal";modal.className="shop-modal";
  const dialog=document.createElement("div");dialog.className="shop-modal-card";dialog.setAttribute("role","dialog");dialog.setAttribute("aria-modal","true");
  const close=document.createElement("button");close.className="shop-modal-close";close.type="button";close.textContent="×";close.setAttribute("aria-label","Закрыть");
  const symbol=document.createElement("div");symbol.className="shop-modal-icon";symbol.textContent=icon;
  const tag=document.createElement("span");tag.className="shop-category";tag.textContent=category;
  const title=document.createElement("h2");title.textContent=item.name;
  const price=document.createElement("p");price.className="shop-modal-price";price.textContent=Number(item.price).toLocaleString("ru-RU")+" баллов";
  const note=document.createElement("p");note.className="shop-modal-note";note.textContent="Покупка через панель пока не подключена. Уточни оформление товара у администрации WhiteGrief.";
  const done=document.createElement("button");done.className="shop-buy-button";done.type="button";done.textContent="Понятно";
  const dismiss=()=>modal.remove();close.addEventListener("click",dismiss);done.addEventListener("click",dismiss);modal.addEventListener("click",e=>{if(e.target===modal)dismiss();});
  dialog.append(close,symbol,tag,title,price,note,done);modal.append(dialog);document.body.append(modal);done.focus();
}
