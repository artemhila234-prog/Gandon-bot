const pageNames={dashboard:"Главная",discord:"Discord от бота",players:"Игроки",requests:"Заявки",shop:"Магазин",messages:"Сообщения",tickets:"Тикеты",logs:"Логи",console:"Консоль",access:"Доступ",settings:"Настройки"};
const content=document.getElementById("pageContent");
const breadcrumb=document.getElementById("breadcrumb");
const sidebar=document.getElementById("sidebar");
const overlay=document.getElementById("overlay");
let currentAccessLevel="none";
const pageMinimumAccess={dashboard:"none",discord:"adm",players:"media",shop:"media",requests:"co_adm",messages:"adm",tickets:"adm",logs:"adm",console:"adm",access:"adm",settings:"none"};
const accessRank={none:0,media:1,co_adm:2,adm:3,full:4};
function canOpenPage(page){
  return !!pageNames[page] && (page==="dashboard" || (isAuthenticated && (accessRank[currentAccessLevel]||0)>=(accessRank[pageMinimumAccess[page]||"none"])));
}
let isAuthenticated=false;
function applyAccessNavigation(){
  document.querySelectorAll(".nav-item[data-page]").forEach(button=>{
    const page=button.dataset.page;
    button.hidden=!canOpenPage(page);
  });
  document.querySelectorAll(".nav-group[data-nav-group]").forEach(group=>{
    const nav=group.querySelector(".nav-list");
    const visible=nav&&Array.from(nav.querySelectorAll(".nav-item")).some(item=>!item.hidden);
    group.hidden=!visible;
  });
}
applyAccessNavigation();
function showPage(page){
  if(!pageNames[page]) return;
  if(!canOpenPage(page)){page="dashboard";}
  document.getElementById("pageContent")?.classList.toggle("discord-fullscreen",page==="discord");
  document.body.classList.toggle("discord-mode",page==="discord");
  document.querySelectorAll(".nav-item").forEach(button=>button.classList.toggle("active",button.dataset.page===page));
  breadcrumb.textContent=pageNames[page];
  if(page!=="dashboard"){
    const descriptions={players:"Управление участниками, балансами, варнами и ролями.",requests:"Проверка заявок на вступление и получение баллов.",shop:"Настройка товаров, наборов, донатов и стоимости.",messages:"Отправка сообщений и Embed-панелей в Discord.",tickets:"Обращения игроков по ошибкам сайта и Discord-бота.",logs:"Просмотр latest.log и audit.log.",console:"Мониторинг и безопасное управление ботом.",settings:"Подключения, роли, каналы и параметры панели.",access:"Все участники сервера, их Discord-роли и фильтрация по ролям."};
    const existing=document.getElementById("comingPage");
    if(existing) existing.remove();
    const section=document.createElement("section");
    section.id="comingPage";section.className="panel coming-page";
    section.innerHTML='<div class="empty-state"><div class="empty-icon">✦</div><strong>'+pageNames[page]+'</strong><p>'+descriptions[page]+'</p><span class="pill pending">Будет реализовано на следующем этапе</span></div>';
    const old=document.getElementById("dashboardBody");
    if(old) old.hidden=true;
    if(page==="players"){
      section.innerHTML='<div class="panel-heading"><div><h2>Игроки</h2><p>Баланс и варны из базы бота</p></div><div class="panel-heading-actions"><button class="text-button" id="openSheetsStaff">Добавить состав в таблицу</button><button class="text-button" id="refreshPlayers">Обновить</button></div></div><div id="sheetsStaffManager" class="sheets-staff-manager" hidden><div class="sheets-staff-head"><div><strong>Добавление состава Медиа</strong><p>Участники с ролью Команда медиа, которых ещё нет в таблице</p></div><button class="text-button" id="refreshSheetsStaff">Обновить список</button></div><div id="sheetsStaffResult" class="empty-state">Нажми «Обновить список».</div></div><input id="playerSearch" class="panel-search" placeholder="⌕  Поиск по Discord ID"><div id="playersResult" class="empty-state">Загрузка игроков…</div>';
      loadPlayers(section);
    } else if(page==="requests"){
      section.innerHTML='<div class="panel-heading"><div><h2>Заявки</h2><p>Очередь заявок из базы бота · только просмотр</p></div><button class="text-button" id="refreshRequests">Обновить</button></div><div id="requestsResult" class="empty-state">Загрузка заявок…</div>';
      loadRequests(section);
    } else if(page==="shop"){
      section.innerHTML='<div class="panel-heading"><div><h2>Магазин</h2><p>Каталог, доступный в API · только просмотр</p></div><button class="text-button" id="refreshShop">Обновить</button></div><div id="shopResult" class="empty-state">Загрузка каталога…</div>';
      loadShop(section);
    } else if(page==="tickets"){
      section.innerHTML='<div class="panel-heading"><div><h2>Тикеты поддержки</h2><p>Обращения игроков из Discord · управление статусами</p></div><button class="text-button" id="refreshTickets">↻ Обновить</button></div><div class="ticket-toolbar"><div><strong id="ticketAcceptanceState">Проверяем приём…</strong><p>Закрытие приёма блокирует только создание новых обращений. Текущие тикеты продолжат работать.</p></div><button class="ticket-action-button" id="toggleTicketAcceptance" type="button" disabled>Загрузка…</button></div><div id="ticketsResult" class="tickets-list"><div class="empty-state">Загружаем тикеты…</div></div>';
      loadTickets(section);
    } else if(page==="messages"){
      section.innerHTML='<div class="panel-heading"><div><h2>Сообщения Discord</h2><p>Отправка обычных сообщений и Embed от имени GastWorld</p></div><button class="text-button" id="refreshMessageChannels">Обновить каналы</button></div><div id="messagesResult" class="messages-workspace"><div class="empty-state">Загружаем каналы Discord…</div></div>';
      loadMessages(section);
    } else if(page==="discord"){
      section.classList.add("bot-discord-preview");
      section.innerHTML='<div class="dc-app dc-live-app"><aside class="dc-guildbar"><div class="dc-guild-icon dc-home">GW</div><div class="dc-guild-divider"></div><div class="dc-live-guilds" id="dcGuildList"><button type="button" class="dc-guild-icon selected" id="dcHomeButton" title="Личные сообщения">＠</button></div><div class="dc-guild-spacer"></div><button type="button" class="dc-guild-icon dc-avatar dc-exit-live" id="dcExitLive" title="Вернуться в панель" aria-label="Вернуться в панель">↩</button></aside><aside class="dc-dm-sidebar"><div class="dc-dm-search" id="dcDmSearch"><input id="dcUserSearch" type="search" placeholder="Найти пользователя или ID"><button id="dcSearchButton" type="button">⌕</button></div><div id="dcSearchResults" class="dc-search-results" hidden></div><div class="dc-dm-section"><span id="dcSidebarTitle">ЛИЧНЫЕ СООБЩЕНИЯ</span><button id="dcRefreshDms" type="button" title="Обновить">↻</button></div><div id="dcDmList" class="dc-live-dm-list"><div class="dc-live-loading">Загружаем диалоги…</div></div><div id="dcChannelList" class="dc-live-dm-list" hidden><div class="dc-live-loading">Выбери сервер слева</div></div><button type="button" class="dc-account dc-account-trigger" id="dcBotAccountTrigger" title="Настройки профиля бота" aria-haspopup="dialog"><div class="dc-account-avatar" id="dcBotAccountAvatar">WG<span class="dc-account-status-dot dc-status-online"></span></div><span class="dc-account-name"><strong id="dcBotName">WhiteGrief</strong><small id="dcBotStatusText">Бот · подключение</small></span><span class="dc-account-open">⌄</span></button></aside><main class="dc-main"><header class="dc-topbar"><button id="dcToggleSidebar" class="dc-mobile-sidebar-toggle" type="button" title="Открыть навигацию" aria-label="Открыть навигацию" aria-expanded="false">☰</button><div class="dc-topbar-title"><span class="dc-hash">＠</span><strong id="dcChatTitle">Личные сообщения</strong><span class="dc-topic" id="dcChatSubtitle">Выбери диалог или найди пользователя</span></div><div class="dc-topbar-actions"><button id="dcAccessibilityButton" type="button" title="Специальные возможности">◉</button><button id="dcToggleMembers" type="button" title="Скрыть участников" aria-label="Показать или скрыть участников" aria-pressed="true">☷</button><button id="dcServerSettingsButton" type="button" title="Настройки сервера" hidden>⚙</button><button id="dcRefreshChat" type="button" title="Обновить переписку">↻</button></div></header><div class="dc-channel-layout dc-live-layout"><section class="dc-chat"><div id="dcChatMessages" class="dc-chat-scroll"><div class="dc-live-welcome"><div class="dc-live-welcome-icon">＠</div><h1>Личные сообщения</h1><p>Выбери существующий диалог слева или найди участника Discord по имени или ID. Сообщения отправляются от имени бота GastWorld.</p></div></div><div class="dc-composer-wrap"><div id="dcReplyPreview" class="dc-reply-preview" hidden></div><div id="dcMentionPicker" class="dc-mention-picker" role="listbox" aria-label="Подсказки упоминаний" hidden></div><div id="dcEmojiPicker" class="dc-emoji-picker" hidden></div><form id="dcComposerForm" class="dc-composer dc-live-composer"><button class="dc-composer-add" id="dcAttachButton" type="button" title="Прикрепить файл" aria-label="Прикрепить файл">＋</button><input id="dcFileInput" type="file" multiple hidden><textarea id="dcMessageInput" rows="1" maxlength="2000" placeholder="Написать сообщение…" disabled></textarea><button class="dc-emoji-button" id="dcEmojiButton" type="button" title="Выбрать эмодзи" aria-label="Выбрать эмодзи">☺</button><button id="dcSendButton" type="submit" disabled>➤</button></form><div id="dcFilePreview" class="dc-file-preview" hidden></div><div id="dcComposerHint" class="dc-composer-hint">Сначала выбери пользователя. Discord может ограничивать отправку DM.</div></div></section><aside class="dc-members dc-live-members" id="dcMembersPanel"><div id="dcDmProfilePanel" class="dc-dm-profile-panel" hidden></div><div class="dc-members-head"><strong>УЧАСТНИКИ</strong><span id="dcMemberCount">—</span></div><input id="dcMemberSearch" class="dc-member-search" type="search" placeholder="Поиск участника"><div id="dcMemberList" class="dc-member-list"><div class="dc-live-empty">Выбери сервер слева</div></div></aside></div><div class="dc-release-ribbon"><span>●</span> ОФИЦИАЛЬНОЕ BOT-ПОДКЛЮЧЕНИЕ <i>•</i> Не личный аккаунт</div></main></div>';
    } else if(page==="console"){
      section.innerHTML='<div class="panel-heading"><div><h2>Управление ботом</h2><p>Состояние Discord-подключения и безопасные действия управления.</p></div><button class="text-button" id="refreshConsole">↻ Обновить</button></div><div id="consoleWorkspace" class="console-workspace"><div class="empty-state">Подключаемся к боту…</div></div>';
      loadConsole(section);
    } else if(page==="access"){
      section.innerHTML='<div class="panel-heading"><div><h2>Доступ к серверу</h2><p>Все участники GastWorld и назначенные им Discord-роли</p></div><button class="text-button" id="refreshAccess">↻ Обновить</button></div><div id="accessWorkspace" class="access-workspace"><div class="empty-state">Загружаем участников сервера…</div></div>';
      loadAccess(section);
    } else if(page==="settings"){
       section.innerHTML='<div class="panel-heading"><div><h2>Настройки системы</h2><p>Подключения, роли доступа, Discord-каналы и интеграции GastWorld.</p></div><button class="text-button" id="refreshSettings">↻ Обновить</button></div><div id="settingsWorkspace" class="settings-workspace"><div class="empty-state">Проверяем конфигурацию…</div></div>';
       loadSettings(section);
    } else if(page==="logs"){
      section.innerHTML='<div class="panel-heading"><div><h2>Папка logs/</h2><p>Все файлы журналов бота. Выбери файл, чтобы открыть просмотрщик.</p></div><button class="text-button" id="refreshLogs">↻ Обновить</button></div><div class="logs-browser-toolbar"><div class="logs-folder-path"><span class="folder-icon">▰</span><span>GastWorld</span><span class="muted">/</span><strong>logs/</strong></div><input id="logsFileSearch" class="panel-search" placeholder="Найти файл…"></div><div class="logs-summary" id="logsSummary">Загрузка списка файлов…</div><div id="logsResult" class="logs-file-grid"><div class="empty-state">Загружаем файлы…</div></div>';
      loadLogs(section);

    }
    content.appendChild(section);
    if(page==="discord")loadBotDiscord();
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
let currentSessionUser=null;
function setConnectionStatus(connected,message){
  const line=document.querySelector(".connection-line span:last-child");
  const pulse=document.querySelector(".connection-line .pulse");
  if(line)line.textContent=message||(connected?"Бот подключён":"Нет соединения с API бота");
  if(pulse){pulse.classList.toggle("is-online",connected);pulse.classList.toggle("is-offline",!connected);}
}
async function refreshBotConnectionStatus(){
  try{
    const response=await fetch("/api/status",{credentials:"same-origin",cache:"no-store"});
    if(!response.ok)throw new Error("Status API unavailable");
    const data=await response.json();
    setConnectionStatus(data.bot_api===true,data.message||"Нет соединения с API бота");
  }catch(error){
    setConnectionStatus(false,"Нет соединения с API бота");
  }
}
function openOwnProfile(){
  if(!currentSessionUser)return;
  document.getElementById("wgProfileOverlay")?.remove();
  const user=currentSessionUser;
  const overlay=document.createElement("div");
  overlay.id="wgProfileOverlay";overlay.className="wg-profile-overlay";
  const dialog=document.createElement("section");
  dialog.className="wg-profile-dialog";dialog.setAttribute("role","dialog");dialog.setAttribute("aria-modal","true");dialog.setAttribute("aria-labelledby","wgProfileTitle");
  const head=document.createElement("div");head.className="wg-profile-head";
  const avatar=document.createElement("div");avatar.className="wg-profile-avatar";
  renderDiscordAvatar(avatar,user,128);
  const identity=document.createElement("div");identity.className="wg-profile-identity";
  const title=document.createElement("strong");title.id="wgProfileTitle";title.textContent=user.username||"Discord user";
  const handle=document.createElement("span");handle.textContent="@"+(user.discord_username||"unknown");
  identity.append(title,handle);
  const close=document.createElement("button");close.className="wg-profile-close";close.type="button";close.textContent="×";close.setAttribute("aria-label","Закрыть профиль");
  head.append(avatar,identity,close);
  const details=document.createElement("div");details.className="wg-profile-details";
  const addDetail=(label,value,copyable=false)=>{const row=document.createElement("div");row.className="wg-profile-detail";const l=document.createElement("span");l.textContent=label;const v=document.createElement("strong");v.textContent=value||"—";if(copyable){v.title="Нажми, чтобы скопировать";v.classList.add("copyable");v.addEventListener("click",()=>{if(navigator.clipboard?.writeText)navigator.clipboard.writeText(value).catch(()=>{});});}row.append(l,v);details.append(row)};
  addDetail("Discord ID",user.id,true);
  addDetail("Уровень доступа",accessLabels[user.access_level]||"Нет доступа");
  const roles=document.createElement("div");roles.className="wg-profile-roles";const label=document.createElement("span");label.textContent="Роли на сервере";roles.append(label);
  const chips=document.createElement("div");chips.className="wg-profile-role-list";
  (user.role_names||[]).forEach(name=>{const chip=document.createElement("span");chip.textContent=name;chips.append(chip)});
  if(!chips.childElementCount){const chip=document.createElement("span");chip.textContent="Роли не найдены";chips.append(chip)}
  roles.append(chips);
  const footer=document.createElement("div");footer.className="wg-profile-footer";const note=document.createElement("span");note.textContent="Профиль Discord · GastWorld";const done=document.createElement("button");done.type="button";done.className="wg-profile-done";done.textContent="Закрыть";footer.append(note,done);
  dialog.append(head,details,roles,footer);overlay.append(dialog);document.body.append(overlay);
  const closeModal=()=>overlay.remove();close.addEventListener("click",closeModal);done.addEventListener("click",closeModal);
  overlay.addEventListener("click",event=>{if(event.target===overlay)closeModal()});
  document.addEventListener("keydown",function onKey(event){if(event.key==="Escape"&&document.getElementById("wgProfileOverlay")){closeModal();document.removeEventListener("keydown",onKey)}});
  close.focus();
}
const accessLabels={none:"Нет доступа",media:"Media",co_adm:"Co.Adm — управление персоналом",adm:"Adm — управление ботом",full:"Full — полный доступ"};
function avatarLetter(name){return (name||"?").trim().slice(0,1).toUpperCase()}
function discordAvatarUrl(user,size=128){
  if(!user?.id||!user?.avatar)return "";
  const animated=String(user.avatar).startsWith("a_");
  return "https://cdn.discordapp.com/avatars/"+encodeURIComponent(user.id)+"/"+encodeURIComponent(user.avatar)+"."+(animated?"gif":"png")+"?size="+size;
}
function renderDiscordAvatar(element,user,size=128){
  if(!element)return;
  const url=discordAvatarUrl(user,size);
  element.replaceChildren();
  if(url){
    const image=document.createElement("img");
    image.src=url;image.alt="Discord avatar";image.loading="lazy";
    image.onerror=()=>{element.replaceChildren(document.createTextNode(avatarLetter(user?.username)))};
    element.append(image);
  }else element.textContent=avatarLetter(user?.username);
}
async function loadSession(){
  try{
    const response=await fetch("/api/me",{credentials:"same-origin"});
    const data=await response.json();
    if(!data.authenticated){
      currentSessionUser=null;
      authBadge.textContent="НЕ АВТОРИЗОВАН";
      sideUserName.textContent="Гость";
      sideUserAccess.textContent="Вход не выполнен";
      applyAccessNavigation();
      if(initialPage && pageNames[initialPage])showPage(initialPage);
      return;
    }
    const user=data.user;
    currentSessionUser=user;
    isAuthenticated=true;
    currentAccessLevel=user.access_level||"none";
    applyAccessNavigation();
    startSettingsLiveSync();
    if(initialPage && pageNames[initialPage])showPage(initialPage);
    const letter=avatarLetter(user.username);
    const avatarUrl=user.avatar
      ? "https://cdn.discordapp.com/avatars/"+encodeURIComponent(user.id)+"/"+encodeURIComponent(user.avatar)+".png?size=128"
      : "https://cdn.discordapp.com/embed/avatars/0.png";
    [sideAvatar,topAvatar].forEach(node=>{
      if(!node)return;
      node.replaceChildren();
      const image=document.createElement("img");
      image.src=avatarUrl;image.alt="Аватар Discord";
      image.onerror=()=>{node.textContent=letter;node.classList.add("avatar-fallback")};
      node.append(image);
      node.classList.remove("avatar-fallback");
      node.setAttribute("aria-label","Открыть мой профиль");
      node.title="Открыть мой профиль";
    });
    authBadge.textContent="DISCORD ПОДКЛЮЧЁН";
    authBadge.classList.add("authenticated");
    loginButton.hidden=true;
    logoutButton.hidden=false;
    sideUserName.textContent=user.username;
    sideUserAccess.textContent=accessLabels[user.access_level]||"Нет доступа";
    renderDiscordAvatar(topAvatar,user,96);
    renderDiscordAvatar(sideAvatar,user,96);
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
    if(wgSettingsLiveTimer){clearInterval(wgSettingsLiveTimer);wgSettingsLiveTimer=null;}
    await fetch("/auth/logout",{method:"POST",credentials:"same-origin"});
    window.location.href="/";
  });
}
if(topAvatar){
  topAvatar.setAttribute("role","button");topAvatar.setAttribute("tabindex","0");
  topAvatar.addEventListener("click",openOwnProfile);
  topAvatar.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();openOwnProfile()}});
}
const profileCard=document.querySelector(".user-card");
if(profileCard){
  profileCard.setAttribute("role","button");profileCard.setAttribute("tabindex","0");profileCard.setAttribute("aria-label","Открыть мой профиль");
  profileCard.addEventListener("click",openOwnProfile);
  profileCard.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();openOwnProfile()}});
}
refreshBotConnectionStatus();
setInterval(refreshBotConnectionStatus,30000);
loadSession();



let wgPreferences={theme:"system",accent:"purple",palette:["#8b5cf6","#ec4899","#38bdf8"],compact_mode:false};
let wgGlobalSettings={announcement_enabled:false,announcement_text:"",default_theme:"dark"};
let wgSettingsLiveTimer=null;

function applyGastWorldAppearance(){
  const root=document.documentElement;
  const theme=wgPreferences.theme==="system"?(wgGlobalSettings.default_theme||"dark"):wgPreferences.theme;
  const fallback=["#8b5cf6","#ec4899","#38bdf8"];
  const palette=Array.isArray(wgPreferences.palette)&&wgPreferences.palette.length===3?wgPreferences.palette:fallback;
  root.dataset.theme=theme;
  root.dataset.accent=wgPreferences.accent||"purple";
  palette.forEach((color,index)=>root.style.setProperty("--wg-palette-"+(index+1),color));
  root.style.setProperty("--wg-bg-tint",`color-mix(in srgb, ${palette[0]} 13%, #0d0e14)`);
  root.style.setProperty("--wg-side-tint",`color-mix(in srgb, ${palette[1]} 11%, #11121a)`);
  root.style.setProperty("--wg-panel-tint",`color-mix(in srgb, ${palette[2]} 10%, #151722)`);
  root.style.setProperty("--wg-surface-glow-1",`color-mix(in srgb, ${palette[0]} 24%, transparent)`);
  root.style.setProperty("--wg-surface-glow-2",`color-mix(in srgb, ${palette[1]} 20%, transparent)`);
  root.style.setProperty("--wg-surface-glow-3",`color-mix(in srgb, ${palette[2]} 19%, transparent)`);
  const luminance=color=>{
    const channels=[1,3,5].map(offset=>parseInt(String(color).slice(offset,offset+2),16)/255).map(value=>value<=.04045?value/12.92:Math.pow((value+.055)/1.055,2));
    return .2126*channels[0]+.7152*channels[1]+.0722*channels[2];
  };
  const average=palette.reduce((sum,color)=>sum+luminance(color),0)/3;
  root.style.setProperty("--wg-palette-ink",average>.48?"#111018":"#ffffff");
  palette.forEach((color,index)=>root.style.setProperty("--wg-palette-ink-"+(index+1),luminance(color)>.42?"#111018":"#ffffff"));
  document.body.classList.toggle("wg-compact",!!wgPreferences.compact_mode);
}
function renderGlobalAnnouncement(){
  const topbar=document.querySelector(".topbar");
  if(!topbar)return;
  let banner=document.getElementById("wgGlobalAnnouncement");
  if(!banner){
    banner=document.createElement("div");
    banner.id="wgGlobalAnnouncement";
    banner.className="wg-global-announcement";
    topbar.insertAdjacentElement("afterend",banner);
  }
  const visible=!!wgGlobalSettings.announcement_enabled&&!!(wgGlobalSettings.announcement_text||"").trim();
  banner.hidden=!visible;
  banner.textContent=visible?wgGlobalSettings.announcement_text:"";
}
async function refreshGastWorldLiveSettings(){
  try{
    const response=await fetch("/api/settings/live",{credentials:"same-origin",cache:"no-store"});
    if(!response.ok)return;
    const data=await response.json();
    const paletteControlFocused=[1,2,3].some(index=>document.activeElement===document.getElementById("wgPaletteColor"+index));
    const localPalette=wgPreferences.palette;
    wgGlobalSettings=data.global_settings||wgGlobalSettings;
    wgPreferences=data.preferences||wgPreferences;
    if(paletteControlFocused&&localPalette)wgPreferences.palette=localPalette;
    applyGastWorldAppearance();
    renderGlobalAnnouncement();
    const liveTheme=document.getElementById("wgPersonalTheme");
    const livePalette=[1,2,3].map(index=>document.getElementById("wgPaletteColor"+index));
    const liveCompact=document.getElementById("wgPersonalCompact");
    const liveAnnouncement=document.getElementById("wgAdminAnnouncementEnabled");
    const liveMessage=document.getElementById("wgAdminAnnouncementText");
    const liveDefaultTheme=document.getElementById("wgAdminDefaultTheme");
    if(liveTheme&&document.activeElement!==liveTheme)liveTheme.value=wgPreferences.theme||"system";
    livePalette.forEach((control,index)=>{if(control&&document.activeElement!==control)control.value=(wgPreferences.palette||["#8b5cf6","#ec4899","#38bdf8"])[index];});
    if(liveCompact&&document.activeElement!==liveCompact)liveCompact.checked=!!wgPreferences.compact_mode;
    if(liveAnnouncement&&document.activeElement!==liveAnnouncement)liveAnnouncement.checked=!!wgGlobalSettings.announcement_enabled;
    if(liveMessage&&document.activeElement!==liveMessage)liveMessage.value=wgGlobalSettings.announcement_text||"";
    if(liveDefaultTheme&&document.activeElement!==liveDefaultTheme)liveDefaultTheme.value=wgGlobalSettings.default_theme||"dark";
  }catch(error){}
}
function startSettingsLiveSync(){
  refreshGastWorldLiveSettings();
  if(wgSettingsLiveTimer)clearInterval(wgSettingsLiveTimer);
  wgSettingsLiveTimer=setInterval(refreshGastWorldLiveSettings,4000);
}

async function loadSettings(section){
  const root=section.querySelector("#settingsWorkspace"),refresh=section.querySelector("#refreshSettings");
  if(!root)return;
  const makeStatus=(label,ok,detail)=>{
    const card=document.createElement("article");card.className="settings-status-card";
    const head=document.createElement("div");head.className="settings-status-head";
    const name=document.createElement("strong");name.textContent=label;
    const badge=document.createElement("span");badge.className="settings-status-pill "+(ok?"is-ready":"is-missing");badge.textContent=ok?"Готово":"Проверить";
    const desc=document.createElement("small");desc.textContent=detail;
    head.append(name,badge);card.append(head,desc);return card;
  };
  const makePanel=(title,description)=>{
    const panel=document.createElement("section");panel.className="settings-panel";
    const heading=document.createElement("div");heading.className="settings-panel-heading";
    const h=document.createElement("h3");h.textContent=title;
    const d=document.createElement("span");d.className="settings-muted";d.textContent=description||"";
    heading.append(h,d);panel.append(heading);return panel;
  };
  const makeField=(label,control,hint)=>{
    const wrap=document.createElement("label");wrap.className="settings-field";
    const name=document.createElement("span");name.className="settings-field-label";name.textContent=label;
    wrap.append(name,control);
    if(hint){const small=document.createElement("small");small.textContent=hint;wrap.append(small);}
    return wrap;
  };
  const requestJSON=async(url,body)=>{
    const response=await fetch(url,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||"Не удалось сохранить настройки.");
    return data;
  };
  const render=data=>{
    root.replaceChildren();
    const hero=document.createElement("div");hero.className="settings-hero";
    const heroIcon=document.createElement("div");heroIcon.className="settings-hero-icon";heroIcon.textContent="✦";
    const heroCopy=document.createElement("div");heroCopy.className="settings-hero-copy";
    const eyebrow=document.createElement("span");eyebrow.textContent="GASTWORLD CONTROL CENTER";
    const heroTitle=document.createElement("strong");heroTitle.textContent="Центр настроек";
    const heroText=document.createElement("p");heroText.textContent="Настрой внешний вид панели, общие параметры и подключение Discord.";heroCopy.append(eyebrow,heroTitle,heroText);hero.append(heroIcon,heroCopy);root.append(hero);
    wgPreferences=data.preferences||wgPreferences;
    wgGlobalSettings=data.global_settings||wgGlobalSettings;
    applyGastWorldAppearance();renderGlobalAnnouncement();

    const personal=makePanel("Мои настройки","Сохраняются для твоего Discord-аккаунта");
    const personalGrid=document.createElement("div");personalGrid.className="settings-edit-grid";
    const theme=document.createElement("select");theme.id="wgPersonalTheme";theme.className="settings-select";
    [["system","По умолчанию сервера"],["dark","Тёмная"],["light","Светлая"]].forEach(([value,label])=>{const o=document.createElement("option");o.value=value;o.textContent=label;theme.append(o);});
    theme.value=wgPreferences.theme||"system";
    const paletteWrap=document.createElement("div");paletteWrap.className="wg-palette-editor";
    const paletteInputs=[1,2,3].map((index)=>{
      const item=document.createElement("div");item.className="wg-palette-swatch";
      const color=document.createElement("input");color.type="color";color.id="wgPaletteColor"+index;color.value=(wgPreferences.palette||["#8b5cf6","#ec4899","#38bdf8"])[index-1];color.setAttribute("aria-label","Цвет палитры "+index);
      const caption=document.createElement("span");caption.textContent="Цвет "+index;
      item.append(color,caption);paletteWrap.append(item);return color;
    });
    const palettePreview=document.createElement("div");palettePreview.className="wg-palette-preview";
    const previewLabel=document.createElement("span");previewLabel.textContent="ТВОЙ ГРАДИЕНТ";
    palettePreview.append(previewLabel);paletteWrap.append(palettePreview);
    const compact=document.createElement("input");compact.id="wgPersonalCompact";compact.type="checkbox";compact.checked=!!wgPreferences.compact_mode;
    const compactLabel=document.createElement("label");compactLabel.className="settings-switch-label";compactLabel.append(compact,document.createTextNode("Компактный интерфейс"));
    personalGrid.append(makeField("Тема оформления",theme,"Можно использовать тему по умолчанию, заданную администрацией."),makeField("Палитра из трёх цветов",paletteWrap,"Выбери три любимых цвета — градиент будет плавно переливаться по всей панели."),makeField("Плотность интерфейса",compactLabel,"Уменьшает отступы между элементами."));
    personal.append(personalGrid);
    const personalStatus=document.createElement("small");personalStatus.className="settings-save-status";personalStatus.textContent="Изменения сохраняются автоматически.";
    personal.append(personalStatus);root.append(personal);

    let savePersonalTimer=null;
    const savePersonal=async()=>{
      if(savePersonalTimer)clearTimeout(savePersonalTimer);
      personalStatus.textContent="Сохраняем…";
      wgPreferences={theme:theme.value,accent:wgPreferences.accent||"purple",palette:paletteInputs.map(input=>input.value),compact_mode:compact.checked};
      applyGastWorldAppearance();
      try{
        await requestJSON("/api/settings/preferences",wgPreferences);
        personalStatus.textContent="Сохранено · применяется сразу";
      }catch(error){personalStatus.textContent=error.message;}
    };
    const updatePalettePreview=()=>{
      palettePreview.style.setProperty("--preview-a",paletteInputs[0].value);
      palettePreview.style.setProperty("--preview-b",paletteInputs[1].value);
      palettePreview.style.setProperty("--preview-c",paletteInputs[2].value);
    };
    paletteInputs.forEach(control=>control.addEventListener("input",()=>{updatePalettePreview();wgPreferences.palette=paletteInputs.map(input=>input.value);applyGastWorldAppearance();}));
    paletteInputs.forEach(control=>control.addEventListener("change",savePersonal));
    updatePalettePreview();
    [theme,compact].forEach(control=>control.addEventListener("change",savePersonal));

    if(data.is_admin){
      const admin=makePanel("Общие настройки панели","Изменения видны всем пользователям");
      const adminGrid=document.createElement("div");adminGrid.className="settings-edit-grid";
      const announce=document.createElement("input");announce.id="wgAdminAnnouncementEnabled";announce.type="checkbox";announce.checked=!!wgGlobalSettings.announcement_enabled;
      const announceLabel=document.createElement("label");announceLabel.className="settings-switch-label";announceLabel.append(announce,document.createTextNode("Показывать общее уведомление"));
      const message=document.createElement("textarea");message.id="wgAdminAnnouncementText";message.className="settings-textarea";message.maxLength=350;message.rows=3;message.placeholder="Напиши объявление для всех пользователей…";message.value=wgGlobalSettings.announcement_text||"";
      const defaultTheme=document.createElement("select");defaultTheme.id="wgAdminDefaultTheme";defaultTheme.className="settings-select";
      [["dark","Тёмная"],["light","Светлая"]].forEach(([value,label])=>{const o=document.createElement("option");o.value=value;o.textContent=label;defaultTheme.append(o);});
      defaultTheme.value=wgGlobalSettings.default_theme||"dark";
      adminGrid.append(makeField("Публичное уведомление",announceLabel,"Показывается вверху панели всем вошедшим участникам."),makeField("Текст уведомления",message,"До 350 символов. Изменение появится у пользователей автоматически."),makeField("Тема по умолчанию",defaultTheme,"Применяется к тем, кто выбрал «По умолчанию сервера»."));
      const adminActions=document.createElement("div");adminActions.className="settings-admin-actions";
      const saveAdmin=document.createElement("button");saveAdmin.type="button";saveAdmin.className="console-action-button";saveAdmin.textContent="Сохранить общие настройки";
      const adminStatus=document.createElement("small");adminStatus.className="settings-save-status";adminStatus.textContent="Только Adm и Full могут менять эти параметры.";
      saveAdmin.addEventListener("click",async()=>{
        saveAdmin.disabled=true;adminStatus.textContent="Сохраняем…";
        try{
          const saved=await requestJSON("/api/settings/admin",{announcement_enabled:announce.checked,announcement_text:message.value,default_theme:defaultTheme.value});
          wgGlobalSettings=saved.global_settings||wgGlobalSettings;
          applyGastWorldAppearance();renderGlobalAnnouncement();
          adminStatus.textContent="Сохранено · обновление у всех пользователей до 4 секунд";
        }catch(error){adminStatus.textContent=error.message;}
        finally{saveAdmin.disabled=false;}
      });
      adminActions.append(saveAdmin,adminStatus);admin.append(adminGrid,adminActions);root.append(admin);

      const intro=document.createElement("div");intro.className="settings-intro";
      const introTitle=document.createElement("strong");introTitle.textContent="Техническая конфигурация";
      const introText=document.createElement("p");introText.textContent="Статусы подключения доступны для просмотра. Секреты и ключи остаются в переменных окружения хостинга и не редактируются через браузер.";
      intro.append(introTitle,introText);root.append(intro);
      const summary=document.createElement("div");summary.className="settings-status-grid";
      const c=data.configuration||{};
      [
        ["Discord OAuth",c.oauth,"Вход через Discord · Client ID и Secret"],
        ["Discord Bot API",c.bot,"Токен бота задан на Dashboard-хостинге"],
        ["Секрет сессии",c.session_secret,"Защита авторизационных cookie"],
        ["OAuth Redirect",c.redirect_uri,"Адрес возврата после входа"],
        ["Синхронизация ролей",c.bot_sync,"Внутренний ключ синхронизации ролей"],
        ["Связь с ботом",c.bot_api,"Адрес первого хостинга и внутренний API"],
        ["TikTok Login Kit",c.tiktok_oauth,"Client Key, Secret и Redirect URI"],
        ["Шифрование TikTok",c.tiktok_encryption,"Ключ шифрования токенов задан"]
      ].forEach(item=>summary.append(makeStatus(item[0],!!item[1],item[2])));
      root.append(summary);

      const guild=makePanel("Discord-сервер","GastWorld");
      const info=document.createElement("div");info.className="settings-info-grid";
      [["Название",data.guild_name||"Недоступно"],["Guild ID",data.guild_id||"—"],["Подключение",data.discord_connected?"Discord API доступен":"Нет доступа к Discord API"]].forEach(pair=>{
        const item=document.createElement("div");item.className="settings-info-item";
        const small=document.createElement("small");small.textContent=pair[0];
        const strong=document.createElement("strong");strong.textContent=pair[1];
        item.append(small,strong);info.append(item);
      });
      guild.append(info);root.append(guild);

      const rolePanel=makePanel("Роли доступа к сайту","Назначай уровень доступа каждой роли Discord");
      const roleList=document.createElement("div");roleList.className="settings-role-list settings-role-editor";
      const roleControls=[];
      const actorIsFull=(data.current_access_level==="full");
      (data.roles||[]).forEach(role=>{
        const row=document.createElement("div");row.className="settings-role-row settings-role-edit-row";
        const copy=document.createElement("div");copy.className="settings-role-copy";
        const name=document.createElement("strong");name.textContent=role.name;
        const id=document.createElement("small");id.textContent="ID: "+role.id;
        copy.append(name,id);
        const select=document.createElement("select");select.className="settings-select settings-role-select";
        const options=[["none","Без доступа"],["media","Media"],["co_adm","Co.Adm"],["adm","Adm"]];
        if(actorIsFull)options.push(["full","Full"]);
        else if(role.access_level==="full")options.push(["full","Full · защищено"]);
        options.forEach(([value,label])=>{const option=document.createElement("option");option.value=value;option.textContent=label;if(value==="full"&&!actorIsFull)option.disabled=true;select.append(option);});
        select.value=role.access_level||"none";
        if(!actorIsFull&&role.access_level==="full")select.disabled=true;
        roleControls.push({id:role.id,select});
        row.append(copy,select);roleList.append(row);
      });
      if(!roleList.children.length){const empty=document.createElement("div");empty.className="settings-empty";empty.textContent="Список ролей Discord недоступен.";roleList.append(empty);}
      const roleActions=document.createElement("div");roleActions.className="settings-admin-actions";
      const saveRoles=document.createElement("button");saveRoles.type="button";saveRoles.className="console-action-button";saveRoles.textContent="Сохранить доступ ролей";
      const roleStatus=document.createElement("small");roleStatus.className="settings-save-status";roleStatus.textContent=actorIsFull?"Full может назначать все уровни. Adm может управлять ролями, кроме Full.":"Adm может менять уровни до Adm; назначать Full может только Full.";
      saveRoles.addEventListener("click",async()=>{
        saveRoles.disabled=true;roleStatus.textContent="Сохраняем права…";
        try{
          await requestJSON("/api/settings/access-roles",{roles:roleControls.map(item=>({id:item.id,access_level:item.select.value}))});
          roleStatus.textContent="Сохранено. Новые права применяются при следующем запросе к панели.";
          await load();
        }catch(error){roleStatus.textContent=error.message;}
        finally{saveRoles.disabled=false;}
      });
      roleActions.append(saveRoles,roleStatus);rolePanel.append(roleList,roleActions);root.append(rolePanel);

      const channelPanel=makePanel("Каналы Discord",(data.channels||[]).length+" текстовых каналов");
      const channelList=document.createElement("div");channelList.className="settings-channel-list";
      (data.channels||[]).forEach(channel=>{
        const row=document.createElement("div");row.className="settings-channel-row";
        const hash=document.createElement("span");hash.className="settings-channel-hash";hash.textContent="#";
        const name=document.createElement("strong");name.textContent=channel.name;
        const id=document.createElement("small");id.textContent=channel.id;
        row.append(hash,name,id);channelList.append(row);
      });
      if(!channelList.children.length){const empty=document.createElement("div");empty.className="settings-empty";empty.textContent=data.channels_error||"Список каналов недоступен.";channelList.append(empty);}
      channelPanel.append(channelList);root.append(channelPanel);
    }else{
      const note=document.createElement("div");note.className="settings-security-note";
      note.textContent="Административные настройки и техническая конфигурация доступны только пользователям с уровнем Adm или Full.";
      root.append(note);
    }
  };
  const load=async()=>{
    if(refresh){refresh.disabled=true;refresh.textContent="Загрузка…";}
    root.innerHTML='<div class="empty-state">Получаем настройки…</div>';
    try{
      const response=await fetch("/api/settings",{credentials:"same-origin",cache:"no-store"});
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||"Не удалось загрузить настройки.");
      render(data);
    }catch(error){
      root.replaceChildren();const message=document.createElement("div");message.className="console-error";message.textContent=error.message||"Ошибка загрузки настроек.";root.append(message);
    }finally{if(refresh){refresh.disabled=false;refresh.textContent="↻ Обновить";}}
  };
  if(refresh)refresh.addEventListener("click",load);
  await load();
}


