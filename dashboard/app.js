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
  if(!result)return;
  let players=[];
  const render=()=>{
    const term=(search?.value||"").trim().toLowerCase();
    const filtered=players.filter(p=>String(p.user_id).toLowerCase().includes(term));
    if(!filtered.length){result.className="empty-state";result.textContent=players.length?"Ничего не найдено.":"В базе пока нет записей об игроках.";return;}
    const grid=document.createElement("div");grid.className="player-grid";
    for(const p of filtered){
      const warns=Math.max(0,Math.min(2,Number(p.warns)||0));
      const card=document.createElement("article");card.className="player-card";
      const top=document.createElement("div");top.className="player-card-top";
      const avatar=document.createElement("div");avatar.className="player-avatar";avatar.textContent="✦";
      const identity=document.createElement("div");identity.className="player-identity";
      const name=document.createElement("strong");name.textContent="Участник WhiteGrief";
      const id=document.createElement("span");id.textContent="ID: "+p.user_id;
      identity.append(name,id);
      const state=document.createElement("span");state.className="player-state";state.textContent="В базе";
      top.append(avatar,identity,state);
      const metrics=document.createElement("div");metrics.className="player-metrics";
      const balance=document.createElement("div");balance.className="player-metric balance-metric";
      balance.innerHTML='<span>✧ Баланс</span>';
      const balanceValue=document.createElement("strong");balanceValue.textContent=Number(p.balance||0).toLocaleString("ru-RU")+" баллов";balance.append(balanceValue);
      const warn=document.createElement("div");warn.className="player-metric warn-metric";
      warn.innerHTML='<span>⚑ Варны</span>';
      const warnValue=document.createElement("strong");warnValue.textContent=warns+"/3";warn.append(warnValue);
      const progress=document.createElement("div");progress.className="warn-progress";
      for(let i=0;i<3;i++){const segment=document.createElement("i");if(i<warns)segment.classList.add("filled");progress.append(segment);}
      warn.append(progress);metrics.append(balance,warn);
      const actions=document.createElement("div");actions.className="player-actions";
      if(["co_adm","adm","full"].includes(currentAccessLevel)){
        const add=document.createElement("button");add.className="action-button primary-action";add.textContent=warns>=2?"Лимит 2/3":"+ Выдать варн";add.disabled=warns>=2;add.title=warns>=2?"Третий варн не выдаётся: за следующее нарушение участника кикают с Discord-сервера.":"Выдать варн";
        add.addEventListener("click",()=>changePlayerWarn(p.user_id,"warn"));
        const remove=document.createElement("button");remove.className="action-button secondary-action";remove.textContent="− Снять варн";remove.disabled=warns===0;remove.addEventListener("click",()=>changePlayerWarn(p.user_id,"remove-warn"));
        actions.append(add,remove);
      }else{const access=document.createElement("span");access.className="permission-note";access.textContent="Просмотр без управления";actions.append(access);}
      card.append(top,metrics,actions);grid.append(card);
    }
    result.className="players-result";result.replaceChildren(grid);
  };
  const load=async()=>{result.className="empty-state";result.textContent="Загружаем игроков…";try{const data=await apiGet("/api/players");players=data.players||[];render();}catch(e){result.className="empty-state";result.textContent=e.message;}};
  search?.addEventListener("input",render);refresh?.addEventListener("click",load);await load();
}
async function changePlayerWarn(userId,action){
  async function loadShop(section){
  const result=section.querySelector("#shopResult"),refresh=section.querySelector("#refreshShop");
  const load=async()=>{result.className="empty-state";result.textContent="Загружаем каталог…";try{
    const data=await apiGet("/api/shop"),items=data.items||[];
    if(!items.length){result.textContent="Каталог пуст.";return;}
    const labels={kit:"Привилегии", "донат":"Донат", "кейс":"Кейсы", "услуга":"Услуги"};
    const icons={kit:"♛","донат":"✦","кейс":"▣","услуга":"⚒"};
    const filters=document.createElement("div");filters.className="shop-filters";
    const grid=document.createElement("div");grid.className="shop-grid";
    const categories=["Все товары",...new Set(items.map(x=>x.type))];
    let active="Все товары";
    const render=()=>{
      filters.replaceChildren();
      for(const category of categories){
        const button=document.createElement("button");button.className="shop-filter"+(active===category?" active":"");button.textContent=category==="Все товары"?category:labels[category]||category;
        button.addEventListener("click",()=>{active=category;render();});filters.append(button);
      }
      const shown=active==="Все товары"?items:items.filter(x=>x.type===active);
      grid.replaceChildren();
      for(const item of shown){
        const card=document.createElement("article");card.className="shop-card";
        const icon=document.createElement("div");icon.className="shop-item-icon "+(item.type==="кейс"?"case-icon":item.type==="донат"?"donate-icon":item.type==="услуга"?"service-icon":"kit-icon");icon.textContent=icons[item.type]||"✦";
        const category=document.createElement("span");category.className="shop-category";category.textContent=labels[item.type]||item.type;
        const title=document.createElement("h3");title.textContent=item.name;
        const price=document.createElement("div");price.className="shop-price";price.innerHTML='<span>✧</span> '+Number(item.price).toLocaleString("ru-RU")+' <small>баллов</small>';
        const note=document.createElement("p");note.className="shop-description";note.textContent=item.type==="кейс"?"Открой и испытай удачу":item.type==="услуга"?"Дополнительная услуга сервера":item.type==="донат"?"Донат-привилегия WhiteGrief":"Игровой набор";
        card.append(icon,category,title,note,price);grid.append(card);
      }
    };
    const wrap=document.createElement("div");wrap.className="shop-content";wrap.append(filters,grid);result.className="shop-result";result.replaceChildren(wrap);render();
  }catch(e){result.className="empty-state";result.textContent=e.message;}};
  refresh?.addEventListener("click",load);await load();
}

async function loadRequests(section){
  const result=section.querySelector("#requestsResult"),refresh=section.querySelector("#refreshRequests");
  const load=async()=>{result.textContent="Загрузка заявок…";try{
    const data=await apiGet("/api/requests"),items=data.requests||[];
    if(!items.length){result.textContent="Ожидающих заявок нет.";return;}
    const list=document.createElement("div");list.className="request-list";
    for(const item of items){
      const card=document.createElement("article");card.className="request-card";
      const title=document.createElement("strong");title.textContent=item.type==="join"?"Заявка на вступление":item.type==="points"?"Заявка на баллы":"Заявка: "+item.type;
      const details=document.createElement("p");details.textContent="Discord ID: "+item.user_id+" · Сообщение: "+item.message_id;
      const dataLine=document.createElement("p");dataLine.textContent=JSON.stringify(item.data||{});
      const date=document.createElement("small");date.textContent="Создана: "+(item.created_at||"—");
      card.append(title,details,dataLine,date);list.append(card);
    }result.replaceChildren(list);
  }catch(e){result.textContent=e.message;}};
  refresh?.addEventListener("click",load);await load();
}
async function loadShop(section){
  const result=section.querySelector("#shopResult"),refresh=section.querySelector("#refreshShop");
  const load=async()=>{result.textContent="Загрузка каталога…";try{
    const data=await apiGet("/api/shop"),items=data.items||[];
    if(!items.length){result.textContent="Каталог пуст.";return;}
    const table=document.createElement("table");table.className="players-table";
    const head=document.createElement("thead");head.innerHTML="<tr><th>Товар</th><th>Категория</th><th>Цена</th></tr>";table.append(head);
    const body=document.createElement("tbody");
    for(const item of items){const row=document.createElement("tr");row.append(makeCell(item.name),makeCell(item.type),makeCell(item.price+" баллов"));body.append(row);}
    table.append(body);result.replaceChildren(table);
  }catch(e){result.textContent=e.message;}};
  refresh?.addEventListener("click",load);await load();
}
