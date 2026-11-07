const pageNames={dashboard:"Главная",players:"Игроки",requests:"Заявки",shop:"Магазин",messages:"Сообщения",logs:"Логи",console:"Консоль",access:"Доступ",settings:"Настройки"};
const content=document.getElementById("pageContent");
const breadcrumb=document.getElementById("breadcrumb");
const sidebar=document.getElementById("sidebar");
const overlay=document.getElementById("overlay");
let currentAccessLevel="none";
function showPage(page){
  if(!pageNames[page]) return;
  if(page==="access" && !["adm","full"].includes(currentAccessLevel)){return;}
  document.querySelectorAll(".nav-item").forEach(button=>button.classList.toggle("active",button.dataset.page===page));
  breadcrumb.textContent=pageNames[page];
  if(page!=="dashboard"){
    const descriptions={players:"Управление участниками, балансами, варнами и ролями.",requests:"Проверка заявок на вступление и получение баллов.",shop:"Настройка товаров, наборов, донатов и стоимости.",messages:"Отправка сообщений и Embed-панелей в Discord.",logs:"Просмотр latest.log и audit.log.",console:"Мониторинг и безопасное управление ботом.",settings:"Подключения, роли, каналы и параметры панели.",access:"Все участники сервера, их Discord-роли и фильтрация по ролям."};
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
    } else if(page==="console"){
      section.innerHTML='<div class="panel-heading"><div><h2>Управление ботом</h2><p>Состояние Discord-подключения и безопасные действия управления.</p></div><button class="text-button" id="refreshConsole">↻ Обновить</button></div><div id="consoleWorkspace" class="console-workspace"><div class="empty-state">Подключаемся к боту…</div></div>';
      loadConsole(section);
    } else if(page==="access"){
      section.innerHTML='<div class="panel-heading"><div><h2>Доступ к серверу</h2><p>Все участники WhiteGrief и назначенные им Discord-роли</p></div><button class="text-button" id="refreshAccess">↻ Обновить</button></div><div id="accessWorkspace" class="access-workspace"><div class="empty-state">Загружаем участников сервера…</div></div>';
      loadAccess(section);
    } else if(page==="settings"){
       section.innerHTML='<div class="panel-heading"><div><h2>Настройки системы</h2><p>Подключения, роли доступа, Discord-каналы и интеграции WhiteGrief.</p></div><button class="text-button" id="refreshSettings">↻ Обновить</button></div><div id="settingsWorkspace" class="settings-workspace"><div class="empty-state">Проверяем конфигурацию…</div></div>';
       loadSettings(section);
    } else if(page==="logs"){
      section.innerHTML='<div class="panel-heading"><div><h2>Папка logs/</h2><p>Все файлы журналов бота. Выбери файл, чтобы открыть просмотрщик.</p></div><button class="text-button" id="refreshLogs">↻ Обновить</button></div><div class="logs-browser-toolbar"><div class="logs-folder-path"><span class="folder-icon">▰</span><span>WhiteGrief</span><span class="muted">/</span><strong>logs/</strong></div><input id="logsFileSearch" class="panel-search" placeholder="Найти файл…"></div><div class="logs-summary" id="logsSummary">Загрузка списка файлов…</div><div id="logsResult" class="logs-file-grid"><div class="empty-state">Загружаем файлы…</div></div>';
      loadLogs(section);

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
    const accessNav=document.querySelector('[data-page="access"]');
    if(accessNav)accessNav.hidden=!["adm","full"].includes(currentAccessLevel);
    startSettingsLiveSync();
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
    if(wgSettingsLiveTimer){clearInterval(wgSettingsLiveTimer);wgSettingsLiveTimer=null;}
    await fetch("/auth/logout",{method:"POST",credentials:"same-origin"});
    window.location.href="/";
  });
}
loadSession();



let wgPreferences={theme:"system",accent:"purple",compact_mode:false};
let wgGlobalSettings={announcement_enabled:false,announcement_text:"",default_theme:"dark"};
let wgSettingsLiveTimer=null;

