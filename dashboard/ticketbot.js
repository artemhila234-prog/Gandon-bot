/* Ticket Bot v2 administration module. The browser never receives the internal Ticket Bot API key. */
window.loadTicketBot = async function(section, sessionUser = {}) {
  const isSupportMode = sessionUser?.ticketbot_access === "support";
  const root = document.createElement("div");
  root.className = "ticketbot-workspace" + (isSupportMode ? " tb-support-mode" : "");
  root.innerHTML = `
    <div class="tb-toolbar">
      <div class="tb-server-select-wrap"><label for="tbGuildSelect">Discord-сервер</label><select id="tbGuildSelect"><option>Загрузка серверов…</option></select></div>
      <div class="tb-toolbar-actions"><span class="tb-api-state" id="tbApiState">Проверяем соединение…</span><button class="text-button" id="tbRefresh">↻ Обновить</button><button class="tb-command-open" id="tbCommandOpen" type="button"><kbd>Ctrl K</kbd> Команды</button></div>
    </div>
    <nav class="tb-tabs" id="tbTabs" aria-label="Управление Ticket Bot">
      <button type="button" data-tab="overview" class="active">Обзор</button>
      <button type="button" data-tab="tickets">Тикеты</button>
      <button type="button" data-tab="panels">Панели</button>
      <button type="button" data-tab="staff">Персонал</button>
      <button type="button" data-tab="settings">Настройки</button>
      <button type="button" data-tab="schedules">Часы поддержки</button>
      <button type="button" data-tab="replies">Ответы</button>
      <button type="button" data-tab="tags">Теги</button>
      <button type="button" data-tab="knowledge">База знаний</button>
      <button type="button" data-tab="analytics">Аналитика</button>
      <button type="button" data-tab="audit">Аудит</button>
    </nav>
    <div class="tb-notice" id="tbNotice" hidden></div>
    <main class="tb-content" id="tbContent"><div class="empty-state">Подключаем Ticket Bot…</div></main>
    <div class="tb-command-modal" id="tbCommandModal" hidden>
      <div class="tb-command-backdrop" data-close="1"></div>
      <section class="tb-command-dialog" role="dialog" aria-modal="true" aria-label="Командная палитра">
        <div class="tb-command-search"><span>⌕</span><input id="tbCommandSearch" type="search" placeholder="Перейти к разделу или действию…"><kbd>ESC</kbd></div>
        <div class="tb-command-results" id="tbCommandResults"></div>
        <div class="tb-command-foot">Ticket Bot · Command Palette</div>
      </section>
    </div>`;
  section.appendChild(root);

  const $ = (selector) => root.querySelector(selector);
  const contentEl = $("#tbContent");
  const noticeEl = $("#tbNotice");
  const guildSelect = $("#tbGuildSelect");
  const stateEl = $("#tbApiState");
  const allTabs = [
    ["overview","Обзор"],["tickets","Тикеты"],["panels","Панели"],["staff","Персонал"],
    ["settings","Настройки"],["schedules","Часы поддержки"],["replies","Сохранённые ответы"],
    ["tags","Теги"],["knowledge","База знаний"],["analytics","Аналитика"],["audit","Аудит"],
    ["botProfile","Профиль бота"]
  ];
  const tabs = isSupportMode ? allTabs.filter(item=>["overview","tickets"].includes(item[0])) : allTabs;
  let guildId = "";
  let activeTab = isSupportMode ? "tickets" : "overview";
  let guildCache = [];
  let channelsCache = [];
  let rolesCache = [];
  let overviewCache = null;
  let currentTicket = null;
  let ticketFilter = "open";
  let ticketCursor = null;
  let ticketItems = [];
  let ticketRefreshTimer = null;
  let ticketRefreshBusy = false;

  const make = (tag, cls, value) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  };
  const button = (label, cls, fn) => {
    const node = make("button", cls, label);
    node.type = "button";
    node.addEventListener("click", fn);
    return node;
  };
  let fieldLabelSequence=0;
  const field = (labelText, control, hint) => {
    const wrap = make("div","tb-field");
    const label = make("span","tb-field-label",labelText);
    label.id = "tb-field-label-" + (++fieldLabelSequence);
    control.setAttribute?.("aria-labelledby",label.id);
    wrap.append(label,control);
    if (hint) wrap.append(make("small","tb-field-hint",hint));
    return wrap;
  };
  const input = (type, value, placeholder) => {
    const node = make("input","tb-input");
    node.type = type || "text";
    node.value = value ?? "";
    if (placeholder) node.placeholder = placeholder;
    return node;
  };
  const textarea = (value, placeholder, rows=4) => {
    const node = make("textarea","tb-textarea");
    node.value = value ?? "";
    node.placeholder = placeholder || "";
    node.rows = rows;
    return node;
  };
  const select = (values, selected, placeholder) => {
    const node = make("select","tb-select");
    if (placeholder) {
      const option = make("option","",placeholder);
      option.value = "";
      node.append(option);
    }
    for (const item of values || []) {
      const option = make("option","",item.label);
      option.value = String(item.value);
      option.selected = String(item.value) === String(selected ?? "");
      node.append(option);
    }
    return node;
  };
  const parseJSON = (value, fallback, label) => {
    try { return JSON.parse(value); }
    catch { throw new Error(label + ": проверь JSON."); }
  };
  const showNotice = (message, kind="info") => {
    noticeEl.hidden = !message;
    noticeEl.textContent = message || "";
    noticeEl.className = "tb-notice " + (kind === "error" ? "is-error" : kind === "success" ? "is-success" : "");
  };
  if (isSupportMode) {
    root.querySelectorAll("#tbTabs [data-tab]").forEach(item=>{
      item.hidden=!tabs.some(tab=>tab[0]===item.dataset.tab);
      item.classList.toggle("active",item.dataset.tab===activeTab);
    });
    showNotice("Режим поддержки: можно просматривать очередь, забирать открытые тикеты, отвечать пользователям, закрывать обращения и открывать транскрипты. Настройки и управление ботом недоступны.");
  }
  const request = async (path, method="GET", payload=null) => {
    if (!guildId && !path.startsWith("@guilds") && !path.startsWith("@profile")) throw new Error("Сначала выбери сервер.");
    const url = path.startsWith("@guilds") ? "/api/ticketbot/guilds"
      : path.startsWith("@profile") ? "/api/ticketbot/profile"
      : "/api/ticketbot/guilds/" + encodeURIComponent(guildId) + path;
    const response = await fetch(url, {
      method,
      credentials:"same-origin",
      cache:"no-store",
      headers:payload === null ? {} : {"Content-Type":"application/json"},
      body:payload === null ? undefined : JSON.stringify(payload)
    });
    const raw = await response.text();
    let data = {};
    try { data = raw ? JSON.parse(raw) : {}; } catch {}
    if (!response.ok) throw new Error(data.detail || "Ticket Bot API недоступен (" + response.status + ").");
    return data;
  };
  const loading = (message="Загружаем…") => {
    contentEl.replaceChildren(make("div","empty-state",message));
  };
  const statusBadge = (text, good=false) => make("span","tb-status"+(good?" is-good":""),text);
  const card = (title, value, hint) => {
    const node=make("article","tb-stat-card");
    node.append(make("span","tb-stat-label",title),make("strong","tb-stat-value",value ?? "—"));
    if(hint) node.append(make("small","tb-stat-hint",hint));
    return node;
  };
  const heading = (title, description, actions) => {
    const wrap=make("div","tb-section-head");
    const copy=make("div","");
    copy.append(make("h2","",title),make("p","",description||""));
    wrap.append(copy);
    if(actions) wrap.append(actions);
    return wrap;
  };
  const idArray = (value) => String(value || "").split(/[,\s]+/).map(x=>x.trim()).filter(x=>/^\d{15,22}$/.test(x));
  const stopTicketRefresh = () => {
    if (ticketRefreshTimer !== null) {
      window.clearInterval(ticketRefreshTimer);
      ticketRefreshTimer = null;
    }
    ticketRefreshBusy = false;
  };
  const setActiveTab = async (tab) => {
    if (!tabs.some(item=>item[0]===tab)) return;
    stopTicketRefresh();
    activeTab=tab;
    currentTicket=null;
    root.querySelectorAll("[data-tab]").forEach(item=>item.classList.toggle("active",item.dataset.tab===tab));
    await renderTab();
  };
  const loadCommonData = async () => {
    const [channels,roles] = await Promise.all([request("/channels"),request("/roles")]);
    channelsCache=channels.channels||[];
    rolesCache=roles.roles||[];
  };
  const channelOptions = (includeCategories=false) => channelsCache
    .filter(x=>includeCategories ? ["text","news","forum","category"].includes(x.type) : ["text","news"].includes(x.type))
    .map(x=>({label:(x.type==="category"?"📁 ":"# ")+x.name+" · "+x.id,value:x.id}));
  const roleOptions = () => rolesCache.filter(x=>!x.managed).map(x=>({label:"@"+x.name+" · "+x.id,name:"@"+x.name,color:x.color,value:x.id}));
  const multiRoleSelect = (selected=[]) => {
    const node=make("div","tb-role-picker");
    node.dataset.rolePicker="true";
    node.setAttribute("role","group");
    const selectedIds=new Set((selected||[]).map(String));
    const roles=roleOptions();
    if(!roles.length) {
      node.append(make("div","tb-role-empty","Роли сервера не загрузились или у бота нет доступа к ним."));
      return node;
    }
    const summary=make("div","tb-role-picker-summary");
    const list=make("div","tb-role-picker-list");
    const updateSummary=()=>{
      const count=list.querySelectorAll('input[type="checkbox"]:checked').length;
      summary.textContent="Выбрано ролей: "+count;
    };
    for(const item of roles) {
      const option=make("label","tb-role-option");
      const check=make("input","tb-role-check");
      check.type="checkbox";
      check.value=String(item.value);
      check.checked=selectedIds.has(check.value);
      check.defaultChecked=check.checked;
      check.addEventListener("change",updateSummary);
      const name=make("span","tb-role-option-name",item.name);
      const roleId=make("small","tb-role-option-id",String(item.value));
      if(item.color) option.style.setProperty("--role-color",item.color);
      option.append(check,name,roleId);
      list.append(option);
    }
    node._updateSummary=updateSummary;
    updateSummary();
    node.append(summary,list);
    return node;
  };
  const selectedValues = (node) => {
    if(node?.dataset?.rolePicker==="true") {
      return Array.from(node.querySelectorAll('input[type="checkbox"]:checked')).map(input=>input.value);
    }
    return Array.from(node?.selectedOptions||[]).map(option=>option.value);
  };
  const setSelectedValues = (node, values=[]) => {
    const selected=new Set((values||[]).map(String));
    node.querySelectorAll('input[type="checkbox"]').forEach(input=>{
      input.checked=selected.has(input.value);
    });
    node._updateSummary?.();
  };
  const renderGuildPicker = async () => {
    const result=await request("@guilds");
    guildCache=result.guilds||[];
    guildSelect.replaceChildren();
    for(const guild of guildCache) {
      const option=make("option","",guild.name+" · "+guild.id);
      option.value=String(guild.id);
      guildSelect.append(option);
    }
    if(!guildCache.length) throw new Error("Ticket Bot пока не добавлен ни на один сервер.");
    guildId=String(guildCache[0].id);
    guildSelect.value=guildId;
    stateEl.textContent="Discord подключён · "+guildCache.length+" сервер(ов)";
    stateEl.classList.add("is-online");
  };

  const renderOverview = async () => {
    const data=await request("/overview");
    overviewCache=data;
    const view=make("div","tb-view");
    view.append(heading("Обзор Ticket Bot","Состояние тикет-системы и быстрый доступ к рабочим разделам."));
    const stats=make("div","tb-stats-grid");
    stats.append(
      card("Открытые тикеты",data.tickets?.open??0,"Требуют внимания поддержки"),
      card("Закрытые тикеты",data.tickets?.closed??0,"История обращений"),
      card("Панели",data.panels?.length??0,"Количество настроенных панелей"),
      card("Сотрудники",data.staff?.length??0,"Назначенная команда поддержки")
    );
    view.append(stats);
    const quick=make("div","tb-quick-grid");
    for(const [tab,title,description,icon] of [
      ["tickets","Тикеты","Просмотр, ответы, claiming и закрытие","🎫"],
      ["panels","Панели","Создать форму и опубликовать панель","▣"],
      ["staff","Персонал","Добавить поддержку и администраторов","♙"],
      ["analytics","Аналитика","Время ответа и активность","↗"]
    ]) {
      if(!tabs.some(entry=>entry[0]===tab)) continue;
      const item=make("button","tb-quick-card");
      item.type="button";
      item.append(make("span","tb-quick-icon",icon),make("strong","",title),make("small","",description));
      item.addEventListener("click",()=>setActiveTab(tab));
      quick.append(item);
    }
    view.append(quick);
    const info=make("div","tb-info-grid");
    const infoCard=make("article","tb-panel-card");
    infoCard.append(make("h3","","Сервер"),make("p","tb-info-value",data.guild?.name||guildId),
      make("small","tb-muted","ID: "+guildId));
    const lang=make("article","tb-panel-card");
    lang.append(make("h3","","Локализация"),make("p","tb-info-value",data.settings?.language||"en"),
      make("small","tb-muted","Часовой пояс: "+(data.settings?.timezone||"UTC")));
    info.append(infoCard,lang);view.append(info);
    contentEl.replaceChildren(view);
  };

  const renderTickets = async (append=false) => {
    if(currentTicket) return renderTicketDetail(currentTicket);
    if(!append) { ticketCursor=null; ticketItems=[]; }
    const view=make("div","tb-view");
    const filter=select([{label:"Открытые",value:"open"},{label:"Закрытые",value:"closed"},{label:"Все",value:"all"}],ticketFilter);
    filter.addEventListener("change",()=>{ticketFilter=filter.value;ticketCursor=null;ticketItems=[];renderTickets().catch(showError);});
    const refresh=button("↻ Обновить","tb-button",()=>renderTickets().catch(showError));
    const actions=make("div","tb-actions");actions.append(filter,refresh);
    view.append(heading("Тикеты","Все обращения, история сообщений, участники и управление статусом. История загружается страницами без лимита на количество тикетов.",actions));
    let url="/tickets?status="+encodeURIComponent(ticketFilter)+"&limit=100";
    if(append && ticketCursor) url+="&before_id="+encodeURIComponent(ticketCursor);
    const result=await request(url);
    const nextPage=result.tickets||[];
    ticketItems=append?ticketItems.concat(nextPage):nextPage;
    ticketCursor=result.next_before_id||null;
    const list=make("div","tb-ticket-list");
    const tickets=ticketItems;
    if(!tickets.length) list.append(make("div","tb-empty","Тикетов пока нет."));
    for(const ticket of tickets) {
      const row=make("article","tb-ticket-row");
      const info=make("div","tb-ticket-main");
      info.append(make("strong","","#"+ticket.ticket_number+" · "+(ticket.subject||"Support")),
        make("small","","Открыл: "+ticket.opener_id+" · Создан: "+ticket.created_at),
        make("small","","Назначен: "+(ticket.assigned_to||"Не назначен")+" · Сообщений: "+ticket.message_count));
      const controls=make("div","tb-ticket-controls");
      controls.append(statusBadge(ticket.status==="open"?"Открыт":"Закрыт",ticket.status==="open"));
      controls.append(button("Открыть","tb-button",()=>{currentTicket=Number(ticket.id);renderTickets().catch(showError);}));
      if(ticket.status==="open") {
        controls.append(button("Забрать","tb-button",async()=>runAction(()=>request("/tickets/"+ticket.id+"/claim","POST",{}),"Тикет назначен.",renderTickets)));
        controls.append(button("Закрыть","tb-button is-danger",async()=>runAction(()=>request("/tickets/"+ticket.id+"/close","POST",{reason:"Closed from GastWorld dashboard"}),"Тикет закрыт.",renderTickets)));
      } else if(!isSupportMode) {
        controls.append(button("Открыть снова","tb-button",async()=>runAction(()=>request("/tickets/"+ticket.id+"/reopen","POST",{}),"Тикет открыт снова.",renderTickets)));
      }
      row.append(info,controls);list.append(row);
    }
    view.append(list);
    if(ticketCursor) {
      view.append(button("Загрузить ещё тикеты","tb-button",()=>renderTickets(true).catch(showError)));
    }
    contentEl.replaceChildren(view);
  };

  const paintTicketEvents = (container, items) => {
    container.replaceChildren(make("h3","","История"));
    for(const event of items||[]) {
      const item=make("article","tb-event");
      const dataObj=(()=>{try{return JSON.parse(event.data_json||"{}");}catch{return {};}})();
      item.append(make("div","tb-event-top",event.event_type+" · "+(event.actor_id||"Система")+" · "+event.created_at));
      if(event.content) item.append(make("p","tb-event-body",event.content));
      for(const file of dataObj.attachments||[]) {
        const a=make("a","tb-file-link",file.filename||"Вложение");
        a.href=file.url||"#";a.target="_blank";a.rel="noopener noreferrer";item.append(a);
      }
      container.append(item);
    }
    if(!(items||[]).length) container.append(make("p","tb-muted","История ещё пуста."));
  };

  const renderTicketDetail = async (ticketId) => {
    stopTicketRefresh();
    const data=await request("/tickets/"+ticketId);
    const ticket=data.ticket;
    if(!ticket || String(ticket.guild_id)!==String(guildId)) throw new Error("Тикет не найден.");
    const view=make("div","tb-view");
    const back=button("← К списку","tb-button",()=>{stopTicketRefresh();currentTicket=null;renderTickets().catch(showError);});
    const tools=make("div","tb-actions");tools.append(back);
    if(ticket.status==="open") {
      tools.append(button("Забрать","tb-button",()=>runAction(()=>request("/tickets/"+ticketId+"/claim","POST",{}),"Тикет назначен.",()=>renderTicketDetail(ticketId))));
      tools.append(button("Закрыть","tb-button is-danger",()=>runAction(()=>request("/tickets/"+ticketId+"/close","POST",{reason:"Closed from dashboard"}),"Тикет закрыт.",()=>renderTicketDetail(ticketId))));
    } else if(!isSupportMode) {
      tools.append(button("Открыть снова","tb-button",()=>runAction(()=>request("/tickets/"+ticketId+"/reopen","POST",{}),"Тикет открыт.",()=>renderTicketDetail(ticketId))));
    }
    tools.append(button("Транскрипт","tb-button",()=>window.open("/api/ticketbot/guilds/"+encodeURIComponent(guildId)+"/transcript/"+ticketId,"_blank","noopener")));
    view.append(heading("Тикет #"+ticket.ticket_number,ticket.subject||"Обращение",tools));
    const meta=make("div","tb-ticket-meta");
    for(const [label,value] of [
      ["Статус",ticket.status],["Автор",ticket.opener_id],["Назначен",ticket.assigned_to||"—"],
      ["Создан",ticket.created_at],["Последняя активность",ticket.last_activity_at],["Режим",ticket.mode]
    ]) {
      const item=make("div","tb-meta-item");item.append(make("small","",label),make("strong","",value));meta.append(item);
    }
    view.append(meta);
    const events=make("section","tb-events-card");
    events.id="tbLiveEvents";
    paintTicketEvents(events,ticket.events||[]);
    view.append(events);
    if(ticket.status==="open") {
      const reply=make("form","tb-reply-form");
      reply.append(make("h3","","Live Reply"));
      const message=textarea("","Ответить пользователю прямо из панели…",4);
      const send=make("button","tb-primary","Отправить ответ");send.type="submit";
      reply.append(message,send);
      reply.addEventListener("submit",async event=>{
        event.preventDefault();
        if(!message.value.trim()) return;
        send.disabled=true;
        try {
          await request("/tickets/"+ticketId+"/reply","POST",{content:message.value});
          message.value="";
          showNotice("Ответ отправлен в Discord.","success");
          await renderTicketDetail(ticketId);
        } catch(error) { showError(error); }
        finally { send.disabled=false; }
      });
      view.append(reply);
      if(!isSupportMode) {
      const members=make("form","tb-member-form");
      members.append(make("h3","","Участники тикета"));
      const row=make("div","tb-inline-form");
      const memberId=input("text","","Discord User ID");
      const add=make("button","tb-button","Добавить");add.type="submit";
      row.append(memberId,add);members.append(row);
      const list=make("div","tb-member-list");
      for(const item of ticket.members||[]) {
        const chip=make("span","tb-member-chip",item.user_id);
        const remove=button("×","tb-remove-chip",()=>runAction(
          ()=>request("/tickets/"+ticketId+"/members","POST",{user_id:item.user_id,operation:"remove"}),
          "Участник удалён.",()=>renderTicketDetail(ticketId)
        ));
        chip.append(remove);list.append(chip);
      }
      members.append(list);
      members.addEventListener("submit",async event=>{
        event.preventDefault();
        if(!/^\d{15,22}$/.test(memberId.value.trim())) {showNotice("Введи корректный Discord User ID.","error");return;}
        await runAction(()=>request("/tickets/"+ticketId+"/members","POST",{user_id:memberId.value.trim(),operation:"add"}),
          "Участник добавлен.",()=>renderTicketDetail(ticketId));
      });
      view.append(members);
      const ticketTags=await request("/tickets/"+ticketId+"/tags");
      const tagSection=make("section","tb-tags-inline");
      tagSection.append(make("h3","","Теги"));
      const tagRow=make("div","tb-inline-form");
      const tags=(await request("/tags")).tags||[];
      const tagSelect=select(tags.map(x=>({label:x.name,value:x.id})),null,"Выбери тег");
      const tagAdd=button("Применить","tb-button",async()=>runAction(
        ()=>request("/tickets/"+ticketId+"/tags","POST",{tag_id:tagSelect.value,operation:"add"}),
        "Тег добавлен.",()=>renderTicketDetail(ticketId)
      ));
      tagRow.append(tagSelect,tagAdd);tagSection.append(tagRow);
      for(const tag of ticketTags.tags||[]) tagSection.append(statusBadge(tag.name));
      view.append(tagSection);
      }
    }
    contentEl.replaceChildren(view);
    if(ticket.status==="open") {
      ticketRefreshTimer=window.setInterval(async()=>{
        if(!root.isConnected) {stopTicketRefresh();return;}
        if(activeTab!=="tickets" || currentTicket!==ticketId ||
           document.visibilityState==="hidden" || ticketRefreshBusy) return;
        const liveContainer=root.querySelector("#tbLiveEvents");
        if(!liveContainer) {stopTicketRefresh();return;}
        ticketRefreshBusy=true;
        try {
          const fresh=await request("/tickets/"+ticketId);
          if(activeTab==="tickets" && currentTicket===ticketId && fresh.ticket) {
            paintTicketEvents(liveContainer,fresh.ticket.events||[]);
          }
        } catch(error) {
          // A transient refresh error should not replace the user's draft reply.
          console.warn("Ticket Bot live history refresh failed:",error);
        } finally {
          ticketRefreshBusy=false;
        }
      },8000);
    }
  };

  const renderPanels = async () => {
    const [panels,channels,roles,schedules]=await Promise.all([
      request("/panels"),request("/channels"),request("/roles"),request("/schedules")
    ]);
    channelsCache=channels.channels||[];rolesCache=roles.roles||[];
    const view=make("div","tb-view");
    view.append(heading("Панели тикетов","Создавай любое количество панелей, форм и меню выбора. Сохраняй и сразу публикуй в Discord."));
    const list=make("div","tb-panel-list");
    const form=make("form","tb-editor-card");
    form.append(make("h3","","Создать / изменить панель"));
    const panelId=input("hidden","");
    const name=input("text","","Например: Поддержка пользователей");
    const description=textarea("","Текст, который увидят перед открытием тикета.",2);
    const target=select(channelOptions(false),"","Выбери канал для панели и thread mode");
    const mode=select([{label:"Отдельный приватный канал",value:"channel"},{label:"Приватный тред",value:"thread"}],"channel");
    const openMode=select([{label:"Кнопка",value:"button"},{label:"Меню выбора категории",value:"select"}],"button");
    const category=select(channelOptions(true),"","Необязательно: категория для каналов тикетов");
    const support=multiRoleSelect([]);const admins=multiRoleSelect([]);
    const buttonLabel=input("text","Create ticket","Текст кнопки");
    const buttonEmoji=input("text","🎫","Эмодзи кнопки");
    const color=input("color","#5865f2");
    const welcome=textarea("Thanks for contacting support. A team member will be with you shortly.","Приветственное сообщение внутри тикета.",3);
    const formFields=textarea("[]",'[{"label":"Описание проблемы","style":"paragraph","required":true}]',4);
    const options=textarea("[]",'[{"label":"Техническая проблема","value":"technical","description":"Ошибки и неисправности"}]',4);
    const schedule=select((schedules.schedules||[]).map(x=>({label:x.name+" · #"+x.id,value:x.id})),null,"Без расписания поддержки");
    const enabled=input("checkbox","");enabled.checked=true;
    const publish=input("checkbox","");publish.checked=true;
    const grid=make("div","tb-form-grid");
    grid.append(
      field("Название панели",name),field("Канал публикации / родительский канал",target),
      field("Описание",description),field("Режим тикетов",mode),
      field("Способ открытия",openMode),field("Категория для новых каналов",category),
      field("Роли поддержки",support,"Отметь нужные роли. Выбор сохранится после нажатия «Сохранить панель»."),field("Роли администраторов",admins,"Отметь роли администраторов и затем сохрани панель."),
      field("Текст кнопки",buttonLabel),field("Эмодзи кнопки",buttonEmoji),
      field("Цвет",color),field("Часы поддержки",schedule),
      field("Приветственное сообщение",welcome),field("Поля формы · JSON (максимум 5)",formFields),
      field("Категории для меню · JSON (максимум 25)",options)
    );
    const toggles=make("div","tb-checkbox-row");
    toggles.append(field("Панель активна",enabled),field("После сохранения опубликовать в Discord",publish));
    const formActions=make("div","tb-form-actions");
    const reset=button("Очистить","tb-button",()=>form.reset());
    form.addEventListener("reset",()=>window.setTimeout(()=>{support._updateSummary?.();admins._updateSummary?.();},0));
    const save=make("button","tb-primary","Сохранить панель");save.type="submit";
    formActions.append(reset,save);
    form.append(panelId,grid,toggles,formActions);

    const showPanelEditor = (panel) => {
      panelId.value=panel.id;
      name.value=panel.name||"";
      description.value=panel.description||"";
      target.value=String(panel.target_channel_id||"");
      mode.value=panel.mode||"channel";openMode.value=panel.open_mode||"button";
      category.value=String(panel.ticket_category_id||"");
      buttonLabel.value=panel.button_label||"Create ticket";
      buttonEmoji.value=panel.button_emoji||"🎫";
      color.value="#"+Number(panel.color||0x5865F2).toString(16).padStart(6,"0").slice(-6);
      welcome.value=panel.welcome_message||"";
      formFields.value=JSON.stringify(panel.form||[],null,2);
      options.value=JSON.stringify(panel.options||[],null,2);
      enabled.checked=!!panel.is_enabled;
      publish.checked=false;
      schedule.value=String(panel.schedule_id||"");
      setSelectedValues(support,panel.support_roles||[]);
      setSelectedValues(admins,panel.admin_roles||[]);
      form.scrollIntoView({behavior:"smooth",block:"start"});
      name.focus();
    };
    for(const panel of panels.panels||[]) {
      const row=make("article","tb-panel-row");
      const details=make("div","tb-panel-main");
      details.append(make("strong","",panel.name),
        make("small","","ID: "+panel.id+" · "+(panel.mode||"channel")+" · "+(panel.open_mode||"button")),
        make("small","","Канал публикации: "+panel.target_channel_id+" · Полей формы: "+(panel.form||[]).length));
      const controls=make("div","tb-panel-actions");
      controls.append(statusBadge(panel.is_enabled?"Активна":"Выключена",!!panel.is_enabled));
      controls.append(button("Изменить","tb-button",()=>showPanelEditor(panel)));
      controls.append(button("Опубликовать / обновить","tb-button",()=>runAction(
        ()=>request("/panels/"+panel.id+"/publish","POST",{}),"Панель опубликована в Discord.",renderPanels
      )));
      controls.append(button("Удалить","tb-button is-danger",()=>confirm("Удалить панель и сообщение в Discord?")&&runAction(
        ()=>request("/panels/"+panel.id,"DELETE",{}),"Панель удалена.",renderPanels
      )));
      row.append(details,controls);list.append(row);
    }
    if(!(panels.panels||[]).length) list.append(make("div","tb-empty","Панелей ещё нет. Создай первую ниже."));
    view.append(list,form);
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      try {
        const data={
          id:panelId.value?Number(panelId.value):undefined,
          name:name.value,description:description.value,target_channel_id:target.value,
          mode:mode.value,open_mode:openMode.value,ticket_category_id:category.value?category.value:null,
          support_roles:selectedValues(support),admin_roles:selectedValues(admins),
          button_label:buttonLabel.value,button_emoji:buttonEmoji.value,
          color:parseInt(color.value.replace("#",""),16),welcome_message:welcome.value,
          form:parseJSON(formFields.value,[],"Поля формы"),
          options:parseJSON(options.value,[],"Категории"),
          schedule_id:schedule.value?Number(schedule.value):null,
          is_enabled:enabled.checked,publish:publish.checked
        };
        if(!data.target_channel_id) throw new Error("Выбери канал публикации.");
        save.disabled=true;
        const result=await request("/panels","POST",data);
        showNotice(result.published?"Панель сохранена и опубликована в Discord.":"Панель сохранена.","success");
        await renderPanels();
      } catch(error){showError(error);}
      finally{save.disabled=false;}
    });
    contentEl.replaceChildren(view);
  };

  const renderStaff = async () => {
    const data=await request("/staff");
    const view=make("div","tb-view");
    view.append(heading("Персонал поддержки","Назначай сотрудников и администраторов. Эти назначения используются при проверке действий в тикетах."));
    const form=make("form","tb-editor-card");
    const userId=input("text","","Discord User ID");
    const role=select([{label:"Support",value:"support"},{label:"Administrator",value:"admin"}],"support");
    const save=make("button","tb-primary","Добавить сотрудника");save.type="submit";
    const row=make("div","tb-inline-form");row.append(field("Discord User ID",userId),field("Уровень",role),save);
    form.append(row);
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      if(!/^\d{15,22}$/.test(userId.value.trim())) {showNotice("Проверь Discord User ID.","error");return;}
      await runAction(()=>request("/staff","POST",{user_id:userId.value.trim(),staff_role:role.value}),
        "Сотрудник сохранён.",renderStaff);
    });
    view.append(form);
    const list=make("div","tb-staff-list");
    for(const staff of data.staff||[]) {
      const item=make("article","tb-staff-row");
      item.append(make("strong","",staff.user_id),statusBadge(staff.staff_role,staff.staff_role==="admin"),
        make("small","", "Добавлен: "+staff.created_at));
      item.append(button("Удалить","tb-button is-danger",()=>runAction(
        ()=>request("/staff","POST",{user_id:staff.user_id,staff_role:"remove"}),"Сотрудник удалён.",renderStaff
      )));
      list.append(item);
    }
    if(!(data.staff||[]).length) list.append(make("div","tb-empty","Назначенный персонал пока отсутствует."));
    view.append(list);contentEl.replaceChildren(view);
  };

  const renderBotProfile = async () => {
    const data=await request("@profile");
    const view=make("div","tb-view");
    view.append(heading("Профиль Discord-бота","Глобальные параметры отдельного Ticket Bot. Имя, аватар и статус изменятся сразу на всех серверах."));
    const form=make("form","tb-editor-card");
    const username=input("text",data.username||"","Имя Ticket Bot");
    username.maxLength=32;
    const status=select([
      {label:"Online",value:"online"},{label:"Idle",value:"idle"},
      {label:"Do Not Disturb",value:"dnd"},{label:"Invisible",value:"invisible"}
    ],data.status||"online");
    const activityType=select([
      {label:"Играет",value:"playing"},{label:"Смотрит",value:"watching"},
      {label:"Слушает",value:"listening"},{label:"Соревнуется",value:"competing"},
      {label:"Стримит",value:"streaming"},{label:"Без активности",value:"none"}
    ],data.activity_type||"playing");
    const activityText=input("text",data.activity_text||"Support tickets","Например: tickets.bot");
    activityText.maxLength=128;
    const activityUrl=input("url",data.activity_url||"","https://www.twitch.tv/...");
    const avatar=input("file","");
    avatar.accept="image/png,image/jpeg,image/gif,image/webp";
    const preview=make("img","tb-bot-avatar-preview");
    preview.alt="Текущий аватар бота";
    if(data.avatar_url) preview.src=data.avatar_url;
    const identity=make("div","tb-bot-profile-identity");
    identity.append(preview,make("div","tb-bot-profile-copy"),
      make("strong","","Текущий аватар"),
      make("small","","Загрузка нового аватара изменит его на всём Discord-аккаунте."));
    const actions=make("div","tb-form-actions");
    const save=make("button","tb-primary","Сохранить профиль бота");save.type="submit";
    actions.append(save);
    form.append(
      field("Имя бота (2–32 символа)",username),
      field("Статус",status),
      field("Тип активности",activityType),
      field("Текст активности",activityText),
      field("Ссылка на стрим · нужна только для Streaming",activityUrl),
      field("Новый аватар · PNG/JPEG/GIF/WEBP, до 8 МБ",avatar),
      identity,actions
    );
    activityType.addEventListener("change",()=>{activityUrl.disabled=activityType.value!=="streaming";});
    activityUrl.disabled=activityType.value!=="streaming";
    avatar.addEventListener("change",()=>{
      const file=avatar.files?.[0];
      if(!file)return;
      if(file.size>8*1024*1024){showNotice("Аватар должен быть не больше 8 МБ.","error");avatar.value="";return;}
      if(!["image/png","image/jpeg","image/gif","image/webp"].includes(file.type)){
        showNotice("Поддерживаются только PNG, JPEG, GIF и WEBP.","error");avatar.value="";return;
      }
      const url=URL.createObjectURL(file);
      preview.src=url;
    });
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      const payload={
        username:username.value.trim(),
        status:status.value,
        activity_type:activityType.value,
        activity_text:activityText.value,
        activity_url:activityUrl.value.trim()
      };
      const file=avatar.files?.[0];
      if(file){
        if(file.size>8*1024*1024){showNotice("Аватар должен быть не больше 8 МБ.","error");return;}
        try{
          const dataUrl=await new Promise((resolve,reject)=>{
            const reader=new FileReader();
            reader.onerror=()=>reject(new Error("Не удалось прочитать файл аватара."));
            reader.onload=()=>resolve(String(reader.result||""));
            reader.readAsDataURL(file);
          });
          payload.avatar_data=dataUrl.split(",")[1]||"";
        }catch(error){showError(error);return;}
      }
      save.disabled=true;
      try{
        const result=await request("@profile","PATCH",payload);
        showNotice("Профиль Ticket Bot обновлён в Discord.","success");
        await renderBotProfile();
      }catch(error){showError(error);}
      finally{save.disabled=false;}
    });
    const note=make("p","tb-profile-note",
      "Важно: Discord изменяет имя и аватар самого bot user глобально. Discord может ограничивать частоту изменения имени/аватара. Статус и активность также общие для всех серверов.");
    view.append(form,note);
    contentEl.replaceChildren(view);
  };

  const renderSettings = async () => {
    const data=overviewCache||await request("/overview");
    const [channels,roles]=await Promise.all([request("/channels"),request("/roles")]);
    channelsCache=channels.channels||[];rolesCache=roles.roles||[];
    const s=data.settings||{};
    const view=make("div","tb-view");
    view.append(heading("Настройки сервера","Конфигурация тикетов, логов, локализации, white-label и автоматизации."));
    const form=make("form","tb-editor-card");
    const languageOptions=[
      ["en","English"],["ru","Русский"],["et","Eesti"],["de","Deutsch"],["es","Español"],["fr","Français"],
      ["pt","Português"],["it","Italiano"],["nl","Nederlands"],["pl","Polski"],["tr","Türkçe"],["uk","Українська"],
      ["cs","Čeština"],["sk","Slovenčina"],["sv","Svenska"],["no","Norsk"],["da","Dansk"],["fi","Suomi"],
      ["ro","Română"],["hu","Magyar"],["ja","日本語"],["ko","한국어"],["zh","中文"],["ar","العربية"],
      ["bg","Български"],["el","Ελληνικά"],["hr","Hrvatski"],["id","Bahasa Indonesia"],["vi","Tiếng Việt"]
    ].map(x=>({value:x[0],label:x[1]}));
    const language=select(languageOptions,s.language||"en");
    const timezone=input("text",s.timezone||"UTC","Europe/Tallinn");
    const category=select(channelOptions(true),s.ticket_category_id,"Категория каналов тикетов");
    const transcript=select(channelOptions(false),s.transcript_channel_id,"Канал транскриптов");
    const logs=select(channelOptions(false),s.log_channel_id,"Канал логов");
    const support=multiRoleSelect(s.default_support_roles||[]);
    const admins=multiRoleSelect(s.default_admin_roles||[]);
    const autoEnabled=input("checkbox","");autoEnabled.checked=!!s.auto_close_enabled;
    const autoMinutes=input("number",s.auto_close_minutes||1440);autoMinutes.min="1";autoMinutes.max="525600";
    const labelName=input("text",s.white_label?.name||"");
    const labelAvatar=input("text",s.white_label?.avatar_url||"","https://...");
    const labelFooter=input("text",s.white_label?.footer||"");
    const save=make("button","tb-primary","Сохранить настройки");save.type="submit";
    const grid=make("div","tb-form-grid");
    grid.append(
      field("Язык",language),field("Часовой пояс",timezone),
      field("Категория тикет-каналов",category),field("Канал транскриптов",transcript),
      field("Канал логов",logs),field("Роли поддержки по умолчанию",support,"Отметь роли сотрудников поддержки. Нажми «Сохранить настройки», чтобы применить."),
      field("Роли администраторов по умолчанию",admins,"Отметь роли администраторов. Нажми «Сохранить настройки», чтобы применить."),field("Пауза до автозакрытия (минуты)",autoMinutes),
      field("White-label · Название",labelName),field("White-label · URL аватара",labelAvatar),
      field("White-label · Подпись",labelFooter)
    );
    form.append(grid,field("Автоматически закрывать неактивные тикеты",autoEnabled),save);
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      await runAction(()=>request("/settings","PATCH",{
        language:language.value,timezone:timezone.value,
        ticket_category_id:category.value?category.value:null,
        transcript_channel_id:transcript.value?transcript.value:null,
        log_channel_id:logs.value?logs.value:null,
        default_support_roles:selectedValues(support),
        default_admin_roles:selectedValues(admins),
        automation:{auto_close_enabled:autoEnabled.checked,auto_close_minutes:Number(autoMinutes.value||1440)},
        white_label:{name:labelName.value,avatar_url:labelAvatar.value,footer:labelFooter.value}
      }),"Настройки сохранены.",async()=>{overviewCache=null;await renderSettings();});
    });
    view.append(form);contentEl.replaceChildren(view);
  };

  const renderSchedules = async () => {
    const data=await request("/schedules");
    const view=make("div","tb-view");
    view.append(heading("Часы поддержки","Расписания с часовыми поясами. Можно назначить разные графики каждой панели."));
    const list=make("div","tb-panel-list");
    for(const schedule of data.schedules||[]) {
      const item=make("article","tb-panel-row");
      item.append(make("div","tb-panel-main",schedule.name),
        make("small","",schedule.timezone+" · ID "+schedule.id),
        make("pre","tb-code",JSON.stringify(schedule.hours||{},null,2)));
      const actions=make("div","tb-actions");
      actions.append(
        button("Изменить","tb-button",()=>{
          scheduleId.value=schedule.id;
          name.value=schedule.name||"";
          timezone.value=schedule.timezone||"UTC";
          hours.value=JSON.stringify(schedule.hours||{},null,2);
          message.value=schedule.closed_message||"";
          form.scrollIntoView({behavior:"smooth",block:"start"});
          name.focus();
        }),
        button("Удалить","tb-button is-danger",()=>runAction(
          ()=>request("/schedules/"+schedule.id,"DELETE",{}),"Расписание удалено.",renderSchedules
        ))
      );
      item.append(actions);
      list.append(item);
    }
    view.append(list);
    const form=make("form","tb-editor-card");form.append(make("h3","","Создать / изменить расписание"));
    const scheduleId=input("hidden","");
    const name=input("text","Support hours","Название расписания");
    const timezone=input("text","Europe/Tallinn","Часовой пояс IANA");
    const hours=textarea(JSON.stringify({"0":[{"start":"09:00","end":"17:00"}],"1":[{"start":"09:00","end":"17:00"}],"2":[{"start":"09:00","end":"17:00"}],"3":[{"start":"09:00","end":"17:00"}],"4":[{"start":"09:00","end":"17:00"}]},null,2),"JSON: дни 0=пн … 6=вс",8);
    const message=textarea("Support is currently offline. You can still open a ticket.","Сообщение вне часов поддержки",2);
    const save=make("button","tb-primary","Сохранить расписание");save.type="submit";
    form.append(field("Название",name),field("Часовой пояс",timezone),field("График · JSON",hours),field("Сообщение вне графика",message),save);
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      try {
        await request("/schedules","POST",{id:scheduleId.value?Number(scheduleId.value):undefined,name:name.value,timezone:timezone.value,hours:parseJSON(hours.value,{},"График"),closed_message:message.value,enabled:true});
        showNotice("Расписание сохранено.","success");await renderSchedules();
      }catch(error){showError(error);}
    });
    view.append(form);contentEl.replaceChildren(view);
  };

  const renderReplies = async () => {
    const data=await request("/replies");
    const view=make("div","tb-view");
    view.append(heading("Сохранённые ответы","Короткие команды /tag позволяют сотрудникам мгновенно отправлять типовые ответы."));
    const list=make("div","tb-panel-list");
    for(const reply of data.replies||[]) {
      const item=make("article","tb-panel-row");
      item.append(make("div","tb-panel-main",reply.title+" · /tag "+reply.shortcut),make("p","tb-wrap",reply.content));
      const controls=make("div","tb-actions");
      controls.append(
        button("Изменить","tb-button",()=>{
          shortcut.value=reply.shortcut;title.value=reply.title;body.value=reply.content;
          form.scrollIntoView({behavior:"smooth",block:"start"});shortcut.focus();
        }),
        button("Удалить","tb-button is-danger",()=>confirm("Удалить сохранённый ответ /tag "+reply.shortcut+"?")&&runAction(
          ()=>request("/replies/"+encodeURIComponent(reply.shortcut),"DELETE",{}),"Ответ удалён.",renderReplies
        ))
      );
      item.append(controls);
      list.append(item);
    }
    if(!(data.replies||[]).length) list.append(make("div","tb-empty","Сохранённых ответов нет."));
    view.append(list);
    const form=make("form","tb-editor-card");
    const shortcut=input("text","","например: greeting");
    const title=input("text","","Название ответа");
    const body=textarea("","Текст ответа…",4);
    const save=make("button","tb-primary","Сохранить ответ");save.type="submit";
    form.append(make("h3","","Добавить / обновить ответ"),field("Команда",shortcut),field("Название",title),field("Текст",body),save);
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      await runAction(()=>request("/replies","POST",{shortcut:shortcut.value,title:title.value,content:body.value}),
        "Ответ сохранён.",renderReplies);
    });
    view.append(form);contentEl.replaceChildren(view);
  };

  const renderTags = async () => {
    const data=await request("/tags");
    const view=make("div","tb-view");
    view.append(heading("Теги","Метки для классификации тикетов."));
    const list=make("div","tb-tag-cloud");
    for(const tag of data.tags||[]) {
      const row=make("div","tb-tag-row");
      const item=make("span","tb-tag-chip",tag.name);
      item.style.borderColor=tag.color||"#8b5cf6";
      item.style.color=tag.color||"#c4b5fd";
      row.append(item,button("Удалить","tb-button is-danger",()=>confirm("Удалить тег «"+tag.name+"»?")&&runAction(
        ()=>request("/tags/"+tag.id,"DELETE",{}),"Тег удалён.",renderTags
      )));
      list.append(row);
    }
    if(!(data.tags||[]).length) list.append(make("div","tb-empty","Теги ещё не созданы."));
    view.append(list);
    const form=make("form","tb-editor-card");
    const name=input("text","","Например: Важно");
    const color=input("color","#8b5cf6");
    const save=make("button","tb-primary","Создать тег");save.type="submit";
    form.append(field("Название",name),field("Цвет",color),save);
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      await runAction(()=>request("/tags","POST",{name:name.value,color:color.value}),"Тег сохранён.",renderTags);
    });
    view.append(form);contentEl.replaceChildren(view);
  };

  const renderKnowledge = async () => {
    const data=await request("/knowledge");
    const view=make("div","tb-view");
    view.append(heading("База знаний","Статьи доступны без лимита продукта. Используй их для быстрых ответов и инструкций."));
    const list=make("div","tb-panel-list");
    for(const article of data.articles||[]) {
      const item=make("article","tb-panel-row");
      item.append(make("div","tb-panel-main",article.title),statusBadge(article.published?"Опубликована":"Черновик",!!article.published),
        make("small","",article.category+" · "+article.language+" · "+article.slug),
        make("p","tb-wrap",article.body));
      const controls=make("div","tb-actions");
      controls.append(
        button("Изменить","tb-button",()=>{
          slug.value=article.slug;title.value=article.title;category.value=article.category||"General";
          language.value=article.language||"en";body.value=article.body||"";
          form.scrollIntoView({behavior:"smooth",block:"start"});title.focus();
        }),
        button("Удалить","tb-button is-danger",()=>confirm("Удалить статью «"+article.title+"»?")&&runAction(
          ()=>request("/knowledge/"+article.id,"DELETE",{}),"Статья удалена.",renderKnowledge
        ))
      );
      item.append(controls);
      list.append(item);
    }
    if(!(data.articles||[]).length) list.append(make("div","tb-empty","Статей пока нет."));
    view.append(list);
    const form=make("form","tb-editor-card");
    const slug=input("text","","getting-started");
    const title=input("text","","Заголовок статьи");
    const category=input("text","General","Категория");
    const language=input("text","en","Язык");
    const body=textarea("","Текст статьи…",7);
    const save=make("button","tb-primary","Сохранить статью");save.type="submit";
    form.append(make("h3","","Новая статья"),field("Slug",slug),field("Название",title),
      field("Категория",category),field("Язык",language),field("Содержание",body),save);
    form.addEventListener("submit",async event=>{
      event.preventDefault();
      await runAction(()=>request("/knowledge","POST",{slug:slug.value,title:title.value,
        category:category.value,language:language.value,body:body.value}),"Статья сохранена.",renderKnowledge);
    });
    view.append(form);contentEl.replaceChildren(view);
  };

  const renderAnalytics = async () => {
    const data=await request("/analytics");
    const counts=data.counts||{};
    const view=make("div","tb-view");
    view.append(heading("Аналитика","Время первого ответа, время решения, активность по дням и часам, рейтинг персонала."));
    const stats=make("div","tb-stats-grid");
    stats.append(card("Всего тикетов",counts.total||0),card("Открыто",counts.open||0),
      card("Закрыто",counts.closed||0),
      card("Среднее время ответа",formatDuration(counts.avg_first_response_seconds)),
      card("Среднее время решения",formatDuration(counts.avg_resolution_seconds)));
    view.append(stats);
    const heat=make("section","tb-editor-card");
    heat.append(make("h3","","Тепловая карта активности"));
    const table=make("table","tb-data-table");
    const header=make("tr","");for(const label of ["День недели","Час","Активность"])header.append(make("th","",label));
    table.append(header);
    const heatRows=data.activity_heatmap||[];
    const maxActivity=Math.max(1,...heatRows.map(item=>Number(item.count)||0));
    for(const event of heatRows) {
      const row=make("tr","");
      row.append(make("td","",weekdayLabel(event.weekday)),make("td","",event.hour+":00"));
      const cell=make("td","",event.count);
      const intensity=Math.min(.82,.12+(Number(event.count)||0)/maxActivity*.62);
      cell.style.backgroundColor="rgba(139,92,246,"+intensity+")";
      cell.style.borderRadius="5px";
      row.append(cell);table.append(row);
    }
    heat.append(table);view.append(heat);
    const board=make("section","tb-editor-card");
    board.append(make("h3","","Лидерборд персонала"));
    for(const item of data.staff_leaderboard||[]) board.append(make("div","tb-leader-row","#"+item.actor_id+" — "+item.claims+" назначений"));
    if(!(data.staff_leaderboard||[]).length) board.append(make("p","tb-muted","Пока нет событий claiming."));
    view.append(board);contentEl.replaceChildren(view);
  };

  const renderAudit = async () => {
    const data=await request("/audit?limit=200");
    const view=make("div","tb-view");
    view.append(heading("Аудит действий","Кто и когда менял настройки, персонал, панели и тикеты."));
    const list=make("div","tb-audit-list");
    for(const event of data.events||[]) {
      const row=make("article","tb-audit-row");
      row.append(make("strong","",event.action),make("small","",event.created_at+" · Actor "+(event.actor_id||"system")),
        make("small","",event.target_type+" · "+event.target_id));
      let detail="";
      try{detail=JSON.stringify(JSON.parse(event.after_json||"{}"));}catch{}
      if(detail && detail!=="{}") row.append(make("code","tb-audit-detail",detail));
      list.append(row);
    }
    if(!(data.events||[]).length) list.append(make("div","tb-empty","Записей аудита пока нет."));
    view.append(list);contentEl.replaceChildren(view);
  };

  const formatDuration = (value) => {
    if(value===null||value===undefined||!Number.isFinite(Number(value))) return "—";
    const total=Math.max(0,Math.round(Number(value)));
    if(total<60) return total+" сек.";
    if(total<3600) return Math.floor(total/60)+" мин.";
    if(total<86400) return Math.floor(total/3600)+" ч "+Math.floor(total%3600/60)+" мин.";
    return Math.floor(total/86400)+" д "+Math.floor(total%86400/3600)+" ч";
  };
  const weekdayLabel = (value) => (["Вс","Пн","Вт","Ср","Чт","Пт","Сб"][Number(value)]||value);
  const showError = (error) => showNotice(error?.message||String(error),"error");
  const runAction = async (action,message,refresh) => {
    try { await action();showNotice(message,"success");if(refresh) await refresh(); }
    catch(error){showError(error);}
  };
  const renderTab = async () => {
    loading("Загружаем раздел…");
    try {
      if(activeTab!=="overview" && activeTab!=="tickets") {
        if(!channelsCache.length || !rolesCache.length) await loadCommonData();
      }
      if(activeTab==="overview") await renderOverview();
      else if(activeTab==="tickets") await renderTickets();
      else if(activeTab==="panels") await renderPanels();
      else if(activeTab==="staff") await renderStaff();
      else if(activeTab==="settings") await renderSettings();
      else if(activeTab==="botProfile") await renderBotProfile();
      else if(activeTab==="schedules") await renderSchedules();
      else if(activeTab==="replies") await renderReplies();
      else if(activeTab==="tags") await renderTags();
      else if(activeTab==="knowledge") await renderKnowledge();
      else if(activeTab==="analytics") await renderAnalytics();
      else if(activeTab==="audit") await renderAudit();
    } catch(error) {
      contentEl.replaceChildren(make("div","tb-empty is-error",error?.message||String(error)));
      showError(error);
    }
  };
  const palette = $("#tbCommandModal");
  const paletteInput = $("#tbCommandSearch");
  const paletteResults = $("#tbCommandResults");
  const renderPalette = () => {
    const query=paletteInput.value.trim().toLowerCase();
    paletteResults.replaceChildren();
    const items=tabs.filter(item=>!query || item[1].toLowerCase().includes(query) || item[0].includes(query));
    for(const item of items) {
      const option=button(item[1],"tb-command-option",()=>{palette.hidden=true;setActiveTab(item[0]);});
      option.append(make("small","",item[0]));
      paletteResults.append(option);
    }
    if(!items.length) paletteResults.append(make("div","tb-empty","Ничего не найдено."));
  };
  const openPalette = () => {
    palette.hidden=false;paletteInput.value="";renderPalette();paletteInput.focus();
  };
  const closePalette = () => {palette.hidden=true;};
  $("#tbCommandOpen").addEventListener("click",openPalette);
  palette.querySelector("[data-close]").addEventListener("click",closePalette);
  paletteInput.addEventListener("input",renderPalette);
  if(window.__ticketBotPaletteHandler) document.removeEventListener("keydown",window.__ticketBotPaletteHandler);
  window.__ticketBotPaletteHandler = (event) => {
    if((event.ctrlKey||event.metaKey) && event.key.toLowerCase()==="k") {
      if(!root.isConnected) return;
      event.preventDefault();
      openPalette();
    } else if(event.key==="Escape" && !palette.hidden) closePalette();
  };
  document.addEventListener("keydown",window.__ticketBotPaletteHandler);

  $("#tbTabs").addEventListener("click",event=>{
    const btn=event.target.closest("[data-tab]");
    if(btn) setActiveTab(btn.dataset.tab);
  });
  guildSelect.addEventListener("change",async()=>{
    guildId=guildSelect.value;overviewCache=null;channelsCache=[];rolesCache=[];currentTicket=null;
    await renderTab();
  });
  $("#tbRefresh").addEventListener("click",async()=>{
    try{overviewCache=null;channelsCache=[];rolesCache=[];await renderTab();showNotice("Данные обновлены.","success");}
    catch(error){showError(error);}
  });

  try {
    await renderGuildPicker();
    await renderTab();
  } catch(error) {
    stateEl.textContent="Нет соединения";
    stateEl.classList.add("is-error");
    contentEl.replaceChildren(make("div","tb-empty is-error",error?.message||String(error)));
    showError(error);
  }
};