async function loadAccess(section){
  const root=section.querySelector("#accessWorkspace");
  const refresh=section.querySelector("#refreshAccess");
  if(!root)return;
  const load=async()=>{
    if(refresh){refresh.disabled=true;refresh.textContent="Загрузка…";}
    root.innerHTML='<div class="empty-state">Получаем полный список участников Discord…</div>';
    try{
      const response=await fetch("/api/access/members",{credentials:"same-origin",cache:"no-store"});
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||"Не удалось загрузить участников.");
      const members=Array.isArray(data.members)?data.members:[];
      const roles=Array.isArray(data.roles)?data.roles:[];
      root.replaceChildren();

      const toolbar=document.createElement("div");toolbar.className="access-toolbar";
      const searchWrap=document.createElement("label");searchWrap.className="access-search-wrap";
      const searchIcon=document.createElement("span");searchIcon.textContent="⌕";
      const search=document.createElement("input");search.className="panel-search access-search";search.placeholder="Поиск по нику, имени или Discord ID…";search.type="search";
      searchWrap.append(searchIcon,search);
      const filterWrap=document.createElement("label");filterWrap.className="access-filter-wrap";
      const filterLabel=document.createElement("span");filterLabel.textContent="Фильтр по роли";
      const filter=document.createElement("select");filter.className="settings-select access-role-filter";
      const allOption=document.createElement("option");allOption.value="";allOption.textContent="Все участники";filter.append(allOption);
      roles.forEach(role=>{
        const option=document.createElement("option");option.value=role.id;
        option.textContent=role.id===data.guild_id?"@everyone · Все участники":role.name;
        filter.append(option);
      });
      filterWrap.append(filterLabel,filter);
      toolbar.append(searchWrap,filterWrap);

      const summary=document.createElement("div");summary.className="access-summary";
      const memberCount=document.createElement("div");memberCount.className="access-summary-card";
      const memberValue=document.createElement("strong");memberValue.textContent=String(members.length);
      const memberLabel=document.createElement("span");memberLabel.textContent="Участников сервера";
      memberCount.append(memberValue,memberLabel);
      const roleCount=document.createElement("div");roleCount.className="access-summary-card";
      const roleValue=document.createElement("strong");roleValue.textContent=String(roles.length);
      const roleLabel=document.createElement("span");roleLabel.textContent="Ролей на сервере";
      roleCount.append(roleValue,roleLabel);
      summary.append(memberCount,roleCount);

      const resultHead=document.createElement("div");resultHead.className="access-result-head";
      const resultTitle=document.createElement("strong");resultTitle.textContent="Участники";
      const resultCount=document.createElement("span");resultCount.className="access-result-count";
      resultHead.append(resultTitle,resultCount);
      const list=document.createElement("div");list.className="access-member-list";
      const openRoleModal=member=>{
        const available=(data.assignable_roles||[]).filter(role=>!member.role_ids.includes(role.id));
        const backdrop=document.createElement("div");backdrop.className="access-role-modal-backdrop";
        const modal=document.createElement("section");modal.className="access-role-modal";modal.setAttribute("role","dialog");modal.setAttribute("aria-modal","true");
        const close=()=>backdrop.remove();
        const closeButton=document.createElement("button");closeButton.type="button";closeButton.className="access-role-modal-close";closeButton.textContent="×";closeButton.setAttribute("aria-label","Закрыть");closeButton.addEventListener("click",close);
        const emblem=document.createElement("div");emblem.className="access-role-modal-emblem";emblem.textContent="✦";
        const eyebrow=document.createElement("div");eyebrow.className="access-role-modal-eyebrow";eyebrow.textContent="GASTWORLD · УПРАВЛЕНИЕ РОЛЯМИ";
        const title=document.createElement("h2");title.textContent="Выдать роль";
        const description=document.createElement("p");description.className="access-role-modal-description";description.textContent="Выбери роль Discord для участника "+(member.display_name||member.username)+".";
        const field=document.createElement("label");field.className="access-role-modal-field";
        const fieldTitle=document.createElement("span");fieldTitle.textContent="РОЛЬ СЕРВЕРА";
        const select=document.createElement("select");select.className="access-role-modal-select";
        const placeholder=document.createElement("option");placeholder.value="";placeholder.textContent=available.length?"Выбери роль…":"Нет доступных для выдачи ролей";select.append(placeholder);
        available.forEach(role=>{const option=document.createElement("option");option.value=role.id;option.textContent=role.name;select.append(option);});
        field.append(fieldTitle,select);
        const preview=document.createElement("div");preview.className="access-role-modal-preview";
        const previewDot=document.createElement("i");const previewText=document.createElement("span");previewText.textContent="После выдачи роль появится в карточке участника.";preview.append(previewDot,previewText);
        select.addEventListener("change",()=>{
          const selected=available.find(role=>role.id===select.value);
          previewText.textContent=selected?"Будет выдана роль «"+selected.name+"».":"После выдачи роль появится в карточке участника.";
          previewDot.style.background=selected&&selected.color?"#"+selected.color.toString(16).padStart(6,"0"):"";
        });
        const notice=document.createElement("div");notice.className="access-role-modal-notice";notice.textContent="Выдача выполняется ботом GastWorld. Discord проверяет права и иерархию ролей.";
        const footer=document.createElement("div");footer.className="access-role-modal-footer";
        const cancel=document.createElement("button");cancel.type="button";cancel.className="access-role-modal-cancel";cancel.textContent="Отмена";cancel.addEventListener("click",close);
        const confirm=document.createElement("button");confirm.type="button";confirm.className="access-role-modal-confirm";confirm.textContent="✦ Выдать роль";confirm.disabled=!available.length;
        confirm.addEventListener("click",async()=>{
          if(!select.value)return;
          confirm.disabled=true;cancel.disabled=true;select.disabled=true;confirm.textContent="Выдаём…";
          try{
            const response=await fetch("/api/access/members/"+encodeURIComponent(member.id)+"/roles",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({role_id:select.value})});
            const result=await response.json();
            if(!response.ok)throw new Error(result.detail||"Не удалось выдать роль.");
            if(!result.already_had_role){
              member.role_ids.push(result.role.id);
              member.roles.push(result.role);
            }
            close();
            if(typeof showToast==="function")showToast(result.message||"Роль выдана.");
            render();
          }catch(error){
            notice.textContent=error.message||"Не удалось выдать роль.";
            notice.classList.add("is-error");
            confirm.disabled=false;cancel.disabled=false;select.disabled=false;confirm.textContent="Повторить";
          }
        });
        footer.append(cancel,confirm);
        modal.append(closeButton,emblem,eyebrow,title,description,field,preview,notice,footer);
        backdrop.append(modal);backdrop.addEventListener("click",event=>{if(event.target===backdrop)close();});
        document.body.append(backdrop);select.focus();
      };
      const render=()=>{
        const term=search.value.trim().toLocaleLowerCase();
        const roleId=filter.value;
        const filtered=members.filter(member=>{
          const matchesRole=!roleId||roleId===data.guild_id||member.role_ids.includes(roleId);
          const haystack=[member.display_name,member.username,member.id].join(" ").toLocaleLowerCase();
          return matchesRole&&(!term||haystack.includes(term));
        });
        resultCount.textContent=filtered.length+" из "+members.length;
        list.replaceChildren();
        if(!filtered.length){
          const empty=document.createElement("div");empty.className="settings-empty";empty.textContent="Никого не нашли. Измени фильтр или поисковый запрос.";list.append(empty);return;
        }
        const fragment=document.createDocumentFragment();
        filtered.forEach(member=>{
          const card=document.createElement("article");card.className="access-member-card";
          const identity=document.createElement("div");identity.className="access-member-identity";
          const avatar=document.createElement("div");avatar.className="access-member-avatar";
          if(member.avatar){const img=document.createElement("img");img.src=member.avatar;img.alt="";img.loading="lazy";img.onerror=()=>{img.remove();avatar.textContent=(member.display_name||"?").slice(0,1).toUpperCase();};avatar.append(img);}
          else avatar.textContent=(member.display_name||"?").slice(0,1).toUpperCase();
          const names=document.createElement("div");names.className="access-member-names";
          const display=document.createElement("strong");display.textContent=member.display_name||member.username;
          const username=document.createElement("span");username.textContent="@"+member.username+" · "+member.id;
          names.append(display,username);
          if(member.bot){const botTag=document.createElement("em");botTag.textContent="BOT";botTag.className="access-bot-tag";names.append(botTag);}
          identity.append(avatar,names);
          const roleBadges=document.createElement("div");roleBadges.className="access-member-roles";
          (member.roles||[]).sort((x,y)=>{
            const xp=roles.find(r=>r.id===x.id)?.position||0,yp=roles.find(r=>r.id===y.id)?.position||0;return yp-xp;
          }).forEach(role=>{
            const badge=document.createElement("span");badge.className="access-role-chip";badge.textContent=role.name;
            if(role.color){badge.style.setProperty("--role-color","#"+role.color.toString(16).padStart(6,"0"));}
            roleBadges.append(badge);
          });
          if(!roleBadges.children.length){const none=document.createElement("span");none.className="access-no-roles";none.textContent="Нет дополнительных ролей";roleBadges.append(none);}
          const roleAction=document.createElement("div");roleAction.className="access-member-actions";
          const assignButton=document.createElement("button");assignButton.type="button";assignButton.className="access-assign-role-button";assignButton.textContent="＋ Выдать роль";
          assignButton.disabled=!(data.assignable_roles||[]).some(role=>!member.role_ids.includes(role.id));
          assignButton.title=assignButton.disabled?"Нет доступных ролей для выдачи":"Выдать Discord-роль участнику";
          assignButton.addEventListener("click",()=>openRoleModal(member));
          roleAction.append(assignButton);
          card.append(identity,roleBadges,roleAction);fragment.append(card);
        });
        list.append(fragment);
      };
      root.append(toolbar,summary,resultHead,list);
      search.addEventListener("input",render);
      filter.addEventListener("change",render);
      render();
    }catch(error){
      root.replaceChildren();const box=document.createElement("div");box.className="console-error";box.textContent=error.message||"Ошибка загрузки списка участников.";root.append(box);
    }finally{if(refresh){refresh.disabled=false;refresh.textContent="↻ Обновить";}}
  };
  refresh?.addEventListener("click",load);
  await load();
}


async function loadConsole(section){
  const root=section.querySelector("#consoleWorkspace"),refresh=section.querySelector("#refreshConsole");
  if(!root)return;
  let pollBusy=false,outputPollBusy=false,commandBusy=false,history=[],historyIndex=0,lastConsoleLineId=0;
  const actions=[["sync_commands","Синхронизировать slash-команды","Обновит команды GastWorld на Discord-сервере."],["sync_roles","Синхронизировать роли доступа","Проверит и обновит роли доступа Control Panel."],["refresh_presence","Обновить активность бота","Повторно установит статус «/shop | модерация»."]];
  const append=(output,text,tone="")=>{const line=document.createElement("div");if(tone)line.className="console-output-"+tone;line.textContent=text;output.append(line);while(output.children.length>800)output.firstElementChild.remove();output.scrollTop=output.scrollHeight;};
  const render=data=>{
    const status=data.status||{},workspace=document.createElement("div");workspace.className="console-workspace-inner";
    const cards=document.createElement("div");cards.className="console-status-grid";
    [["СОСТОЯНИЕ",status.online?"В сети":"Не в сети",status.online?"online":"offline"],["DISCORD",status.bot_name||"GastWorld",""],["СЕРВЕР",status.guild_name||"—",""],["ЗАДЕРЖКА",status.latency_ms==null?"—":status.latency_ms+" мс",""]].forEach(([label,value,tone])=>{const card=document.createElement("article");card.className="console-status-card";const small=document.createElement("small");small.textContent=label;const strong=document.createElement("strong");strong.textContent=value;if(tone)strong.classList.add(tone);card.append(small,strong);cards.append(card);});
    const controls=document.createElement("div");controls.className="console-controls";const heading=document.createElement("div");heading.className="console-section-heading";const h=document.createElement("h3");h.textContent="Быстрые действия";const note=document.createElement("span");note.textContent=currentAccessLevel==="full"?"Полный доступ: команды, действия и перезапуск":"Adm: просмотр, быстрые действия и перезапуск · ввод команд доступен только Full";heading.append(h,note);controls.append(heading);
    actions.forEach(([key,label,description])=>{const card=document.createElement("div");card.className="console-action-card";const copy=document.createElement("div");copy.className="console-action-copy";const title=document.createElement("strong");title.textContent=label;const desc=document.createElement("small");desc.textContent=description;copy.append(title,desc);const button=document.createElement("button");button.type="button";button.className="console-action-button";button.textContent="Выполнить";button.disabled=!status.online||!["adm","full"].includes(currentAccessLevel);button.title=!["adm","full"].includes(currentAccessLevel)?"Требуется уровень Adm":(!status.online?"Бот не подключён":"");button.addEventListener("click",async()=>{button.disabled=true;button.textContent="Выполняется…";try{const response=await fetch("/api/console/action",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:key})});const result=await response.json();if(!response.ok)throw new Error(result.detail||"Действие не выполнено.");showToast(result.message||"Действие выполнено.");await poll();}catch(error){showToast(error.message||"Ошибка управления.");}finally{button.textContent="Выполнить";button.disabled=!status.online||!["adm","full"].includes(currentAccessLevel);}});card.append(copy,button);controls.append(card);});
    const terminal=document.createElement("section");terminal.className="console-terminal";const top=document.createElement("div");top.className="console-terminal-top";const terminalTitle=document.createElement("div");terminalTitle.className="console-terminal-title";const led=document.createElement("i");led.className=status.online?"online":"";const termName=document.createElement("strong");termName.textContent="Терминал GastWorld · host";terminalTitle.append(led,termName);const tools=document.createElement("div");tools.className="console-terminal-tools";
    const clear=document.createElement("button");clear.type="button";clear.className="console-tool-button";clear.textContent="Очистить";clear.addEventListener("click",()=>{output.replaceChildren();append(output,"Терминал очищен. Напиши help для списка команд.","muted");});if(currentAccessLevel==="full")tools.append(clear);top.append(terminalTitle,tools);
    const output=document.createElement("div");output.className="console-terminal-output";append(output,"GastWorld Host Terminal","system");append(output,"Подключение к процессу бота установлено.","muted");append(output,currentAccessLevel==="full"?"Full: команды shell выполняются на первом хостинге. Любые символы передаются без фильтрации.":"Режим просмотра: вывод хостинга доступен, ввод команд отключён для Adm.","muted");
    const form=document.createElement("form");form.className="console-command-form";const prompt=document.createElement("label");prompt.className="console-command-prompt";prompt.textContent="container~";const input=document.createElement("input");input.className="console-command-input";input.type="text";input.autocomplete="off";input.spellcheck=false;input.placeholder="Введите команду или символ…";input.disabled=currentAccessLevel!=="full";const run=document.createElement("button");run.type="submit";run.className="console-action-button";run.textContent="Выполнить";run.disabled=currentAccessLevel!=="full";form.append(prompt,input,run);
    const restartRow=document.createElement("div");restartRow.className="console-restart-row";const restartHint=document.createElement("small");restartHint.textContent="Перезапуск заменит текущий процесс бота и временно отключит Discord.";const restart=document.createElement("button");restart.type="button";restart.className="console-restart-button";restart.textContent="↻ Перезапустить бота";restart.disabled=!["adm","full"].includes(currentAccessLevel);restart.addEventListener("click",()=>{
      const previous=document.getElementById("consoleRestartModal");if(previous)previous.remove();
      const modal=document.createElement("div");modal.id="consoleRestartModal";modal.className="action-modal";
      const dialog=document.createElement("div");dialog.className="action-modal-card";dialog.setAttribute("role","dialog");dialog.setAttribute("aria-modal","true");dialog.setAttribute("aria-labelledby","consoleRestartTitle");
      const close=document.createElement("button");close.type="button";close.className="action-modal-close";close.textContent="×";close.setAttribute("aria-label","Закрыть");
      const icon=document.createElement("div");icon.className="action-modal-icon";icon.textContent="↻";
      const eyebrow=document.createElement("div");eyebrow.className="action-modal-eyebrow";eyebrow.textContent="GASTWORLD CONTROL PANEL";
      const title=document.createElement("h2");title.id="consoleRestartTitle";title.textContent="Перезапустить бота?";
      const description=document.createElement("p");description.className="action-modal-description";description.textContent="Discord-бот временно отключится и запустится заново. Панель может на несколько секунд потерять соединение.";
      const note=document.createElement("div");note.className="action-modal-note";note.textContent="Перезапуск затронет весь процесс бота и встроенного API. Продолжить?";
      const footer=document.createElement("div");footer.className="action-modal-footer";
      const cancel=document.createElement("button");cancel.type="button";cancel.className="action-modal-cancel";cancel.textContent="Отмена";
      const confirm=document.createElement("button");confirm.type="button";confirm.className="action-modal-confirm";confirm.textContent="Да, перезапустить";
      const dismiss=()=>modal.remove();close.addEventListener("click",dismiss);cancel.addEventListener("click",dismiss);modal.addEventListener("click",event=>{if(event.target===modal)dismiss();});
      const originalProcessStartedAt=(data.status||{}).process_started_at||"";
      const waitForRestart=async()=>{
        let sawDisconnect=false;
        const deadline=Date.now()+45000;
        while(Date.now()<deadline){
          await new Promise(resolve=>setTimeout(resolve,1200));
          try{
            const check=await fetch("/api/console",{credentials:"same-origin",cache:"no-store"});
            if(!check.ok){sawDisconnect=true;continue;}
            const state=await check.json(),status=state.status||{};
            if(!status.online){sawDisconnect=true;continue;}
            // PID может сохраниться при os.execv, поэтому сверяем timestamp запуска модуля.
            if(status.process_started_at&&status.process_started_at!==originalProcessStartedAt)return true;
            if(sawDisconnect&&!originalProcessStartedAt)return true;
          }catch(_error){sawDisconnect=true;}
        }
        return false;
      };
      confirm.addEventListener("click",async()=>{
        confirm.disabled=true;cancel.disabled=true;close.disabled=true;confirm.textContent="Отправка…";restart.disabled=true;restart.textContent="Перезапуск…";
        try{
          const response=await fetch("/api/console/action",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"restart"})});
          const result=await response.json();
          if(!response.ok)throw new Error(result.detail||"Не удалось отправить команду перезапуска.");
          note.textContent="Команда принята. Проверяем отключение и повторное подключение бота…";
          note.classList.remove("error");confirm.textContent="Ожидание…";
          append(output,"Команда перезапуска отправлена. Ожидаем переподключения…","system");
          const restarted=await waitForRestart();
          if(!restarted)throw new Error("За 45 секунд не удалось подтвердить перезапуск. Проверь консоль первого хостинга: там должна появиться запись «Выполняю os.execv…» или ошибка перезапуска.");
          note.textContent="Бот отключился и успешно подключился заново. Перезапуск подтверждён.";
          confirm.textContent="Перезапуск подтверждён";append(output,"Бот снова в сети. Перезапуск подтверждён.","success");
          setTimeout(dismiss,2200);
        }catch(error){
          note.textContent=error.message||"Не удалось подтвердить перезапуск.";
          note.classList.add("error");confirm.disabled=false;cancel.disabled=false;close.disabled=false;
          confirm.textContent="Повторить";restart.disabled=false;restart.textContent="↻ Перезапустить бота";
          append(output,"Ошибка: "+(error.message||"Перезапуск не подтверждён."),"error");
        }
      });
      footer.append(cancel,confirm);dialog.append(close,icon,eyebrow,title,description,note,footer);modal.append(dialog);document.body.append(modal);confirm.focus();
    });restartRow.append(restartHint,restart);
    const tabs=document.createElement("div");tabs.className="console-mode-tabs";
    const shellTab=document.createElement("button");shellTab.type="button";shellTab.className="console-mode-tab active";shellTab.textContent="Shell";
    const appTab=document.createElement("button");appTab.type="button";appTab.className="console-mode-tab";appTab.textContent="Ввод в приложение";
    tabs.append(shellTab,appTab);
    const shellPane=document.createElement("div");shellPane.className="console-mode-pane";
    const appPane=document.createElement("div");appPane.className="console-mode-pane";appPane.hidden=true;
    const appOutput=document.createElement("div");appOutput.className="console-terminal-output console-app-output";
    append(appOutput,"GastWorld Application Input","system");
    append(appOutput,"Ввод передаётся обработчику приложения. Неизвестные команды тоже принимаются и возвращают ответ приложения.","muted");
    const appForm=document.createElement("form");appForm.className="console-command-form";
    const appPrompt=document.createElement("label");appPrompt.className="console-command-prompt";appPrompt.textContent="GastWorld>";
    const appInput=document.createElement("input");appInput.className="console-command-input";appInput.type="text";appInput.autocomplete="off";appInput.spellcheck=false;appInput.placeholder="Введите команду приложения или любой текст…";appInput.disabled=currentAccessLevel!=="full";
    const appRun=document.createElement("button");appRun.type="submit";appRun.className="console-action-button";appRun.textContent="Выполнить";appRun.disabled=currentAccessLevel!=="full";
    appForm.append(appPrompt,appInput,appRun);
    const appFoot=document.createElement("div");appFoot.className="console-terminal-foot";appFoot.textContent="Ввод в приложение · произвольная строка до 2000 символов · доступ Full. Команда обрабатывается логикой GastWorld, а не Linux.";
    appPane.append(appOutput,appForm,appFoot);
    const foot=document.createElement("div");foot.className="console-terminal-foot";foot.textContent=currentAccessLevel==="full"?"Shell · Linux первого хостинга · произвольные команды и символы · доступ Full. Команды могут изменять файлы и настройки сервера.":"Adm: live-просмотр вывода первого хостинга, быстрые действия и перезапуск. Команды доступны только Full.";
    shellPane.append(output);
    if(currentAccessLevel==="full")shellPane.append(form,restartRow,foot);else shellPane.append(restartRow,foot);
    const switchMode=(mode)=>{const shell=mode==="shell";shellTab.classList.toggle("active",shell);appTab.classList.toggle("active",!shell);shellPane.hidden=!shell;appPane.hidden=shell;};
    shellTab.addEventListener("click",()=>switchMode("shell"));appTab.addEventListener("click",()=>switchMode("app"));
    if(currentAccessLevel==="full")terminal.append(top,tabs,shellPane,appPane);else terminal.append(top,tabs,shellPane,appPane);
    workspace.append(cards,controls,terminal);root.replaceChildren(workspace);
    form.addEventListener("submit",async event=>{event.preventDefault();const command=input.value;if(!command.trim()||commandBusy)return;if(command.toLowerCase()==="clear"){output.replaceChildren();append(output,"Терминал очищен.","muted");input.value="";return;}if(command.toLowerCase()==="restart"){restart.click();input.value="";return;}if(currentAccessLevel!=="full"){append(output,"Недостаточно прав. Требуется уровень Full.","error");return;}commandBusy=true;history.push(command);historyIndex=history.length;append(output,"container~ "+command,"command");input.value="";run.disabled=true;run.textContent="…";try{const response=await fetch("/api/console/command",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({command})});const result=await response.json();if(!response.ok)throw new Error(result.detail||"Команда не выполнена.");append(output,result.output||"Команда выполнена.",Number(result.exit_code)===0?"success":"error");if(Number(result.exit_code)!==0)append(output,"Код завершения: "+result.exit_code,"muted");}catch(error){append(output,"Ошибка: "+(error.message||"Команда не выполнена."),"error");}finally{commandBusy=false;run.disabled=currentAccessLevel!=="full";run.textContent="Выполнить";input.focus();}});
    appForm.addEventListener("submit",async event=>{
      event.preventDefault();
      const command=appInput.value;
      if(!command.trim()||commandBusy)return;
      if(command.toLowerCase()==="clear"){appOutput.replaceChildren();append(appOutput,"Вывод приложения очищен.","muted");appInput.value="";return;}
      if(currentAccessLevel!=="full"){append(appOutput,"Недостаточно прав. Требуется уровень Full.","error");return;}
      commandBusy=true;append(appOutput,"GastWorld> "+command,"command");appInput.value="";appRun.disabled=true;appRun.textContent="…";
      try{
        const response=await fetch("/api/console/app-command",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({command})});
        const result=await response.json();
        if(!response.ok)throw new Error(result.detail||"Ввод в приложение не выполнен.");
        append(appOutput,result.output||"Приложение не вернуло ответ.",Number(result.exit_code)===0?"success":"error");
        if(Number(result.exit_code)!==0)append(appOutput,"Код ответа: "+result.exit_code,"muted");
      }catch(error){append(appOutput,"Ошибка: "+(error.message||"Не удалось передать ввод."),"error");}
      finally{commandBusy=false;appRun.disabled=currentAccessLevel!=="full";appRun.textContent="Выполнить";appInput.focus();}
    });
    input.addEventListener("keydown",event=>{if(event.key==="ArrowUp"){event.preventDefault();if(history.length){historyIndex=Math.max(0,historyIndex-1);input.value=history[historyIndex]||"";}}if(event.key==="ArrowDown"){event.preventDefault();if(history.length){historyIndex=Math.min(history.length,historyIndex+1);input.value=history[historyIndex]||"";}}});
    input.focus();
  };
  const pollOutput=async()=>{
    if(outputPollBusy)return;
    outputPollBusy=true;
    try{
      const result=await apiGet("/api/console/output?after_id="+encodeURIComponent(lastConsoleLineId));
      const output=root.querySelector(".console-terminal-output");
      if(!output)return;
      (result.lines||[]).forEach(item=>{
        const id=Number(item.id)||0;
        if(id>lastConsoleLineId){append(output,item.text||"","live");lastConsoleLineId=id;}
      });
      if(Number(result.latest_id)>lastConsoleLineId)lastConsoleLineId=Number(result.latest_id);
    }catch(error){
      // Ошибки короткого опроса не засоряют терминал; статус соединения виден в карточках.
    }finally{outputPollBusy=false;}
  };
  const poll=async()=>{if(pollBusy)return;pollBusy=true;try{const data=await apiGet("/api/console"),status=data.status||{};const strong=root.querySelectorAll(".console-status-card strong");if(strong[0]){strong[0].textContent=status.online?"В сети":"Не в сети";strong[0].className=status.online?"online":"offline";}if(strong[1])strong[1].textContent=status.bot_name||"GastWorld";if(strong[2])strong[2].textContent=status.guild_name||"—";if(strong[3])strong[3].textContent=status.latency_ms==null?"—":status.latency_ms+" мс";const led=root.querySelector(".console-terminal-title i");if(led)led.className=status.online?"online":"";}catch(error){const output=root.querySelector(".console-terminal-output");if(output)append(output,"[соединение] "+error.message,"error");}finally{pollBusy=false;}await pollOutput();};
  refresh?.addEventListener("click",async()=>{refresh.disabled=true;refresh.textContent="Загрузка…";await poll();refresh.disabled=false;refresh.textContent="↻ Обновить";});
  try{const data=await apiGet("/api/console");render(data);await pollOutput();}catch(error){root.replaceChildren();const msg=document.createElement("div");msg.className="console-error";msg.textContent="Не удалось подключиться к консоли: "+error.message;root.append(msg);}
  const timer=window.setInterval(()=>{if(!section.isConnected){window.clearInterval(timer);return;}if(!document.hidden){poll();pollOutput();}},1800);
}

async function loadLogs(section){
  const result=section.querySelector("#logsResult"),refresh=section.querySelector("#refreshLogs");
  const search=section.querySelector("#logsFileSearch"),summary=section.querySelector("#logsSummary");
  if(!result)return;
  result.classList.remove("log-viewer-mode");
  let files=[],busy=false;
  const formatSize=bytes=>bytes<1024?bytes+" B":bytes<1024*1024?(bytes/1024).toFixed(1)+" KB":(bytes/1024/1024).toFixed(2)+" MB";
  const showFiles=()=>{
    const term=(search.value||"").trim().toLowerCase();
    const filtered=files.filter(file=>file.name.toLowerCase().includes(term));
    result.replaceChildren();
    if(!filtered.length){
      const empty=document.createElement("div");empty.className="empty-state";empty.textContent=files.length?"Файлы по такому запросу не найдены.":"В папке logs/ пока нет .log файлов.";result.append(empty);return;
    }
    filtered.forEach(file=>{
      const card=document.createElement("button");card.type="button";card.className="log-file-card";
      const icon=document.createElement("span");icon.className="log-file-icon";icon.textContent="▤";
      const details=document.createElement("span");details.className="log-file-details";
      const name=document.createElement("strong");name.textContent=file.name;
      const meta=document.createElement("small");meta.textContent=formatSize(file.size)+" · Изменён: "+(file.modified||"—");
      details.append(name,meta);
      const arrow=document.createElement("span");arrow.className="log-file-arrow";arrow.textContent="›";
      card.append(icon,details,arrow);
      card.addEventListener("click",()=>openLogFile(section,file.name));
      result.append(card);
    });
  };
  const load=async()=>{
    if(busy)return;busy=true;refresh.disabled=true;
    try{
      const response=await fetch("/api/log-files",{credentials:"same-origin"});
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||"Не удалось получить список логов.");
      files=data.files||[];
      summary.textContent=data.available?"logs/ · "+files.length+" "+(files.length===1?"файл":"файлов"):"Папка logs/ не найдена на сервере бота.";
      showFiles();
    }catch(error){
      summary.textContent="Не удалось открыть папку logs/";
      result.replaceChildren();const empty=document.createElement("div");empty.className="empty-state";empty.textContent=error.message||"Ошибка загрузки.";result.append(empty);
    }finally{busy=false;refresh.disabled=false;}
  };
  refresh?.addEventListener("click",load);
  search?.addEventListener("input",showFiles);
  await load();
}
async function openLogFile(section,filename){
  const result=section.querySelector("#logsResult"),summary=section.querySelector("#logsSummary");
  result.classList.add("log-viewer-mode");
  result.replaceChildren();const loading=document.createElement("div");loading.className="empty-state";loading.textContent="Открываем "+filename+"…";result.append(loading);
  try{
    const response=await fetch("/api/log-file?name="+encodeURIComponent(filename),{credentials:"same-origin"});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||"Не удалось открыть файл.");
    const wrap=document.createElement("div");wrap.className="log-viewer";
    const top=document.createElement("div");top.className="log-viewer-top";
    const back=document.createElement("button");back.type="button";back.className="log-back-button";back.textContent="← Все файлы";
    back.addEventListener("click",()=>loadLogs(section));
    const title=document.createElement("div");title.className="log-viewer-title";
    const name=document.createElement("strong");name.textContent=data.name;
    const meta=document.createElement("small");meta.textContent=formatLogSize(data.size)+" · "+data.total_lines+" строк · Изменён: "+(data.modified||"—");
    title.append(name,meta);top.append(back,title);
    const tools=document.createElement("div");tools.className="log-viewer-tools";
    const find=document.createElement("input");find.className="panel-search";find.placeholder="Поиск внутри файла…";
    const count=document.createElement("span");count.className="log-viewer-count";count.textContent=data.truncated?"Показаны последние "+data.shown_lines+" строк":" "+data.shown_lines+" строк";
    tools.append(find,count);
    const pre=document.createElement("pre");pre.className="log-file-content";
    const lines=data.lines||[];
    const render=()=>{
      const term=find.value.trim().toLowerCase();
      pre.replaceChildren();
      const matches=lines.map((line,index)=>({line,index})).filter(item=>!term||item.line.toLowerCase().includes(term));
      matches.forEach(item=>{
        const row=document.createElement("div");row.className="log-file-line";
        const number=document.createElement("span");number.className="log-line-number";number.textContent=String(data.total_lines-data.shown_lines+item.index+1);
        const text=document.createElement("span");text.className="log-line-text";text.textContent=item.line||" ";
        row.append(number,text);pre.append(row);
      });
      count.textContent=matches.length+" / "+lines.length+" строк"+(data.truncated?" · показан конец файла":"");
    };
    find.addEventListener("input",render);render();
    wrap.append(top,tools,pre);result.replaceChildren(wrap);
    summary.textContent="Просмотр файла · "+data.name;
  }catch(error){
    result.replaceChildren();const empty=document.createElement("div");empty.className="empty-state";empty.textContent=error.message||"Ошибка открытия файла.";result.append(empty);
  }
}
function formatLogSize(bytes){
  return bytes<1024?bytes+" B":bytes<1024*1024?(bytes/1024).toFixed(1)+" KB":(bytes/1024/1024).toFixed(2)+" MB";
}