function applyWhiteGriefAppearance(){
  const theme=wgPreferences.theme==="system"?(wgGlobalSettings.default_theme||"dark"):wgPreferences.theme;
  document.documentElement.dataset.theme=theme;
  document.documentElement.dataset.accent=wgPreferences.accent||"purple";
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
async function refreshWhiteGriefLiveSettings(){
  try{
    const response=await fetch("/api/settings/live",{credentials:"same-origin",cache:"no-store"});
    if(!response.ok)return;
    const data=await response.json();
    wgGlobalSettings=data.global_settings||wgGlobalSettings;
    wgPreferences=data.preferences||wgPreferences;
    applyWhiteGriefAppearance();
    renderGlobalAnnouncement();
    const liveTheme=document.getElementById("wgPersonalTheme");
    const liveAccent=document.getElementById("wgPersonalAccent");
    const liveCompact=document.getElementById("wgPersonalCompact");
    const liveAnnouncement=document.getElementById("wgAdminAnnouncementEnabled");
    const liveMessage=document.getElementById("wgAdminAnnouncementText");
    const liveDefaultTheme=document.getElementById("wgAdminDefaultTheme");
    if(liveTheme&&document.activeElement!==liveTheme)liveTheme.value=wgPreferences.theme||"system";
    if(liveAccent&&document.activeElement!==liveAccent)liveAccent.value=wgPreferences.accent||"purple";
    if(liveCompact&&document.activeElement!==liveCompact)liveCompact.checked=!!wgPreferences.compact_mode;
    if(liveAnnouncement&&document.activeElement!==liveAnnouncement)liveAnnouncement.checked=!!wgGlobalSettings.announcement_enabled;
    if(liveMessage&&document.activeElement!==liveMessage)liveMessage.value=wgGlobalSettings.announcement_text||"";
    if(liveDefaultTheme&&document.activeElement!==liveDefaultTheme)liveDefaultTheme.value=wgGlobalSettings.default_theme||"dark";
  }catch(error){}
}
function startSettingsLiveSync(){
  refreshWhiteGriefLiveSettings();
  if(wgSettingsLiveTimer)clearInterval(wgSettingsLiveTimer);
  wgSettingsLiveTimer=setInterval(refreshWhiteGriefLiveSettings,4000);
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
    const eyebrow=document.createElement("span");eyebrow.textContent="WHITEGRIEF CONTROL CENTER";
    const heroTitle=document.createElement("strong");heroTitle.textContent="Центр настроек";
    const heroText=document.createElement("p");heroText.textContent="Настрой внешний вид панели, общие параметры и подключение Discord.";heroCopy.append(eyebrow,heroTitle,heroText);hero.append(heroIcon,heroCopy);root.append(hero);
    wgPreferences=data.preferences||wgPreferences;
    wgGlobalSettings=data.global_settings||wgGlobalSettings;
    applyWhiteGriefAppearance();renderGlobalAnnouncement();

    const personal=makePanel("Мои настройки","Сохраняются для твоего Discord-аккаунта");
    const personalGrid=document.createElement("div");personalGrid.className="settings-edit-grid";
    const theme=document.createElement("select");theme.id="wgPersonalTheme";theme.className="settings-select";
    [["system","По умолчанию сервера"],["dark","Тёмная"],["light","Светлая"]].forEach(([value,label])=>{const o=document.createElement("option");o.value=value;o.textContent=label;theme.append(o);});
    theme.value=wgPreferences.theme||"system";
    const accent=document.createElement("select");accent.id="wgPersonalAccent";accent.className="settings-select";
    [["purple","Фиолетовый"],["blue","Синий"],["green","Зелёный"],["red","Красный"]].forEach(([value,label])=>{const o=document.createElement("option");o.value=value;o.textContent=label;accent.append(o);});
    accent.value=wgPreferences.accent||"purple";
    const compact=document.createElement("input");compact.id="wgPersonalCompact";compact.type="checkbox";compact.checked=!!wgPreferences.compact_mode;
    const compactLabel=document.createElement("label");compactLabel.className="settings-switch-label";compactLabel.append(compact,document.createTextNode("Компактный интерфейс"));
    personalGrid.append(makeField("Тема оформления",theme,"Можно использовать тему по умолчанию, заданную администрацией."),makeField("Цвет акцента",accent,"Цвет выделения элементов панели."),makeField("Плотность интерфейса",compactLabel,"Уменьшает отступы между элементами."));
    personal.append(personalGrid);
    const personalStatus=document.createElement("small");personalStatus.className="settings-save-status";personalStatus.textContent="Изменения сохраняются автоматически.";
    personal.append(personalStatus);root.append(personal);

    let savePersonalTimer=null;
    const savePersonal=async()=>{
      if(savePersonalTimer)clearTimeout(savePersonalTimer);
      personalStatus.textContent="Сохраняем…";
      wgPreferences={theme:theme.value,accent:accent.value,compact_mode:compact.checked};
      applyWhiteGriefAppearance();
      try{
        await requestJSON("/api/settings/preferences",wgPreferences);
        personalStatus.textContent="Сохранено · применяется сразу";
      }catch(error){personalStatus.textContent=error.message;}
    };
    [theme,accent,compact].forEach(control=>control.addEventListener("change",savePersonal));

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
          applyWhiteGriefAppearance();renderGlobalAnnouncement();
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

      const guild=makePanel("Discord-сервер","WhiteGrief");
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
          card.append(identity,roleBadges);fragment.append(card);
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
  const actions=[["sync_commands","Синхронизировать slash-команды","Обновит команды WhiteGrief на Discord-сервере."],["sync_roles","Синхронизировать роли доступа","Проверит и обновит роли доступа Control Panel."],["refresh_presence","Обновить активность бота","Повторно установит статус «/shop | модерация»."]];
  const append=(output,text,tone="")=>{const line=document.createElement("div");if(tone)line.className="console-output-"+tone;line.textContent=text;output.append(line);while(output.children.length>800)output.firstElementChild.remove();output.scrollTop=output.scrollHeight;};
  const render=data=>{
    const status=data.status||{},workspace=document.createElement("div");workspace.className="console-workspace-inner";
    const cards=document.createElement("div");cards.className="console-status-grid";
    [["СОСТОЯНИЕ",status.online?"В сети":"Не в сети",status.online?"online":"offline"],["DISCORD",status.bot_name||"WhiteGrief",""],["СЕРВЕР",status.guild_name||"—",""],["ЗАДЕРЖКА",status.latency_ms==null?"—":status.latency_ms+" мс",""]].forEach(([label,value,tone])=>{const card=document.createElement("article");card.className="console-status-card";const small=document.createElement("small");small.textContent=label;const strong=document.createElement("strong");strong.textContent=value;if(tone)strong.classList.add(tone);card.append(small,strong);cards.append(card);});
    const controls=document.createElement("div");controls.className="console-controls";const heading=document.createElement("div");heading.className="console-section-heading";const h=document.createElement("h3");h.textContent="Быстрые действия";const note=document.createElement("span");note.textContent=currentAccessLevel==="full"?"Полный доступ: команды, действия и перезапуск":"Adm: просмотр, быстрые действия и перезапуск · ввод команд доступен только Full";heading.append(h,note);controls.append(heading);
    actions.forEach(([key,label,description])=>{const card=document.createElement("div");card.className="console-action-card";const copy=document.createElement("div");copy.className="console-action-copy";const title=document.createElement("strong");title.textContent=label;const desc=document.createElement("small");desc.textContent=description;copy.append(title,desc);const button=document.createElement("button");button.type="button";button.className="console-action-button";button.textContent="Выполнить";button.disabled=!status.online||!["adm","full"].includes(currentAccessLevel);button.title=!["adm","full"].includes(currentAccessLevel)?"Требуется уровень Adm":(!status.online?"Бот не подключён":"");button.addEventListener("click",async()=>{button.disabled=true;button.textContent="Выполняется…";try{const response=await fetch("/api/console/action",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:key})});const result=await response.json();if(!response.ok)throw new Error(result.detail||"Действие не выполнено.");showToast(result.message||"Действие выполнено.");await poll();}catch(error){showToast(error.message||"Ошибка управления.");}finally{button.textContent="Выполнить";button.disabled=!status.online||!["adm","full"].includes(currentAccessLevel);}});card.append(copy,button);controls.append(card);});
    const terminal=document.createElement("section");terminal.className="console-terminal";const top=document.createElement("div");top.className="console-terminal-top";const terminalTitle=document.createElement("div");terminalTitle.className="console-terminal-title";const led=document.createElement("i");led.className=status.online?"online":"";const termName=document.createElement("strong");termName.textContent="Терминал WhiteGrief · host";terminalTitle.append(led,termName);const tools=document.createElement("div");tools.className="console-terminal-tools";
    const clear=document.createElement("button");clear.type="button";clear.className="console-tool-button";clear.textContent="Очистить";clear.addEventListener("click",()=>{output.replaceChildren();append(output,"Терминал очищен. Напиши help для списка команд.","muted");});if(currentAccessLevel==="full")tools.append(clear);top.append(terminalTitle,tools);
    const output=document.createElement("div");output.className="console-terminal-output";append(output,"WhiteGrief Host Terminal","system");append(output,"Подключение к процессу бота установлено.","muted");append(output,currentAccessLevel==="full"?"Full: команды shell выполняются на первом хостинге. Любые символы передаются без фильтрации.":"Режим просмотра: вывод хостинга доступен, ввод команд отключён для Adm.","muted");
    const form=document.createElement("form");form.className="console-command-form";const prompt=document.createElement("label");prompt.className="console-command-prompt";prompt.textContent="container~";const input=document.createElement("input");input.className="console-command-input";input.type="text";input.autocomplete="off";input.spellcheck=false;input.placeholder="Введите команду или символ…";input.disabled=currentAccessLevel!=="full";const run=document.createElement("button");run.type="submit";run.className="console-action-button";run.textContent="Выполнить";run.disabled=currentAccessLevel!=="full";form.append(prompt,input,run);
    const restartRow=document.createElement("div");restartRow.className="console-restart-row";const restartHint=document.createElement("small");restartHint.textContent="Перезапуск заменит текущий процесс бота и временно отключит Discord.";const restart=document.createElement("button");restart.type="button";restart.className="console-restart-button";restart.textContent="↻ Перезапустить бота";restart.disabled=!["adm","full"].includes(currentAccessLevel);restart.addEventListener("click",()=>{
      const previous=document.getElementById("consoleRestartModal");if(previous)previous.remove();
      const modal=document.createElement("div");modal.id="consoleRestartModal";modal.className="action-modal";
      const dialog=document.createElement("div");dialog.className="action-modal-card";dialog.setAttribute("role","dialog");dialog.setAttribute("aria-modal","true");dialog.setAttribute("aria-labelledby","consoleRestartTitle");
      const close=document.createElement("button");close.type="button";close.className="action-modal-close";close.textContent="×";close.setAttribute("aria-label","Закрыть");
      const icon=document.createElement("div");icon.className="action-modal-icon";icon.textContent="↻";
      const eyebrow=document.createElement("div");eyebrow.className="action-modal-eyebrow";eyebrow.textContent="WHITEGRIEF CONTROL PANEL";
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
    append(appOutput,"WhiteGrief Application Input","system");
    append(appOutput,"Ввод передаётся обработчику приложения. Неизвестные команды тоже принимаются и возвращают ответ приложения.","muted");
    const appForm=document.createElement("form");appForm.className="console-command-form";
    const appPrompt=document.createElement("label");appPrompt.className="console-command-prompt";appPrompt.textContent="WhiteGrief>";
    const appInput=document.createElement("input");appInput.className="console-command-input";appInput.type="text";appInput.autocomplete="off";appInput.spellcheck=false;appInput.placeholder="Введите команду приложения или любой текст…";appInput.disabled=currentAccessLevel!=="full";
    const appRun=document.createElement("button");appRun.type="submit";appRun.className="console-action-button";appRun.textContent="Выполнить";appRun.disabled=currentAccessLevel!=="full";
    appForm.append(appPrompt,appInput,appRun);
    const appFoot=document.createElement("div");appFoot.className="console-terminal-foot";appFoot.textContent="Ввод в приложение · произвольная строка до 2000 символов · доступ Full. Команда обрабатывается логикой WhiteGrief, а не Linux.";
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
      commandBusy=true;append(appOutput,"WhiteGrief> "+command,"command");appInput.value="";appRun.disabled=true;appRun.textContent="…";
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
  const poll=async()=>{if(pollBusy)return;pollBusy=true;try{const data=await apiGet("/api/console"),status=data.status||{};const strong=root.querySelectorAll(".console-status-card strong");if(strong[0]){strong[0].textContent=status.online?"В сети":"Не в сети";strong[0].className=status.online?"online":"offline";}if(strong[1])strong[1].textContent=status.bot_name||"WhiteGrief";if(strong[2])strong[2].textContent=status.guild_name||"—";if(strong[3])strong[3].textContent=status.latency_ms==null?"—":status.latency_ms+" мс";const led=root.querySelector(".console-terminal-title i");if(led)led.className=status.online?"online":"";}catch(error){const output=root.querySelector(".console-terminal-output");if(output)append(output,"[соединение] "+error.message,"error");}finally{pollBusy=false;}await pollOutput();};
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
          <label class="messages-label">Файлы <span>до 10 файлов · до 8 МБ каждый · общий размер до 25 МБ</span>
            <input id="messageFiles" class="messages-control messages-file-input" type="file" multiple>
          </label>
          <div id="messageFilesPreview" class="messages-attachments-preview" hidden></div>
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
    const content=root.querySelector("#messageContent"),title=root.querySelector("#embedTitle"),description=root.querySelector("#embedDescription"),color=root.querySelector("#embedColor"),filesInput=root.querySelector("#messageFiles"),filesPreview=root.querySelector("#messageFilesPreview"),previewSender=root.querySelector("#messagePreviewSender"),attributionPreview=root.querySelector("#messagePreviewAttribution");
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
    const renderFilesPreview=()=>{
      filesPreview.replaceChildren();
      const selected=Array.from(filesInput.files||[]);
      filesPreview.hidden=!selected.length;
      selected.forEach((file,index)=>{
        const row=document.createElement("div");row.className="messages-attachment-item";
        const icon=document.createElement("span");icon.className="messages-attachment-icon";icon.textContent="▤";
        const info=document.createElement("span");info.className="messages-attachment-info";
        const name=document.createElement("strong");name.textContent=file.name;
        const size=document.createElement("small");size.textContent=file.size<1024*1024?(file.size/1024).toFixed(1)+" КБ":(file.size/1024/1024).toFixed(2)+" МБ";
        info.append(name,size);
        const remove=document.createElement("button");remove.type="button";remove.className="messages-attachment-remove";remove.textContent="×";remove.title="Убрать файл";
        remove.addEventListener("click",()=>{const transfer=new DataTransfer();Array.from(filesInput.files||[]).forEach((item,i)=>{if(i!==index)transfer.items.add(item);});filesInput.files=transfer.files;renderFilesPreview();});
        row.append(icon,info,remove);filesPreview.append(row);
      });
    };
    filesInput.addEventListener("change",renderFilesPreview);
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
      const body=content.value.trim(),embedTitle=title.value.trim(),embedDescription=description.value.trim(),files=Array.from(filesInput.files||[]);
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
        content.value="";filesInput.value="";renderFilesPreview();updatePreview();
      }catch(error){status.textContent=error.message;status.className="messages-status error";}
      finally{send.disabled=false;send.textContent="Отправить в Discord";}
    });;
  }catch(error){root.innerHTML="";const box=document.createElement("div");box.className="empty-state";const title=document.createElement("strong");title.textContent="Не удалось загрузить каналы";const detail=document.createElement("p");detail.textContent=error.message;box.append(title,detail);root.append(box);}
  refresh?.addEventListener("click",()=>loadMessages(section));
}
