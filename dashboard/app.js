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
    } else if(page==="messages"){
      section.innerHTML='<div class="panel-heading"><div><h2>Сообщения Discord</h2><p>Отправка обычных сообщений и Embed от имени WhiteGrief</p></div><button class="text-button" id="refreshMessageChannels">Обновить каналы</button></div><div id="messagesResult" class="messages-workspace"><div class="empty-state">Загружаем каналы Discord…</div></div>';
      loadMessages(section);
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
const initialPage=new URLSearchParams(window.location.search).get("page");
if(initialPage && pageNames[initialPage]) showPage(initialPage);
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


async function loadMessages(section){
  const root=section.querySelector("#messagesResult");
  const refresh=section.querySelector("#refreshMessageChannels");
  if(!root)return;
  root.innerHTML='<div class="empty-state">Загружаем текстовые каналы…</div>';
  try{
    const data=await apiGet("/api/messages/channels");
    const channels=data.channels||[];
    if(!channels.length){root.innerHTML='<div class="empty-state"><strong>Нет доступных каналов</strong><p>Бот не видит текстовые каналы сервера или у него нет прав на просмотр каналов.</p></div>';return;}
    root.innerHTML=`
      <div class="messages-compose">
        <div class="messages-form">
          <label class="messages-label">Канал Discord
            <select id="messageChannel" class="messages-control"></select>
          </label>
          <label class="messages-label">Текст сообщения <span>необязательно; подпись отправителя добавится автоматически</span>
            <textarea id="messageContent" class="messages-control" rows="4" maxlength="1750" placeholder="Напиши сообщение от имени WhiteGrief…"></textarea>
          </label>
          <label class="messages-label">Изображение <span>PNG, JPG, GIF или WEBP · до 8 МБ</span>
            <input id="messageImage" class="messages-control messages-file-input" type="file" accept="image/png,image/jpeg,image/gif,image/webp">
          </label>
          <div id="messageImagePreview" class="messages-image-preview" hidden><img id="messageImagePreviewImg" alt="Предпросмотр изображения"><button id="removeMessageImage" type="button">Убрать изображение</button></div>
          <div class="messages-section-caption">EMBED-ПАНЕЛЬ <span>необязательно</span></div>
          <label class="messages-label">Заголовок Embed
            <input id="embedTitle" class="messages-control" maxlength="256" placeholder="Например: WHITEGRIEF • ОБЪЯВЛЕНИЕ">
          </label>
          <label class="messages-label">Описание Embed
            <textarea id="embedDescription" class="messages-control" rows="5" maxlength="4096" placeholder="Текст внутри Embed…"></textarea>
          </label>
          <label class="messages-label">Цвет Embed
            <div class="messages-color-row"><input id="embedColor" type="color" value="#8b6bd6"><code id="embedColorText">#8B6BD6</code></div>
          </label>
          <div class="messages-form-footer"><span id="messageStatus" class="messages-status">Отправка доступна уровням Adm и Full.</span><button id="sendDiscordMessage" class="messages-send-button" type="button">Отправить в Discord</button></div>
        </div>
        <aside class="messages-preview-wrap"><div class="messages-preview-heading">ПРЕДПРОСМОТР</div><div class="messages-preview-meta"><span class="messages-meta-item"><small>ОТПРАВИТЕЛЬ ПАНЕЛИ</small><strong id="messagePreviewSender">Администратор</strong></span><span class="messages-meta-arrow">→</span><span class="messages-meta-item"><small>КАНАЛ ПОЛУЧАТЕЛЬ</small><strong id="messagePreviewChannel">общий-чат</strong></span></div><div class="discord-preview"><div class="discord-preview-avatar">W</div><div class="discord-preview-body"><strong>WhiteGrief <small>БОТ</small></strong><p id="messagePreviewContent" class="discord-preview-content">Текст сообщения появится здесь.</p><div id="embedPreview" class="discord-embed-preview" hidden><div id="embedPreviewTitle" class="discord-embed-title"></div><div id="embedPreviewDescription" class="discord-embed-description"></div></div></div></div><div id="messagePreviewImageWrap" class="discord-image-preview" hidden><img id="messagePreviewImage" alt="Изображение к сообщению"></div><div id="messagePreviewAttribution" class="discord-attribution-preview">— Отправитель: Администратор<br>Отправлено через WhiteGrief Control Panel</div></div><p class="messages-preview-note">Внизу сообщения автоматически появится подпись отправителя.</p></aside>
      </div><section class="messages-incoming"><div class="messages-incoming-head"><div><h3>Сообщения игроков</h3><p>Входящие сообщения из выбранного Discord-канала</p></div><button id="refreshIncomingMessages" class="text-button" type="button">Обновить</button></div><div id="incomingMessagesFeed" class="messages-incoming-feed"><div class="empty-state">Загружаем сообщения…</div></div></section>`;
    const channelSelect=root.querySelector("#messageChannel");
    channels.forEach(ch=>{
      const option=document.createElement("option");option.value=ch.id;option.textContent=(ch.parent_name?ch.parent_name+" / ":"")+ch.name;channelSelect.append(option);
    });
    const content=root.querySelector("#messageContent"),title=root.querySelector("#embedTitle"),description=root.querySelector("#embedDescription"),color=root.querySelector("#embedColor"),imageInput=root.querySelector("#messageImage"),imagePreview=root.querySelector("#messageImagePreview"),imagePreviewImg=root.querySelector("#messageImagePreviewImg"),previewImageWrap=root.querySelector("#messagePreviewImageWrap"),previewImage=root.querySelector("#messagePreviewImage"),previewSender=root.querySelector("#messagePreviewSender"),attributionPreview=root.querySelector("#messagePreviewAttribution");
    const previewContent=root.querySelector("#messagePreviewContent"),preview=root.querySelector("#embedPreview"),previewTitle=root.querySelector("#embedPreviewTitle"),previewDescription=root.querySelector("#embedPreviewDescription"),previewChannel=root.querySelector("#messagePreviewChannel"),status=root.querySelector("#messageStatus"),send=root.querySelector("#sendDiscordMessage"),colorText=root.querySelector("#embedColorText");
    const updatePreview=()=>{
      previewContent.textContent=content.value.trim()||"Текст сообщения появится здесь.";
      const hasEmbed=title.value.trim()||description.value.trim();
      preview.hidden=!hasEmbed;previewTitle.textContent=title.value;previewDescription.textContent=description.value;
      preview.style.setProperty("--embed-preview-color",color.value);
      preview.style.backgroundColor="#2b2d31";
      preview.style.boxShadow="none";
      colorText.textContent=color.value.toUpperCase();
      const selected=channelSelect.options[channelSelect.selectedIndex];
      previewChannel.textContent=selected?selected.textContent.split(" / ").pop():"канал";
      const senderLabel=data.sender?.username||"Администратор";
      previewSender.textContent=senderLabel;
      attributionPreview.innerHTML="— Отправитель: "+senderLabel.replace(/[&<>"]/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]))+"<br>Отправлено через WhiteGrief Control Panel";
    };
    [content,title,description,color].forEach(el=>el.addEventListener("input",updatePreview));
    channelSelect.addEventListener("change",updatePreview);
    imageInput.addEventListener("change",()=>{const file=imageInput.files?.[0];if(!file){imagePreview.hidden=true;previewImageWrap.hidden=true;return;}const url=URL.createObjectURL(file);imagePreviewImg.src=url;previewImage.src=url;imagePreview.hidden=false;previewImageWrap.hidden=false;});
    root.querySelector("#removeMessageImage").addEventListener("click",()=>{imageInput.value="";imagePreview.hidden=true;previewImageWrap.hidden=true;});
    updatePreview();
    const incomingFeed=root.querySelector("#incomingMessagesFeed");
    const refreshIncoming=root.querySelector("#refreshIncomingMessages");
    let incomingBusy=false;
    const loadIncoming=async()=>{
      if(incomingBusy||!channelSelect.value)return;
      incomingBusy=true;
      try{
        const result=await apiGet("/api/messages/history?channel_id="+encodeURIComponent(channelSelect.value));
        const messages=(result.messages||[]).slice().reverse(); // Discord API returns newest first; show oldest at top and newest at bottom.
        incomingFeed.replaceChildren();
        if(!messages.length){const empty=document.createElement("div");empty.className="empty-state";empty.textContent="Пока нет сообщений от игроков в этом канале.";incomingFeed.append(empty);return;}
        messages.forEach(message=>{
          const card=document.createElement("article");card.className="incoming-message";
          const icon=document.createElement("div");icon.className="incoming-message-avatar";
          if(message.avatar){const avatar=document.createElement("img");avatar.src=message.avatar;avatar.alt="";avatar.loading="lazy";icon.append(avatar);}
          else{icon.textContent=(message.author||"И").trim().slice(0,1).toUpperCase();}
          const main=document.createElement("div");main.className="incoming-message-main";
          if(message.reply){
            const reply=document.createElement("div");reply.className="incoming-message-context";
            const glyph=document.createElement("span");glyph.className="incoming-context-icon";glyph.textContent="↪";
            const label=document.createElement("span");label.textContent="Ответ на ";
            const who=document.createElement("strong");who.textContent=message.reply.author||"сообщение";
            const excerpt=document.createElement("span");excerpt.className="incoming-context-excerpt";excerpt.textContent=message.reply.content||"Вложение или сообщение без текста";
            reply.append(glyph,label,who,excerpt);main.append(reply);
          }
          (message.forwarded||[]).forEach(source=>{
            const forward=document.createElement("div");forward.className="incoming-message-context incoming-message-forward";
            const glyph=document.createElement("span");glyph.className="incoming-context-icon";glyph.textContent="➦";
            const label=document.createElement("span");label.textContent="Переслано из ";
            const channel=document.createElement("strong");channel.textContent="#"+(source.channel_name||"другого канала");
            const who=document.createElement("span");who.textContent=" · "+(source.author||"игрок");
            const excerpt=document.createElement("span");excerpt.className="incoming-context-excerpt";excerpt.textContent=source.content||"Вложение или сообщение без текста";
            forward.append(glyph,label,channel,who,excerpt);main.append(forward);
          });
          const head=document.createElement("div");head.className="incoming-message-head";
          const identity=document.createElement("div");identity.className="incoming-message-identity";
          const author=document.createElement("strong");author.textContent=message.author||"Игрок";
          const channelBadge=document.createElement("span");channelBadge.className="incoming-message-channel";channelBadge.textContent="В WhiteGrief";
          identity.append(author,channelBadge);
          const time=document.createElement("time");
          const date=new Date(message.timestamp);time.textContent=Number.isNaN(date.getTime())?"":date.toLocaleString("ru-RU",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
          head.append(identity,time);main.append(head);
          if(message.content){const body=document.createElement("p");body.className="incoming-message-content";body.textContent=message.content;main.append(body);}
          (message.attachments||[]).forEach(file=>{
            const link=document.createElement("a");link.className="incoming-message-attachment";link.href=file.url;link.target="_blank";link.rel="noopener noreferrer";link.textContent="📎 "+file.name;main.append(link);
            if((file.content_type||"").startsWith("image/")||/\.(png|jpe?g|gif|webp)(\?|$)/i.test(file.url)){const img=document.createElement("img");img.className="incoming-message-image";img.src=file.url;img.alt=file.name;img.loading="lazy";main.append(img);}
          });
          (message.embeds||[]).forEach(embed=>{const box=document.createElement("div");box.className="incoming-message-embed";if(embed.title){const t=document.createElement("strong");t.textContent=embed.title;box.append(t);}if(embed.description){const d=document.createElement("p");d.textContent=embed.description;box.append(d);}main.append(box);});
          card.append(icon,main);incomingFeed.append(card);
        });
      }catch(error){incomingFeed.replaceChildren();const empty=document.createElement("div");empty.className="empty-state";empty.textContent="Не удалось загрузить сообщения: "+error.message;incomingFeed.append(empty);}
      finally{incomingBusy=false;}
    };
    refreshIncoming.addEventListener("click",loadIncoming);
    channelSelect.addEventListener("change",loadIncoming);
    loadIncoming();
    const incomingPoll=window.setInterval(()=>{if(!section.isConnected){window.clearInterval(incomingPoll);return;}if(!document.hidden)loadIncoming();},10000);
    send.addEventListener("click",async()=>{
      const body=content.value.trim(),embedTitle=title.value.trim(),embedDescription=description.value.trim(),file=imageInput.files?.[0]||null;
      if(!body&&!embedTitle&&!embedDescription&&!file){status.textContent="Добавь текст, Embed или изображение.";status.className="messages-status error";return;}
      if(file&&file.size>8*1024*1024){status.textContent="Изображение должно быть не больше 8 МБ.";status.className="messages-status error";return;}
      send.disabled=true;send.textContent="Отправляем…";status.textContent="Связываемся с Discord…";status.className="messages-status";
      try{
        let image=null;if(file){const dataUrl=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error("Не удалось прочитать изображение."));reader.readAsDataURL(file);});image={name:file.name,mime:file.type,data:dataUrl};}
        const response=await fetch("/api/messages/send",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({channel_id:channelSelect.value,content:body,embed:embedTitle||embedDescription?{title:embedTitle,description:embedDescription,color:color.value}:null,image})});
        const raw=await response.text();let result={};try{result=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ (HTTP "+response.status+").");}
        if(!response.ok)throw new Error(result.detail||"Не удалось отправить сообщение.");
        status.textContent="✓ Сообщение отправлено в "+(channels.find(c=>c.id===channelSelect.value)?.name||"Discord");status.className="messages-status success";
        if(typeof showToast==="function")showToast("Сообщение успешно отправлено в Discord.");
        content.value="";imageInput.value="";imagePreview.hidden=true;previewImageWrap.hidden=true;updatePreview();
      }catch(error){status.textContent=error.message;status.className="messages-status error";}
      finally{send.disabled=false;send.textContent="Отправить в Discord";}
    });
  }catch(error){root.innerHTML="";const box=document.createElement("div");box.className="empty-state";const title=document.createElement("strong");title.textContent="Не удалось загрузить каналы";const detail=document.createElement("p");detail.textContent=error.message;box.append(title,detail);root.append(box);}
  refresh?.addEventListener("click",()=>loadMessages(section));
}