function makeCell(value){
  const cell=document.createElement("td");
  cell.textContent=String(value??"—");
  return cell;
}
async function apiPost(url,payload){
  const response=await fetch(url,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  const data=await response.json();
  if(!response.ok)throw new Error(data.detail||"Ошибка запроса.");
  return data;
}

let dcActiveUser=null,dcPollTimer=null,dcConversationCache=[];
function dcEscape(value){return String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));}
function dcAvatar(user,extra=""){
  const label=(user?.global_name||user?.username||"?").slice(0,2).toUpperCase();
  return user?.avatar_url?'<img class="dc-live-avatar '+extra+'" src="'+dcEscape(user.avatar_url)+'" alt="">':'<span class="dc-live-avatar '+extra+'">'+dcEscape(label)+'</span>';
}
async function dcLoadConversationList(){
  const list=document.getElementById("dcDmList");if(!list)return;
  try{
    const data=await apiGet("/api/discord/dms");dcConversationCache=data.conversations||[];
    const botLabel=document.getElementById("dcBotName");if(botLabel)botLabel.textContent=data.bot?.global_name||data.bot?.username||"WhiteGrief";
    list.replaceChildren();
    if(!dcConversationCache.length){const empty=document.createElement("div");empty.className="dc-live-empty";empty.textContent="Пока нет сохранённых личных диалогов. Найди участника через поиск и открой переписку.";list.append(empty);return;}
    dcConversationCache.forEach(item=>{
      const button=document.createElement("button");button.type="button";button.className="dc-live-dm-item"+(dcActiveUser?.id===item.user.id?" active":"");
      const avatar=document.createElement("span");avatar.innerHTML=dcAvatar(item.user);
      const body=document.createElement("span");body.className="dc-live-dm-copy";
      const name=document.createElement("strong");name.textContent=item.user.global_name||item.user.username;
      const preview=document.createElement("small");preview.textContent=item.last_message?.content||"Открыть диалог";
      body.append(name,preview);button.append(avatar.firstElementChild,body);button.addEventListener("click",()=>dcOpenConversation(item.user));list.append(button);
    });
  }catch(error){list.textContent=error.message;}
}
async function dcSearchUsers(){
  const input=document.getElementById("dcUserSearch"),results=document.getElementById("dcSearchResults");if(!input||!results)return;
  const query=input.value.trim();if(query.length<2){results.hidden=true;return;}
  results.hidden=false;results.textContent="Поиск…";
  try{
    const data=await apiGet("/api/discord/dms/search?q="+encodeURIComponent(query));results.replaceChildren();
    if(!(data.users||[]).length){results.textContent="Не найдено среди участников серверов, доступных боту. Попробуй точный Discord ID.";return;}
    data.users.forEach(user=>{
      const button=document.createElement("button");button.type="button";button.className="dc-search-result";
      const avatar=document.createElement("span");avatar.innerHTML=dcAvatar(user);
      const label=document.createElement("span");label.className="dc-live-dm-copy";
      const name=document.createElement("strong");name.textContent=user.global_name||user.username;
      const id=document.createElement("small");id.textContent="@"+user.username+" · "+user.id;
      label.append(name,id);button.append(avatar.firstElementChild,label);
      button.addEventListener("click",()=>{results.hidden=true;input.value="";dcOpenConversation(user);});results.append(button);
    });
  }catch(error){results.textContent=error.message;}
}
function dcAppendInlineMarkdown(parent,value){
  const source=String(value||"");
  const token=/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*]+)\*\*|__([^_]+)__|~~([^~]+)~~|\|\|([^|]+)\|\||\x60([^\x60]+)\x60|\*([^*\n]+)\*/g;
  let cursor=0,match;
  while((match=token.exec(source))){
    if(match.index>cursor)parent.append(document.createTextNode(source.slice(cursor,match.index)));
    let node;
    if(match[1]!==undefined){node=document.createElement("a");node.href=match[2];node.target="_blank";node.rel="noopener noreferrer";node.textContent=match[1];}
    else if(match[3]!==undefined){node=document.createElement("strong");node.textContent=match[3];}
    else if(match[4]!==undefined){node=document.createElement("u");node.textContent=match[4];}
    else if(match[5]!==undefined){node=document.createElement("s");node.textContent=match[5];}
    else if(match[6]!==undefined){node=document.createElement("span");node.className="dc-spoiler";node.textContent=match[6];}
    else if(match[7]!==undefined){node=document.createElement("code");node.textContent=match[7];}
    else{node=document.createElement("em");node.textContent=match[8];}
    parent.append(node);cursor=token.lastIndex;
  }
  if(cursor<source.length)parent.append(document.createTextNode(source.slice(cursor)));
}
function dcRenderMessageContent(parent,message){
  const content=String(message.content||"");
  const fallbackUsers=[...(dcMemberCache||[]),...(dcActiveUser?[dcActiveUser]:[])];
  const users=new Map([...fallbackUsers,...(message.mentions||[])].map(item=>[String(item.id),item]));
  const roleItems=[...(dcMemberRoleCache||[]),...(message.role_mentions||[])];
  const roles=new Map(roleItems.map(item=>[String(item.id),item]));
  const cachedChannels=dcActiveGuild?(dcChannelsCacheByGuild.get(dcActiveGuild.id)?.channels||[]):[];
  const channels=new Map([...cachedChannels,...(message.channel_mentions||[])].map(item=>[String(item.id),item]));
  const token=/<@!?([0-9]{5,})>|<@&([0-9]{5,})>|<#([0-9]{5,})>|<t:(-?[0-9]+)(?::([tTdDfFR]))?>|<(a?):([A-Za-z0-9_]+):([0-9]{5,})>|(https?:\/\/[^\s<]+)/g;
  let cursor=0,match;
  while((match=token.exec(content))){
    if(match.index>cursor)dcAppendInlineMarkdown(parent,content.slice(cursor,match.index));
    let node;
    if(match[1]){
      const user=users.get(match[1]);node=document.createElement("span");node.className="dc-mention dc-user-mention";node.textContent="@"+(user?.global_name||user?.display_name||user?.username||"пользователь");node.title=user?("@"+user.username+" · "+user.id):"Участник Discord";
      if(user){node.tabIndex=0;node.setAttribute("role","button");node.setAttribute("aria-label","Открыть профиль "+(user.global_name||user.username||"участника"));node.addEventListener("click",()=>dcOpenMentionProfile(user));node.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();dcOpenMentionProfile(user);}});}
    }else if(match[2]){
      const role=roles.get(match[2]);node=document.createElement("span");node.className="dc-mention dc-role-mention";node.textContent="@"+(role?.name||"роль");if(role?.color_hex)node.style.setProperty("--mention-color",role.color_hex);node.title=role?.name||"Роль Discord";
    }else if(match[3]){
      const channel=channels.get(match[3]);node=document.createElement("span");node.className="dc-mention dc-channel-mention";node.textContent="#"+(channel?.name||"канал");node.title=channel?.name||"Канал Discord";
      const target=cachedChannels.find(item=>String(item.id)===match[3]);
      if(target){node.tabIndex=0;node.setAttribute("role","button");node.addEventListener("click",()=>dcOpenGuildChannel(target));}
    }else if(match[4]){
      const stamp=Number(match[4]);node=document.createElement("time");node.className="dc-timestamp";node.dateTime=new Date(stamp*1000).toISOString();const date=new Date(stamp*1000);const style=(match[5]||"f").toLowerCase();node.textContent=style==="r"?new Intl.RelativeTimeFormat("ru",{numeric:"auto"}).format(Math.round((stamp*1000-Date.now())/60000),"minute"):date.toLocaleString("ru-RU",style==="t"||style==="T"?{hour:"2-digit",minute:"2-digit"}:style==="d"?{day:"2-digit",month:"2-digit",year:"numeric"}:style==="f"?{day:"numeric",month:"long",year:"numeric",hour:"2-digit",minute:"2-digit"}:{weekday:"long",day:"numeric",month:"long",year:"numeric",hour:"2-digit",minute:"2-digit"});node.title=date.toLocaleString("ru-RU");
    }else if(match[7]){
      node=document.createElement("img");node.className="dc-custom-emoji";node.alt=":"+match[8]+":";node.title=node.alt;const animateEmoji=match[7]==="a"&&dcAccessibilityPrefs.animatedEmoji&&!dcAccessibilityPrefs.reducedMotion;node.src="https://cdn.discordapp.com/emojis/"+match[9]+"."+(animateEmoji?"gif":"png")+"?size=48&quality=lossless";node.onerror=()=>{if(animateEmoji){node.src="https://cdn.discordapp.com/emojis/"+match[9]+".png?size=48&quality=lossless";}else node.replaceWith(document.createTextNode(node.alt));};
    }else{
      node=document.createElement("a");node.href=match[10];node.target="_blank";node.rel="noopener noreferrer";node.textContent=match[10];
    }
    parent.append(node);cursor=token.lastIndex;
  }
  if(cursor<content.length)dcAppendInlineMarkdown(parent,content.slice(cursor));
}
function dcActiveMessageChannelId(){return dcActiveChannel?.id||dcActiveDmChannelId||"";}
async function dcMessageRequest(method,channelId,messageId,payload){
  const response=await fetch("/api/discord/channels/"+encodeURIComponent(channelId)+"/messages/"+encodeURIComponent(messageId)+(method==="POST"&&payload?.emoji?"/reactions":method==="POST"&&typeof payload?.pinned==="boolean"?"/pin":""),{
    method,credentials:"same-origin",headers:payload?{"Content-Type":"application/json"}:undefined,body:payload?JSON.stringify(payload):undefined
  });
  const raw=await response.text();let data={};try{data=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ.");}
  if(!response.ok)throw new Error(data.detail||"Действие с сообщением не выполнено.");
  return data;
}
function dcRefreshCurrentHistory(){
  if(dcActiveChannel)return dcOpenGuildChannel(dcActiveChannel,true);
  if(dcActiveUser)return dcOpenConversation(dcActiveUser,true);
}
function dcSetReplyTarget(message){
  dcReplyTarget=message;
  const preview=document.getElementById("dcReplyPreview"),input=document.getElementById("dcMessageInput");
  if(preview){
    preview.replaceChildren();preview.hidden=false;
    const text=document.createElement("span");text.textContent="Ответ "+(message.author?.global_name||message.author?.username||"участнику")+": "+String(message.content||"[вложение]").slice(0,120);
    const close=document.createElement("button");close.type="button";close.textContent="×";close.title="Отменить ответ";close.addEventListener("click",dcClearReplyTarget);
    preview.append(text,close);
  }
  if(input){input.focus();input.placeholder="Ответить на сообщение…";}
}
function dcClearReplyTarget(){
  dcReplyTarget=null;
  const preview=document.getElementById("dcReplyPreview"),input=document.getElementById("dcMessageInput");
  if(preview){preview.replaceChildren();preview.hidden=true;}
  if(input)input.placeholder="Написать сообщение…";
}
async function dcToggleReaction(message,emoji){
  const channelId=dcActiveMessageChannelId();if(!channelId||!message?.id)return;
  try{await dcMessageRequest("POST",channelId,message.id,{emoji});await dcRefreshCurrentHistory();}
  catch(error){if(typeof showToast==="function")showToast(error.message);else alert(error.message);}
}
const dcGuildEmojiCache=new Map();
async function dcLoadGuildEmojis(guildId){
  if(!guildId)return [];
  if(dcGuildEmojiCache.has(String(guildId)))return dcGuildEmojiCache.get(String(guildId));
  const response=await fetch("/api/discord/guilds/"+encodeURIComponent(guildId)+"/emojis",{credentials:"same-origin",cache:"no-store"});
  const raw=await response.text();let data={};try{data=raw?JSON.parse(raw):{};}catch{}
  if(!response.ok)throw new Error(data.detail||"Не удалось загрузить эмодзи сервера.");
  const emojis=Array.isArray(data.emojis)?data.emojis:[];
  dcGuildEmojiCache.set(String(guildId),emojis);
  return emojis;
}
function dcMakeCustomEmojiButton(emoji,onPick){
  const button=document.createElement("button");button.type="button";button.className="dc-reaction-choice dc-custom-emoji-choice";
  button.title=":"+emoji.name+":";
  const image=document.createElement("img");image.src=emoji.url;image.alt=":"+emoji.name+":";image.loading="lazy";
  button.append(image);button.addEventListener("click",()=>onPick(emoji));return button;
}
function dcShowReactionPicker(event,message){
  document.querySelector(".dc-message-context")?.remove();
  const menu=document.createElement("div");menu.className="dc-message-context dc-reaction-picker";
  const addUnicode=emoji=>{const button=document.createElement("button");button.type="button";button.className="dc-reaction-choice";button.textContent=emoji;button.addEventListener("click",()=>{menu.remove();dcToggleReaction(message,emoji);});menu.append(button);};
  ["👍","❤️","😂","🎉","🔥","👀","✅","😮","😭","💀","🤝","⭐"].forEach(addUnicode);
  const guildId=dcActiveGuild?.id;
  if(guildId){
    const loading=document.createElement("div");loading.className="dc-reaction-emoji-state";loading.textContent="Загрузка эмодзи сервера…";menu.append(loading);
    dcLoadGuildEmojis(guildId).then(emojis=>{
      loading.remove();
      if(emojis.length){const heading=document.createElement("div");heading.className="dc-reaction-emoji-heading";heading.textContent="ЭМОДЗИ СЕРВЕРА";menu.append(heading);
        emojis.forEach(emoji=>menu.append(dcMakeCustomEmojiButton(emoji,selected=>{menu.remove();dcToggleReaction(message,"custom:"+selected.id);})));
      }else{const empty=document.createElement("div");empty.className="dc-reaction-emoji-state";empty.textContent="На сервере нет доступных эмодзи.";menu.append(empty);}
    }).catch(error=>{loading.textContent=error.message;});
  }
  document.body.append(menu);
  const rect=event.currentTarget?.getBoundingClientRect?.();
  const x=Math.min(event.clientX??rect?.left??20,window.innerWidth-280),y=Math.min(event.clientY??rect?.top??20,window.innerHeight-260);
  menu.style.left=Math.max(8,x)+"px";menu.style.top=Math.max(8,y)+"px";
  setTimeout(()=>document.addEventListener("click",()=>menu.remove(),{once:true}),0);
}
function dcShowMessageMenu(event,message){
  event.preventDefault();document.querySelector(".dc-message-context")?.remove();
  const menu=document.createElement("div");menu.className="dc-message-context";
  const ownMessage=String(message.author?.id||"")===String(dcBotProfileCache?.bot?.id||"");
  const channelId=dcActiveMessageChannelId();
  const actions=[
    ["Ответить",()=>dcSetReplyTarget(message)],
    ["Добавить реакцию",()=>dcShowReactionPicker(event,message)],
    ["Копировать текст",()=>navigator.clipboard.writeText(message.content||"")],
    ["Копировать ID сообщения",()=>navigator.clipboard.writeText(String(message.id||""))]
  ];
  if(ownMessage)actions.push(["Изменить сообщение",async()=>{
    const edited=window.prompt("Изменить сообщение:",message.content||"");
    if(edited===null)return;
    await dcMessageRequest("PATCH",channelId,message.id,{content:edited});
    await dcRefreshCurrentHistory();
  }]);
  if(ownMessage||dcActiveChannel?.can_manage_messages)actions.push(["Удалить сообщение",async()=>{
    if(!window.confirm("Удалить это сообщение?"))return;
    await dcMessageRequest("DELETE",channelId,message.id);
    await dcRefreshCurrentHistory();
  }]);
  const messageLink=dcActiveGuild
    ?"https://discord.com/channels/"+dcActiveGuild.id+"/"+channelId+"/"+message.id
    :"https://discord.com/channels/@me/"+channelId+"/"+message.id;
  actions.push(["Копировать ссылку",()=>navigator.clipboard.writeText(messageLink)]);
  if(dcActiveChannel?.can_manage_messages)actions.push([message.pinned?"Открепить сообщение":"Закрепить сообщение",async()=>{
    await dcMessageRequest("POST",channelId,message.id,{pinned:!message.pinned});
    await dcRefreshCurrentHistory();
  }]);
  actions.forEach(([label,action])=>{const button=document.createElement("button");button.type="button";button.textContent=label;button.addEventListener("click",async()=>{try{await action();}catch(error){if(typeof showToast==="function")showToast(error.message);else alert(error.message);}menu.remove();});menu.append(button);});
  document.body.append(menu);const x=Math.min(event.clientX,window.innerWidth-240),y=Math.min(event.clientY,window.innerHeight-220);menu.style.left=Math.max(8,x)+"px";menu.style.top=Math.max(8,y)+"px";
  setTimeout(()=>document.addEventListener("click",()=>menu.remove(),{once:true}),0);
}
function dcRenderMessageReactions(body,message){
  const reactions=Array.isArray(message.reactions)?message.reactions:[];
  if(!reactions.length&&!dcActiveMessageChannelId())return;
  const row=document.createElement("div");row.className="dc-message-reactions";
  reactions.forEach(reaction=>{
    const button=document.createElement("button");button.type="button";button.className="dc-reaction"+(reaction.me?" is-me":"");
    if(reaction.url){const image=document.createElement("img");image.src=reaction.url;image.alt=reaction.name||"emoji";button.append(image);}
    else button.append(document.createTextNode(reaction.name||reaction.emoji||"✦"));
    const count=document.createElement("span");count.textContent=String(reaction.count||1);button.append(count);
    button.title="Добавить или убрать реакцию";button.addEventListener("click",()=>dcToggleReaction(message,reaction.emoji));row.append(button);
  });
  if(dcActiveMessageChannelId()){
    const add=document.createElement("button");add.type="button";add.className="dc-reaction dc-reaction-add";add.textContent="＋";add.title="Добавить реакцию";add.addEventListener("click",event=>dcShowReactionPicker(event,message));row.append(add);
  }
  body.append(row);
}
function dcRenderMessages(messages){
  const root=document.getElementById("dcChatMessages");if(!root)return;root.replaceChildren();
  if(!messages.length){const empty=document.createElement("div");empty.className="dc-live-welcome";empty.innerHTML='<div class="dc-live-welcome-icon">＠</div><h1>Это начало переписки</h1><p>Здесь пока нет сообщений. Можешь отправить первое сообщение, если Discord разрешает открыть DM.</p>';root.append(empty);return;}
  messages.forEach(message=>{
    const row=document.createElement("article");row.className="dc-message dc-live-message";row.dataset.messageId=message.id||"";row.addEventListener("contextmenu",event=>dcShowMessageMenu(event,message));
    const avatar=document.createElement("div");avatar.className="dc-message-avatar";
    if(message.author?.avatar_url){const img=document.createElement("img");img.src=message.author.avatar_url;img.alt="";avatar.append(img);}else avatar.textContent=(message.author?.global_name||message.author?.username||"?").slice(0,2).toUpperCase();
    const body=document.createElement("div");body.className="dc-message-body";
    const head=document.createElement("div");head.className="dc-message-head";
    const author=document.createElement("strong");author.textContent=message.author?.global_name||message.author?.username||"Discord user";
    const messageHighestRole=(message.author_roles||[]).filter(role=>role.color_hex||role.secondary_color_hex).sort((a,b)=>(Number(b.position)||0)-(Number(a.position)||0))[0];
    if(messageHighestRole&&dcAccessibilityPrefs.roleColorMode==="name")dcApplyRoleColor(author,messageHighestRole,true);
    const time=document.createElement("time");const created=new Date(message.created_at);time.dateTime=created.toISOString();time.textContent=created.toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"});time.title=created.toLocaleString("ru-RU");
    if(messageHighestRole&&dcAccessibilityPrefs.roleColorMode==="dot"){const roleDot=document.createElement("i");roleDot.className="dc-member-role-color";dcApplyRoleColor(roleDot,messageHighestRole,false);head.append(author,roleDot,time);}else head.append(author,time);
    if(message.edited_at){const edited=document.createElement("small");edited.className="dc-edited-label";edited.textContent="(изменено)";head.append(edited);}
    body.append(head);
    if(message.reply_preview){
      const reply=document.createElement("button");reply.type="button";reply.className="dc-message-reply-preview";
      reply.textContent="↪ "+(message.reply_preview.author?.global_name||message.reply_preview.author?.username||"Ответ на сообщение")+": "+(message.reply_preview.content||"[сообщение недоступно]").slice(0,120);
      reply.addEventListener("click",()=>{const target=document.querySelector('[data-message-id="'+CSS.escape(String(message.reply_preview.message_id))+'"]');target?.scrollIntoView({behavior:"smooth",block:"center"});target?.classList.add("dc-message-target");setTimeout(()=>target?.classList.remove("dc-message-target"),1400);});
      body.append(reply);
    }
    if(message.content){const text=document.createElement("p");text.className="dc-message-content";dcRenderMessageContent(text,message);body.append(text);}
    (message.attachments||[]).forEach(file=>{
      const link=document.createElement("a");link.href=file.url;link.target="_blank";link.rel="noopener noreferrer";link.textContent="📎 "+file.filename;link.className="dc-attachment-link";body.append(link);
      if((file.content_type||"").startsWith("image/")){
        const isGif=(file.content_type||"").toLowerCase().includes("gif")||/\.gif(?:$|\?)/i.test(file.filename||file.url||"");
        const showImage= !isGif || (dcAccessibilityPrefs.autoplayGifs&&!dcAccessibilityPrefs.reducedMotion);
        if(showImage){const preview=document.createElement("img");preview.className="dc-attachment-preview";preview.src=file.url;preview.alt=file.filename;preview.loading="lazy";body.append(preview);}
        else{const play=document.createElement("button");play.type="button";play.className="dc-animated-media-trigger";play.textContent="▶  Воспроизвести GIF";play.addEventListener("click",()=>{const preview=document.createElement("img");preview.className="dc-attachment-preview";preview.src=file.url;preview.alt=file.filename;preview.loading="lazy";play.replaceWith(preview);});body.append(play);}
      }
    });
    if((message.stickers||[]).length){
      const stickerWrap=document.createElement("div");stickerWrap.className="dc-message-stickers";
      (message.stickers||[]).forEach(sticker=>{
        const format=String(sticker.format||"").toLowerCase();
        const animated=["apng","gif","2","4"].includes(format);
        const mode=dcAccessibilityPrefs.reducedMotion?"never":dcAccessibilityPrefs.stickerAnimation;
        if(format==="lottie"||format==="3"){
          const link=document.createElement("a");link.className="dc-sticker-static-label";link.href=sticker.url||"#";link.target="_blank";link.rel="noopener noreferrer";link.textContent="Lottie-стикер · "+(sticker.name||"Discord");stickerWrap.append(link);return;
        }
        const showNow=!animated||mode==="always";
        if(!sticker.url){const label=document.createElement("span");label.textContent="Стикер: "+(sticker.name||"Discord");stickerWrap.append(label);return;}
        if(showNow){const image=document.createElement("img");image.className="dc-message-sticker";image.src=sticker.url;image.alt=sticker.name||"Стикер Discord";image.loading="lazy";stickerWrap.append(image);}
        else if(mode==="interaction"){const trigger=document.createElement("button");trigger.type="button";trigger.className="dc-sticker-trigger";trigger.textContent="✦  "+(sticker.name||"Показать стикер");trigger.addEventListener("click",()=>{const image=document.createElement("img");image.className="dc-message-sticker";image.src=sticker.url;image.alt=sticker.name||"Стикер Discord";image.loading="lazy";trigger.replaceWith(image);});stickerWrap.append(trigger);}
        else{const label=document.createElement("span");label.className="dc-sticker-static-label";label.textContent="Стикер · "+(sticker.name||"Discord");stickerWrap.append(label);}
      });
      body.append(stickerWrap);
    }
    (message.embeds||[]).forEach(embed=>{const card=document.createElement("div");card.className="dc-embed-card";if(embed.title){const title=document.createElement(embed.url?"a":"strong");title.textContent=embed.title;if(embed.url){title.href=embed.url;title.target="_blank";title.rel="noopener noreferrer";}card.append(title);}if(embed.description){const description=document.createElement("p");dcAppendInlineMarkdown(description,embed.description);card.append(description);}if(embed.image_url){const image=document.createElement("img");image.src=embed.image_url;image.alt="";image.loading="lazy";card.append(image);}body.append(card);});
    if(!message.content&&!message.attachments?.length&&!message.embeds?.length&&!message.stickers?.length){const empty=document.createElement("p");empty.className="dc-message-content";empty.textContent="[Сообщение без текста]";body.append(empty);}
    dcRenderMessageReactions(body,message);
    if(message.pinned){const pin=document.createElement("small");pin.className="dc-message-pinned";pin.textContent="📌 Закреплено";body.append(pin);}
    const toolbar=document.createElement("div");toolbar.className="dc-message-toolbar";
    const quick=(label,glyph,title,handler)=>{const button=document.createElement("button");button.type="button";button.textContent=glyph;button.title=title;button.setAttribute("aria-label",title);button.addEventListener("click",handler);toolbar.append(button);};
    quick("Ответить","↶","Ответить",()=>dcSetReplyTarget(message));
    quick("Реакция","☺","Добавить реакцию",event=>dcShowReactionPicker(event,message));
    quick("Ещё","···","Действия с сообщением",event=>dcShowMessageMenu(event,message));
    row.append(avatar,body,toolbar);root.append(row);
  });
  root.scrollTop=root.scrollHeight;
}
async function dcOpenConversation(user,silent=false){
  if(!user?.id)return;
  if(dcActiveUser?.id!==user.id||dcActiveChannel)dcClearReplyTarget();
  dcActiveUser=user;dcActiveChannel=null;dcActiveGuild=null;dcActiveDmChannelId=null;dcSetMode("dm");
  const title=document.getElementById("dcChatTitle"),subtitle=document.getElementById("dcChatSubtitle"),input=document.getElementById("dcMessageInput"),send=document.getElementById("dcSendButton"),hint=document.getElementById("dcComposerHint"),card=document.getElementById("dcRecipientCard");
  if(title)title.textContent=user.global_name||user.username;if(subtitle)subtitle.textContent="@"+user.username+" · "+user.id;
  if(input)input.disabled=false;if(send)send.disabled=false;
  if(hint)hint.textContent="Сообщение будет отправлено от имени "+(document.getElementById("dcBotName")?.textContent||"бота")+".";
  if(card){card.replaceChildren();const avatar=document.createElement("div");avatar.innerHTML=dcAvatar(user,"dc-recipient-avatar");const name=document.createElement("strong");name.textContent=user.global_name||user.username;const handle=document.createElement("span");handle.textContent="@"+user.username;const id=document.createElement("small");id.textContent="ID: "+user.id;card.append(avatar.firstElementChild,name,handle,id);}
  document.querySelectorAll(".dc-live-dm-item").forEach(item=>item.classList.toggle("active",item.textContent.includes(user.global_name||user.username)));
  const profilePanel=document.getElementById("dcDmProfilePanel");
  if(profilePanel){
    profilePanel.replaceChildren();
    const banner=document.createElement("div");banner.className="dc-dm-profile-banner";profilePanel.append(banner);
    const avatarWrap=document.createElement("div");avatarWrap.className="dc-dm-profile-avatar";const avatarImage=document.createElement("img");avatarImage.src=user.avatar_url||"";avatarImage.alt="";if(!user.avatar_url)avatarImage.hidden=true;avatarWrap.append(avatarImage);profilePanel.append(avatarWrap);
    const name=document.createElement("h2");name.textContent=user.global_name||user.username||"Discord";profilePanel.append(name);
    const username=document.createElement("p");username.className="dc-dm-profile-username";username.textContent="@"+(user.username||"");profilePanel.append(username);
    const divider=document.createElement("div");divider.className="dc-dm-profile-divider";profilePanel.append(divider);
    const details=document.createElement("section");details.className="dc-dm-profile-details";const heading=document.createElement("h3");heading.textContent="ПОЛЬЗОВАТЕЛЬ DISCORD";const id=document.createElement("p");id.textContent="ID: "+user.id;details.append(heading,id);profilePanel.append(details);
    const action=document.createElement("button");action.type="button";action.className="dc-dm-profile-action";action.textContent="Открыть профиль";action.addEventListener("click",()=>{const member=dcMemberCache.find(item=>String(item.id)===String(user.id));if(member&&dcActiveGuild)dcOpenProfile(member);else{action.textContent="Профиль сервера доступен при выборе сервера";}});profilePanel.append(action);
  }
  const root=document.getElementById("dcChatMessages");if(root&&!silent)root.innerHTML='<div class="dc-live-loading">Открываем личную переписку…</div>';
  try{const data=await apiGet("/api/discord/dms/"+encodeURIComponent(user.id)+"/messages");if(dcActiveUser?.id!==user.id)return;dcActiveDmChannelId=String(data.channel_id||"");dcRenderMessages(data.messages||[]);await dcLoadConversationList();}
  catch(error){if(root){root.replaceChildren();const msg=document.createElement("div");msg.className="dc-live-error";msg.textContent=error.message;root.append(msg);}if(hint)hint.textContent="Не удалось открыть DM. Проверь ограничения приватности Discord.";}
}
async function dcSendMessage(event){
  event.preventDefault();
  const input=document.getElementById("dcMessageInput"),send=document.getElementById("dcSendButton"),hint=document.getElementById("dcComposerHint"),filesInput=document.getElementById("dcFileInput");
  const content=input?.value.trim()||"",files=Array.from(filesInput?.files||[]);
  if((!content&&!files.length)||(!dcActiveUser&&!dcActiveChannel))return;
  if(files.length>10){hint.textContent="Можно прикрепить не больше 10 файлов.";return;}
  if(files.some(file=>file.size>8*1024*1024)){hint.textContent="Каждый файл должен быть не больше 8 МБ.";return;}
  if(files.reduce((sum,file)=>sum+file.size,0)>25*1024*1024){hint.textContent="Общий размер файлов не должен превышать 25 МБ.";return;}
  send.disabled=true;hint.textContent="Отправляем сообщение и вложения…";
  try{
    const form=new FormData();form.append("content",content);if(dcReplyTarget?.id)form.append("reply_to",String(dcReplyTarget.id));files.forEach(file=>form.append("files",file,file.name));
    const url=dcActiveChannel?"/api/discord/channels/"+encodeURIComponent(dcActiveChannel.id)+"/messages":"/api/discord/dms/"+encodeURIComponent(dcActiveUser.id)+"/messages";
    const response=await fetch(url,{method:"POST",credentials:"same-origin",body:form});
    const raw=await response.text();let result={};try{result=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ.");}
    if(!response.ok)throw new Error(result.detail||"Не удалось отправить сообщение.");
    input.value="";if(filesInput)filesInput.value="";dcClearReplyTarget();dcCloseMentionPicker();dcCloseEmojiPicker();
    const preview=document.getElementById("dcFilePreview");if(preview){preview.replaceChildren();preview.hidden=true;}
    if(dcActiveChannel)await dcOpenGuildChannel(dcActiveChannel,true);else await dcOpenConversation(dcActiveUser,true);
    hint.textContent="Сообщение отправлено от имени бота.";
  }catch(error){hint.textContent=error.message;}
  finally{send.disabled=!!(dcActiveChannel&&!dcActiveChannel.can_send);input?.focus();}
}
let dcActiveGuild=null,dcActiveChannel=null,dcGuildCache=[];
let dcActiveDmChannelId=null,dcReplyTarget=null;
let dcMemberCache=[];
let dcMemberCacheByGuild=new Map();
let dcMemberRolesByGuild=new Map();
let dcChannelsCacheByGuild=new Map();
let dcMembersLoading=new Set();
let dcChannelsLoading=new Set();
function dcSetMode(mode){
  const dm=mode==="dm",search=document.getElementById("dcDmSearch"),searchResults=document.getElementById("dcSearchResults"),dmList=document.getElementById("dcDmList"),channelList=document.getElementById("dcChannelList"),title=document.getElementById("dcSidebarTitle"),refresh=document.getElementById("dcRefreshDms");
  if(search)search.hidden=!dm;if(searchResults)searchResults.hidden=true;if(dmList)dmList.hidden=!dm;if(channelList)channelList.hidden=dm;
  const membersPanel=document.getElementById("dcMembersPanel"),profilePanel=document.getElementById("dcDmProfilePanel"),membersHead=membersPanel?.querySelector(".dc-members-head"),memberSearch=document.getElementById("dcMemberSearch"),memberList=document.getElementById("dcMemberList");
  if(membersPanel)membersPanel.hidden=false;if(profilePanel)profilePanel.hidden=!dm;if(membersHead)membersHead.hidden=dm;if(memberSearch)memberSearch.hidden=dm;if(memberList)memberList.hidden=dm;const settingsButton=document.getElementById("dcServerSettingsButton");if(settingsButton)settingsButton.hidden=dm||!dcActiveGuild;
  if(title)title.textContent=dm?"ЛИЧНЫЕ СООБЩЕНИЯ":"ТЕКСТОВЫЕ КАНАЛЫ";if(refresh)refresh.title=dm?"Обновить диалоги":"Обновить каналы";
  document.querySelectorAll(".dc-guild-icon").forEach(x=>x.classList.toggle("selected",dm?x.id==="dcHomeButton":x.dataset.guildId===dcActiveGuild?.id));
}

let dcBotProfileCache=null;
const dcBotStatusLabels={online:"В сети",idle:"Неактивен",dnd:"Не беспокоить",invisible:"Невидимый"};
const dcBotActivityLabels={playing:"Играет",listening:"Слушает",watching:"Смотрит",competing:"Соревнуется"};
function dcRenderBotAccount(profile){
  if(!profile)return;
  dcBotProfileCache={...(dcBotProfileCache||{}),...profile};
  const bot=dcBotProfileCache.bot||profile.bot||{};
  const name=document.getElementById("dcBotName"),small=document.getElementById("dcBotStatusText"),avatar=document.getElementById("dcBotAccountAvatar");
  if(name)name.textContent=bot.global_name||bot.username||"GastWorld";
  if(small){
    const status=dcBotStatusLabels[dcBotProfileCache.status]||"Подключён";
    const type=dcBotActivityLabels[dcBotProfileCache.activity_type];
    const activity=type&&dcBotProfileCache.activity_text?type+" "+dcBotProfileCache.activity_text:"";
    small.textContent="Бот · "+status+(activity?" · "+activity:"");
  }
  if(avatar){
    avatar.replaceChildren();
    if(bot.avatar_url){const image=document.createElement("img");image.src=bot.avatar_url;image.alt="";avatar.append(image);}
    else avatar.append(document.createTextNode((bot.global_name||bot.username||"GW").slice(0,2).toUpperCase()));
    const dot=document.createElement("span");dot.className="dc-account-status-dot dc-status-"+(dcBotProfileCache.status||"online");avatar.append(dot);
  }
}
async function dcLoadBotProfile(){
  try{const profile=await apiGet("/api/discord/bot-profile");dcRenderBotAccount(profile);}
  catch(error){const small=document.getElementById("dcBotStatusText");if(small)small.textContent="Бот · профиль недоступен";}
}
function dcReadFileAsDataUrl(file){
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();reader.onload=()=>resolve(String(reader.result||""));reader.onerror=()=>reject(new Error("Не удалось прочитать изображение."));reader.readAsDataURL(file);
  });
}
async function dcOpenBotProfileSettings(){
  document.getElementById("dcBotProfileModal")?.remove();
  let profile=dcBotProfileCache;
  try{profile=await apiGet("/api/discord/bot-profile");dcRenderBotAccount(profile);}
  catch(error){alert(error.message);return;}
  const modal=document.createElement("div");modal.id="dcBotProfileModal";modal.className="dc-settings-backdrop";
  const card=document.createElement("section");card.className="dc-accessibility-card dc-bot-profile-card";card.setAttribute("role","dialog");card.setAttribute("aria-modal","true");card.setAttribute("aria-labelledby","dcBotProfileTitle");
  card.innerHTML=`
    <header class="dc-settings-header">
      <div class="dc-settings-heading"><span>GASTWORLD • DISCORD BOT</span><h2 id="dcBotProfileTitle">Профиль бота</h2><p>Изменения применяются к реальному аккаунту бота в Discord.</p></div>
      <button type="button" class="dc-settings-close" data-close aria-label="Закрыть">×</button>
    </header>
    <div class="dc-bot-profile-body">
      <div class="dc-bot-profile-avatar-row">
        <img id="dcBotProfileAvatarPreview" alt="Аватар бота">
        <label class="dc-bot-profile-upload">Изменить аватар<input id="dcBotProfileAvatar" type="file" accept="image/png,image/jpeg,image/gif"></label>
        <small>PNG, JPG или GIF · до 8 МБ</small>
      </div>
      <label class="dc-settings-field">Имя пользователя Discord<input id="dcBotProfileUsername" maxlength="32" minlength="2" autocomplete="off" required></label>
      <label class="dc-settings-field">Статус<select id="dcBotProfileStatus">
        <option value="online">🟢 В сети</option><option value="idle">🌙 Неактивен</option><option value="dnd">⛔ Не беспокоить</option><option value="invisible">⚫ Невидимый</option>
      </select></label>
      <label class="dc-settings-field">Активность<select id="dcBotProfileActivityType">
        <option value="none">Не показывать активность</option><option value="playing">Играет</option><option value="listening">Слушает</option><option value="watching">Смотрит</option><option value="competing">Соревнуется</option>
      </select></label>
      <label class="dc-settings-field">Текст активности<input id="dcBotProfileActivityText" maxlength="128" placeholder="Например: GastWorld"></label>
      <label class="dc-settings-field wide">О себе / описание профиля<textarea id="dcBotProfileAbout" rows="4" maxlength="400" placeholder="Расскажи о боте…"></textarea><small>Это описание приложения Discord, которое отображается в профиле бота.</small></label>
      <p class="dc-bot-profile-note">Discord не разрешает ботам устанавливать пользовательский статус с эмодзи и произвольной фразой, как у обычного аккаунта. Вместо этого здесь настраивается активность.</p>
      <div class="dc-settings-status" id="dcBotProfileStatusMessage" role="status"></div>
      <div class="dc-settings-footer"><button type="button" class="dc-settings-cancel" data-close>Отмена</button><button type="button" class="dc-settings-save" id="dcBotProfileSave">Сохранить изменения</button></div>
    </div>`;
  modal.append(card);document.body.append(modal);
  const close=()=>modal.remove();
  modal.addEventListener("click",event=>{if(event.target===modal||event.target.closest("[data-close]"))close();});
  const username=card.querySelector("#dcBotProfileUsername"),status=card.querySelector("#dcBotProfileStatus"),activityType=card.querySelector("#dcBotProfileActivityType"),activityText=card.querySelector("#dcBotProfileActivityText"),about=card.querySelector("#dcBotProfileAbout"),avatarInput=card.querySelector("#dcBotProfileAvatar"),avatarPreview=card.querySelector("#dcBotProfileAvatarPreview"),message=card.querySelector("#dcBotProfileStatusMessage"),save=card.querySelector("#dcBotProfileSave");
  const currentBot=profile.bot||{};
  username.value=currentBot.username||currentBot.global_name||"GastWorld";
  status.value=profile.status||"online";activityType.value=profile.activity_type||"playing";activityText.value=profile.activity_text||"";about.value=profile.about||"";
  if(currentBot.avatar_url){avatarPreview.src=currentBot.avatar_url;}else{avatarPreview.hidden=true;}
  activityType.addEventListener("change",()=>{activityText.disabled=activityType.value==="none";});
  activityType.dispatchEvent(new Event("change"));
  avatarInput.addEventListener("change",()=>{
    const file=avatarInput.files?.[0];if(!file)return;
    if(file.size>8*1024*1024){message.textContent="Аватар должен быть не больше 8 МБ.";avatarInput.value="";return;}
    if(!["image/png","image/jpeg","image/gif"].includes(file.type)){message.textContent="Поддерживаются PNG, JPG и GIF.";avatarInput.value="";return;}
    avatarPreview.hidden=false;avatarPreview.src=URL.createObjectURL(file);
    message.textContent="Новый аватар готов к загрузке.";
  });
  save.addEventListener("click",async()=>{
    const chosenAvatar=avatarInput.files?.[0];
    if(!username.value.trim()){message.textContent="Укажи имя бота.";return;}
    if(activityType.value!=="none"&&!activityText.value.trim()){message.textContent="Укажи текст активности.";return;}
    save.disabled=true;message.textContent="Сохраняем изменения в Discord…";
    try{
      const payload={username:username.value.trim(),status:status.value,activity_type:activityType.value,activity_text:activityText.value.trim(),about:about.value.trim()};
      if(chosenAvatar)payload.avatar_data=await dcReadFileAsDataUrl(chosenAvatar);
      const response=await fetch("/api/discord/bot-profile",{method:"PATCH",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const raw=await response.text();let result={};try{result=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ.");}
      if(!response.ok)throw new Error(result.detail||"Не удалось изменить профиль бота.");
      dcRenderBotAccount(result);close();
    }catch(error){message.textContent=error.message;save.disabled=false;}
  });
  card.querySelector("#dcBotProfileUsername").focus();
}
async function dcLoadGuilds(){
  const rail=document.getElementById("dcGuildList");if(!rail)return;
  try{
    const data=await apiGet("/api/discord/guilds");dcGuildCache=data.guilds||[];
    if(data.bot)dcRenderBotAccount({bot:data.bot});
    rail.querySelectorAll("[data-guild-id]").forEach(x=>x.remove());
    dcGuildCache.forEach(guild=>{
      const button=document.createElement("button");button.type="button";button.className="dc-guild-icon";button.dataset.guildId=guild.id;button.title=guild.name;
      if(guild.icon_url){const img=document.createElement("img");img.src=guild.icon_url;img.alt="";img.className="dc-guild-image";button.append(img);}else button.textContent=(guild.name||"GW").split(/\s+/).slice(0,2).map(x=>x[0]).join("").toUpperCase();
      button.addEventListener("click",()=>dcOpenGuild(guild));rail.append(button);
    });
    if(!dcGuildCache.length){const note=document.createElement("div");note.className="dc-guild-empty";note.textContent="Бот пока не состоит на серверах";rail.append(note);}
  }catch(error){const note=document.createElement("div");note.className="dc-guild-empty";note.textContent=error.message;rail.append(note);}
}
async function dcLoadGuildMembers(guild,force=false){
  const root=document.getElementById("dcMemberList"),count=document.getElementById("dcMemberCount");
  if(!root||!guild?.id)return;
  if(dcMemberCacheByGuild.has(guild.id)&&!force){dcMemberCache=dcMemberCacheByGuild.get(guild.id);dcMemberRoleCache=dcMemberRolesByGuild.get(guild.id)||[];dcRenderGuildMembers();return;}
  if(dcMembersLoading.has(guild.id))return;
  dcMembersLoading.add(guild.id);
  root.replaceChildren();const loading=document.createElement("div");loading.className="dc-live-empty";loading.textContent="Загружаем участников…";root.append(loading);
  if(count)count.textContent="…";
  const pageSize=500;
  const allMembers=[];
  let roles=[],after="0",hasMore=true;
  try{
    while(hasMore){
      const url="/api/discord/guilds/"+encodeURIComponent(guild.id)+"/members?limit="+pageSize+"&after="+encodeURIComponent(after);
      let data;
      try{data=await apiGet(url);}
      catch(error){
        if(error?.message==="Failed to fetch"){
          await new Promise(resolve=>setTimeout(resolve,700));
          data=await apiGet(url);
        }else throw error;
      }
      if(dcActiveGuild?.id!==guild.id)return;
      const page=Array.isArray(data.members)?data.members:[];
      if(!roles.length)roles=Array.isArray(data.roles)?data.roles:[];
      allMembers.push(...page);
      dcMemberCache=allMembers.slice();dcMemberRoleCache=roles;
      dcRenderGuildMembers();
      const nextAfter=String(data.next_after||"");
      hasMore=Boolean(data.has_more)&&page.length>0&&!!nextAfter&&nextAfter!==after;
      if(hasMore){
        after=nextAfter;
        if(count)count.textContent=allMembers.length.toLocaleString("ru-RU")+" загружено…";
      }
    }
    if(dcActiveGuild?.id!==guild.id)return;
    dcMemberCache=allMembers;dcMemberRoleCache=roles;
    dcMemberCacheByGuild.set(guild.id,dcMemberCache);dcMemberRolesByGuild.set(guild.id,dcMemberRoleCache);
    dcRenderGuildMembers();dcUpdateMentionPicker(document.getElementById("dcMessageInput"));
  }catch(error){
    if(dcActiveGuild?.id!==guild.id)return;
    dcMemberCacheByGuild.delete(guild.id);dcMemberRolesByGuild.delete(guild.id);
    const detail=error?.message==="Failed to fetch"
      ?"Не удалось получить ответ от API панели. Проверь соединение с сервером бота."
      :(error.message||"Не удалось загрузить участников.");
    const message=document.createElement("div");message.className="dc-live-empty dc-member-error";
    message.textContent=allMembers.length
      ?detail+" Загружено частично: "+allMembers.length.toLocaleString("ru-RU")+". Нажми ↻, чтобы повторить."
      :detail+" Нажми ↻, чтобы повторить.";
    if(allMembers.length)root.append(message);else{root.replaceChildren(message);}
    if(count)count.textContent=allMembers.length?allMembers.length.toLocaleString("ru-RU")+" · частично":"—";
  }finally{dcMembersLoading.delete(guild.id);}
}
let dcMemberRoleCache=[];
let dcMentionPickerItems=[],dcMentionPickerIndex=0,dcMentionTrigger=null;
const dcEmojiChoices=["😀","😃","😄","😁","😆","😅","😂","🤣","😊","😍","🥰","😘","😎","🤔","😴","😭","😡","🤯","🥳","😱","👍","👎","👏","🙌","🙏","🤝","💪","🔥","❤️","💙","💜","✨","⭐","✅","❌","🎉","🎮","💀","👀","🍀"];
function dcCloseMentionPicker(){
  const root=document.getElementById("dcMentionPicker");if(root){root.hidden=true;root.replaceChildren();}
  dcMentionPickerItems=[];dcMentionPickerIndex=0;dcMentionTrigger=null;
}
function dcMentionCandidates(trigger,query){
  const needle=String(query||"").toLocaleLowerCase("ru");
  const users=[],roles=[],channels=[],broadcasts=[];
  if(trigger==="@"||trigger==="@&"){
    if(trigger==="@" ){
      const members=dcActiveGuild?dcMemberCache:(dcActiveUser?[dcActiveUser]:[]);
      members.forEach(member=>{
        const label=member.global_name||member.display_name||member.username||"Участник";
        if((label+" "+(member.username||"")+" "+member.id).toLocaleLowerCase("ru").includes(needle))
          users.push({kind:"user",id:String(member.id),label,detail:"@"+(member.username||""),avatar:member.avatar_url||member.avatar||""});
      });
      if(dcActiveChannel?.can_mention_everyone){
        if("everyone".includes(needle))broadcasts.push({kind:"everyone",label:"everyone",detail:"Упоминание всех участников канала"});
        if("here".includes(needle))broadcasts.push({kind:"here",label:"here",detail:"Упоминание участников онлайн"});
      }
    }
    if(dcActiveGuild){
      (dcMemberRoleCache||[]).forEach(role=>{
        if((role.name||"").toLocaleLowerCase("ru").includes(needle))
          roles.push({kind:"role",id:String(role.id),label:role.name,detail:role.mentionable?"Упоминание включено":"Может потребоваться право MENTION_EVERYONE",color:role.color_hex||""});
      });
    }
    return trigger==="@&"?roles.slice(0,30):[...broadcasts,...users.slice(0,13),...roles.slice(0,15)];
  }
  if(trigger==="#"){
    const available=dcActiveGuild?(dcChannelsCacheByGuild.get(dcActiveGuild.id)?.channels||[]):[];
    available.forEach(channel=>{
      if((channel.name||"").toLocaleLowerCase("ru").includes(needle))
        channels.push({kind:"channel",id:String(channel.id),label:channel.name,detail:channel.category_name||"Текстовый канал"});
    });
  }
  return channels.slice(0,30);
}
function dcRenderMentionPicker(){
  const root=document.getElementById("dcMentionPicker");if(!root)return;
  root.replaceChildren();
  if(!dcMentionPickerItems.length){root.hidden=true;return;}
  root.hidden=false;
  const title=document.createElement("div");title.className="dc-mention-picker-title";title.textContent=dcMentionTrigger?.type==="#"?"КАНАЛЫ":dcMentionTrigger?.type==="@&"?"РОЛИ":"УЧАСТНИКИ И РОЛИ";root.append(title);
  dcMentionPickerItems.forEach((item,index)=>{
    const button=document.createElement("button");button.type="button";button.className="dc-mention-option"+(index===dcMentionPickerIndex?" is-active":"");button.setAttribute("role","option");button.setAttribute("aria-selected",String(index===dcMentionPickerIndex));
    if(item.kind==="user"&&item.avatar){const avatar=document.createElement("img");avatar.className="dc-mention-option-avatar";avatar.src=item.avatar;avatar.alt="";button.append(avatar);}
    else{const glyph=document.createElement("span");glyph.className="dc-mention-option-glyph";glyph.textContent=item.kind==="channel"?"#":item.kind==="role"||item.kind==="everyone"||item.kind==="here"?"@":"●";if(item.color)glyph.style.color=item.color;button.append(glyph);}
    const copy=document.createElement("span");copy.className="dc-mention-option-copy";const name=document.createElement("strong");name.textContent=(item.kind==="channel"?"#":"@")+item.label;const detail=document.createElement("small");detail.textContent=item.detail||"";copy.append(name,detail);button.append(copy);
    button.addEventListener("mousedown",event=>event.preventDefault());
    button.addEventListener("click",()=>dcInsertMention(item));
    root.append(button);
  });
}
function dcUpdateMentionPicker(input){
  const root=document.getElementById("dcMentionPicker");if(!root||!input||input.disabled)return dcCloseMentionPicker();
  const caret=input.selectionStart??input.value.length;
  const before=input.value.slice(0,caret);
  const match=before.match(/(^|\s)([@#])(&?[^\s@#]*)$/u);
  if(!match)return dcCloseMentionPicker();
  const isRole=match[2]==="@"&&match[3].startsWith("&");
  const type=match[2]==="#"?"#":isRole?"@&":"@";
  const query=isRole?match[3].slice(1):match[3];
  dcMentionTrigger={type,start:caret-(match[2].length+match[3].length),end:caret};
  dcMentionPickerItems=dcMentionCandidates(type,query);
  dcMentionPickerIndex=0;
  dcRenderMentionPicker();
}
function dcInsertMention(item){
  const input=document.getElementById("dcMessageInput");if(!input||!dcMentionTrigger)return;
  const start=dcMentionTrigger.start,end=dcMentionTrigger.end;
  const token=item.kind==="user"?"<@"+item.id+">":item.kind==="role"?"<@&"+item.id+">":item.kind==="everyone"?"@everyone":item.kind==="here"?"@here":"<#"+item.id+">";
  input.value=input.value.slice(0,start)+token+" "+input.value.slice(end);
  const caret=start+token.length+1;input.setSelectionRange(caret,caret);input.focus();dcCloseMentionPicker();dcUpdateMentionPicker(input);
}
function dcHandleMentionKeydown(event,input){
  if(!dcMentionPickerItems.length)return false;
  if(event.key==="ArrowDown"){event.preventDefault();dcMentionPickerIndex=(dcMentionPickerIndex+1)%dcMentionPickerItems.length;dcRenderMentionPicker();return true;}
  if(event.key==="ArrowUp"){event.preventDefault();dcMentionPickerIndex=(dcMentionPickerIndex-1+dcMentionPickerItems.length)%dcMentionPickerItems.length;dcRenderMentionPicker();return true;}
  if(event.key==="Enter"||event.key==="Tab"){event.preventDefault();dcInsertMention(dcMentionPickerItems[dcMentionPickerIndex]);return true;}
  if(event.key==="Escape"){event.preventDefault();dcCloseMentionPicker();return true;}
  return false;
}
function dcCloseEmojiPicker(){
  const root=document.getElementById("dcEmojiPicker");if(root){root.hidden=true;root.replaceChildren();}
}
function dcToggleEmojiPicker(){
  const root=document.getElementById("dcEmojiPicker"),input=document.getElementById("dcMessageInput");if(!root||!input)return;
  if(!root.hidden){dcCloseEmojiPicker();return;}
  root.replaceChildren();
  const insert=value=>{const start=input.selectionStart??input.value.length,end=input.selectionEnd??start;input.value=input.value.slice(0,start)+value+input.value.slice(end);const caret=start+value.length;input.setSelectionRange(caret,caret);input.focus();dcCloseEmojiPicker();};
  const heading=document.createElement("div");heading.className="dc-reaction-emoji-heading";heading.textContent="ОБЫЧНЫЕ ЭМОДЗИ";root.append(heading);
  dcEmojiChoices.forEach(emoji=>{const button=document.createElement("button");button.type="button";button.textContent=emoji;button.addEventListener("click",()=>insert(emoji));root.append(button);});
  if(dcActiveGuild?.id){
    const serverHeading=document.createElement("div");serverHeading.className="dc-reaction-emoji-heading dc-composer-server-emoji-heading";serverHeading.textContent="ЭМОДЗИ СЕРВЕРА";root.append(serverHeading);
    const state=document.createElement("div");state.className="dc-reaction-emoji-state";state.textContent="Загрузка…";root.append(state);
    dcLoadGuildEmojis(dcActiveGuild.id).then(emojis=>{state.remove();if(!emojis.length){const empty=document.createElement("div");empty.className="dc-reaction-emoji-state";empty.textContent="Нет доступных эмодзи.";root.append(empty);return;}emojis.forEach(emoji=>root.append(dcMakeCustomEmojiButton(emoji,selected=>insert(selected.markup))));}).catch(error=>{state.textContent=error.message;});
  }
  root.hidden=false;
}
const dcStatusLabels={online:"В сети",idle:"Не активен",dnd:"Не беспокоить",offline:"Не в сети"};
function dcStatusClass(status){return ["online","idle","dnd"].includes(status)?status:"offline";}
function dcEnsureProfileModal(){
  let modal=document.getElementById("dcProfileModal");
  if(!modal){
    modal=document.createElement("div");modal.id="dcProfileModal";modal.className="dc-profile-backdrop";
    modal.addEventListener("click",event=>{if(event.target===modal)modal.remove();});
    document.body.append(modal);
  }
  return modal;
}
function dcOpenBasicProfile(user,notice=""){
  if(!user?.id)return;
  const modal=dcEnsureProfileModal();modal.replaceChildren();
  const card=document.createElement("section");card.className="dc-profile-card dc-basic-profile-card";card.setAttribute("role","dialog");card.setAttribute("aria-modal","true");
  const close=document.createElement("button");close.className="dc-profile-close";close.type="button";close.textContent="×";close.setAttribute("aria-label","Закрыть профиль");close.addEventListener("click",()=>modal.remove());card.append(close);
  const banner=document.createElement("div");banner.className="dc-profile-banner";card.append(banner);
  const avatar=document.createElement("div");avatar.className="dc-profile-avatar";avatar.innerHTML=dcAvatar(user);
  const status=document.createElement("i");status.className="dc-status-dot "+dcStatusClass(user.status);avatar.append(status);card.append(avatar);
  const name=document.createElement("h2");name.textContent=user.global_name||user.display_name||user.username||"Пользователь Discord";card.append(name);
  const tag=document.createElement("p");tag.className="dc-profile-tag";tag.textContent="@"+(user.username||"unknown")+" · "+user.id;card.append(tag);
  const statusLine=document.createElement("div");statusLine.className="dc-profile-status";const dot=document.createElement("i");dot.className="dc-status-dot "+dcStatusClass(user.status);const statusText=document.createElement("span");statusText.textContent=dcStatusLabels[dcStatusClass(user.status)]||"Не в сети";if(user.bot)statusText.textContent+=" · Бот";statusLine.append(dot,statusText);card.append(statusLine);
  const about=document.createElement("div");about.className="dc-profile-section";const aboutTitle=document.createElement("h3");aboutTitle.textContent="ПРОФИЛЬ DISCORD";const aboutText=document.createElement("p");aboutText.textContent=user.bot?"Бот Discord":"Пользователь Discord";about.append(aboutTitle,aboutText);
  if(notice){const note=document.createElement("p");note.className="dc-profile-role-hint";note.textContent=notice;about.append(note);}
  card.append(about);
  const details=document.createElement("div");details.className="dc-profile-section";const detailsTitle=document.createElement("h3");detailsTitle.textContent="ИНФОРМАЦИЯ";const id=document.createElement("p");id.textContent="ID: "+user.id;details.append(detailsTitle,id);card.append(details);
  const footer=document.createElement("div");footer.className="dc-profile-actions";
  const copy=document.createElement("button");copy.type="button";copy.textContent="Копировать ID";copy.addEventListener("click",async()=>{try{await navigator.clipboard.writeText(String(user.id));copy.textContent="Скопировано";}catch{copy.textContent="Не удалось скопировать";}});
  const dm=document.createElement("button");dm.type="button";dm.textContent="Открыть ЛС";dm.addEventListener("click",()=>{modal.remove();dcActiveChannel=null;dcActiveGuild=null;dcActiveDmChannelId=null;dcSetMode("dm");dcOpenConversation(user);});
  footer.append(copy,dm);card.append(footer);modal.append(card);
  document.addEventListener("keydown",function esc(event){if(event.key==="Escape"){modal.remove();document.removeEventListener("keydown",esc);}});
}
async function dcOpenMentionProfile(user){
  if(!user?.id)return;
  if(!dcActiveGuild){dcOpenBasicProfile(user);return;}
  const cached=dcMemberCache.find(member=>String(member.id)===String(user.id));
  if(cached){dcOpenProfile({...user,...cached});return;}
  try{
    const data=await apiGet("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/members/"+encodeURIComponent(user.id));
    if(!dcActiveGuild){dcOpenBasicProfile(user);return;}
    dcOpenProfile({...user,...(data.member||{})},data.roles||dcMemberRoleCache);
  }catch(error){
    dcOpenBasicProfile(user,"Показаны доступные данные. Не удалось загрузить сведения участника сервера: "+error.message);
  }
}
function dcOpenProfile(member,roleDefinitions=dcMemberRoleCache){
  if(!member?.id||!dcActiveGuild)return;
  let modal=document.getElementById("dcProfileModal");
  if(!modal){modal=document.createElement("div");modal.id="dcProfileModal";modal.className="dc-profile-backdrop";modal.addEventListener("click",event=>{if(event.target===modal)modal.remove();});document.body.append(modal);}
  modal.replaceChildren();
  const card=document.createElement("section");card.className="dc-profile-card";card.setAttribute("role","dialog");card.setAttribute("aria-modal","true");
  const close=document.createElement("button");close.className="dc-profile-close";close.type="button";close.textContent="×";close.addEventListener("click",()=>modal.remove());card.append(close);
  const banner=document.createElement("div");banner.className="dc-profile-banner";card.append(banner);
  const avatar=document.createElement("div");avatar.className="dc-profile-avatar";avatar.innerHTML=dcAvatar(member);const status=document.createElement("i");status.className="dc-status-dot "+dcStatusClass(member.status);avatar.append(status);card.append(avatar);
  const name=document.createElement("h2");name.textContent=member.global_name||member.username;card.append(name);
  const tag=document.createElement("p");tag.className="dc-profile-tag";tag.textContent="@"+member.username+" · "+member.id;card.append(tag);
  const statusLine=document.createElement("div");statusLine.className="dc-profile-status";const dot=document.createElement("i");dot.className="dc-status-dot "+dcStatusClass(member.status);const statusText=document.createElement("span");statusText.textContent=dcStatusLabels[dcStatusClass(member.status)]||"Не в сети";if(member.activity){statusText.textContent+=" · "+member.activity;}statusLine.append(dot,statusText);card.append(statusLine);
  const about=document.createElement("div");about.className="dc-profile-section";const aboutTitle=document.createElement("h3");aboutTitle.textContent="УЧАСТНИК СЕРВЕРА";const aboutText=document.createElement("p");aboutText.textContent=(member.bot?"Бот":"Участник")+" · "+(member.joined_at?"На сервере с "+new Date(member.joined_at).toLocaleDateString("ru-RU"):"");about.append(aboutTitle,aboutText);card.append(about);
  const rolesSection=document.createElement("div");rolesSection.className="dc-profile-section";const rolesTitle=document.createElement("h3");rolesTitle.textContent="РОЛИ · УПРАВЛЕНИЕ";rolesSection.append(rolesTitle);
  const roleList=document.createElement("div");roleList.className="dc-profile-roles";
  const assigned=new Set((member.role_ids||[]).map(String));
  const sortedProfileRoles=[...(roleDefinitions||dcMemberRoleCache||[])].sort((a,b)=>(Number(b.position)||0)-(Number(a.position)||0));
  sortedProfileRoles.forEach(role=>{
    const manageable=role.manageable===true;
    const label=document.createElement("label");label.className="dc-profile-role"+(manageable?"":" dc-profile-role-unmanageable");
    const checkbox=document.createElement("input");checkbox.type="checkbox";checkbox.checked=assigned.has(String(role.id));checkbox.disabled=!manageable;
    if(!manageable)checkbox.title=role.managed?"Роль управляется интеграцией Discord.":"Бот не может управлять этой ролью: проверь Manage Roles и иерархию ролей.";
    checkbox.addEventListener("change",async()=>{
      checkbox.disabled=true;
      try{await apiPost("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/members/"+encodeURIComponent(member.id)+"/roles",{role_id:String(role.id),action:checkbox.checked?"add":"remove"});const fresh=await apiGet("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/members/"+encodeURIComponent(member.id));dcMemberCache=dcMemberCache.map(item=>String(item.id)===String(member.id)?fresh.member:item);dcMemberCacheByGuild.set(dcActiveGuild.id,dcMemberCache);modal.remove();dcOpenProfile(fresh.member,fresh.roles||roleDefinitions);}
      catch(error){checkbox.checked=!checkbox.checked;alert(error.message);}
      finally{checkbox.disabled=!manageable;}
    });
    const color=document.createElement("i");color.className="dc-profile-role-color"+(role.style==="holographic"?" dc-role-color-holographic":"");dcApplyRoleColor(color,role,false);
    const roleIcon=role.icon_url?document.createElement("img"):document.createElement("span");roleIcon.className="dc-profile-role-icon";if(role.icon_url){roleIcon.src=role.icon_url;roleIcon.alt="";}else roleIcon.textContent=role.unicode_emoji||"";
    const roleName=document.createElement("span");roleName.textContent=role.name;label.append(checkbox,color);if(role.icon_url||role.unicode_emoji)label.append(roleIcon);label.append(roleName);roleList.append(label);
  });
  if(!roleList.children.length){const note=document.createElement("p");note.textContent="На этом сервере не найдено пользовательских ролей.";roleList.append(note);}
  else if(!sortedProfileRoles.some(role=>role.manageable===true)){const note=document.createElement("p");note.className="dc-profile-role-hint";note.textContent="Все роли показаны, но бот не может менять их. Нужны Manage Roles и высшая роль бота выше ролей, которыми нужно управлять.";roleList.append(note);}
  rolesSection.append(roleList);card.append(rolesSection);
  const footer=document.createElement("div");footer.className="dc-profile-actions";const dm=document.createElement("button");dm.type="button";dm.textContent="Открыть ЛС";dm.addEventListener("click",()=>{modal.remove();dcActiveChannel=null;dcSetMode("dm");dcOpenConversation(member);});footer.append(dm);card.append(footer);
  modal.append(card);document.addEventListener("keydown",function esc(event){if(event.key==="Escape"){modal.remove();document.removeEventListener("keydown",esc);}});
}
const dcAccessibilityDefaults={roleColorMode:"name",saturation:100,highContrast:false,reducedMotion:false,autoplayGifs:true,stickerAnimation:"interaction",animatedEmoji:true};
function dcReadAccessibilityPreferences(){
  try{return {...dcAccessibilityDefaults,...JSON.parse(localStorage.getItem("gastworld-discord-accessibility")||"{}")};}
  catch{return {...dcAccessibilityDefaults};}
}
let dcAccessibilityPrefs=dcReadAccessibilityPreferences();
function dcSaveAccessibilityPreferences(){
  try{localStorage.setItem("gastworld-discord-accessibility",JSON.stringify(dcAccessibilityPrefs));}catch{}
  dcApplyAccessibilityPreferences();
}
function dcRefreshAccessibilityViews(){
  if(dcActiveGuild)dcRenderGuildMembers();
  if(dcActiveChannel)dcOpenGuildChannel(dcActiveChannel,true);
  else if(dcActiveUser)dcOpenConversation(dcActiveUser,true);
}
function dcApplyAccessibilityPreferences(){
  const app=document.querySelector(".dc-live-app");if(!app)return;
  app.style.setProperty("--dc-saturation",Math.max(0,Math.min(150,Number(dcAccessibilityPrefs.saturation)||100))+"%");
  app.style.filter="saturate("+Math.max(0,Math.min(150,Number(dcAccessibilityPrefs.saturation)||100))+"%)";
  app.classList.toggle("dc-high-contrast",!!dcAccessibilityPrefs.highContrast);
  app.classList.toggle("dc-reduced-motion",!!dcAccessibilityPrefs.reducedMotion);
}
function dcRoleStyleBackground(role){
  const primary=role?.color_hex||role?.color||(role?.style==="holographic"?"#A9C9FF":"#99AAB5");
  const secondary=role?.secondary_color_hex||role?.secondary_color||(role?.style==="holographic"?"#FFBBEC":null);
  const tertiary=role?.tertiary_color_hex||role?.tertiary_color||(role?.style==="holographic"?"#FFC3A0":null);
  if(role?.style==="holographic"&&secondary&&tertiary)return "linear-gradient(115deg,"+primary+" 0%,"+secondary+" 48%,"+tertiary+" 100%)";
  if(role?.style==="gradient"&&secondary)return "linear-gradient(110deg,"+primary+" 0%,"+secondary+" 100%)";
  return primary;
}
function dcApplyRoleColor(element,role,asText=false){
  if(!element||!role)return;
  const mode=dcAccessibilityPrefs.roleColorMode||"name";
  const background=dcRoleStyleBackground(role);
  if(asText&&(mode==="none"||mode==="dot")){
    element.style.color="";element.style.background="";element.style.backgroundImage="none";element.style.backgroundClip="";element.style.webkitBackgroundClip="";element.style.webkitTextFillColor="";element.classList.remove("dc-holographic-text");return;
  }
  if(!asText)element.classList.toggle("dc-role-color-holographic",role.style==="holographic"&&!dcAccessibilityPrefs.reducedMotion);
  if(asText&&mode==="name"&&role.style!=="solid"){
    element.style.color="transparent";element.style.background="";element.style.backgroundImage=background;element.style.backgroundClip="text";element.style.webkitBackgroundClip="text";element.style.webkitTextFillColor="transparent";
    if(role.style==="holographic"&&!dcAccessibilityPrefs.reducedMotion)element.classList.add("dc-holographic-text");else element.classList.remove("dc-holographic-text");
    return;
  }
  if(asText&&mode==="name"){element.style.background="";element.style.backgroundImage="none";element.style.backgroundClip="";element.style.webkitBackgroundClip="";element.style.webkitTextFillColor="";element.style.color=role.color_hex||role.color||"";element.classList.remove("dc-holographic-text");return;}
  element.style.backgroundImage=background;element.style.background=background;
}
function dcOpenAccessibilitySettings(){
  document.getElementById("dcAccessibilityModal")?.remove();
  const modal=document.createElement("div");modal.id="dcAccessibilityModal";modal.className="dc-settings-backdrop";
  const card=document.createElement("section");card.className="dc-accessibility-card";card.setAttribute("role","dialog");card.setAttribute("aria-modal","true");
  const head=document.createElement("header");head.className="dc-settings-header";const intro=document.createElement("div");intro.className="dc-settings-heading";
  const eyebrow=document.createElement("span");eyebrow.textContent="GASTWORLD • DISPLAY";const title=document.createElement("h2");title.textContent="Специальные возможности";const sub=document.createElement("p");sub.textContent="Локальные настройки отображения этой панели.";
  intro.append(eyebrow,title,sub);const close=document.createElement("button");close.type="button";close.className="dc-settings-close";close.textContent="×";close.addEventListener("click",()=>modal.remove());head.append(intro,close);
  const body=document.createElement("div");body.className="dc-accessibility-body";
  const roleMode=document.createElement("label");roleMode.className="dc-settings-field";const modeTitle=document.createElement("span");modeTitle.textContent="Отображение цветов ролей";
  const select=document.createElement("select");[["name","Показывать цвет в имени"],["dot","Показывать цвет рядом с именем"],["none","Не показывать цвет роли"]].forEach(([value,label])=>{const option=document.createElement("option");option.value=value;option.textContent=label;select.append(option);});select.value=dcAccessibilityPrefs.roleColorMode;select.addEventListener("change",()=>{dcAccessibilityPrefs.roleColorMode=select.value;dcSaveAccessibilityPreferences();dcRefreshAccessibilityViews();});roleMode.append(modeTitle,select);body.append(roleMode);
  const saturation=document.createElement("label");saturation.className="dc-settings-field dc-accessibility-slider";const saturationTitle=document.createElement("span");saturationTitle.textContent="Насыщенность цветов";
  const slider=document.createElement("input");slider.type="range";slider.min="0";slider.max="150";slider.step="5";slider.value=String(dcAccessibilityPrefs.saturation);const saturationValue=document.createElement("strong");saturationValue.textContent=slider.value+"%";
  slider.addEventListener("input",()=>{dcAccessibilityPrefs.saturation=Number(slider.value);saturationValue.textContent=slider.value+"%";dcSaveAccessibilityPreferences();});saturation.append(saturationTitle,slider,saturationValue);body.append(saturation);
  const toggle=(labelText,key,description)=>{
    const label=document.createElement("label");label.className="dc-accessibility-toggle";const copy=document.createElement("span");const strong=document.createElement("strong");strong.textContent=labelText;const small=document.createElement("small");small.textContent=description;copy.append(strong,small);const input=document.createElement("input");input.type="checkbox";input.checked=!!dcAccessibilityPrefs[key];input.addEventListener("change",()=>{dcAccessibilityPrefs[key]=input.checked;dcSaveAccessibilityPreferences();dcRefreshAccessibilityViews();});label.append(copy,input);body.append(label);
  };
  toggle("Высокая контрастность","highContrast","Усиливает контраст границ, текста и интерактивных элементов.");
  toggle("Уменьшить движение","reducedMotion","Отключает декоративную анимацию и переливание в этой панели.");
  toggle("Автоматически воспроизводить GIF","autoplayGifs","При отключении GIF открываются только после нажатия.");
  toggle("Воспроизводить анимированные эмодзи","animatedEmoji","При отключении вместо анимации используется статичное изображение эмодзи.");
  const stickerLabel=document.createElement("label");stickerLabel.className="dc-settings-field";const stickerTitle=document.createElement("span");stickerTitle.textContent="Анимация стикеров";
  const stickerSelect=document.createElement("select");[["always","Всегда анимировать"],["interaction","Анимировать при взаимодействии"],["never","Никогда не анимировать"]].forEach(([value,label])=>{const option=document.createElement("option");option.value=value;option.textContent=label;stickerSelect.append(option);});
  stickerSelect.value=dcAccessibilityPrefs.stickerAnimation;stickerSelect.addEventListener("change",()=>{dcAccessibilityPrefs.stickerAnimation=stickerSelect.value;dcSaveAccessibilityPreferences();dcRefreshAccessibilityViews();});
  stickerLabel.append(stickerTitle,stickerSelect);body.append(stickerLabel);
  const foot=document.createElement("p");foot.className="dc-accessibility-footnote";foot.textContent="Эти параметры меняют отображение GastWorld в этом браузере. Они не изменяют настройки Discord и не влияют на других участников.";
  body.append(foot);card.append(head,body);modal.append(card);modal.addEventListener("click",event=>{if(event.target===modal)modal.remove();});document.body.append(modal);
  dcApplyAccessibilityPreferences();
}
function dcRenderGuildMembers(){
  const root=document.getElementById("dcMemberList"),search=document.getElementById("dcMemberSearch"),count=document.getElementById("dcMemberCount");if(!root)return;
  const query=(search?.value||"").trim().toLocaleLowerCase("ru");
  const members=dcMemberCache.filter(member=>((member.global_name||"")+" "+(member.username||"")+" "+(member.id||"")).toLocaleLowerCase("ru").includes(query));
  root.replaceChildren();
  const onlineTotal=dcMemberCache.filter(member=>dcStatusClass(member.status)!=="offline").length;
  if(count)count.textContent=(query?members.length+" / "+dcMemberCache.length:String(dcMemberCache.length))+" · "+onlineTotal+" в сети";
  if(!members.length){const empty=document.createElement("div");empty.className="dc-live-empty";empty.textContent=query?"Участники не найдены.":"На сервере нет участников для отображения.";root.append(empty);return;}
  const onlineMembers=members.filter(member=>dcStatusClass(member.status)!=="offline");
  const offlineMembers=members.filter(member=>dcStatusClass(member.status)==="offline");
  const displayRoles=(dcMemberRoleCache||[]).filter(role=>role.hoist===true).sort((a,b)=>(Number(b.position)||0)-(Number(a.position)||0));
  const groups=new Map(),ungrouped=[];
  for(const member of onlineMembers){
    const roleIds=new Set((member.role_ids||[]).map(id=>String(id)));
    const primary=displayRoles.find(role=>roleIds.has(String(role.id)));
    if(primary){if(!groups.has(String(primary.id)))groups.set(String(primary.id),[]);groups.get(String(primary.id)).push(member);}
    else ungrouped.push(member);
  }
  const appendGroup=(label,items,roleStyle=null)=>{
    if(!items.length)return;
    const online=items.filter(member=>dcStatusClass(member.status)!=="offline").length;
    const heading=document.createElement("div");heading.className="dc-member-group-title";heading.textContent=label+" — "+items.length+(online?" · "+online+" в сети":"");
    if(roleStyle)dcApplyRoleColor(heading,roleStyle,true);root.append(heading);
    items.sort((a,b)=>(a.global_name||a.username||"").localeCompare(b.global_name||b.username||"","ru"));
    items.forEach(member=>{
      const button=document.createElement("button");button.type="button";button.className="dc-member dc-member-button";button.title=(member.global_name||member.username)+" · @"+member.username;
      const avatar=document.createElement("span");avatar.className="dc-member-avatar-wrap";avatar.innerHTML=dcAvatar(member,"dc-member-avatar");const status=document.createElement("i");status.className="dc-status-dot "+dcStatusClass(member.status);avatar.append(status);button.append(avatar);
      const info=document.createElement("span");info.className="dc-member-copy";const name=document.createElement("strong");name.textContent=member.global_name||member.username;
      const assignedRoleIds=new Set((member.role_ids||[]).map(id=>String(id)));
      const highestColoredRole=[...(dcMemberRoleCache||[])].filter(role=>assignedRoleIds.has(String(role.id))&&(role.color_hex||role.secondary_color_hex)).sort((a,b)=>(Number(b.position)||0)-(Number(a.position)||0))[0];
      if(highestColoredRole&&dcAccessibilityPrefs.roleColorMode==="name")dcApplyRoleColor(name,highestColoredRole,true);
      else if(highestColoredRole&&dcAccessibilityPrefs.roleColorMode==="dot"){const roleDot=document.createElement("i");roleDot.className="dc-member-role-color";dcApplyRoleColor(roleDot,highestColoredRole,false);info.append(roleDot);}
      const handle=document.createElement("small");handle.textContent="@"+member.username;info.append(name,handle);button.append(info);
      button.addEventListener("click",()=>dcOpenProfile(member));root.append(button);
    });
  };
  displayRoles.forEach(role=>appendGroup(role.name,groups.get(String(role.id))||[],role));
  appendGroup("В СЕТИ",ungrouped.filter(member=>!member.bot),"");
  appendGroup("БОТЫ",ungrouped.filter(member=>member.bot),"");
  // Discord-style offline section is deliberately rendered last, regardless of role/hoist assignments.
  appendGroup("НЕ В СЕТИ",offlineMembers,"");
}
async function dcOpenServerSettings(){
  if(!dcActiveGuild?.id)return;
  const guild=dcActiveGuild;
  const button=document.getElementById("dcServerSettingsButton");
  if(button){button.disabled=true;button.textContent="…";}
  try{
    const data=await apiGet("/api/discord/guilds/"+encodeURIComponent(guild.id)+"/settings");
    if(dcActiveGuild?.id!==guild.id)return;
    dcRenderServerSettings(data);
  }catch(error){if(typeof showToast==="function")showToast(error.message);else alert(error.message);}
  finally{if(button){button.disabled=false;button.textContent="⚙";}}
}
function dcRenderServerSettings(data){
  document.getElementById("dcServerSettingsModal")?.remove();
  const modal=document.createElement("div");modal.id="dcServerSettingsModal";modal.className="dc-settings-backdrop";
  const card=document.createElement("section");card.className="dc-settings-card dc-settings-discord-card";card.setAttribute("role","dialog");card.setAttribute("aria-modal","true");
  const head=document.createElement("header");head.className="dc-settings-header";
  const heading=document.createElement("div");heading.className="dc-settings-heading";
  const eyebrow=document.createElement("span");eyebrow.textContent="GASTWORLD • SERVER SETTINGS";
  const title=document.createElement("h2");title.textContent="Настройки сервера";
  const sub=document.createElement("p");sub.textContent=data.guild?.name||dcActiveGuild?.name||"Discord";
  heading.append(eyebrow,title,sub);
  const close=document.createElement("button");close.type="button";close.className="dc-settings-close";close.textContent="×";close.title="Закрыть";close.addEventListener("click",()=>modal.remove());
  head.append(heading,close);

  const layout=document.createElement("div");layout.className="dc-settings-layout";
  const sidebar=document.createElement("aside");sidebar.className="dc-settings-sidebar";
  const main=document.createElement("main");main.className="dc-settings-content";
  layout.append(sidebar,main);

  const navSections=[
    {title:"НАСТРОЙКИ СЕРВЕРА",items:[["overview","Обзор","▦",true],["roles","Роли","♙",true],["channels","Каналы и категории","#",true],["members","Участники","♧",true],["invites","Приглашения","↗",true]]},
    {title:"МОДЕРАЦИЯ",items:[["safety","Настройка безопасности","⛨",true],["audit","Журнал аудита","≋",true],["automod","AutoMod","◇",true]]},
    {title:"СЕРВИСЫ",items:[["integrations","Интеграции","⌘",true],["emoji","Эмодзи и стикеры","☺",true],["events","События","◷",true]]}
  ];
  const navButtons=new Map();
  navSections.forEach(group=>{
    const block=document.createElement("div");block.className="dc-settings-nav-group";
    const label=document.createElement("div");label.className="dc-settings-nav-label";label.textContent=group.title;block.append(label);
    group.items.forEach(([key,text,icon,enabled])=>{
      const button=document.createElement("button");button.type="button";button.className="dc-settings-nav-item";button.disabled=!enabled;button.title=enabled?text:"Этот раздел ещё не реализован.";
      const symbol=document.createElement("span");symbol.textContent=icon;const name=document.createElement("span");name.textContent=text;button.append(symbol,name);
      if(!enabled){const tag=document.createElement("small");tag.textContent="Скоро";button.append(tag);}
      navButtons.set(key,button);block.append(button);
    });
    sidebar.append(block);
  });

  const renderOverview=()=>{
    main.replaceChildren();
    const pageHead=document.createElement("div");pageHead.className="dc-settings-page-heading";
    const pageTitle=document.createElement("h3");pageTitle.textContent="Обзор";
    const pageDesc=document.createElement("p");pageDesc.textContent="Основные параметры сервера и безопасности участников.";
    pageHead.append(pageTitle,pageDesc);main.append(pageHead);
    const stats=document.createElement("div");stats.className="dc-settings-stats";
    [["УЧАСТНИКИ",data.guild?.member_count??"—"],["РОЛИ",data.guild?.roles_count??"—"],["КАНАЛЫ",data.guild?.channels_count??"—"]].forEach(([label,value])=>{const item=document.createElement("div");const small=document.createElement("small");small.textContent=label;const strong=document.createElement("strong");strong.textContent=String(value);item.append(small,strong);stats.append(item);});
    main.append(stats);
    const form=document.createElement("form");form.className="dc-settings-form";
    const section=document.createElement("section");section.className="dc-settings-section";
    const sectionTitle=document.createElement("h4");sectionTitle.textContent="ОБЩИЕ СВЕДЕНИЯ";section.append(sectionTitle);
    const fields=document.createElement("div");fields.className="dc-settings-fields";
    const makeInput=(labelText,name,value,options={})=>{
      const wrap=document.createElement("label");wrap.className="dc-settings-field"+(options.wide?" wide":"");
      const caption=document.createElement("span");caption.textContent=labelText;
      const input=document.createElement(options.multiline?"textarea":"input");if(!options.multiline)input.type="text";
      input.name=name;input.value=value??"";if(options.maxLength)input.maxLength=options.maxLength;
      if(options.multiline){input.rows=3;input.maxLength=options.maxLength||120;}
      wrap.append(caption,input);fields.append(wrap);return input;
    };
    const makeSelect=(labelText,name,value,options,wide=false)=>{
      const wrap=document.createElement("label");wrap.className="dc-settings-field"+(wide?" wide":"");
      const caption=document.createElement("span");caption.textContent=labelText;
      const select=document.createElement("select");select.name=name;
      options.forEach(([optionValue,optionLabel])=>{const option=document.createElement("option");option.value=String(optionValue);option.textContent=optionLabel;select.append(option);});
      select.value=String(value??"");wrap.append(caption,select);fields.append(wrap);return select;
    };
    const settings=data.settings||{},textChannels=data.text_channels||[],voiceChannels=data.voice_channels||[];
    makeInput("Название сервера","name",data.guild?.name,{maxLength:100});
    makeInput("Описание сервера","description",data.guild?.description,{maxLength:120,multiline:true,wide:true});
    section.append(fields);form.append(section);
    const safety=document.createElement("section");safety.className="dc-settings-section";
    const safetyTitle=document.createElement("h4");safetyTitle.textContent="БЕЗОПАСНОСТЬ И УВЕДОМЛЕНИЯ";safety.append(safetyTitle);
    const safetyFields=document.createElement("div");safetyFields.className="dc-settings-fields";
    const originalFields=fields;
    // Reuse the same input builders for the second section without detaching fields already in the first one.
    const appendSelect=(parent,labelText,name,value,options,wide=false)=>{
      const wrap=document.createElement("label");wrap.className="dc-settings-field"+(wide?" wide":"");
      const caption=document.createElement("span");caption.textContent=labelText;
      const select=document.createElement("select");select.name=name;
      options.forEach(([optionValue,optionLabel])=>{const option=document.createElement("option");option.value=String(optionValue);option.textContent=optionLabel;select.append(option);});
      select.value=String(value??"");wrap.append(caption,select);parent.append(wrap);return select;
    };
    appendSelect(safetyFields,"Уровень проверки","verification_level",settings.verification_level,[[0,"Без ограничений"],[1,"Низкий — подтверждённая почта"],[2,"Средний — аккаунт старше 5 минут"],[3,"Высокий — участник на сервере 10 минут"],[4,"Самый высокий — подтверждённый телефон"]]);
    appendSelect(safetyFields,"Фильтр контента","explicit_content_filter",settings.explicit_content_filter,[[0,"Не сканировать"],[1,"Участники без ролей"],[2,"Все участники"]]);
    appendSelect(safetyFields,"Уведомления по умолчанию","default_notifications",settings.default_notifications,[[0,"Все сообщения"],[1,"Только упоминания"]]);
    appendSelect(safetyFields,"Время до AFK","afk_timeout",settings.afk_timeout,[[60,"1 минута"],[300,"5 минут"],[900,"15 минут"],[1800,"30 минут"],[3600,"1 час"]]);
    const channelOptions=list=>[["","Не выбран"],...list.map(channel=>[channel.id,channel.name])];
    appendSelect(safetyFields,"AFK голосовой канал","afk_channel_id",settings.afk_channel_id,channelOptions(voiceChannels),true);
    appendSelect(safetyFields,"Системный канал","system_channel_id",settings.system_channel_id,channelOptions(textChannels),true);
    const community=(data.guild?.features||[]).includes("COMMUNITY");
    if(community){
      appendSelect(safetyFields,"Канал правил","rules_channel_id",settings.rules_channel_id,channelOptions(textChannels),true);
      appendSelect(safetyFields,"Канал обновлений Discord","public_updates_channel_id",settings.public_updates_channel_id,channelOptions(textChannels),true);
      appendSelect(safetyFields,"Канал уведомлений безопасности","safety_alerts_channel_id",settings.safety_alerts_channel_id,channelOptions(textChannels),true);
    }
    safety.append(safetyFields);form.append(safety);
    const featureStrip=document.createElement("div");featureStrip.className="dc-settings-features";
    const featureTitle=document.createElement("strong");featureTitle.textContent="ВОЗМОЖНОСТИ СЕРВЕРА";featureStrip.append(featureTitle);
    const features=data.guild?.features||[];
    if(features.length){features.forEach(feature=>{const tag=document.createElement("span");tag.textContent=feature.replaceAll("_"," ").toLowerCase();featureStrip.append(tag);});}
    else{const note=document.createElement("span");note.textContent="Дополнительные функции сервера не включены.";featureStrip.append(note);}
    form.append(featureStrip);
    const permissionNote=document.createElement("div");permissionNote.className="dc-settings-permission";
    if(!data.actor_can_edit)permissionNote.textContent="У твоего Discord-аккаунта нет права «Управлять сервером». Настройки доступны только для просмотра.";
    else if(!data.bot_can_edit)permissionNote.textContent="У бота нет права «Управлять сервером». Выдать это право боту можно в настройках ролей Discord.";
    else permissionNote.textContent="Изменения сохраняются непосредственно в Discord от имени бота с серверной проверкой прав.";
    form.append(permissionNote);
    const status=document.createElement("p");status.className="dc-settings-status";status.setAttribute("aria-live","polite");form.append(status);
    const footer=document.createElement("footer");footer.className="dc-settings-footer";
    const save=document.createElement("button");save.type="submit";save.className="dc-settings-save";save.textContent="Сохранить изменения";save.disabled=!data.can_edit;footer.append(save);form.append(footer);
    form.querySelectorAll("input,textarea,select").forEach(input=>input.disabled=!data.can_edit);
    form.addEventListener("submit",async event=>{
      event.preventDefault();if(!data.can_edit||save.disabled)return;
      save.disabled=true;save.textContent="Сохраняем…";status.textContent="";
      const fieldValue=name=>form.querySelector('[name="'+name+'"]')?.value??"";
      const payload={
        name:fieldValue("name").trim(),
        description:fieldValue("description").trim(),
        verification_level:Number(fieldValue("verification_level")),
        explicit_content_filter:Number(fieldValue("explicit_content_filter")),
        default_notifications:Number(fieldValue("default_notifications")),
        afk_timeout:Number(fieldValue("afk_timeout")),
        afk_channel_id:fieldValue("afk_channel_id")||null,
        system_channel_id:fieldValue("system_channel_id")||null
      };
      ["rules_channel_id","public_updates_channel_id","safety_alerts_channel_id"].forEach(key=>{if(form.querySelector('[name="'+key+'"]'))payload[key]=fieldValue(key)||null;});
      try{
        const response=await fetch("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/settings",{method:"PATCH",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
        const result=await response.json();if(!response.ok)throw new Error(result.detail||"Не удалось сохранить настройки.");
        if(typeof showToast==="function")showToast("Настройки сервера сохранены.");
        data=result;renderOverview();
      }catch(error){status.textContent=error.message;save.disabled=false;save.textContent="Повторить сохранение";}
    });
    main.append(form);
  };

  const permissionLabels={
    administrator:"Администратор",manage_guild:"Управлять сервером",view_audit_log:"Просмотр журнала аудита",
    manage_roles:"Управлять ролями",manage_channels:"Управлять каналами",manage_webhooks:"Управлять вебхуками",
    manage_expressions:"Управлять эмодзи и стикерами",manage_events:"Управлять событиями",manage_threads:"Управлять ветками",
    manage_messages:"Управлять сообщениями",manage_nicknames:"Управлять никами",create_instant_invite:"Создавать приглашения",
    change_nickname:"Изменять свой ник",kick_members:"Исключать участников",ban_members:"Банить участников",
    moderate_members:"Выдавать тайм-аут",view_channel:"Просматривать каналы",send_messages:"Отправлять сообщения",
    send_messages_in_threads:"Отправлять сообщения в ветках",send_tts_messages:"Отправлять TTS-сообщения",
    read_message_history:"Читать историю сообщений",mention_everyone:"Упоминать @everyone и роли",
    embed_links:"Встраивать ссылки",attach_files:"Прикреплять файлы",add_reactions:"Добавлять реакции",
    use_external_emojis:"Использовать внешние эмодзи",use_external_stickers:"Использовать внешние стикеры",
    use_application_commands:"Использовать команды приложений",create_public_threads:"Создавать публичные ветки",
    create_private_threads:"Создавать приватные ветки",connect:"Подключаться к голосовым каналам",
    speak:"Говорить",stream:"Передавать видео и экран",use_vad:"Использовать голосовую активацию",
    priority_speaker:"Приоритетный участник",mute_members:"Отключать микрофон участников",
    deafen_members:"Отключать звук участникам",move_members:"Перемещать участников",
    request_to_speak:"Запрашивать выступление",use_soundboard:"Использовать звуковую панель",
    use_external_sounds:"Использовать внешние звуки",send_voice_messages:"Отправлять голосовые сообщения",
    send_polls:"Создавать опросы",pin_messages:"Закреплять сообщения",bypass_slowmode:"Обходить медленный режим"
  };
  const permissionGroups=[
    {title:"ОБЩИЕ ПРАВА СЕРВЕРА",keys:["administrator","manage_guild","view_audit_log","manage_roles","manage_channels","manage_webhooks","manage_expressions","manage_events","manage_threads"]},
    {title:"УПРАВЛЕНИЕ УЧАСТНИКАМИ",keys:["create_instant_invite","change_nickname","manage_nicknames","kick_members","ban_members","moderate_members"]},
    {title:"ТЕКСТОВЫЕ КАНАЛЫ",keys:["view_channel","send_messages","send_messages_in_threads","read_message_history","embed_links","attach_files","add_reactions","mention_everyone","manage_messages","send_tts_messages","use_external_emojis","use_external_stickers","use_application_commands","create_public_threads","create_private_threads","pin_messages","send_polls","bypass_slowmode"]},
    {title:"ГОЛОСОВЫЕ КАНАЛЫ",keys:["connect","speak","stream","use_vad","priority_speaker","mute_members","deafen_members","move_members","request_to_speak","use_soundboard","use_external_sounds","send_voice_messages"]}
  ];

  const renderRoles=async()=>{
    main.replaceChildren();
    const pageHead=document.createElement("div");pageHead.className="dc-settings-page-heading";
    const pageTitle=document.createElement("h3");pageTitle.textContent="Роли";
    const pageDesc=document.createElement("p");pageDesc.textContent="Создавай роли, настраивай цвет, положение в иерархии и разрешения сервера.";
    pageHead.append(pageTitle,pageDesc);main.append(pageHead);
    const work=document.createElement("div");work.className="dc-roles-workspace";
    const listPane=document.createElement("aside");listPane.className="dc-roles-list-pane";
    const listTitle=document.createElement("div");listTitle.className="dc-roles-list-title";listTitle.textContent="РОЛИ СЕРВЕРА";
    const add=document.createElement("button");add.type="button";add.className="dc-role-create-button";add.textContent="＋ Создать роль";
    const roleList=document.createElement("div");roleList.className="dc-roles-list";
    listPane.append(listTitle,add,roleList);
    const editor=document.createElement("section");editor.className="dc-role-editor";
    work.append(listPane,editor);main.append(work);
    const hint=document.createElement("div");hint.className="dc-settings-permission";
    const refreshRoles=async(selectId)=>{
      roleList.textContent="Загрузка ролей…";
      const rolesData=await apiGet("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/roles");
      roleList.replaceChildren();
      const roles=rolesData.roles||[];
      const current=roles.find(role=>String(role.id)===String(selectId))||roles.find(role=>role.editable)||roles[0];
      roles.forEach(role=>{
        const item=document.createElement("button");item.type="button";item.className="dc-role-list-item"+(current&&String(current.id)===String(role.id)?" active":"");
        const color=document.createElement("i");color.className="dc-role-color-dot"+(role.style==="holographic"?" dc-role-color-holographic":"");dcApplyRoleColor(color,role,false);
        const name=document.createElement("span");name.textContent=role.is_default?"@everyone":role.name;
        if(role.icon_url){const icon=document.createElement("img");icon.className="dc-role-list-icon";icon.src=role.icon_url;icon.alt="";item.append(icon);}
        else if(role.unicode_emoji){const icon=document.createElement("span");icon.className="dc-role-list-emoji";icon.textContent=role.unicode_emoji;item.append(icon);}
        item.append(color,name);
        if(role.managed){const managed=document.createElement("small");managed.textContent="ИНТЕГРАЦИЯ";item.append(managed);}
        item.addEventListener("click",()=>refreshRoles(role.id));
        roleList.append(item);
      });
      add.disabled=!rolesData.can_create;
      add.title=rolesData.can_create?"Создать новую роль":"Нужны Manage Roles у тебя и у бота";
      if(current)renderRoleEditor(current,rolesData,refreshRoles);
      else editor.textContent="На сервере пока нет ролей.";
      if(!rolesData.actor_can_manage)hint.textContent="У твоего Discord-аккаунта нет права «Управлять ролями».";
      else if(!rolesData.bot_can_manage)hint.textContent="Боту требуется разрешение Manage Roles и роль выше ролей, которыми нужно управлять.";
      else hint.textContent="Иерархия Discord соблюдается: менять можно только роли ниже высшей роли администратора и бота.";
    };
    add.addEventListener("click",async()=>{
      add.disabled=true;add.textContent="Создаём…";
      try{
        const result=await apiPost("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/roles",{name:"Новая роль",color:"#99AAB5",style:"solid",secondary_color:"#FFBBEC",hoist:false,mentionable:false,permissions:{}});
        await refreshRoles(result.role?.id);
        await dcLoadGuildMembers(dcActiveGuild,true);
        if(typeof showToast==="function")showToast("Роль создана.");
      }catch(error){if(typeof showToast==="function")showToast(error.message);else alert(error.message);}
      finally{add.disabled=false;add.textContent="＋ Создать роль";}
    });
    const renderRoleEditor=(role,rolesData,refresh)=>{
      editor.replaceChildren();
      const isEditable=role.editable===true;
      const roleDisplayEditable=isEditable&&!role.is_default;
      let draft={name:role.name,color:role.color||"#000000",secondary_color:role.secondary_color||"#FFBBEC",style:role.style||"solid",icon_emoji:role.unicode_emoji||"",icon_data:null,remove_icon:false,position:Number(role.position)||1,hoist:!!role.hoist,mentionable:!!role.mentionable,permissions:{...(role.permissions||{})}};
      const top=document.createElement("div");top.className="dc-role-editor-top";
      const rolePreview=document.createElement("div");rolePreview.className="dc-role-editor-preview";
      const previewDot=document.createElement("i");previewDot.className="dc-role-color-dot";dcApplyRoleColor(previewDot,draft,false);
      const previewName=document.createElement("strong");previewName.textContent=role.is_default?"@everyone":draft.name;dcApplyRoleColor(previewName,draft,true);
      rolePreview.append(previewDot,previewName);
      const tag=document.createElement("span");tag.className="dc-role-position-tag";tag.textContent="Позиция #"+draft.position;
      top.append(rolePreview,tag);editor.append(top);
      const roleTabs=document.createElement("div");roleTabs.className="dc-role-tabs";
      const panel=document.createElement("div");panel.className="dc-role-tab-content";
      const tabNames=[["display","Отображение"],["permissions","Права доступа"],["members","Управление участниками"]];
      let activeTab="display";
      const tabButtons=new Map();
      const saveStatus=document.createElement("p");saveStatus.className="dc-settings-status";
      const footer=document.createElement("div");footer.className="dc-role-editor-footer";
      const deleteButton=document.createElement("button");deleteButton.type="button";deleteButton.className="dc-role-delete-button";deleteButton.textContent="Удалить роль";deleteButton.disabled=!isEditable||role.is_default;
      deleteButton.addEventListener("click",async()=>{
        if(!confirm("Удалить роль «"+role.name+"»? Это действие нельзя отменить."))return;
        deleteButton.disabled=true;
        try{await fetch("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/roles/"+encodeURIComponent(role.id),{method:"DELETE",credentials:"same-origin"}).then(async response=>{const result=await response.json();if(!response.ok)throw new Error(result.detail||"Не удалось удалить роль.");return result;});await refresh(null);await dcLoadGuildMembers(dcActiveGuild,true);if(typeof showToast==="function")showToast("Роль удалена.");}
        catch(error){saveStatus.textContent=error.message;deleteButton.disabled=false;}
      });
      const saveButton=document.createElement("button");saveButton.type="button";saveButton.className="dc-settings-save";saveButton.textContent="Сохранить изменения";saveButton.disabled=!isEditable;
      saveButton.addEventListener("click",async()=>{
        saveButton.disabled=true;saveButton.textContent="Сохраняем…";saveStatus.textContent="";
        try{
          const payload=role.is_default?{permissions:draft.permissions}:draft;
          const response=await fetch("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/roles/"+encodeURIComponent(role.id),{method:"PATCH",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
          const result=await response.json();if(!response.ok)throw new Error(result.detail||"Не удалось сохранить роль.");
          await refresh(result.role?.id);
          await dcLoadGuildMembers(dcActiveGuild,true);
          if(typeof showToast==="function")showToast("Настройки роли сохранены.");
        }catch(error){saveStatus.textContent=error.message;saveButton.disabled=false;saveButton.textContent="Повторить сохранение";}
      });
      footer.append(deleteButton,saveButton);
      tabNames.forEach(([key,label])=>{
        const button=document.createElement("button");button.type="button";button.className="dc-role-tab";button.textContent=label;
        button.addEventListener("click",()=>{activeTab=key;renderRoleTab();});tabButtons.set(key,button);roleTabs.append(button);
      });
      const renderRoleTab=()=>{
        panel.replaceChildren();tabButtons.forEach((button,key)=>button.classList.toggle("active",key===activeTab));
        if(activeTab==="display"){
          const fields=document.createElement("div");fields.className="dc-role-display-fields";
          const nameLabel=document.createElement("label");nameLabel.className="dc-settings-field";const nameCaption=document.createElement("span");nameCaption.textContent="Название роли";
          const nameInput=document.createElement("input");nameInput.value=draft.name;nameInput.maxLength=100;nameInput.disabled=!roleDisplayEditable;nameInput.addEventListener("input",()=>{draft.name=nameInput.value;previewName.textContent=draft.name;});nameLabel.append(nameCaption,nameInput);
          const colorLabel=document.createElement("label");colorLabel.className="dc-settings-field";const colorCaption=document.createElement("span");colorCaption.textContent="Цвет роли";
          const colorRow=document.createElement("div");colorRow.className="dc-role-color-input-row";
          const colorInput=document.createElement("input");colorInput.type="color";colorInput.value=/^#[0-9a-f]{6}$/i.test(draft.color)?draft.color:"#000000";colorInput.disabled=!roleDisplayEditable;
          const colorText=document.createElement("input");colorText.type="text";colorText.value=draft.color;colorText.maxLength=7;colorText.disabled=!roleDisplayEditable;
          const setColor=value=>{if(/^#[0-9a-f]{6}$/i.test(value)){draft.color=value;colorInput.value=value;colorText.value=value;dcApplyRoleColor(previewDot,draft,false);dcApplyRoleColor(previewName,draft,true);}};
          colorInput.addEventListener("input",()=>setColor(colorInput.value));colorText.addEventListener("change",()=>setColor(colorText.value));colorRow.append(colorInput,colorText);colorLabel.append(colorCaption,colorRow);
          const styleLabel=document.createElement("label");styleLabel.className="dc-settings-field dc-role-style-field";const styleCaption=document.createElement("span");styleCaption.textContent="Стиль роли";
          const styleSelect=document.createElement("select");styleSelect.name="role_style";
          [["solid","Сплошной"],["gradient","Градиент"],["holographic","Голографический"]].forEach(([value,label])=>{const option=document.createElement("option");option.value=value;option.textContent=label;styleSelect.append(option);});
          styleSelect.value=draft.style||"solid";styleSelect.disabled=!roleDisplayEditable||!rolesData.enhanced_role_styles_enabled;
          const styleHint=document.createElement("small");styleHint.className="dc-role-style-hint";
          const secondaryLabel=document.createElement("label");secondaryLabel.className="dc-settings-field";const secondaryCaption=document.createElement("span");secondaryCaption.textContent="Второй цвет градиента";
          const secondaryRow=document.createElement("div");secondaryRow.className="dc-role-color-input-row";
          const secondaryInput=document.createElement("input");secondaryInput.type="color";secondaryInput.value=draft.secondary_color||"#FFBBEC";
          const secondaryText=document.createElement("input");secondaryText.type="text";secondaryText.maxLength=7;secondaryText.value=draft.secondary_color||"#FFBBEC";
          const syncSecondary=value=>{if(/^#[0-9a-f]{6}$/i.test(value)){draft.secondary_color=value;secondaryInput.value=value;secondaryText.value=value;dcApplyRoleColor(previewDot,draft,false);dcApplyRoleColor(previewName,draft,true);}};
          secondaryInput.addEventListener("input",()=>syncSecondary(secondaryInput.value));secondaryText.addEventListener("change",()=>syncSecondary(secondaryText.value));secondaryRow.append(secondaryInput,secondaryText);secondaryLabel.append(secondaryCaption,secondaryRow);
          const holoNote=document.createElement("div");holoNote.className="dc-role-holo-note";holoNote.textContent="Голографический стиль использует фиксированную палитру Discord из трёх цветов.";
          const updateRoleStyleFields=()=>{
            const enabled=rolesData.enhanced_role_styles_enabled===true;
            const current=draft.style||"solid";
            secondaryLabel.hidden=current==="solid";
            secondaryInput.disabled=!roleDisplayEditable||current!=="gradient"||!enabled;
            secondaryText.disabled=!roleDisplayEditable||current!=="gradient"||!enabled;
            holoNote.hidden=current!=="holographic";
            styleHint.textContent=enabled?"Enhanced Role Styles активен на этом сервере.":"Для градиента и голографического стиля серверу требуется включить Enhanced Role Styles за 3 буста.";
            styleHint.classList.toggle("warning",!enabled);
            styleSelect.disabled=!roleDisplayEditable||!enabled;
            dcApplyRoleColor(previewDot,draft,false);dcApplyRoleColor(previewName,draft,true);
          };
          styleSelect.addEventListener("change",()=>{
            draft.style=styleSelect.value;
            if(draft.style==="holographic"){draft.color="#A9C9FF";draft.secondary_color="#FFBBEC";colorInput.value=draft.color;colorText.value=draft.color;secondaryInput.value=draft.secondary_color;secondaryText.value=draft.secondary_color;}
            updateRoleStyleFields();
          });
          styleLabel.append(styleCaption,styleSelect,styleHint);
          fields.append(nameLabel,colorLabel,styleLabel,secondaryLabel,holoNote);
          updateRoleStyleFields();
          const iconSection=document.createElement("div");iconSection.className="dc-role-icon-editor";
          const iconTitle=document.createElement("strong");iconTitle.textContent="Значок роли";
          const iconDescription=document.createElement("small");iconDescription.textContent=rolesData.role_icons_enabled?"PNG/JPEG до 256 КБ или Unicode-эмодзи. Значок отображается рядом с названием роли.":"Значки ролей требуют функции Role Icons на сервере.";
          const iconControls=document.createElement("div");iconControls.className="dc-role-icon-controls";
          const iconFile=document.createElement("input");iconFile.type="file";iconFile.accept="image/png,image/jpeg";iconFile.disabled=!roleDisplayEditable||!rolesData.role_icons_enabled;
          const iconEmoji=document.createElement("input");iconEmoji.type="text";iconEmoji.maxLength=32;iconEmoji.placeholder="Или Unicode-эмодзи";iconEmoji.value=draft.icon_emoji;iconEmoji.disabled=!roleDisplayEditable||!rolesData.role_icons_enabled;
          const iconStatus=document.createElement("span");iconStatus.className="dc-role-icon-status";iconStatus.textContent=role.icon_url?"Текущий значок загружен":(draft.icon_emoji||"Без значка");
          iconFile.addEventListener("change",()=>{
            const file=iconFile.files?.[0];if(!file)return;
            if(!["image/png","image/jpeg"].includes(file.type)||file.size>256*1024){iconStatus.textContent="Нужен PNG/JPEG до 256 КБ.";iconFile.value="";return;}
            const reader=new FileReader();reader.onload=()=>{draft.icon_data=String(reader.result||"");draft.icon_emoji="";draft.remove_icon=false;iconEmoji.value="";iconStatus.textContent="Новое изображение выбрано: "+file.name;};
            reader.onerror=()=>{iconStatus.textContent="Не удалось прочитать изображение."};reader.readAsDataURL(file);
          });
          iconEmoji.addEventListener("input",()=>{draft.icon_emoji=iconEmoji.value.trim();draft.icon_data=null;draft.remove_icon=false;iconFile.value="";iconStatus.textContent=draft.icon_emoji||"Без значка";});
          const clearIcon=document.createElement("button");clearIcon.type="button";clearIcon.className="dc-role-icon-clear";clearIcon.textContent="Убрать значок";clearIcon.disabled=!roleDisplayEditable||!rolesData.role_icons_enabled||(!role.icon_url&&!role.unicode_emoji);
          clearIcon.addEventListener("click",()=>{draft.icon_data=null;draft.icon_emoji="";draft.remove_icon=true;iconFile.value="";iconEmoji.value="";iconStatus.textContent="Значок будет удалён после сохранения.";});
          iconControls.append(iconFile,iconEmoji,clearIcon);iconSection.append(iconTitle,iconDescription,iconControls,iconStatus);
          if(!rolesData.role_icons_enabled){iconSection.classList.add("is-unavailable");}
          fields.append(iconSection);
          const positionLabel=document.createElement("label");positionLabel.className="dc-settings-field";const positionCaption=document.createElement("span");positionCaption.textContent="Позиция в иерархии";
          const positionInput=document.createElement("input");positionInput.type="number";positionInput.min="1";positionInput.max=String(Math.max(1,Number(role.max_position)||Number(role.position)||1));positionInput.value=String(draft.position);positionInput.disabled=!roleDisplayEditable;positionInput.addEventListener("input",()=>{draft.position=Number(positionInput.value)||1;tag.textContent="Позиция #"+draft.position;});positionLabel.append(positionCaption,positionInput);
          const hoistLabel=document.createElement("label");hoistLabel.className="dc-role-switch";const hoist=document.createElement("input");hoist.type="checkbox";hoist.checked=draft.hoist;hoist.disabled=!roleDisplayEditable;hoist.addEventListener("change",()=>draft.hoist=hoist.checked);const hoistCopy=document.createElement("span");const hoistTitle=document.createElement("strong");hoistTitle.textContent="Отображать отдельно";const hoistDesc=document.createElement("small");hoistDesc.textContent="Создаёт отдельную группу этой роли в списке участников сервера.";hoistCopy.append(hoistTitle,hoistDesc);hoistLabel.append(hoist,hoistCopy);
          const mentionLabel=document.createElement("label");mentionLabel.className="dc-role-switch";const mention=document.createElement("input");mention.type="checkbox";mention.checked=draft.mentionable;mention.disabled=!roleDisplayEditable;mention.addEventListener("change",()=>draft.mentionable=mention.checked);const mentionCopy=document.createElement("span");const mentionTitle=document.createElement("strong");mentionTitle.textContent="Разрешить упоминание роли";const mentionDesc=document.createElement("small");mentionDesc.textContent="Участники смогут упоминать эту роль через @название.";mentionCopy.append(mentionTitle,mentionDesc);mentionLabel.append(mention,mentionCopy);
          fields.append(positionLabel,hoistLabel,mentionLabel);
          if(role.is_default){const note=document.createElement("div");note.className="dc-settings-permission";note.textContent="Это базовая роль @everyone. Здесь можно настраивать только разрешения, которые наследуют все участники сервера.";fields.append(note);}
          else if(role.managed){const note=document.createElement("div");note.className="dc-settings-permission";note.textContent="Эта роль создана интеграцией. Её параметры управляются внешним сервисом Discord.";fields.append(note);}
          panel.append(fields);
        }else if(activeTab==="permissions"){
          const intro=document.createElement("p");intro.className="dc-role-permissions-intro";intro.textContent="Разрешения роли действуют на сервере. Ограничения конкретных каналов задаются отдельно в переопределениях прав.";panel.append(intro);
          const flags=Object.keys(draft.permissions||{});
          const used=new Set();
          const canSet=new Set(rolesData.manageable_permission_keys||[]);
          const renderPermissionGroup=group=>{
            const keys=group.keys.filter(key=>Object.prototype.hasOwnProperty.call(draft.permissions,key));
            keys.forEach(key=>used.add(key));if(!keys.length)return;
            const box=document.createElement("section");box.className="dc-permission-group";const heading=document.createElement("h4");heading.textContent=group.title;box.append(heading);
            keys.forEach(key=>{
              const current=!!draft.permissions[key];const allowed=canSet.has(key);
              const row=document.createElement("label");row.className="dc-permission-row"+(!allowed&&!current?" disabled":"");
              const textWrap=document.createElement("span");textWrap.className="dc-permission-copy";const label=document.createElement("strong");label.textContent=permissionLabels[key]||key.replaceAll("_"," ").replace(/(^|\s)([a-z])/g,(_,space,letter)=>space+letter.toUpperCase());const description=document.createElement("small");description.textContent=key==="administrator"?"Даёт все разрешения и обходит ограничения каналов. Используй с осторожностью.":key==="manage_roles"?"Позволяет создавать, редактировать и назначать роли ниже своей высшей роли.":"";textWrap.append(label);if(description.textContent)textWrap.append(description);
              const checkbox=document.createElement("input");checkbox.type="checkbox";checkbox.checked=current;checkbox.disabled=!isEditable||(!allowed&&!current);checkbox.addEventListener("change",()=>draft.permissions[key]=checkbox.checked);row.append(textWrap,checkbox);box.append(row);
            });
            panel.append(box);
          };
          permissionGroups.forEach(renderPermissionGroup);
          const rest=flags.filter(key=>!used.has(key));
          if(rest.length)renderPermissionGroup({title:"ДОПОЛНИТЕЛЬНЫЕ ПРАВА",keys:rest});
          const note=document.createElement("div");note.className="dc-settings-permission";note.textContent="Права, которых нет у твоей роли или у бота, нельзя включить. Уже существующие ограничения сохраняются; недоступные права можно снять.";panel.append(note);
        }else{
          const search=document.createElement("input");search.type="search";search.className="dc-role-member-search";search.placeholder="Поиск участника по имени или ID";
          const membersRoot=document.createElement("div");membersRoot.className="dc-role-member-list";membersRoot.textContent="Загружаем участников…";panel.append(search,membersRoot);
          let members=[];
          const renderMembers=()=>{
            const query=search.value.trim().toLocaleLowerCase("ru");
            const filtered=members.filter(member=>((member.global_name||"")+" "+(member.username||"")+" "+member.id).toLocaleLowerCase("ru").includes(query));
            membersRoot.replaceChildren();
            if(!filtered.length){membersRoot.textContent="Участники не найдены.";return;}
            filtered.slice(0,500).forEach(member=>{
              const row=document.createElement("label");row.className="dc-role-member-row";
              const avatar=document.createElement("span");avatar.className="dc-role-member-avatar";avatar.innerHTML=dcAvatar(member,"");
              const name=document.createElement("span");name.className="dc-role-member-name";name.textContent=member.global_name||member.username;
              const id=document.createElement("small");id.textContent="@"+member.username;name.append(id);
              const checkbox=document.createElement("input");checkbox.type="checkbox";checkbox.checked=(member.role_ids||[]).map(String).includes(String(role.id));checkbox.disabled=!isEditable||role.is_default;
              checkbox.addEventListener("change",async()=>{
                checkbox.disabled=true;
                try{
                  await apiPost("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/members/"+encodeURIComponent(member.id)+"/roles",{role_id:String(role.id),action:checkbox.checked?"add":"remove"});
                  const ids=new Set((member.role_ids||[]).map(String));if(checkbox.checked)ids.add(String(role.id));else ids.delete(String(role.id));member.role_ids=[...ids];
                  const cachedMember=dcMemberCache.find(item=>String(item.id)===String(member.id));
                  if(cachedMember)cachedMember.role_ids=[...ids];
                  if(dcActiveGuild?.id){dcMemberCacheByGuild.set(dcActiveGuild.id,dcMemberCache);dcRenderGuildMembers();}
                }catch(error){checkbox.checked=!checkbox.checked;saveStatus.textContent=error.message;}
                finally{checkbox.disabled=!isEditable||role.is_default;}
              });
              row.append(avatar,name,checkbox);membersRoot.append(row);
            });
          };
          search.addEventListener("input",renderMembers);
          apiGet("/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/members").then(result=>{members=result.members||[];renderMembers();}).catch(error=>{membersRoot.textContent="Не удалось загрузить участников: "+error.message;});
        }
      };
      editor.append(roleTabs,panel,saveStatus,footer);
      renderRoleTab();
    };
    main.append(hint);
    try{await refreshRoles(null);}catch(error){roleList.textContent="Не удалось загрузить роли: "+error.message;}
  };


  const serverSettingsBase="/api/discord/guilds/"+encodeURIComponent(dcActiveGuild.id)+"/settings/";
  const serverSettingsRequest=async(section,method="GET",payload=null,itemId="")=>{
    const suffix=itemId?(section==="members"?"/"+encodeURIComponent(itemId)+"/action":"/"+encodeURIComponent(itemId)):"";
    const url=serverSettingsBase+section+suffix;
    const options={method,credentials:"same-origin"};
    if(payload instanceof FormData)options.body=payload;
    else if(payload!==null){options.headers={"Content-Type":"application/json"};options.body=JSON.stringify(payload);}
    const response=await fetch(url,options);
    const raw=await response.text();let result={};try{result=raw?JSON.parse(raw):{};}catch{throw new Error("Discord вернул неожиданный ответ (HTTP "+response.status+").");}
    if(!response.ok)throw new Error(result.detail||"Запрос к настройкам сервера не выполнен.");
    return result;
  };
  const settingsHeading=(name,description)=>{
    main.replaceChildren();
    const head=document.createElement("div");head.className="dc-settings-page-heading";
    const h=document.createElement("h3");h.textContent=name;
    const p=document.createElement("p");p.textContent=description||"Настройки сервера GastWorld.";
    head.append(h,p);main.append(head);return head;
  };
  const settingsNotice=(text,error=false)=>{
    const node=document.createElement("div");node.className="dc-settings-permission"+(error?" dc-settings-notice-error":"");node.textContent=text;main.append(node);return node;
  };
  const settingsButton=(text,action,kind="secondary")=>{
    const button=document.createElement("button");button.type="button";button.className="dc-settings-action dc-settings-action-"+kind;button.textContent=text;
    button.addEventListener("click",action);return button;
  };
  const settingsLabel=(caption,control,wide=false)=>{
    const label=document.createElement("label");label.className="dc-settings-field"+(wide?" wide":"");
    const span=document.createElement("span");span.textContent=caption;label.append(span,control);return label;
  };
  const settingsInput=(value="",type="text",placeholder="")=>{
    const input=document.createElement("input");input.type=type;input.value=value??"";input.placeholder=placeholder;return input;
  };
  const settingsSelect=(items,value)=>{
    const select=document.createElement("select");(items||[]).forEach(item=>{
      const option=document.createElement("option");option.value=String(item[0]);option.textContent=String(item[1]);select.append(option);
    });select.value=String(value??"");return select;
  };
  const settingsPanel=(title)=>{
    const panel=document.createElement("section");panel.className="dc-settings-section dc-settings-data-panel";
    if(title){const h=document.createElement("h4");h.textContent=title;panel.append(h);}return panel;
  };
  const settingsError=(container,error)=>{
    const box=document.createElement("div");box.className="dc-settings-permission dc-settings-notice-error";box.textContent=error?.message||String(error||"Неизвестная ошибка");container.append(box);
  };
  const settingsEmpty=(container,message)=>{
    const empty=document.createElement("div");empty.className="dc-settings-empty";empty.textContent=message;container.append(empty);
  };
  const settingsRow=(container,title,subtitle,actions=[])=>{
    const row=document.createElement("div");row.className="dc-settings-list-row";
    const copy=document.createElement("div");copy.className="dc-settings-list-copy";
    const strong=document.createElement("strong");strong.textContent=title||"Без названия";
    copy.append(strong);
    if(subtitle){const small=document.createElement("small");small.textContent=subtitle;copy.append(small);}
    const tools=document.createElement("div");tools.className="dc-settings-list-actions";actions.forEach(a=>tools.append(a));
    row.append(copy,tools);container.append(row);return row;
  };
  const settingsLoadError=(title,desc,error)=>{settingsHeading(title,desc);settingsError(main,error);};

  const renderChannels=async()=>{
    settingsHeading("Каналы и категории","Создавай, редактируй, перемещай и удаляй каналы и категории сервера.");
    const workspace=document.createElement("div");workspace.className="dc-settings-management-workspace";
    const listPane=settingsPanel("СТРУКТУРА СЕРВЕРА");
    const addBar=document.createElement("div");addBar.className="dc-settings-toolbar";
    const refresh=settingsButton("Обновить",()=>loadChannels(),"secondary");
    addBar.append(refresh);listPane.append(addBar);
    const list=document.createElement("div");list.className="dc-settings-data-list";list.textContent="Загрузка каналов…";listPane.append(list);
    const editor=settingsPanel("СОЗДАТЬ / ИЗМЕНИТЬ");
    const permissionsEditor=settingsPanel("ПРАВА КАНАЛА");
    permissionsEditor.textContent="Выбери «Права» у канала, чтобы настроить разрешения ролей и участников.";
    workspace.append(listPane,editor,permissionsEditor);main.append(workspace);
    let currentData={channels:[],categories:[]};
    const typeSelect=settingsSelect([["text","Текстовый канал"],["announcement","Канал объявлений"],["voice","Голосовой канал"],["stage","Stage-канал"],["forum","Форум"],["category","Категория"]],"text");
    const nameInput=settingsInput("","");
    const categorySelect=settingsSelect([["","Без категории"]],"");
    const topicInput=settingsInput("","");
    const slowInput=settingsInput("0","number");
    const positionInput=settingsInput("0","number");
    const bitrateInput=settingsInput("64000","number");
    const userLimitInput=settingsInput("0","number");
    const nsfwInput=document.createElement("input");nsfwInput.type="checkbox";
    const createForm=document.createElement("form");createForm.className="dc-settings-form dc-settings-compact-form";
    const fields=document.createElement("div");fields.className="dc-settings-fields";
    fields.append(settingsLabel("Тип",typeSelect),settingsLabel("Название",nameInput),settingsLabel("Категория",categorySelect),settingsLabel("Позиция",positionInput),settingsLabel("Медленный режим (сек.)",slowInput),settingsLabel("Битрейт (бит/с)",bitrateInput),settingsLabel("Лимит участников",userLimitInput),settingsLabel("Тема / описание",topicInput,true),settingsLabel("Канал для взрослых (NSFW)",nsfwInput));
    const submit=document.createElement("button");submit.type="submit";submit.className="dc-settings-save";submit.textContent="Создать";
    const reset=settingsButton("Очистить",()=>{createForm.dataset.editId="";createForm.reset();submit.textContent="Создать";typeSelect.disabled=false;categorySelect.disabled=false;typeSelect.dispatchEvent(new Event("change"));});
    createForm.append(fields);const foot=document.createElement("div");foot.className="dc-settings-footer";foot.append(reset,submit);createForm.append(foot);editor.append(createForm);
    const permissionLabels={
      view_channel:"Просмотр канала",send_messages:"Отправка сообщений",read_message_history:"Чтение истории",
      add_reactions:"Добавление реакций",embed_links:"Встраивание ссылок",attach_files:"Прикрепление файлов",
      mention_everyone:"Упоминание @everyone",manage_messages:"Управление сообщениями",
      use_external_emojis:"Внешние эмодзи",use_external_stickers:"Внешние стикеры",
      use_application_commands:"Команды приложений",create_public_threads:"Создание публичных веток",
      create_private_threads:"Создание приватных веток",send_messages_in_threads:"Сообщения в ветках",
      connect:"Подключение к голосу",speak:"Говорить",stream:"Трансляция",use_vad:"Голосовая активация",
      mute_members:"Отключение микрофона",deafen_members:"Отключение звука",move_members:"Перемещение участников"
    };
    const loadChannelPermissions=async channel=>{
      permissionsEditor.replaceChildren();
      const loading=document.createElement("p");loading.className="dc-settings-permission";loading.textContent="Загрузка переопределений прав…";permissionsEditor.append(loading);
      const endpoint=serverSettingsBase+"channels/"+encodeURIComponent(channel.id)+"/permissions";
      const request=async(method="GET",payload=null,targetId="")=>{
        const url=endpoint+(targetId?"/"+encodeURIComponent(targetId):"");
        const options={method,credentials:"same-origin"};
        if(payload){options.headers={"Content-Type":"application/json"};options.body=JSON.stringify(payload);}
        const response=await fetch(url,options);const raw=await response.text();let result={};try{result=raw?JSON.parse(raw):{};}catch{}
        if(!response.ok)throw new Error(result.detail||"Не удалось изменить права канала.");return result;
      };
      try{
        const data=await request();permissionsEditor.replaceChildren();
        const intro=document.createElement("p");intro.className="dc-settings-permission";intro.textContent="Канал: #"+(channel.name||channel.id)+". Для каждой настройки выбери «Наследовать», «Разрешить» или «Запретить».";
        permissionsEditor.append(intro);
        const targetType=settingsSelect([["role","Роль"],["member","Участник"]],"role");
        const roleSelect=settingsSelect((data.roles||[]).map(role=>[role.id,role.name]),data.roles?.[0]?.id||"");
        const memberId=settingsInput("","text","Discord ID участника");memberId.inputMode="numeric";memberId.hidden=true;
        const controls=document.createElement("div");controls.className="dc-settings-fields";
        controls.append(settingsLabel("Тип цели",targetType),settingsLabel("Роль",roleSelect),settingsLabel("ID участника",memberId));permissionsEditor.append(controls);
        const overwriteTargets=new Map((data.targets||[]).map(item=>[item.type+":"+item.id,item]));
        const permissionControls=document.createElement("div");permissionControls.className="dc-channel-permission-grid";permissionsEditor.append(permissionControls);
        const currentTarget=()=>{
          if(targetType.value==="role")return {id:roleSelect.value,type:"role"};
          return {id:memberId.value.trim(),type:"member"};
        };
        const renderPermissionControls=()=>{
          const target=currentTarget();const current=overwriteTargets.get(target.type+":"+target.id);
          permissionControls.replaceChildren();
          (data.permission_keys||[]).forEach(key=>{
            const value=current?.permissions?.[key];
            const select=settingsSelect([["","Наследовать"],["true","Разрешить"],["false","Запретить"]],value===true?"true":value===false?"false":"");
            permissionControls.append(settingsLabel(permissionLabels[key]||key,select));
          });
        };
        targetType.addEventListener("change",()=>{
          const isMember=targetType.value==="member";roleSelect.hidden=isMember;memberId.hidden=!isMember;
          renderPermissionControls();
        });
        roleSelect.addEventListener("change",renderPermissionControls);memberId.addEventListener("input",renderPermissionControls);
        renderPermissionControls();
        const actions=document.createElement("div");actions.className="dc-settings-footer";
        const clear=settingsButton("Сбросить переопределение",async()=>{
          const target=currentTarget();if(!target.id||!confirm("Сбросить индивидуальные права этой роли/участника?"))return;
          try{await request("DELETE",null,target.id);await loadChannelPermissions(channel);showToast?.("Переопределение удалено.");}catch(error){settingsError(permissionsEditor,error);}
        },"danger");
        const save=settingsButton("Сохранить права",async()=>{
          const target=currentTarget();if(!target.id||!/^\d+$/.test(target.id)){settingsError(permissionsEditor,new Error("Выбери роль или введи корректный Discord ID участника."));return;}
          const values={};Array.from(permissionControls.querySelectorAll("select")).forEach((select,index)=>{const key=(data.permission_keys||[])[index];values[key]=select.value===""?null:select.value==="true";});
          save.disabled=true;
          try{await request("PATCH",{target_type:target.type,permissions:values},target.id);showToast?.("Права канала сохранены.");await loadChannelPermissions(channel);}
          catch(error){settingsError(permissionsEditor,error);}finally{save.disabled=false;}
        },"primary");
        actions.append(clear,save);permissionsEditor.append(actions);
      }catch(error){permissionsEditor.replaceChildren();settingsError(permissionsEditor,error);}
      permissionsEditor.scrollIntoView({behavior:"smooth",block:"nearest"});
    };
    typeSelect.addEventListener("change",()=>{
      const type=typeSelect.value;
      topicInput.disabled=!["text","announcement","forum"].includes(type);
      slowInput.disabled=!["text","announcement"].includes(type);
      bitrateInput.disabled=type!=="voice";userLimitInput.disabled=type!=="voice";
      nsfwInput.disabled=!["text","announcement","forum","voice","stage"].includes(type);
      categorySelect.disabled=type==="category";
    });
    const loadChannels=async()=>{
      list.textContent="Загрузка каналов…";
      try{
        currentData=await serverSettingsRequest("channels");
        const options=[["","Без категории"],...(currentData.categories||[]).map(c=>[c.id,c.name])];
        categorySelect.replaceChildren();options.forEach(item=>{const o=document.createElement("option");o.value=item[0];o.textContent=item[1];categorySelect.append(o);});
        list.replaceChildren();
        const categories=currentData.categories||[],channels=currentData.channels||[];
        if(!categories.length&&!channels.length){settingsEmpty(list,"На сервере пока нет каналов и категорий.");return;}
        const renderItem=(item,isCategory)=>{
          const actions=[];
          actions.push(settingsButton("Изменить",()=>{
            createForm.dataset.editId=String(item.id);nameInput.value=item.name||"";typeSelect.value=isCategory?"category":(item.type||"text");
            typeSelect.disabled=true;categorySelect.value=item.category_id||"";categorySelect.disabled=isCategory;
            topicInput.value=item.topic||"";topicInput.disabled=isCategory||!["text","announcement","forum"].includes(typeSelect.value);
            slowInput.value=String(item.slowmode_delay||0);slowInput.disabled=isCategory||!["text","announcement"].includes(typeSelect.value);
            positionInput.value=String(item.position??0);
            bitrateInput.value=String(item.bitrate||64000);bitrateInput.disabled=typeSelect.value!=="voice";
            userLimitInput.value=String(item.user_limit||0);userLimitInput.disabled=typeSelect.value!=="voice";
            nsfwInput.checked=!!item.nsfw;nsfwInput.disabled=isCategory||!["text","announcement","forum","voice","stage"].includes(typeSelect.value);
            submit.textContent="Сохранить";
            editor.scrollIntoView({behavior:"smooth",block:"nearest"});
          }));
          actions.push(settingsButton("Права",()=>loadChannelPermissions(item)));
          actions.push(settingsButton("Удалить",async()=>{
            if(!confirm("Удалить "+(isCategory?"категорию ":"канал ")+"«"+item.name+"»? Это действие нельзя отменить."))return;
            try{await serverSettingsRequest("channels","DELETE",null,item.id);await loadChannels();showToast?.("Объект удалён.");}catch(error){settingsError(editor,error);}
          },"danger"));
          settingsRow(list,(isCategory?"▾ ":"# ")+item.name,isCategory?"Категория":"Тип: "+(item.type||"канал")+" · "+(item.category_name||"Без категории"),actions);
        };
        categories.forEach(item=>renderItem(item,true));
        channels.forEach(item=>renderItem(item,false));
      }catch(error){list.replaceChildren();settingsError(list,error);}
    };
    createForm.addEventListener("submit",async event=>{
      event.preventDefault();submit.disabled=true;
      const editId=createForm.dataset.editId||"";
      const payload={name:nameInput.value.trim()};
      if(!payload.name){settingsError(editor,new Error("Укажи название."));submit.disabled=false;return;}
      if(!editId){
        payload.type=typeSelect.value;
        payload.position=Math.max(0,Number(positionInput.value)||0);
        if(typeSelect.value!=="category")payload.category_id=categorySelect.value||null;
        if(["text","announcement","forum"].includes(typeSelect.value))payload.topic=topicInput.value.trim();
        if(["text","announcement"].includes(typeSelect.value))payload.slowmode_delay=Number(slowInput.value)||0;
        if(typeSelect.value==="voice"){payload.bitrate=Number(bitrateInput.value)||64000;payload.user_limit=Number(userLimitInput.value)||0;}
        if(["text","announcement","forum","voice","stage"].includes(typeSelect.value))payload.nsfw=!!nsfwInput.checked;
      }else{
        payload.position=Math.max(0,Number(positionInput.value)||0);
        if(typeSelect.value!=="category")payload.category_id=categorySelect.value||null;
        if(["text","announcement","forum"].includes(typeSelect.value))payload.topic=topicInput.value.trim();
        if(["text","announcement"].includes(typeSelect.value))payload.slowmode_delay=Number(slowInput.value)||0;
        if(typeSelect.value==="voice"){payload.bitrate=Number(bitrateInput.value)||64000;payload.user_limit=Number(userLimitInput.value)||0;}
        if(["text","announcement","forum","voice","stage"].includes(typeSelect.value))payload.nsfw=!!nsfwInput.checked;
      }
      try{await serverSettingsRequest("channels",editId?"PATCH":"POST",payload,editId);createForm.dataset.editId="";createForm.reset();typeSelect.disabled=false;categorySelect.disabled=false;submit.textContent="Создать";typeSelect.dispatchEvent(new Event("change"));await loadChannels();showToast?.(editId?"Канал обновлён.":"Объект создан.");}
      catch(error){settingsError(editor,error);}
      finally{submit.disabled=false;}
    });
    await loadChannels();
  };

  const renderMembers=async()=>{
    settingsHeading("Участники","Список участников сервера, быстрый поиск и инструменты модерации. Все действия учитывают права и иерархию Discord.");
    const search=settingsInput("","search","Поиск по имени, нику или ID");search.className="dc-role-member-search";main.append(search);
    const memberToolbar=document.createElement("div");memberToolbar.className="dc-settings-toolbar";
    const bansButton=settingsButton("Заблокированные участники",()=>loadBans());memberToolbar.append(bansButton);main.append(memberToolbar);
    const status=document.createElement("p");status.className="dc-settings-status";status.textContent="Загрузка участников…";main.append(status);
    const list=document.createElement("div");list.className="dc-settings-data-list dc-settings-member-list";main.append(list);
    let members=[];
    const draw=()=>{
      const term=search.value.trim().toLocaleLowerCase("ru");
      const filtered=members.filter(m=>[m.global_name,m.username,m.id].join(" ").toLocaleLowerCase("ru").includes(term));
      list.replaceChildren();
      if(!filtered.length){settingsEmpty(list,members.length?"Участники не найдены.":"Список пуст.");return;}
      filtered.slice(0,1200).forEach(member=>{
        const actions=[];
        actions.push(settingsButton("Профиль",()=>dcOpenProfile(member)));
        actions.push(settingsButton("Ник",async()=>{
          const nickname=prompt("Новый ник (пусто — сбросить):",member.global_name||member.username||"");if(nickname===null)return;
          try{await serverSettingsRequest("members","POST",{action:"nickname",nickname},member.id);showToast?.("Ник участника изменён.");}catch(error){settingsError(list,error);}
        }));
        actions.push(settingsButton("Тайм-аут",async()=>{
          const minutes=prompt("Минуты тайм-аута (0 — снять, максимум 40320):","10");if(minutes===null)return;
          const n=Number(minutes);if(!Number.isInteger(n)||n<0||n>40320){alert("Укажи число от 0 до 40320.");return;}
          try{await serverSettingsRequest("members","POST",{action:"timeout",minutes:n},member.id);showToast?.(n?"Тайм-аут выдан.":"Тайм-аут снят.");}catch(error){settingsError(list,error);}
        }));
        actions.push(settingsButton("Кик",async()=>{
          if(!confirm("Исключить "+(member.global_name||member.username)+" с сервера?"))return;
          try{await serverSettingsRequest("members","POST",{action:"kick"},member.id);members=members.filter(m=>m.id!==member.id);draw();showToast?.("Участник исключён.");}catch(error){settingsError(list,error);}
        },"danger"));
        actions.push(settingsButton("Бан",async()=>{
          if(!confirm("Заблокировать "+(member.global_name||member.username)+" на сервере?"))return;
          try{await serverSettingsRequest("members","POST",{action:"ban",delete_message_seconds:0},member.id);members=members.filter(m=>m.id!==member.id);draw();showToast?.("Участник заблокирован.");}catch(error){settingsError(list,error);}
        },"danger"));
        const avatar=document.createElement("span");avatar.className="dc-settings-member-avatar";
        const url=member.avatar||member.avatar_url||"";
        if(url){const img=document.createElement("img");img.src=url;img.alt="";avatar.append(img);}else avatar.textContent=(member.global_name||member.username||"?").slice(0,1).toUpperCase();
        const row=settingsRow(list,(member.bot?"◆ ":"")+ (member.global_name||member.username||member.id),"@"+(member.username||"unknown")+" · ID "+member.id,actions);row.prepend(avatar);
      });
    };
    search.addEventListener("input",draw);
    const loadBans=async()=>{
      bansButton.disabled=true;status.textContent="Загрузка списка блокировок…";list.replaceChildren();
      try{
        const bans=await serverSettingsRequest("bans");
        status.textContent="Заблокировано пользователей: "+(bans||[]).length;
        if(!bans?.length){settingsEmpty(list,"Заблокированных пользователей нет.");return;}
        bans.forEach(entry=>{
          const user=entry.user||{};const id=String(user.id||"");
          const name=user.global_name||user.username||id||"Неизвестный пользователь";
          const unban=settingsButton("Разблокировать",async()=>{
            if(!confirm("Снять блокировку с "+name+"?"))return;
            unban.disabled=true;
            try{await serverSettingsRequest("bans","DELETE",null,id);entry._removed=true;row.remove();showToast?.("Пользователь разблокирован.");status.textContent="Заблокировано пользователей: "+bans.filter(x=>!x._removed).length;}
            catch(error){settingsError(list,error);unban.disabled=false;}
          },"primary");
          const row=settingsRow(list,name,"@"+(user.username||"unknown")+" · ID "+id+(entry.reason?" · "+entry.reason:"")+" · "+(entry.timestamp?new Date(entry.timestamp).toLocaleString("ru-RU"):""),[unban]);
          const avatar=document.createElement("span");avatar.className="dc-settings-member-avatar";if(user.avatar){const img=document.createElement("img");img.src="https://cdn.discordapp.com/avatars/"+id+"/"+user.avatar+".png?size=64";img.alt="";avatar.append(img);}else avatar.textContent=name.slice(0,1).toUpperCase();row.prepend(avatar);
        });
      }catch(error){settingsError(list,error);status.textContent="Не удалось загрузить список блокировок.";}
      finally{bansButton.disabled=false;}
    };
    try{
      let after="0",hasMore=true;
      while(hasMore&&members.length<10000){
        const page=await apiGet(serverSettingsBase+"members?after="+encodeURIComponent(after)+"&limit=500");
        const batch=page.members||[];members.push(...batch);status.textContent="Загружено участников: "+members.length;
        hasMore=!!page.has_more;after=String(page.next_after||"");
        if(!hasMore||!after||!batch.length)break;
      }
      draw();status.textContent="Всего загружено: "+members.length+" участников"+(members.length>=10000?" · показана первая часть списка":"");
    }catch(error){status.textContent="Ошибка загрузки участников: "+error.message;}
  };

  const renderInvites=async()=>{
    settingsHeading("Приглашения","Просматривай активные ссылки приглашений и создавай новые с ограничением по сроку и числу использований.");
    const form=settingsPanel("СОЗДАТЬ ПРИГЛАШЕНИЕ");
    const channelSelect=settingsSelect([["","Загрузка каналов…"]],"");
    const expiry=settingsSelect([[3600,"1 час"],[21600,"6 часов"],[86400,"24 часа"],[604800,"7 дней"],[0,"Без срока"]],86400);
    const uses=settingsSelect([[0,"Без лимита"],[1,"1 использование"],[5,"5 использований"],[10,"10 использований"],[25,"25 использований"],[50,"50 использований"],[100,"100 использований"]],0);
    const fields=document.createElement("div");fields.className="dc-settings-fields";fields.append(settingsLabel("Канал",channelSelect),settingsLabel("Срок действия",expiry),settingsLabel("Лимит использований",uses));
    const create=settingsButton("Создать ссылку",async()=>{
      if(!channelSelect.value){settingsError(form,new Error("Выбери канал."));return;}
      create.disabled=true;
      try{const invite=await serverSettingsRequest("invites","POST",{channel_id:channelSelect.value,max_age:Number(expiry.value),max_uses:Number(uses.value),unique:true});
        const result=document.createElement("div");result.className="dc-settings-created-invite";const link=document.createElement("a");link.href="https://discord.gg/"+invite.code;link.target="_blank";link.rel="noopener noreferrer";link.textContent="https://discord.gg/"+invite.code;
        const copy=settingsButton("Копировать",()=>navigator.clipboard?.writeText(link.href));result.append(link,copy);form.append(result);await loadInvites();
      }catch(error){settingsError(form,error);}finally{create.disabled=false;}
    },"primary");
    form.append(fields,create);main.append(form);
    const listPanel=settingsPanel("АКТИВНЫЕ ПРИГЛАШЕНИЯ"),list=document.createElement("div");list.className="dc-settings-data-list";list.textContent="Загрузка…";listPanel.append(list);main.append(listPanel);
    try{const channels=await serverSettingsRequest("channels");channelSelect.replaceChildren();(channels.channels||[]).filter(c=>["text","announcement"].includes(c.type)).forEach(c=>{const op=document.createElement("option");op.value=c.id;op.textContent="# "+c.name;channelSelect.append(op);});if(!channelSelect.options.length)channelSelect.add(new Option("Нет текстовых каналов",""));
    }catch(error){channelSelect.replaceChildren(new Option("Не удалось загрузить каналы",""));}
    const loadInvites=async()=>{
      list.textContent="Загрузка приглашений…";
      try{const data=await serverSettingsRequest("invites");list.replaceChildren();if(!data.length){settingsEmpty(list,"Активных приглашений нет.");return;}
        data.forEach(inv=>{
          const expiryLabel=inv.max_age?new Date(new Date(inv.created_at).getTime()+inv.max_age*1000).toLocaleString("ru-RU"):"Без срока";
          const acts=[settingsButton("Открыть",()=>window.open("https://discord.gg/"+inv.code,"_blank","noopener"))];
          acts.push(settingsButton("Отозвать",async()=>{if(!confirm("Отозвать приглашение "+inv.code+"?"))return;try{await serverSettingsRequest("invites","DELETE",null,inv.code);await loadInvites();}catch(error){settingsError(list,error);}},"danger"));
          settingsRow(list,"discord.gg/"+inv.code,"Канал: "+(inv.channel?.name||inv.channel_id||"—")+" · Использовано: "+(inv.uses||0)+(inv.max_uses?"/"+inv.max_uses:"")+" · "+expiryLabel,acts);
        });
      }catch(error){list.replaceChildren();settingsError(list,error);}
    };
    await loadInvites();
  };

  const renderSafety=async()=>{
    settingsHeading("Настройка безопасности","Уровни проверки участников, фильтры контента и временная защита сервера от рейдов.");
    const panel=settingsPanel("БЕЗОПАСНОСТЬ УЧАСТНИКОВ");panel.textContent="Загрузка параметров безопасности…";main.append(panel);
    try{
      const data=await serverSettingsRequest("safety"),settings=data.settings||{},incidents=data.incidents||{};
      panel.replaceChildren();const fields=document.createElement("div");fields.className="dc-settings-fields";
      const verification=settingsSelect([[0,"Без ограничений"],[1,"Подтверждённая почта"],[2,"Аккаунт старше 5 минут"],[3,"На сервере 10 минут"],[4,"Подтверждённый телефон"]],settings.verification_level);
      const filter=settingsSelect([[0,"Не фильтровать"],[1,"Без роли"],[2,"Все сообщения"]],settings.explicit_content_filter);
      const notify=settingsSelect([[0,"Все сообщения"],[1,"Только упоминания"]],settings.default_notifications);
      fields.append(settingsLabel("Уровень проверки",verification),settingsLabel("Фильтр медиа-контента",filter),settingsLabel("Уведомления по умолчанию",notify));
      panel.append(fields);
      const incidentPanel=settingsPanel("ЗАЩИТА ОТ РЕЙДОВ");incidentPanel.classList.add("dc-settings-nested-panel");
      const inviteUntil=settingsSelect([[0,"Включено"],[1,"Отключить на 1 час"],[6,"Отключить на 6 часов"],[12,"Отключить на 12 часов"],[24,"Отключить на 24 часа"]],incidents.invites_disabled_until?Math.max(1,Math.ceil((new Date(incidents.invites_disabled_until)-Date.now())/3600000)):0);
      const dmUntil=settingsSelect([[0,"Включено"],[1,"Отключить на 1 час"],[6,"Отключить на 6 часов"],[12,"Отключить на 12 часов"],[24,"Отключить на 24 часа"]],incidents.dms_disabled_until?Math.max(1,Math.ceil((new Date(incidents.dms_disabled_until)-Date.now())/3600000)):0);
      const ifields=document.createElement("div");ifields.className="dc-settings-fields";ifields.append(settingsLabel("Новые приглашения",inviteUntil),settingsLabel("Личные сообщения новых участников",dmUntil));incidentPanel.append(ifields);panel.append(incidentPanel);
      const note=document.createElement("p");note.className="dc-settings-permission";note.textContent="Текущий уровень MFA: "+(data.mfa_level===2?"Включён":data.mfa_level===1?"Требуется для модерации":"Не требуется")+" · Для защиты от рейдов Discord разрешает временное отключение приглашений и личных сообщений не более чем на 24 часа.";panel.append(note);
      const status=document.createElement("p");status.className="dc-settings-status";panel.append(status);
      const save=settingsButton("Сохранить безопасность",async()=>{
        save.disabled=true;
        const expiryIso=value=>Number(value)>0?new Date(Date.now()+Number(value)*3600000).toISOString():null;
        try{await serverSettingsRequest("safety","PATCH",{verification_level:Number(verification.value),explicit_content_filter:Number(filter.value),default_notifications:Number(notify.value),invites_disabled_until:expiryIso(inviteUntil.value),dms_disabled_until:expiryIso(dmUntil.value)});status.textContent="✓ Настройки безопасности сохранены.";showToast?.("Настройки безопасности сохранены.");}
        catch(error){status.textContent=error.message;}
        finally{save.disabled=false;}
      },"primary");panel.append(save);
    }catch(error){panel.replaceChildren();settingsError(panel,error);}
  };

  const renderAudit=async()=>{
    settingsHeading("Журнал аудита","Последние действия администраторов и модераторов на сервере GastWorld.");
    const refresh=settingsButton("Обновить",()=>loadAudit());main.append(refresh);
    const list=settingsPanel("ПОСЛЕДНИЕ 100 ДЕЙСТВИЙ");list.classList.add("dc-settings-audit-list");list.textContent="Загрузка журнала…";main.append(list);
    const loadAudit=async()=>{
      list.textContent="Загрузка журнала аудита…";
      try{
        const data=await serverSettingsRequest("audit");list.replaceChildren();
        const users=new Map((data.users||[]).map(u=>[String(u.id),u]));
        const actions=data.audit_log_entries||[];
        if(!actions.length){settingsEmpty(list,"Записей в журнале нет или Discord не вернул доступную историю.");return;}
        actions.forEach(entry=>{
          const user=users.get(String(entry.user_id));const action=String(entry.action_type||"Неизвестное действие");const target=entry.target_id?"ID объекта: "+entry.target_id:"";
          const time=entry.id?new Date(Number(BigInt(entry.id)>>22n)+1420070400000).toLocaleString("ru-RU"):"";
          settingsRow(list,action+" · "+(user?.global_name||user?.username||entry.user_id||"Система"),[target,entry.reason?"Причина: "+entry.reason:"",time].filter(Boolean).join(" · "));
        });
      }catch(error){list.replaceChildren();settingsError(list,error);}
    };
    await loadAudit();
  };

  const renderAutoMod=async()=>{
    settingsHeading("AutoMod","Настраивай автоматические правила: блокировка слов, спам, упоминания и фильтр профилей.");
    const createPanel=settingsPanel("НОВОЕ ПРАВИЛО");
    const fields=document.createElement("div");fields.className="dc-settings-fields";
    const name=settingsInput("Фильтр GastWorld");const type=settingsSelect([[1,"Ключевые слова"],[3,"Спам"],[4,"Слова из пресетов Discord"],[5,"Массовые упоминания"],[6,"Слова в профиле участника"]],1);
    const keywords=settingsInput("","text","слово1, слово2");const mentionLimit=settingsInput("5","number");const action=settingsSelect([[1,"Блокировать сообщение"],[2,"Отправить предупреждение в канал"],[3,"Тайм-аут"],[4,"Блокировать взаимодействия"]],1);
    const alertChannel=settingsSelect([["","Выбери канал"]],"");const timeout=settingsInput("600","number");const custom=settingsInput("Сообщение заблокировано фильтром сервера");
    fields.append(settingsLabel("Название",name),settingsLabel("Тип правила",type),settingsLabel("Ключевые слова",keywords,true),settingsLabel("Лимит упоминаний",mentionLimit),settingsLabel("Действие",action),settingsLabel("Канал для логов",alertChannel),settingsLabel("Тайм-аут (сек.)",timeout),settingsLabel("Сообщение пользователю",custom,true));
    const typeHint=document.createElement("p");typeHint.className="dc-settings-permission";typeHint.textContent="Ключевые слова и профили поддерживают список слов; пресеты используют встроенные наборы Discord; спам и массовые упоминания анализируются Discord.";
    createPanel.append(fields,typeHint);main.append(createPanel);
    const rulesPanel=settingsPanel("ПРАВИЛА СЕРВЕРА");const list=document.createElement("div");list.className="dc-settings-data-list";list.textContent="Загрузка AutoMod…";rulesPanel.append(list);main.append(rulesPanel);
    const loadRules=async()=>{
      list.textContent="Загрузка AutoMod…";
      try{
        const rules=await serverSettingsRequest("automod");list.replaceChildren();
        if(!rules.length){settingsEmpty(list,"Правила AutoMod ещё не созданы.");}
        rules.forEach(rule=>{
          const detail="Тип триггера: "+rule.trigger_type+" · Действия: "+(rule.actions||[]).map(a=>({1:"блокировка",2:"уведомление",3:"тайм-аут",4:"блокировка взаимодействий"}[a.type]||a.type)).join(", ");
          const toggle=settingsButton(rule.enabled?"Отключить":"Включить",async()=>{
            try{await serverSettingsRequest("automod","PATCH",{enabled:!rule.enabled},rule.id);await loadRules();}catch(error){settingsError(list,error);}
          });
          const del=settingsButton("Удалить",async()=>{if(!confirm("Удалить правило «"+rule.name+"»?"))return;try{await serverSettingsRequest("automod","DELETE",null,rule.id);await loadRules();}catch(error){settingsError(list,error);}},"danger");
          settingsRow(list,rule.name,detail,[toggle,del]);
        });
      }catch(error){list.replaceChildren();settingsError(list,error);}
    };
    const save=settingsButton("Создать правило",async()=>{
      const triggerType=Number(type.value);const actionType=Number(action.value);
      let metadata={};
      if([1,6].includes(triggerType)){metadata.keyword_filter=keywords.value.split(",").map(x=>x.trim()).filter(Boolean);if(!metadata.keyword_filter.length){settingsError(createPanel,new Error("Введи хотя бы одно ключевое слово."));return;}}
      if(triggerType===4)metadata.presets=[1,2,3];
      if(triggerType===5){metadata.mention_total_limit=Number(mentionLimit.value)||5;metadata.mention_raid_protection_enabled=true;}
      if(triggerType===6&&actionType===3){settingsError(createPanel,new Error("Для фильтра профилей нельзя использовать тайм-аут. Выбери блокировку взаимодействий или другое действие."));return;}
      let actionPayload={type:actionType};
      if(actionType===1&&custom.value.trim())actionPayload.metadata={custom_message:custom.value.trim().slice(0,150)};
      if(actionType===2){if(!alertChannel.value){settingsError(createPanel,new Error("Для уведомлений выбери канал."));return;}actionPayload.metadata={channel_id:alertChannel.value};}
      if(actionType===3){if(![1,5].includes(triggerType)){settingsError(createPanel,new Error("Тайм-аут доступен для правил ключевых слов и массовых упоминаний."));return;}actionPayload.metadata={duration_seconds:Math.max(60,Math.min(2419200,Number(timeout.value)||600))};}
      const body={name:name.value.trim(),event_type:triggerType===6?2:1,trigger_type:triggerType,actions:[actionPayload],enabled:true};
      if(Object.keys(metadata).length)body.trigger_metadata=metadata;
      if(!body.name){settingsError(createPanel,new Error("Укажи название правила."));return;}
      save.disabled=true;
      try{await serverSettingsRequest("automod","POST",body);showToast?.("Правило AutoMod создано.");await loadRules();}
      catch(error){settingsError(createPanel,error);}
      finally{save.disabled=false;}
    },"primary");
    createPanel.append(save);
    try{const channels=await serverSettingsRequest("channels");alertChannel.replaceChildren();alertChannel.add(new Option("Выбери канал",""));(channels.channels||[]).filter(c=>["text","announcement"].includes(c.type)).forEach(c=>alertChannel.add(new Option("# "+c.name,c.id)));}
    catch(error){settingsError(createPanel,error);}
    await loadRules();
  };

  const renderIntegrations=async()=>{
    settingsHeading("Интеграции","Подключённые интеграции Discord и их состояние. Удаление отключает соответствующую связь сервера.");
    const list=settingsPanel("ИНТЕГРАЦИИ СЕРВЕРА");list.textContent="Загрузка интеграций…";main.append(list);
    try{
      const items=await serverSettingsRequest("integrations");list.replaceChildren();
      if(!items.length){settingsEmpty(list,"Подключённых интеграций не найдено.");return;}
      items.forEach(item=>{
        const subtitle=[item.type,item.enabled===false?"Отключена":"Активна",item.account?.name].filter(Boolean).join(" · ");
        const remove=settingsButton("Отключить",async()=>{
          if(!confirm("Удалить интеграцию «"+(item.name||item.application?.name||item.id)+"»? Связанные вебхуки могут быть удалены."))return;
          try{await serverSettingsRequest("integrations","DELETE",null,item.id);await renderIntegrations();}catch(error){settingsError(list,error);}
        },"danger");
        settingsRow(list,item.name||item.application?.name||"Интеграция",subtitle,[remove]);
      });
    }catch(error){list.replaceChildren();settingsError(list,error);}
  };

  const renderEmoji=async()=>{
    settingsHeading("Эмодзи и стикеры","Управляй пользовательскими эмодзи и стикерами сервера. Discord ограничивает размер и поддерживаемые форматы файлов.");
    const emojiPanel=settingsPanel("ЭМОДЗИ");const emojiList=document.createElement("div");emojiList.className="dc-settings-expression-grid";emojiList.textContent="Загрузка эмодзи…";emojiPanel.append(emojiList);main.append(emojiPanel);
    const emojiForm=document.createElement("form");emojiForm.className="dc-settings-form dc-settings-expression-form";
    const emojiName=settingsInput("","text","имя_эмодзи");const emojiFile=settingsInput("");emojiFile.type="file";emojiFile.accept="image/png,image/jpeg,image/gif,image/webp";
    const addEmoji=document.createElement("button");addEmoji.type="submit";addEmoji.className="dc-settings-save";addEmoji.textContent="Загрузить эмодзи";
    emojiForm.append(settingsLabel("Имя (2–32, латиница/цифры/_)",emojiName),settingsLabel("Изображение (до 256 КБ)",emojiFile),addEmoji);emojiPanel.append(emojiForm);
    const stickerPanel=settingsPanel("СТИКЕРЫ");const stickerList=document.createElement("div");stickerList.className="dc-settings-expression-grid";stickerList.textContent="Загрузка стикеров…";stickerPanel.append(stickerList);main.append(stickerPanel);
    const stickerForm=document.createElement("form");stickerForm.className="dc-settings-form dc-settings-expression-form";
    const stickerName=settingsInput("","text","Название");const stickerTags=settingsInput("🔥","text","например 🔥");const stickerDesc=settingsInput("","text","Описание");const stickerFile=settingsInput("");stickerFile.type="file";stickerFile.accept="image/png,image/apng,image/gif,application/json";
    const addSticker=document.createElement("button");addSticker.type="submit";addSticker.className="dc-settings-save";addSticker.textContent="Загрузить стикер";
    stickerForm.append(settingsLabel("Название",stickerName),settingsLabel("Эмодзи-тег (Unicode)",stickerTags),settingsLabel("Описание",stickerDesc),settingsLabel("Файл (до 512 КБ)",stickerFile),addSticker);stickerPanel.append(stickerForm);
    try{
      const data=await serverSettingsRequest("emoji");emojiList.replaceChildren();stickerList.replaceChildren();
      (data.emojis||[]).forEach(item=>{
        const card=document.createElement("div");card.className="dc-expression-card";const img=document.createElement("img");img.src=item.url||("https://cdn.discordapp.com/emojis/"+item.id+".png");img.alt=item.name;
        const label=document.createElement("span");label.textContent=":"+item.name+":";
        const edit=settingsButton("Переименовать",async()=>{
          const next=prompt("Новое имя эмодзи (2–32 символа):",item.name);if(next===null)return;
          try{await serverSettingsRequest("emoji","PATCH",{name:next.trim()},item.id);await renderEmoji();showToast?.("Имя эмодзи изменено.");}catch(error){settingsError(emojiPanel,error);}
        });
        const del=settingsButton("Удалить",async()=>{if(!confirm("Удалить эмодзи :"+item.name+":?"))return;try{await serverSettingsRequest("emoji","DELETE",null,item.id);await renderEmoji();}catch(error){settingsError(emojiPanel,error);}},"danger");
        card.append(img,label,edit,del);emojiList.append(card);
      });
      if(!(data.emojis||[]).length)settingsEmpty(emojiList,"Эмодзи отсутствуют.");
      (data.stickers||[]).forEach(item=>{
        const card=document.createElement("div");card.className="dc-expression-card";const img=document.createElement("img");img.src="https://cdn.discordapp.com/stickers/"+item.id+".png?size=128";img.alt=item.name;
        const label=document.createElement("span");label.textContent=item.name;
        const edit=settingsButton("Изменить",async()=>{
          const nextName=prompt("Название стикера:",item.name);if(nextName===null)return;
          const nextTags=prompt("Эмодзи-тег (например 🔥):",item.tags||"🔥");if(nextTags===null)return;
          const nextDescription=prompt("Описание (можно оставить пустым):",item.description||"");if(nextDescription===null)return;
          try{await serverSettingsRequest("stickers","PATCH",{name:nextName.trim(),tags:nextTags.trim(),description:nextDescription.trim()},item.id);await renderEmoji();showToast?.("Стикер обновлён.");}catch(error){settingsError(stickerPanel,error);}
        });
        const del=settingsButton("Удалить",async()=>{if(!confirm("Удалить стикер «"+item.name+"»?"))return;try{await serverSettingsRequest("stickers","DELETE",null,item.id);await renderEmoji();}catch(error){settingsError(stickerPanel,error);}},"danger");
        card.append(img,label,edit,del);stickerList.append(card);
      });
      if(!(data.stickers||[]).length)settingsEmpty(stickerList,"Стикеры отсутствуют.");
    }catch(error){emojiList.replaceChildren();stickerList.replaceChildren();settingsError(emojiList,error);}
    emojiForm.addEventListener("submit",async event=>{
      event.preventDefault();if(!emojiFile.files?.[0]){settingsError(emojiPanel,new Error("Выбери изображение."));return;}
      const file=emojiFile.files[0];if(file.size>256*1024){settingsError(emojiPanel,new Error("Эмодзи должен быть не больше 256 КБ."));return;}
      const reader=new FileReader();reader.onload=async()=>{
        addEmoji.disabled=true;try{await serverSettingsRequest("emoji","POST",{name:emojiName.value.trim(),image:String(reader.result)});await renderEmoji();showToast?.("Эмодзи добавлен.");}
        catch(error){settingsError(emojiPanel,error);}finally{addEmoji.disabled=false;}
      };reader.readAsDataURL(file);
    });
    stickerForm.addEventListener("submit",async event=>{
      event.preventDefault();const file=stickerFile.files?.[0];if(!file){settingsError(stickerPanel,new Error("Выбери файл стикера."));return;}
      if(file.size>512*1024){settingsError(stickerPanel,new Error("Файл стикера должен быть не больше 512 КБ."));return;}
      const form=new FormData();form.append("name",stickerName.value.trim());form.append("tags",stickerTags.value.trim());form.append("description",stickerDesc.value.trim());form.append("file",file,file.name);
      addSticker.disabled=true;try{await serverSettingsRequest("stickers","POST",form);await renderEmoji();showToast?.("Стикер добавлен.");}
      catch(error){settingsError(stickerPanel,error);}finally{addSticker.disabled=false;}
    });
  };

  const renderEvents=async()=>{
    settingsHeading("События","Создавай внешние события и мероприятия в голосовых или Stage-каналах сервера.");
    const panel=settingsPanel("СОЗДАТЬ СОБЫТИЕ");const form=document.createElement("form");form.className="dc-settings-form";
    const name=settingsInput("","text","Название события");const description=settingsInput("","text","Описание");
    const type=settingsSelect([[3,"Внешнее событие"],[2,"Голосовой канал"],[1,"Stage-канал"]],3);
    const location=settingsInput("","text","Место проведения");const channel=settingsSelect([["","Выбери канал"]],"");
    const start=settingsInput("","datetime-local");const end=settingsInput("","datetime-local");
    const fields=document.createElement("div");fields.className="dc-settings-fields";
    fields.append(settingsLabel("Название",name),settingsLabel("Тип события",type),settingsLabel("Описание",description,true),settingsLabel("Место",location),settingsLabel("Канал",channel),settingsLabel("Начало",start),settingsLabel("Окончание",end));
    form.append(fields);
    const create=document.createElement("button");create.type="submit";create.className="dc-settings-save";create.textContent="Создать событие";form.append(create);panel.append(form);main.append(panel);
    const list=settingsPanel("СОБЫТИЯ СЕРВЕРА");list.textContent="Загрузка событий…";main.append(list);
    const loadEvents=async()=>{
      try{const items=await serverSettingsRequest("events");list.replaceChildren();if(!items.length){settingsEmpty(list,"Запланированных событий нет.");return;}
        items.forEach(item=>{
          const startDate=item.scheduled_start_time?new Date(item.scheduled_start_time).toLocaleString("ru-RU"):"";
          const subtitle=[startDate,item.entity_type===3?(item.entity_metadata?.location||"Внешнее событие"):(item.channel_id?"Канал "+item.channel_id:""),"Участников: "+(item.user_count??0)].filter(Boolean).join(" · ");
          const acts=[];
          if(item.status===1)acts.push(settingsButton("Изменить",async()=>{
            const nextName=prompt("Название события:",item.name||"");if(nextName===null)return;
            const nextDescription=prompt("Описание события:",item.description||"");if(nextDescription===null)return;
            const body={name:nextName.trim(),description:nextDescription.trim()};
            if(item.entity_type===3){
              const nextLocation=prompt("Место проведения:",item.entity_metadata?.location||"");if(nextLocation===null)return;
              if(!nextLocation.trim()){settingsError(list,new Error("Для внешнего события нужно место проведения."));return;}
              body.entity_metadata={location:nextLocation.trim()};
            }
            const nextStart=prompt("Новое время начала (ISO 8601, например 2026-12-01T18:00:00Z):",item.scheduled_start_time||"");
            if(nextStart===null)return;
            if(Number.isNaN(Date.parse(nextStart))){settingsError(list,new Error("Время начала должно быть корректной ISO-датой."));return;}
            body.scheduled_start_time=new Date(nextStart).toISOString();
            if(item.entity_type===3){
              const nextEnd=prompt("Новое время окончания (ISO 8601):",item.scheduled_end_time||"");
              if(nextEnd===null)return;
              if(Number.isNaN(Date.parse(nextEnd))||Date.parse(nextEnd)<=Date.parse(body.scheduled_start_time)){settingsError(list,new Error("Окончание должно быть позже начала."));return;}
              body.scheduled_end_time=new Date(nextEnd).toISOString();
            }
            try{await serverSettingsRequest("events","PATCH",body,item.id);showToast?.("Событие обновлено.");await loadEvents();}
            catch(error){settingsError(list,error);}
          }));
          if(item.status===1)acts.push(settingsButton("Отменить",async()=>{if(!confirm("Отменить событие «"+item.name+"»?"))return;try{await serverSettingsRequest("events","PATCH",{status:4},item.id);await loadEvents();}catch(error){settingsError(list,error);}},"danger"));
          acts.push(settingsButton("Удалить",async()=>{if(!confirm("Удалить событие «"+item.name+"»?"))return;try{await serverSettingsRequest("events","DELETE",null,item.id);await loadEvents();}catch(error){settingsError(list,error);}},"danger"));
          settingsRow(list,item.name,subtitle,acts);
        });
      }catch(error){list.replaceChildren();settingsError(list,error);}
    };
    try{const channels=await serverSettingsRequest("channels");channel.replaceChildren();channel.add(new Option("Выбери голосовой канал",""));(channels.channels||[]).filter(c=>["voice","stage"].includes(c.type)).forEach(c=>channel.add(new Option(c.name,c.id)));}
    catch(error){settingsError(panel,error);}
    type.addEventListener("change",()=>{const external=type.value==="3";location.disabled=!external;channel.disabled=external;});
    type.dispatchEvent(new Event("change"));
    form.addEventListener("submit",async event=>{
      event.preventDefault();if(!name.value.trim()||!start.value){settingsError(panel,new Error("Укажи название и время начала."));return;}
      const startDate=new Date(start.value),endDate=end.value?new Date(end.value):null;
      if(Number.isNaN(startDate.getTime())||startDate.getTime()<=Date.now()){settingsError(panel,new Error("Время начала должно быть в будущем."));return;}
      if(endDate&&endDate<=startDate){settingsError(panel,new Error("Время окончания должно быть позже начала."));return;}
      const body={name:name.value.trim(),description:description.value.trim(),entity_type:Number(type.value),scheduled_start_time:startDate.toISOString()};
      if(Number(type.value)===3){if(!location.value.trim()||!endDate){settingsError(panel,new Error("Для внешнего события укажи место и время окончания."));return;}body.entity_metadata={location:location.value.trim()};body.scheduled_end_time=endDate.toISOString();}
      else {if(!channel.value){settingsError(panel,new Error("Выбери голосовой или Stage-канал."));return;}body.channel_id=channel.value;if(endDate)body.scheduled_end_time=endDate.toISOString();}
      create.disabled=true;try{await serverSettingsRequest("events","POST",body);showToast?.("Событие создано.");await loadEvents();form.reset();}
      catch(error){settingsError(panel,error);}finally{create.disabled=false;}
    });
    await loadEvents();
  };

  const renderSection=async tab=>{
    if(tab==="channels")return renderChannels();
    if(tab==="members")return renderMembers();
    if(tab==="invites")return renderInvites();
    if(tab==="safety")return renderSafety();
    if(tab==="audit")return renderAudit();
    if(tab==="automod")return renderAutoMod();
    if(tab==="integrations")return renderIntegrations();
    if(tab==="emoji")return renderEmoji();
    if(tab==="events")return renderEvents();
  };
  const switchTab=tab=>{
    navButtons.forEach((button,key)=>button.classList.toggle("active",key===tab));
    if(tab==="overview")renderOverview();
    else if(tab==="roles")renderRoles();
    else renderSection(tab).catch(error=>{settingsHeading("Ошибка загрузки раздела");settingsError(main,error);});
  };
  navButtons.get("overview").addEventListener("click",()=>switchTab("overview"));
  navButtons.get("roles").addEventListener("click",()=>switchTab("roles"));
  navButtons.forEach((button,key)=>button.addEventListener("click",()=>switchTab(key)));
  card.append(head,layout);modal.append(card);
  modal.addEventListener("click",event=>{if(event.target===modal)modal.remove();});
  document.body.append(modal);
  switchTab("overview");
  document.addEventListener("keydown",function esc(event){if(event.key==="Escape"){modal.remove();document.removeEventListener("keydown",esc);}});
}
function dcRenderGuildChannels(data,list,title,guild){
  if(!list||dcActiveGuild?.id!==guild.id)return;
  if(title)title.textContent=data.guild?.name||guild.name;
  list.replaceChildren();
  const channels=data.channels||[],categories=data.categories||[];
  if(!channels.length){list.textContent="Нет доступных текстовых каналов или у бота нет права их просматривать.";return;}
  const grouped=new Map();
  channels.forEach(channel=>{const key=channel.category_id||"__none";if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(channel);});
  const ordered=[
    ...categories.filter(category=>grouped.has(category.id)).map(category=>({id:category.id,name:category.name})),
    ...(grouped.has("__none")?[{id:"__none",name:"БЕЗ КАТЕГОРИИ"}]:[])
  ];
  ordered.forEach(category=>{
    const heading=document.createElement("button");
    heading.type="button";heading.className="dc-channel-category";
    heading.setAttribute("aria-expanded","true");
    const chevron=document.createElement("span");chevron.className="dc-category-chevron";chevron.textContent="⌄";
    const label=document.createElement("span");label.className="dc-category-label";label.textContent=category.name;
    heading.append(chevron,label);
    const items=document.createElement("div");items.className="dc-channel-category-items";
    heading.addEventListener("click",()=>{
      const collapsed=heading.getAttribute("aria-expanded")==="true";
      heading.setAttribute("aria-expanded",String(!collapsed));
      items.hidden=collapsed;
    });
    list.append(heading,items);
    (grouped.get(category.id)||[]).forEach(channel=>{
      const button=document.createElement("button");button.type="button";button.className="dc-channel-item";button.dataset.channelId=channel.id;
      const hash=document.createElement("span");hash.className="dc-channel-symbol";hash.textContent=channel.type==="announcement"?"▤":"#";
      const name=document.createElement("span");name.textContent=channel.name;
      button.append(hash,name);
      if(!channel.can_send){const lock=document.createElement("small");lock.textContent="Только чтение";button.append(lock);}
      button.addEventListener("click",()=>dcOpenGuildChannel(channel));
      items.append(button);
    });
  });
}
async function dcOpenGuild(guild){
  if(!guild?.id)return;dcActiveGuild=guild;dcActiveChannel=null;dcActiveUser=null;dcActiveDmChannelId=null;dcClearReplyTarget();dcSetMode("guild");
  const list=document.getElementById("dcChannelList"),title=document.getElementById("dcChatTitle"),subtitle=document.getElementById("dcChatSubtitle"),input=document.getElementById("dcMessageInput"),send=document.getElementById("dcSendButton"),hint=document.getElementById("dcComposerHint"),card=document.getElementById("dcRecipientCard");
  if(title)title.textContent=guild.name;if(subtitle)subtitle.textContent="Выбери текстовый канал";if(input){input.value="";input.disabled=true;}if(send)send.disabled=true;if(hint)hint.textContent="Сообщения будут отправляться от имени Discord-бота.";if(card)card.textContent="Выбран сервер: "+guild.name;
  dcLoadGuildMembers(guild);
  const root=document.getElementById("dcChatMessages");if(root){root.innerHTML="";const welcome=document.createElement("div");welcome.className="dc-live-welcome";welcome.innerHTML='<div class="dc-live-welcome-icon">#</div><h1>'+dcEscape(guild.name)+'</h1><p>Выбери канал слева, чтобы читать историю и отправлять сообщения.</p>';root.append(welcome);}
  const cachedChannels=dcChannelsCacheByGuild.get(guild.id);
  if(cachedChannels){dcRenderGuildChannels(cachedChannels,list,title,guild);dcUpdateMentionPicker(document.getElementById("dcMessageInput"));return;}
  if(dcChannelsLoading.has(guild.id))return;
  dcChannelsLoading.add(guild.id);
  if(list)list.innerHTML='<div class="dc-live-loading">Загружаем список каналов…</div>';
  try{
    const data=await apiGet("/api/discord/guilds/"+encodeURIComponent(guild.id)+"/channels");if(dcActiveGuild?.id!==guild.id)return;dcChannelsCacheByGuild.set(guild.id,data);dcRenderGuildChannels(data,list,title,guild);dcUpdateMentionPicker(document.getElementById("dcMessageInput"));

  }catch(error){if(dcActiveGuild?.id===guild.id&&list)list.textContent=error.message;}finally{dcChannelsLoading.delete(guild.id);}
}
async function dcOpenGuildChannel(channel,silent=false){
  if(!channel?.id||!dcActiveGuild)return;
  if(dcActiveChannel?.id!==channel.id||dcActiveUser)dcClearReplyTarget();
  dcActiveChannel=channel;dcActiveUser=null;dcActiveDmChannelId=null;document.querySelectorAll(".dc-channel-item").forEach(x=>x.classList.toggle("active",x.dataset.channelId===channel.id));
  const title=document.getElementById("dcChatTitle"),subtitle=document.getElementById("dcChatSubtitle"),input=document.getElementById("dcMessageInput"),send=document.getElementById("dcSendButton"),hint=document.getElementById("dcComposerHint"),card=document.getElementById("dcRecipientCard"),root=document.getElementById("dcChatMessages");
  if(title)title.textContent="# "+channel.name;if(subtitle)subtitle.textContent=dcActiveGuild.name;if(input)input.disabled=!channel.can_send;if(send)send.disabled=!channel.can_send;if(hint)hint.textContent=channel.can_send?"Сообщение будет отправлено от имени бота.":"У бота нет права отправлять сообщения в этот канал.";if(card)card.textContent=dcActiveGuild.name+" · #"+channel.name;
  if(root&&!silent)root.innerHTML='<div class="dc-live-loading">Загружаем сообщения канала…</div>';
  try{const data=await apiGet("/api/discord/channels/"+encodeURIComponent(channel.id)+"/messages");if(dcActiveChannel?.id!==channel.id)return;dcRenderMessages(data.messages||[]);}
  catch(error){if(root){root.replaceChildren();const msg=document.createElement("div");msg.className="dc-live-error";msg.textContent=error.message;root.append(msg);}if(hint)hint.textContent="Не удалось загрузить канал.";}
}
function loadBotDiscord(){
  if(dcPollTimer)clearInterval(dcPollTimer);dcActiveUser=null;dcActiveChannel=null;dcActiveGuild=null;dcActiveDmChannelId=null;dcReplyTarget=null;
  const search=document.getElementById("dcUserSearch"),searchButton=document.getElementById("dcSearchButton"),refresh=document.getElementById("dcRefreshDms"),refreshChat=document.getElementById("dcRefreshChat"),form=document.getElementById("dcComposerForm");
  document.getElementById("dcServerSettingsButton")?.addEventListener("click",dcOpenServerSettings);
  document.getElementById("dcAccessibilityButton")?.addEventListener("click",dcOpenAccessibilitySettings);
  document.getElementById("dcBotAccountTrigger")?.addEventListener("click",dcOpenBotProfileSettings);
  document.getElementById("dcExitLive")?.addEventListener("click",()=>showPage("dashboard"));
  const closeMobileSidebar=()=>document.querySelector(".dc-live-app")?.classList.remove("dc-mobile-sidebar-open");
  document.getElementById("dcToggleSidebar")?.addEventListener("click",()=>{
    const app=document.querySelector(".dc-live-app");if(!app)return;
    const open=app.classList.toggle("dc-mobile-sidebar-open");
    document.getElementById("dcToggleSidebar")?.setAttribute("aria-expanded",String(open));
  });
  document.getElementById("dcGuildList")?.addEventListener("click",event=>{if(event.target.closest("[data-guild-id]"))closeMobileSidebar();});
  document.getElementById("dcDmList")?.addEventListener("click",event=>{if(event.target.closest(".dc-live-dm-item"))closeMobileSidebar();});
  document.getElementById("dcChannelList")?.addEventListener("click",event=>{if(event.target.closest(".dc-channel-item"))closeMobileSidebar();});
  document.querySelector(".dc-main")?.addEventListener("click",event=>{if(event.target.closest("#dcToggleSidebar"))return;closeMobileSidebar();});

  document.getElementById("dcToggleMembers")?.addEventListener("click",()=>{const layout=document.querySelector(".dc-live-layout");if(!layout)return;const hidden=layout.classList.toggle("dc-hide-members");const button=document.getElementById("dcToggleMembers");button?.setAttribute("aria-pressed",String(!hidden));if(button)button.title=hidden?"Показать участников":"Скрыть участников";});
  dcLoadBotProfile();
  searchButton?.addEventListener("click",dcSearchUsers);search?.addEventListener("keydown",event=>{if(event.key==="Enter"){event.preventDefault();dcSearchUsers();}});
  document.getElementById("dcMemberSearch")?.addEventListener("input",dcRenderGuildMembers);
  refresh?.addEventListener("click",()=>{if(dcActiveGuild)dcOpenGuild(dcActiveGuild);else dcLoadConversationList();});
  refreshChat?.addEventListener("click",()=>{if(dcActiveChannel)dcOpenGuildChannel(dcActiveChannel);else if(dcActiveUser)dcOpenConversation(dcActiveUser);});
  document.getElementById("dcHomeButton")?.addEventListener("click",()=>{dcActiveGuild=null;dcActiveChannel=null;dcActiveUser=null;dcActiveDmChannelId=null;dcClearReplyTarget();dcSetMode("dm");dcLoadConversationList();});
  form?.addEventListener("submit",dcSendMessage);
  dcApplyAccessibilityPreferences();
  const messageInput=document.getElementById("dcMessageInput");
  messageInput?.addEventListener("input",()=>{dcUpdateMentionPicker(messageInput);messageInput.style.height="auto";messageInput.style.height=Math.min(messageInput.scrollHeight,130)+"px";});
  messageInput?.addEventListener("keydown",event=>{
    if(dcHandleMentionKeydown(event,messageInput))return;
    if(event.key==="Enter"&&!event.shiftKey&&!event.isComposing){
      event.preventDefault();
      if(!messageInput.disabled)form?.requestSubmit();
    }
  });
  document.getElementById("dcEmojiButton")?.addEventListener("click",dcToggleEmojiPicker);
  document.addEventListener("click",event=>{
    if(!event.target.closest("#dcEmojiPicker")&&!event.target.closest("#dcEmojiButton"))dcCloseEmojiPicker();
    if(!event.target.closest("#dcMentionPicker")&&!event.target.closest("#dcMessageInput"))dcCloseMentionPicker();
  });
  const attachButton=document.getElementById("dcAttachButton"),fileInput=document.getElementById("dcFileInput"),filePreview=document.getElementById("dcFilePreview"),composerHint=document.getElementById("dcComposerHint");
  attachButton?.addEventListener("click",()=>fileInput?.click());
  let dcPreviewObjectUrls=[];
  const renderComposerFiles=()=>{
    if(!filePreview||!fileInput)return;
    dcPreviewObjectUrls.forEach(url=>URL.revokeObjectURL(url));dcPreviewObjectUrls=[];
    filePreview.replaceChildren();
    const files=Array.from(fileInput.files||[]);
    filePreview.hidden=!files.length;
    files.forEach((file,index)=>{
      const item=document.createElement("div");item.className="dc-file-preview-item";
      if(file.type.startsWith("image/")){
        const thumb=document.createElement("img");thumb.alt="";thumb.src=URL.createObjectURL(file);dcPreviewObjectUrls.push(thumb.src);item.append(thumb);
      }else{
        const glyph=document.createElement("span");glyph.className="dc-file-preview-glyph";glyph.textContent="📎";item.append(glyph);
      }
      const label=document.createElement("span");label.className="dc-file-preview-name";label.textContent=file.name+" · "+(file.size/1024/1024).toFixed(2)+" МБ";item.append(label);
      const remove=document.createElement("button");remove.type="button";remove.className="dc-file-preview-remove";remove.title="Убрать вложение";remove.setAttribute("aria-label","Убрать "+file.name);remove.textContent="×";
      remove.addEventListener("click",()=>{
        const transfer=new DataTransfer();Array.from(fileInput.files||[]).forEach((entry,i)=>{if(i!==index)transfer.items.add(entry);});
        fileInput.files=transfer.files;renderComposerFiles();
      });
      item.append(remove);filePreview.append(item);
    });
  };
  const addComposerFiles=incoming=>{
    if(!fileInput||!incoming.length)return;
    const existing=Array.from(fileInput.files||[]),combined=[...existing,...incoming],unique=[],seen=new Set();
    combined.forEach(file=>{
      const signature=[file.name,file.size,file.type,file.lastModified].join("|");
      if(!seen.has(signature)){seen.add(signature);unique.push(file);}
    });
    if(unique.length>10){if(composerHint)composerHint.textContent="Можно прикрепить не больше 10 файлов.";return;}
    if(unique.some(file=>file.size>8*1024*1024)){if(composerHint)composerHint.textContent="Каждый файл должен быть не больше 8 МБ.";return;}
    if(unique.reduce((sum,file)=>sum+file.size,0)>25*1024*1024){if(composerHint)composerHint.textContent="Общий размер файлов не должен превышать 25 МБ.";return;}
    const transfer=new DataTransfer();unique.forEach(file=>transfer.items.add(file));fileInput.files=transfer.files;renderComposerFiles();
    if(composerHint)composerHint.textContent="Добавлено вложений: "+unique.length+". Нажми ➤ для отправки.";
  };
  fileInput?.addEventListener("change",renderComposerFiles);
  messageInput?.addEventListener("paste",event=>{
    const clipboard=event.clipboardData;
    if(!clipboard||messageInput.disabled||!fileInput)return;
    const pasted=[];
    Array.from(clipboard.items||[]).forEach(item=>{
      if(item.kind!=="file")return;
      const file=item.getAsFile();if(file)pasted.push(file);
    });
    Array.from(clipboard.files||[]).forEach(file=>pasted.push(file));
    if(!pasted.length)return;
    event.preventDefault();
    const named=pasted.map((file,index)=>{
      if(file.name)return file;
      const extension=(file.type.split("/")[1]||"bin").replace(/[^a-z0-9.+-]/gi,"");
      return new File([file],"clipboard-"+(Date.now())+"-"+index+"."+extension,{type:file.type||"application/octet-stream",lastModified:file.lastModified||Date.now()});
    });
    addComposerFiles(named);
  });
  dcSetMode("dm");dcLoadConversationList();dcLoadGuilds();
  dcPollTimer=setInterval(()=>{if(!document.getElementById("dcDmList")){clearInterval(dcPollTimer);dcPollTimer=null;return;}if(dcActiveGuild){const guildId=dcActiveGuild.id;apiGet("/api/discord/guilds/"+encodeURIComponent(guildId)+"/presence").then(data=>{if(dcActiveGuild?.id!==guildId)return;const states=new Map((data.members||[]).map(item=>[String(item.id),item]));dcMemberCache=dcMemberCache.map(member=>({...member,...(states.get(String(member.id))||{})}));dcMemberCacheByGuild.set(guildId,dcMemberCache);dcRenderGuildMembers();}).catch(()=>{});}if(dcActiveChannel)dcOpenGuildChannel(dcActiveChannel,true);else if(dcActiveUser)dcOpenConversation(dcActiveUser,true);else if(!dcActiveGuild)dcLoadConversationList();},15000);
}

async function apiGet(url){
  const response=await fetch(url,{credentials:"same-origin"});
  const data=await response.json();
  if(!response.ok)throw new Error(data.detail||"Ошибка запроса.");
  return data;
}
async function loadPlayers(section){
  const result=section.querySelector("#playersResult"),refresh=section.querySelector("#refreshPlayers"),search=section.querySelector("#playerSearch");
  const sheetsToggle=section.querySelector("#openSheetsStaff"),sheetsManager=section.querySelector("#sheetsStaffManager");
  if(sheetsToggle){
    sheetsToggle.hidden=!["co_adm","adm","full"].includes(currentAccessLevel);
    sheetsToggle.addEventListener("click",async()=>{sheetsManager.hidden=!sheetsManager.hidden;if(!sheetsManager.hidden)await loadSheetsStaff(section);});
    section.querySelector("#refreshSheetsStaff")?.addEventListener("click",()=>loadSheetsStaff(section));
  }
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
      const name=document.createElement("strong");name.textContent=p.username||"Участник GastWorld";
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
async function loadSheetsStaff(section){
  const result=section.querySelector("#sheetsStaffResult");
  if(!result)return;
  result.className="empty-state";result.textContent="Получаем участников с ролью Команда медиа…";
  try{
    const data=await apiGet("/api/sheets/staff-candidates");
    const candidates=data.candidates||[];
    if(!candidates.length){result.textContent="Все участники с ролью Команда медиа уже внесены в базу профилей.";return;}
    const list=document.createElement("div");list.className="sheets-staff-list";
    for(const candidate of candidates){
      const card=document.createElement("form");card.className="sheets-staff-card";
      const header=document.createElement("div");header.className="sheets-staff-identity";
      const name=document.createElement("strong");name.textContent=candidate.username||"Участник";
      const id=document.createElement("small");id.textContent="@"+(candidate.discord_username||"")+" · Discord ID: "+candidate.user_id;
      header.append(name,id);
      const grid=document.createElement("div");grid.className="sheets-staff-fields";
      const nickname=document.createElement("input");nickname.className="panel-search";nickname.placeholder="Никнейм для таблицы";nickname.value=candidate.username||"";nickname.required=true;nickname.maxLength=100;
      const position=document.createElement("select");position.className="panel-search";position.required=true;
      const choose=document.createElement("option");choose.value="";choose.textContent="Выбери должность";choose.disabled=true;choose.selected=true;
      const tt=document.createElement("option");tt.value="TT";tt.textContent="TikTok (TT)";
      const yt=document.createElement("option");yt.value="YT";yt.textContent="YouTube (YT)";position.append(choose,tt,yt);
      const profile=document.createElement("input");profile.className="panel-search";profile.placeholder="Ссылка на TikTok / YouTube";profile.type="url";profile.required=true;
      const channel=document.createElement("input");channel.className="panel-search";channel.placeholder="ID личного Discord-канала";channel.inputMode="numeric";channel.required=true;channel.value=candidate.personal_channel_id||"";
      const add=document.createElement("button");add.className="member-action give-warn";add.type="submit";add.textContent="Добавить в таблицу";
      const error=document.createElement("p");error.className="sheets-staff-error";error.hidden=true;
      grid.append(nickname,position,profile,channel);
      card.append(header,grid,error,add);
      card.addEventListener("submit",async event=>{
        event.preventDefault();error.hidden=true;add.disabled=true;add.textContent="Добавляем…";
        try{
          const saved=await apiPost("/api/sheets/staff-add",{user_id:candidate.user_id,nickname:nickname.value.trim(),position:position.value,profile_url:profile.value.trim(),personal_channel_id:channel.value.trim()});
          if(saved.sheets_synced){showToast("Участник добавлен в Google Sheets.");}
          else{showToast("Профиль сохранён в базе. Проверь Google Sheets и запусти /sheets_sync.");}
          card.remove();
          if(!list.children.length){result.className="empty-state";result.textContent="Все найденные участники обработаны.";}
        }catch(errorValue){error.textContent=errorValue.message||"Не удалось добавить участника.";error.hidden=false;add.disabled=false;add.textContent="Добавить в таблицу";}
      });
      list.append(card);
    }
    result.className="sheets-staff-result";result.replaceChildren(list);
  }catch(error){result.className="empty-state";result.textContent=error.message||"Не удалось получить список участников.";}
}
function openWarnDialog(userId,action){
  const existing=document.getElementById("warnActionModal");if(existing)existing.remove();
  const isAdd=action==="warn";
  const modal=document.createElement("div");modal.id="warnActionModal";modal.className="warn-modal";
  const dialog=document.createElement("form");dialog.className="warn-modal-card";dialog.setAttribute("role","dialog");dialog.setAttribute("aria-modal","true");
  const close=document.createElement("button");close.type="button";close.className="warn-modal-close";close.textContent="×";close.setAttribute("aria-label","Закрыть");
  const eyebrow=document.createElement("span");eyebrow.className="warn-modal-eyebrow";eyebrow.textContent="GASTWORLD • MODERATION";
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
      hero.innerHTML='<div class="requests-hero-copy"><span class="requests-kicker">GASTWORLD • APPLICATION CENTER</span><h2>Центр заявок</h2><p>Все обращения сообщества собраны в одном месте.</p></div><div class="requests-hero-symbol" aria-hidden="true">▤</div>';
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
  const eyebrow=document.createElement("span");eyebrow.className="action-modal-eyebrow";eyebrow.textContent="GASTWORLD • APPLICATION CENTER";
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
  const eyebrow=document.createElement("span");eyebrow.className="action-modal-eyebrow";eyebrow.textContent="GASTWORLD • APPLICATION CENTER";
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
      hero.innerHTML='<div class="shop-hero-copy"><span class="shop-kicker">GASTWORLD • REWARDS</span><h2>Магазин</h2><p>Выбирай награды, наборы и привилегии за баллы.</p><span class="shop-hero-note">✦ Твой прогресс — твои преимущества</span></div><div class="shop-hero-art" aria-hidden="true"><span class="hero-orbit orbit-one">✦</span><span class="hero-crown">👑</span><span class="hero-orbit orbit-two">✧</span></div>';
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
  const note=document.createElement("p");note.className="shop-modal-note";note.textContent="После подтверждения баллы спишутся с твоего баланса. Обязательно укажи правильный ник Minecraft: без него администрация не сможет выдать покупку. Уведомление о заказе придёт в твой личный Discord-канал.";
  const balance=document.createElement("div");balance.className="shop-modal-balance";balance.textContent="Проверяем баланс…";
  const nickLabel=document.createElement("label");nickLabel.className="shop-nick-label";nickLabel.textContent="Ник в Minecraft (обязательно)";
  const nickInput=document.createElement("input");nickInput.className="shop-nick-input";nickInput.type="text";nickInput.name="minecraft_nick";nickInput.autocomplete="off";nickInput.maxLength=16;nickInput.placeholder="Введите свой ник";nickInput.required=true;nickInput.pattern="[A-Za-z0-9_]{3,16}";nickLabel.append(nickInput);
  const confirm=document.createElement("button");confirm.className="shop-buy-button";confirm.type="button";confirm.textContent="Подтвердить покупку";
  const cancel=document.createElement("button");cancel.className="shop-modal-cancel";cancel.type="button";cancel.textContent="Отмена";
  const status=document.createElement("p");status.className="shop-modal-status";status.setAttribute("aria-live","polite");
  let requestId=(globalThis.crypto?.randomUUID?.()||("wg-"+Date.now()+"-"+Math.random().toString(36).slice(2)));
  let currentBalance=null;
  const dismiss=()=>modal.remove();
  close.addEventListener("click",dismiss);cancel.addEventListener("click",dismiss);modal.addEventListener("click",e=>{if(e.target===modal)dismiss();});
  confirm.addEventListener("click",async()=>{
    if(confirm.disabled)return;
    confirm.disabled=true;cancel.disabled=true;confirm.textContent="Оформляем покупку…";status.textContent="";
    try{
      const minecraftNick=nickInput.value.trim();
      if(!/^[A-Za-z0-9_]{3,16}$/.test(minecraftNick)){
        status.textContent="Введи ник Minecraft: 3–16 символов, латиница, цифры и _.";
        confirm.disabled=false;cancel.disabled=false;confirm.textContent="Подтвердить покупку";nickInput.focus();return;
      }
      const result=await apiPost("/api/shop/purchase",{item:item.name,request_id:requestId,minecraft_nick:minecraftNick});
      balance.textContent="Остаток: "+Number(result.balance||0).toLocaleString("ru-RU")+" баллов";
      note.textContent=result.notification_sent?"Покупка успешно оформлена. Уведомление отправлено в твой личный Discord-канал. Товар будет выдан администрацией.":(result.message||"Покупка оформлена, но уведомление не отправлено.");
      status.textContent="Покупка №"+result.purchase_id+" оформлена.";
      confirm.textContent="Готово";confirm.disabled=true;cancel.textContent="Закрыть";cancel.disabled=false;
      confirm.onclick=dismiss;
      if(typeof loadMyBalance==="function")loadMyBalance();
    }catch(error){
      status.textContent=error.message;confirm.textContent="Повторить покупку";confirm.disabled=false;cancel.disabled=false;
    }
  });
  dialog.append(close,symbol,tag,title,price,balance,nickLabel,note,status,confirm,cancel);modal.append(dialog);document.body.append(modal);
  apiGet("/api/me/balance").then(data=>{
    currentBalance=Number(data.balance||0);
    balance.textContent="Твой баланс: "+currentBalance.toLocaleString("ru-RU")+" баллов";
    if(currentBalance<Number(item.price)){confirm.disabled=true;status.textContent="Не хватает "+(Number(item.price)-currentBalance).toLocaleString("ru-RU")+" баллов.";}
  }).catch(error=>{balance.textContent="Не удалось загрузить баланс";status.textContent=error.message;confirm.disabled=true;});
  nickInput.addEventListener("input",()=>{if(nickInput.value.trim())status.textContent="";});
  close.focus();
}


async function loadTickets(section){
  const root=section.querySelector("#ticketsResult"),refresh=section.querySelector("#refreshTickets");
  const acceptanceState=section.querySelector("#ticketAcceptanceState"),toggle=section.querySelector("#toggleTicketAcceptance");
  if(!root)return;
  let accepting=true;
  const syncAcceptance=async()=>{
    if(!acceptanceState||!toggle)return;
    toggle.disabled=true;
    try{
      const state=await apiGet("/api/tickets/acceptance");accepting=!!state.accepting;
      acceptanceState.textContent=accepting?"Приём новых тикетов открыт":"Приём новых тикетов закрыт";
      acceptanceState.dataset.state=accepting?"open":"closed";
      toggle.textContent=accepting?"Закрыть приём":"Открыть приём";toggle.disabled=false;
    }catch(error){acceptanceState.textContent="Не удалось получить состояние приёма";toggle.textContent="Повторить";toggle.disabled=false;throw error;}
  };
  toggle?.addEventListener("click",async()=>{
    toggle.disabled=true;
    try{
      const result=await apiPost("/api/tickets/acceptance",{accepting:!accepting});
      accepting=!!result.accepting;
      acceptanceState.textContent=accepting?"Приём новых тикетов открыт":"Приём новых тикетов закрыт";
      acceptanceState.dataset.state=accepting?"open":"closed";
      toggle.textContent=accepting?"Закрыть приём":"Открыть приём";
      showToast(accepting?"Приём новых тикетов открыт.":"Приём новых тикетов закрыт.","success");
    }catch(error){showToast(error.message||"Не удалось изменить приём тикетов.","error");}
    finally{toggle.disabled=false;}
  });
  const load=async()=>{
    refresh.disabled=true;root.innerHTML='<div class="empty-state">Загружаем тикеты…</div>';
    try{
      const data=await apiGet("/api/tickets"),tickets=data.tickets||[];
      await syncAcceptance();
      root.replaceChildren();
      if(!tickets.length){const empty=document.createElement("div");empty.className="empty-state";empty.innerHTML="<strong>Тикетов пока нет</strong><p>Новые обращения появятся здесь после создания тикета в Discord.</p>";root.append(empty);return;}
      tickets.forEach(ticket=>{
        const card=document.createElement("article");card.className="ticket-card";
        const head=document.createElement("div");head.className="ticket-card-head";
        const title=document.createElement("strong");title.textContent=ticket.subject||"Без темы";
        const status=document.createElement("span");status.className="ticket-status "+ticket.status;status.textContent=({open:"Открыт",closed:"Закрыт",resolved:"Решено"})[ticket.status]||ticket.status;head.append(title,status);
        const meta=document.createElement("div");meta.className="ticket-meta";meta.textContent=(ticket.username||"Участник")+" · Discord ID "+ticket.user_id+" · "+(ticket.created_at||"");
        const desc=document.createElement("p");desc.className="ticket-description";desc.textContent=ticket.description||"Описание отсутствует.";
        const actions=document.createElement("div");actions.className="ticket-actions";
        const link=document.createElement("a");link.href="https://discord.com/channels/1492974397001171176/"+encodeURIComponent(ticket.channel_id);link.target="_blank";link.rel="noopener noreferrer";link.className="ticket-open-link";link.textContent="Открыть канал Discord";actions.append(link);
        [["open","Переоткрыть"],["closed","Закрыть"],["resolved","Решено"]].forEach(([value,label])=>{
          if(ticket.status===value)return;
          const button=document.createElement("button");button.type="button";button.className="ticket-action-button";button.textContent=label;
          button.addEventListener("click",async()=>{button.disabled=true;try{await apiPost("/api/tickets/"+encodeURIComponent(ticket.channel_id)+"/status",{status:value});await load();}catch(error){showToast(error.message||"Не удалось изменить тикет.","error");button.disabled=false;}});
          actions.append(button);
        });
        card.append(head,meta,desc,actions);root.append(card);
      });
    }catch(error){root.innerHTML="";const empty=document.createElement("div");empty.className="empty-state";empty.textContent=error.message||"Не удалось загрузить тикеты.";root.append(empty);}
    finally{refresh.disabled=false;}
  };
  refresh?.addEventListener("click",load);await load();
}

async function loadMessages(section){
  const root=section.querySelector("#messagesResult");
  const refresh=section.querySelector("#refreshMessageChannels");
  if(!root)return;
  root.innerHTML='<div class="empty-state">Загружаем список серверов Discord…</div>';
  try{
    const initial=await apiGet("/api/messages/channels?guild_id=1492974397001171176");
    const servers=initial.servers||[];
    if(!servers.length)throw new Error("Список серверов Discord недоступен.");
    let activeGuildId=initial.guild_id||"1492974397001171176";
    let data=initial, channels=initial.channels||[];
    root.innerHTML=`
      <div class="messages-compose">
        <div class="messages-form">
          <label class="messages-label">Сервер Discord
            <select id="messageGuild" class="messages-control"></select>
          </label>
          <label class="messages-label">Канал Discord
            <select id="messageChannel" class="messages-control"></select>
          </label>
          <label class="messages-label">Текст сообщения <span>необязательно; подпись отправителя добавится автоматически</span>
            <textarea id="messageContent" class="messages-control" rows="4" maxlength="1750" placeholder="Напиши сообщение от имени GastWorld…"></textarea>
          </label>
          <label class="messages-label">Файлы <span>можно добавлять по несколько раз — файлы объединяются; до 10 файлов, до 8 МБ каждый, всего до 25 МБ</span>
            <input id="messageFiles" class="messages-control messages-file-input" type="file" multiple>
          </label>
          <div id="messageFilesPreview" class="messages-attachments-preview" hidden></div>
          <div class="messages-section-caption">EMBED-ПАНЕЛЬ <span>необязательно</span></div>
          <label class="messages-label">Заголовок Embed
            <input id="embedTitle" class="messages-control" maxlength="256" placeholder="Например: GASTWORLD • ОБЪЯВЛЕНИЕ">
          </label>
          <label class="messages-label">Описание Embed
            <textarea id="embedDescription" class="messages-control" rows="5" maxlength="4096" placeholder="Текст внутри Embed…"></textarea>
          </label>
          <label class="messages-label">Цвет Embed
            <div class="messages-color-row"><input id="embedColor" type="color" value="#8b6bd6"><code id="embedColorText">#8B6BD6</code></div>
          </label>
          <div class="messages-form-footer"><span id="messageStatus" class="messages-status">Отправка доступна уровням Adm и Full.</span><button id="sendDiscordMessage" class="messages-send-button" type="button">Отправить в Discord</button></div>
        </div>
        <aside class="messages-preview-wrap"><div class="messages-preview-heading">ПРЕДПРОСМОТР</div><div class="messages-preview-meta"><span class="messages-meta-item"><small>ОТПРАВИТЕЛЬ ПАНЕЛИ</small><strong id="messagePreviewSender">Администратор</strong></span><span class="messages-meta-arrow">→</span><span class="messages-meta-item"><small>КАНАЛ ПОЛУЧАТЕЛЬ</small><strong id="messagePreviewChannel">общий-чат</strong></span></div><div class="discord-preview"><div class="discord-preview-avatar" id="messagePreviewBotAvatar">G</div><div class="discord-preview-body"><strong>GastWorld <small>БОТ</small></strong><p id="messagePreviewContent" class="discord-preview-content">Текст сообщения появится здесь.</p><div id="embedPreview" class="discord-embed-preview" hidden><div id="embedPreviewTitle" class="discord-embed-title"></div><div id="embedPreviewDescription" class="discord-embed-description"></div></div></div></div><div id="messagePreviewImageWrap" class="discord-image-preview" hidden><img id="messagePreviewImage" alt="Изображение к сообщению"></div><div id="messagePreviewAttribution" class="discord-attribution-preview">— Отправитель: Администратор<br>Отправлено через GastWorld Control Panel</div></div><p class="messages-preview-note">Внизу сообщения автоматически появится подпись отправителя.</p></aside>
      </div><section class="messages-incoming"><div class="messages-incoming-head"><div><h3>Сообщения игроков</h3><p>Входящие сообщения из выбранного Discord-канала</p></div><button id="refreshIncomingMessages" class="text-button" type="button">Обновить</button></div><div id="incomingMessagesFeed" class="messages-incoming-feed"><div class="empty-state">Загружаем сообщения…</div></div></section>`;
    const guildSelect=root.querySelector("#messageGuild");
    const channelSelect=root.querySelector("#messageChannel");
    const fillChannels=(items)=>{
      channels=items||[];
      channelSelect.replaceChildren();
      channels.forEach(ch=>{
        const option=document.createElement("option");option.value=ch.id;option.textContent=(ch.parent_name?ch.parent_name+" / ":"")+ch.name;channelSelect.append(option);
      });
      if(!channels.length){
        const option=document.createElement("option");option.value="";option.textContent="Нет доступных текстовых каналов";channelSelect.append(option);
      }
    };
    servers.forEach(server=>{
      const option=document.createElement("option");option.value=server.id;option.textContent=server.name;guildSelect.append(option);
    });
    guildSelect.value=activeGuildId;
    fillChannels(channels);
    const content=root.querySelector("#messageContent"),title=root.querySelector("#embedTitle"),description=root.querySelector("#embedDescription"),color=root.querySelector("#embedColor"),filesInput=root.querySelector("#messageFiles"),filesPreview=root.querySelector("#messageFilesPreview"),previewSender=root.querySelector("#messagePreviewSender"),attributionPreview=root.querySelector("#messagePreviewAttribution");
    const previewContent=root.querySelector("#messagePreviewContent"),preview=root.querySelector("#embedPreview"),previewTitle=root.querySelector("#embedPreviewTitle"),previewDescription=root.querySelector("#embedPreviewDescription"),previewChannel=root.querySelector("#messagePreviewChannel"),status=root.querySelector("#messageStatus"),send=root.querySelector("#sendDiscordMessage"),colorText=root.querySelector("#embedColorText");
    const botPreviewAvatar=root.querySelector("#messagePreviewBotAvatar");
    const botProfile=initial.bot_profile||{};
    if(botPreviewAvatar){
      if(botProfile.avatar_url){const avatarImage=document.createElement("img");avatarImage.src=botProfile.avatar_url;avatarImage.alt="Аватар GastWorld";avatarImage.onerror=()=>{botPreviewAvatar.textContent="G";};botPreviewAvatar.replaceChildren(avatarImage);}
      else botPreviewAvatar.textContent=(botProfile.username||"GastWorld").trim().slice(0,1).toUpperCase()||"G";
    }
    const previewBotName=root.querySelector(".discord-preview-body > strong");
    if(previewBotName&&botProfile.username)previewBotName.childNodes[0].textContent=botProfile.username+" ";
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
      attributionPreview.innerHTML="— Отправитель: "+senderLabel.replace(/[&<>"]/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]))+"<br>Отправлено через GastWorld Control Panel";
    };
    [content,title,description,color].forEach(el=>el.addEventListener("input",updatePreview));
    channelSelect.addEventListener("change",updatePreview);
    let selectedMessageFiles=[];
    const syncMessageFiles=()=>{
      const transfer=new DataTransfer();
      selectedMessageFiles.forEach(file=>transfer.items.add(file));
      filesInput.files=transfer.files;
    };
    const renderFilesPreview=()=>{
      filesPreview.replaceChildren();
      const selected=selectedMessageFiles;
      filesPreview.hidden=!selected.length;
      selected.forEach((file,index)=>{
        const row=document.createElement("div");row.className="messages-attachment-item";
        const icon=document.createElement("span");icon.className="messages-attachment-icon";icon.textContent="▤";
        const info=document.createElement("span");info.className="messages-attachment-info";
        const name=document.createElement("strong");name.textContent=file.name;
        const size=document.createElement("small");size.textContent=file.size<1024*1024?(file.size/1024).toFixed(1)+" КБ":(file.size/1024/1024).toFixed(2)+" МБ";
        info.append(name,size);
        const remove=document.createElement("button");remove.type="button";remove.className="messages-attachment-remove";remove.textContent="×";remove.title="Убрать файл";
        remove.addEventListener("click",()=>{selectedMessageFiles=selectedMessageFiles.filter((item,i)=>i!==index);syncMessageFiles();renderFilesPreview();});
        row.append(icon,info,remove);filesPreview.append(row);
      });
    };
    filesInput.addEventListener("change",()=>{
      const incoming=Array.from(filesInput.files||[]);
      const existing=selectedMessageFiles.slice();
      const merged=existing.slice();
      incoming.forEach(file=>{
        if(!merged.some(item=>item.name===file.name&&item.size===file.size&&item.lastModified===file.lastModified))merged.push(file);
      });
      if(merged.length>10){status.textContent="Можно прикрепить не больше 10 файлов. Лишние файлы не добавлены.";status.className="messages-status error";selectedMessageFiles=merged.slice(0,10);}
      else selectedMessageFiles=merged;
      syncMessageFiles();renderFilesPreview();
    });
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
          const channelBadge=document.createElement("span");channelBadge.className="incoming-message-channel";channelBadge.textContent="В GastWorld";
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
    channelSelect.addEventListener("change",()=>{updatePreview();loadIncoming();});
    guildSelect.addEventListener("change",async()=>{
      const nextGuildId=guildSelect.value;
      guildSelect.disabled=true;
      channelSelect.disabled=true;
      incomingFeed.innerHTML='<div class="empty-state">Загружаем каналы выбранного сервера…</div>';
      try{
        const next=await apiGet("/api/messages/channels?guild_id="+encodeURIComponent(nextGuildId));
        activeGuildId=next.guild_id;data=next;
        fillChannels(next.channels||[]);
        updatePreview();
        await loadIncoming();
        status.textContent="Выбран сервер: "+(next.guild_name||"Discord");
        status.className="messages-status";
      }catch(error){
        status.textContent=error.message||"Не удалось загрузить сервер.";
        status.className="messages-status error";
      }finally{guildSelect.disabled=false;channelSelect.disabled=false;}
    });
    loadIncoming();
    const incomingPoll=window.setInterval(()=>{if(!section.isConnected){window.clearInterval(incomingPoll);return;}if(!document.hidden)loadIncoming();},10000);
    send.addEventListener("click",async()=>{
      const body=content.value.trim(),embedTitle=title.value.trim(),embedDescription=description.value.trim(),files=selectedMessageFiles.slice();
      if(!body&&!embedTitle&&!embedDescription&&!files.length){status.textContent="Добавь текст, Embed или хотя бы один файл.";status.className="messages-status error";return;}
      if(files.length>10){status.textContent="Можно прикрепить не больше 10 файлов.";status.className="messages-status error";return;}
      if(files.some(file=>file.size>8*1024*1024)){status.textContent="Каждый файл должен быть не больше 8 МБ.";status.className="messages-status error";return;}
      if(files.reduce((sum,file)=>sum+file.size,0)>25*1024*1024){status.textContent="Общий размер файлов не должен превышать 25 МБ.";status.className="messages-status error";return;}
      send.disabled=true;send.textContent="Отправляем…";status.textContent="Загружаем сообщение и файлы в Discord…";status.className="messages-status";
      try{
        const form=new FormData();
        form.append("payload_json",JSON.stringify({channel_id:channelSelect.value,content:body,embed:embedTitle||embedDescription?{title:embedTitle,description:embedDescription,color:color.value}:null}));
        files.forEach(file=>form.append("files",file,file.name));
        const response=await fetch("/api/messages/send",{method:"POST",credentials:"same-origin",body:form});
        const raw=await response.text();let result={};try{result=raw?JSON.parse(raw):{};}catch{throw new Error("Сервер вернул неожиданный ответ (HTTP "+response.status+").");}
        if(!response.ok)throw new Error(result.detail||"Не удалось отправить сообщение.");
        status.textContent="✓ Сообщение отправлено в "+(channels.find(c=>c.id===channelSelect.value)?.name||"Discord")+(result.attachments?" · файлов: "+result.attachments:"");
        status.className="messages-status success";
        if(typeof showToast==="function")showToast("Сообщение успешно отправлено в Discord.");
        content.value="";selectedMessageFiles=[];filesInput.value="";renderFilesPreview();updatePreview();
      }catch(error){status.textContent=error.message;status.className="messages-status error";}
      finally{send.disabled=false;send.textContent="Отправить в Discord";}
    });;
  }catch(error){root.innerHTML="";const box=document.createElement("div");box.className="empty-state";const title=document.createElement("strong");title.textContent="Не удалось загрузить каналы";const detail=document.createElement("p");detail.textContent=error.message;box.append(title,detail);root.append(box);}
  refresh?.addEventListener("click",()=>loadMessages(section));
}
