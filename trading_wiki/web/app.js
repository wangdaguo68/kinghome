const state = {
  data: null,
  pages: new Map(),
  focusId: null,
  selectedDomain: "全部",
  selectedModule: "",
  view: "home",
  depth: 1,
  query: "",
  books: [],
  readerRequestId: 0,
  graphRenderTimer: null,
};

const SYSTEM_TREE = [
  {
    id: "01",
    name: "认知系统",
    subtitle: "人如何思考",
    modules: [
      ["脑科学", ["神经", "脑区", "多巴胺", "奖赏", "杏仁核", "海马体", "注意力系统", "默认模式网络"]],
      ["认知心理学", ["认知心理", "系统1", "系统2", "认知偏差", "确认偏误", "锚定", "记忆", "注意"]],
      ["行为心理学", ["行为心理", "习惯", "行为改变", "强化", "奖赏", "上瘾"]],
      ["决策心理学", ["决策", "损失厌恶", "风险决策", "判断", "偏差"]],
      ["学习科学", ["学习", "刻意练习", "心流", "记忆", "反馈", "迁移"]],
      ["亲子教育", ["亲子", "教育", "发展心理", "依恋", "儿童"]],
    ],
  },
  {
    id: "02",
    name: "智能系统",
    subtitle: "AI如何工作",
    modules: [
      ["AI基础", ["AI基础", "人工智能", "Transformer", "Token", "参数", "机器学习", "深度学习"]],
      ["大模型", ["大模型", "Scaling Law", "训练", "推理", "多模态", "世界模型"]],
      ["Agent", ["Agent", "工具调用", "工作流", "自动化"]],
      ["数据与知识库", ["数据", "知识库", "RAG", "Embedding", "向量数据库", "语义搜索"]],
      ["算力", ["算力", "GPU", "HBM", "CoWoS", "Chiplet", "AI服务器", "推理成本"]],
      ["AI应用", ["AI应用", "应用层", "AI医疗", "端侧AI", "AI PC", "AI手机"]],
      ["AI安全", ["AI安全", "幻觉", "偏见", "越权", "风险管理"]],
    ],
  },
  {
    id: "03",
    name: "产业系统",
    subtitle: "技术如何变成产业",
    modules: [
      ["半导体", ["半导体", "芯片", "HBM", "先进封装", "光刻", "刻蚀", "沉积", "CMP", "晶圆"]],
      ["AI硬件", ["AI硬件", "AI服务器", "PCB", "CPO", "光模块", "MLCC", "液冷", "电源"]],
      ["机器人", ["机器人", "人形机器人", "减速器", "伺服", "执行器", "传感器"]],
      ["汽车", ["汽车", "车载", "智能驾驶", "汽车电子", "车机"]],
      ["化工材料", ["化工", "材料", "树脂", "铜箔", "电子布", "特气", "高分子"]],
      ["电力能源", ["电力", "能源", "HVDC", "储能", "电网", "铜", "铝"]],
      ["医疗生物", ["医药", "医疗", "创新药", "CXO", "器械", "IVD", "生物"]],
    ],
  },
  {
    id: "04",
    name: "财富系统",
    subtitle: "价值如何流动",
    modules: [
      ["经济学", ["经济学", "供需", "价格弹性", "周期", "库存周期", "通胀"]],
      ["金融学", ["金融", "利率", "资产定价", "现金流", "DCF", "ROE", "杜邦"]],
      ["投资框架", ["投资框架", "估值", "PEG", "风险收益比", "赔率", "预期差"]],
      ["交易系统", ["交易系统", "交易", "主线", "补涨", "退潮", "情绪周期", "赚钱效应"]],
      ["公司研究", ["公司研究", "商业质量", "护城河", "财报", "订单", "利润弹性"]],
      ["A股产业链机会库", ["A股", "产业链机会", "涨价链", "国产替代", "核心受益标的"]],
    ],
  },
  {
    id: "05",
    name: "生命系统",
    subtitle: "生命如何运转",
    modules: [
      ["基础医学", ["基础医学", "细胞", "基因", "DNA", "RNA", "蛋白质", "免疫", "炎症"]],
      ["营养学", ["营养", "代谢", "胰岛素", "线粒体", "饮食"]],
      ["睡眠科学", ["睡眠", "昼夜节律", "清理", "修复"]],
      ["运动科学", ["运动", "小脑", "运动系统", "训练", "体能"]],
      ["AI医疗", ["AI医疗", "AI制药", "医疗AI", "诊断", "药物发现"]],
      ["长寿科学", ["长寿", "衰老", "抗衰", "寿命", "慢病"]],
    ],
  },
  {
    id: "06",
    name: "物理系统",
    subtitle: "现实世界如何运转",
    modules: [
      ["物理基础", ["物理基础", "能量", "力", "电", "热", "物理约束"]],
      ["能源", ["能源", "电力", "数据中心", "AI基础设施", "电网"]],
      ["材料", ["材料", "材料强度", "高分子", "玻璃基板", "ABF", "电子材料"]],
      ["热管理", ["热管理", "液冷", "导热", "散热", "相变材料"]],
      ["制造", ["制造", "良率", "规模化", "自动化", "工业工程"]],
      ["机器人硬件", ["机器人硬件", "电机", "减速器", "传感器", "BOM", "执行器"]],
    ],
  },
  {
    id: "07",
    name: "美学系统",
    subtitle: "什么是美",
    modules: [
      ["美学", ["美学", "高级感", "风格", "比例", "留白", "构图", "色彩"]],
      ["艺术史", ["艺术史", "艺术", "文明", "风格演化"]],
      ["视觉设计", ["视觉设计", "视觉层级", "构图", "色彩", "字体", "界面"]],
      ["产品美学", ["产品美学", "产品", "质感", "体验", "交互"]],
      ["审美心理学", ["审美心理", "格式塔", "熟悉感", "陌生感", "审美周期"]],
      ["AI美学", ["AI美学", "AI生成", "AIGC", "AI图片", "生成内容"]],
    ],
  },
  {
    id: "08",
    name: "意义系统",
    subtitle: "什么值得被记住",
    modules: [
      ["哲学", ["哲学", "存在", "认识论", "伦理学", "形而上学", "价值", "意义", "现象学", "自由意志"]],
      ["哲学大师", ["孔子", "孟子", "老子", "庄子", "王阳明", "苏格拉底", "柏拉图", "亚里士多德", "笛卡尔", "休谟", "康德", "黑格尔", "尼采", "马克思", "海德格尔", "维特根斯坦", "福柯", "弗洛伊德", "荣格"]],
      ["符号学", ["符号", "隐喻", "象征", "意义生成"]],
      ["叙事学", ["叙事", "故事", "英雄之旅", "冲突"]],
      ["品牌学", ["品牌", "定位", "心智", "溢价", "信任"]],
      ["传播学", ["传播", "裂变", "媒介", "社群", "IP"]],
      ["文化研究", ["文化", "圈层", "身份认同", "消费符号"]],
      ["消费心理", ["消费心理", "情绪价值", "仪式感", "意义溢价"]],
    ],
  },
  {
    id: "09",
    name: "范式系统",
    subtitle: "新旧世界如何更替",
    modules: [
      ["科学哲学", ["科学哲学", "知识更新", "证伪", "科学"]],
      ["范式理论", ["范式", "范式转移", "科学革命"]],
      ["复杂系统", ["复杂系统", "系统科学", "涌现", "临界点", "路径依赖"]],
      ["创新理论", ["创新", "技术扩散", "S曲线", "颠覆式创新", "跨越鸿沟"]],
      ["未来学", ["未来学", "场景推演", "情景规划", "未来场景"]],
      ["技术哲学", ["技术哲学", "技术", "人类改变"]],
      ["文明史", ["文明史", "文明周期", "大周期", "变迁"]],
    ],
  },
];
const SYSTEM_NAMES = SYSTEM_TREE.map((system) => system.name);
const CREATE_DRAFT_KEY = "knowledge-os-create-draft";
const BOOK_READER_ORIGIN = "http://127.0.0.1:8793";
const SYSTEM_BOOK_CATEGORIES = {
  "认知系统": ["心理学", "脑科学"],
  "智能系统": ["科技AI"],
  "产业系统": ["商业产业", "科技AI", "经济金融"],
  "财富系统": ["经济金融", "商业产业"],
  "生命系统": ["医学健康", "心理学", "脑科学"],
  "物理系统": ["科技AI", "商业产业"],
  "美学系统": ["美学", "品牌传播"],
  "意义系统": ["哲学", "佛学", "心理学", "历史文明", "品牌传播"],
  "范式系统": ["哲学", "历史文明", "商业产业", "科技AI"],
};

async function boot() {
  const response = await fetch("./data/wiki-index.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`无法读取图谱数据: ${response.status}`);
  const data = await response.json();
  if (!data.pages?.length) throw new Error("图谱数据为空，请先运行 python scripts/build_web_data.py");
  state.data = data;
  state.pages = new Map(data.pages.map((page) => [page.id, page]));
  state.focusId = data.root_id || data.pages[0]?.id;
  try {
    const bookResponse = await fetch("./data/book-index.json", { cache: "no-store" });
    if (bookResponse.ok) {
      const bookData = await bookResponse.json();
      state.books = bookData.books || [];
    }
  } catch {
    state.books = [];
  }
  renderStaticControls();
  bindEvents();
  await render();
}

function bindEvents() {
  document.getElementById("searchInput").addEventListener("input", (event) => {
    state.query = event.target.value.trim().toLowerCase();
    const best = state.query ? searchPages()[0] : null;
    if (best) state.focusId = best.id;
    if (state.query && state.view !== "home") setView("home", false);
    render();
  });

  document.querySelectorAll("#viewTabs button[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  document.getElementById("depthControl").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-depth]");
    if (!button) return;
    state.depth = Number(button.dataset.depth);
    document.querySelectorAll("#depthControl button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    scheduleGraphRender();
  });

  document.getElementById("resetBtn").addEventListener("click", () => {
    selectDomain("全部");
    render();
  });
  document.getElementById("openReaderBtn").addEventListener("click", () => setView("reader"));
  document.getElementById("openGraphBtn").addEventListener("click", () => setView("graph"));
  document.getElementById("allTopicsBtn").addEventListener("click", () => setView("library"));
  document.getElementById("allNotesBtn").addEventListener("click", () => setView("library"));
  bindCreateForm();

  document.getElementById("domainList").addEventListener("click", (event) => {
    const moduleButton = event.target.closest("button[data-module]");
    if (moduleButton) {
      selectModule(moduleButton.dataset.domain, moduleButton.dataset.module);
      render();
      return;
    }

    const button = event.target.closest("button[data-domain]");
    if (!button) return;
    selectDomain(button.dataset.domain);
    render();
  });
}

function renderStaticControls() {
  renderDomains();
  renderStats();
}

function renderDomains() {
  const target = document.getElementById("domainList");
  const allCount = state.data.pages.length;
  target.innerHTML = `
    <button class="domain-button all-domain ${state.selectedDomain === "全部" ? "active" : ""}" data-domain="全部">
      <span>个人知识库大全</span>
      <small>${allCount}</small>
    </button>
    ${SYSTEM_TREE.map((system) => {
      const systemCount = countSystemPages(system.name);
      const expanded = state.selectedDomain === system.name;
      return `
        <section class="system-group ${expanded ? "expanded" : ""}">
          <button class="domain-button system-head ${expanded && !state.selectedModule ? "active" : ""}" data-domain="${escapeAttr(system.name)}">
            <span><b>${system.id}</b>${escapeHtml(system.name.replace(/系统$/, ""))}</span>
            <small>${systemCount}</small>
          </button>
          <div class="module-list">
            ${system.modules.map(([moduleName]) => {
              const count = countModulePages(system.name, moduleName);
              const active = expanded && state.selectedModule === moduleName;
              return `
                <button class="module-button ${active ? "active" : ""}" data-domain="${escapeAttr(system.name)}" data-module="${escapeAttr(moduleName)}">
                  <span>${escapeHtml(moduleName)}</span>
                  <small>${count}</small>
                </button>
              `;
            }).join("")}
          </div>
        </section>
      `;
    }).join("")}
  `;
}

function renderStats() {
  const target = document.getElementById("statsGrid");
  const stats = [
    ["页面", state.data.pages.length],
    ["关系", state.data.edges.length],
    ["专题", state.data.topic_maps?.length || topicMaps().length],
    ["系统", state.data.domains.filter((item) => item.name !== "全部" && item.count > 0).length],
  ];
  target.innerHTML = stats.map(([name, count]) => `
    <div class="stat"><strong>${count}</strong><span>${name}</span></div>
  `).join("");
}

async function render() {
  renderDomains();
  const visiblePages = filteredPages();
  if (state.query && visiblePages.length && !visiblePages.some((page) => page.id === state.focusId)) {
    state.focusId = visiblePages[0].id;
  }
  const focus = state.pages.get(state.focusId) || visiblePages[0] || state.data.pages[0];
  if (!focus) return;
  document.getElementById("focusTitle").textContent = currentScopeTitle();
  document.getElementById("workspaceEyebrow").textContent = state.view === "reader" ? "Reading" : currentScopeEyebrow();
  renderContext(focus);
  await renderActiveView();
}

function setView(view, shouldRender = true) {
  state.view = view;
  document.querySelectorAll("#viewTabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  document.querySelectorAll(".workspace-view").forEach((section) => {
    section.classList.toggle("active", section.id === `${view}View`);
  });
  document.getElementById("workspaceEyebrow").textContent = view === "reader" ? "Reading" : currentScopeEyebrow();
  if (shouldRender) renderActiveView();
}

async function renderActiveView() {
  if (state.view === "home") renderHome();
  else if (state.view === "library") renderLibrary();
  else if (state.view === "reader") await renderReader();
  else if (state.view === "graph") scheduleGraphRender();
  else if (state.view === "table") renderTable();
  else if (state.view === "create") renderCreate();
}

function filteredPages() {
  const query = state.query;
  if (query) {
    return searchPages();
  }
  return state.data.pages
    .filter((page) => matchesSystem(page, state.selectedDomain))
    .filter((page) => matchesModule(page, state.selectedDomain, state.selectedModule));
}

function searchPages() {
  const query = state.query;
  if (!query) return [];
  return state.data.pages
    .map((page) => ({ page, score: searchRank(page, query) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || String(b.page.updated || b.page.created).localeCompare(String(a.page.updated || a.page.created)))
    .map((item) => item.page);
}

function searchRank(page, query) {
  const title = String(page.title || "").toLowerCase();
  const stem = String(page.path || "").split("/").pop()?.replace(/\.md$/, "").toLowerCase() || "";
  const topics = [...(page.topics || []), ...(page.tags || [])].map((item) => String(item).toLowerCase());
  const summary = String(page.summary || "").toLowerCase();
  const body = String(page.search_text || "").toLowerCase();
  const system = String(page.system || page.domain || "").toLowerCase();
  let score = 0;

  if (title === query || stem === query) score += 10000;
  if (title.startsWith(query) || stem.startsWith(query)) score += 6500;
  if (title.includes(query)) score += 5200 - Math.min(title.indexOf(query), 100);
  if (stem.includes(query)) score += 4800 - Math.min(stem.indexOf(query), 100);
  if (topics.some((item) => item === query)) score += 2600;
  if (topics.some((item) => item.includes(query))) score += 1600;
  if (system.includes(query)) score += 900;
  if (summary.includes(query)) score += 700;
  if (body.includes(query)) score += 200;
  if (page.is_topic_map) score += 80;
  if (page.folder === "概念") score += 50;
  return score;
}

function topicMaps() {
  const ids = new Set(state.data.topic_maps || []);
  return state.data.pages.filter((page) => ids.has(page.id) || page.is_topic_map);
}

function renderHome() {
  const pages = filteredPages();
  if (state.query) {
    renderSearchHome(pages);
    return;
  }
  setHomeLabels("专题地图", "查看全部", "最近更新", "进入目录", "待思考 / 待验证");
  const overview = document.getElementById("overviewGrid");
  const domains = state.data.domains.filter((domain) => domain.name !== "全部");
  overview.innerHTML = domains.map((domain) => `
    <button class="domain-card ${domain.name === state.selectedDomain ? "active" : ""}" data-domain="${escapeAttr(domain.name)}">
      <strong>${escapeHtml(domain.name)}</strong>
      <span>${domain.count ? `${domain.count} 条笔记` : "等待沉淀"}</span>
      <p class="meta-line">${domainHint(domain.name)}</p>
    </button>
  `).join("");
  overview.querySelectorAll("[data-domain]").forEach((button) => {
    button.addEventListener("click", () => {
      selectDomain(button.dataset.domain);
      render();
    });
  });

  const topics = topicMaps()
    .filter((page) => matchesSystem(page, state.selectedDomain))
    .filter((page) => matchesModule(page, state.selectedDomain, state.selectedModule))
    .filter((page) => !state.query || searchable(page).includes(state.query))
    .slice(0, 9);
  document.getElementById("topicGrid").innerHTML = topics.length ? topics.map(topicCard).join("") : emptyState("这个领域还没有专题地图。以后新增 Markdown 并写入 domain 后，会自动出现在这里。");
  bindPageButtons(document.getElementById("topicGrid"));

  const recent = [...pages]
    .sort((a, b) => String(b.updated || b.created).localeCompare(String(a.updated || a.created)))
    .slice(0, 12);
  document.getElementById("recentList").innerHTML = recent.length ? recent.map(noteRow).join("") : emptyState("没有匹配的笔记。");
  bindPageButtons(document.getElementById("recentList"));

  const questions = collectQuestions(pages).slice(0, 12);
  document.getElementById("questionCount").textContent = `${questions.length} 项`;
  document.getElementById("questionList").innerHTML = questions.length ? questions.map((item) => `
    <button class="question-item" data-id="${escapeAttr(item.page.id)}">
      <strong>${escapeHtml(item.text)}</strong>
      <span>${escapeHtml(item.page.title)} · ${escapeHtml(item.page.system || item.page.domain || "未分类")}</span>
    </button>
  `).join("") : emptyState("当前筛选下没有待思考或待验证清单。");
  bindPageButtons(document.getElementById("questionList"));
  renderHomeReading(state.pages.get(state.focusId) || pages[0]);
}

function renderSearchHome(pages) {
  setHomeLabels("命中结果", "进入目录", "上下游 / 关联概念", "看全部", "验证清单 / 相关问题");
  const overview = document.getElementById("overviewGrid");
  const focus = state.pages.get(state.focusId) || pages[0];
  const related = relatedConceptPages(focus);

  overview.innerHTML = focus ? `
    <article class="search-focus-card">
      <div>
        <p class="eyebrow">Best Match</p>
        <h3>${escapeHtml(focus.title)}</h3>
        <p>${escapeHtml(focus.summary || "暂无摘要。")}</p>
        <div class="tag-list">
          <span class="tag">${escapeHtml(focus.system || focus.domain || "未分类")}</span>
          <span class="tag">${escapeHtml(focus.folder || "知识卡")}</span>
          ${focus.is_topic_map ? '<span class="tag">专题地图</span>' : ""}
        </div>
      </div>
      <div class="search-focus-actions">
        <button data-id="${escapeAttr(focus.id)}">定位到该概念</button>
        <button data-view-target="reader">阅读全文</button>
        <button data-view-target="graph">看关系</button>
      </div>
    </article>
  ` : emptyState("没有匹配的概念。");

  overview.querySelector("[data-id]")?.addEventListener("click", () => selectPage(focus.id));
  overview.querySelector('[data-view-target="reader"]')?.addEventListener("click", () => selectPage(focus.id, "reader"));
  overview.querySelector('[data-view-target="graph"]')?.addEventListener("click", () => selectPage(focus.id, "graph"));

  document.getElementById("topicGrid").innerHTML = pages.length ? pages.slice(0, 12).map(searchResultCard).join("") : emptyState("没有匹配的笔记。");
  bindPageButtons(document.getElementById("topicGrid"));

  document.getElementById("recentList").innerHTML = related.length ? related.slice(0, 12).map(relationRow).join("") : emptyState("这个概念还没有直接出链或反链。后续需要补 wikilink 才能形成上下游关系。");
  bindPageButtons(document.getElementById("recentList"));

  const questions = collectQuestions([focus, ...related.map((item) => item.page)].filter(Boolean)).slice(0, 12);
  document.getElementById("questionCount").textContent = `${questions.length} 项`;
  document.getElementById("questionList").innerHTML = questions.length ? questions.map((item) => `
    <button class="question-item" data-id="${escapeAttr(item.page.id)}">
      <strong>${escapeHtml(item.text)}</strong>
      <span>${escapeHtml(item.page.title)} · ${escapeHtml(item.page.system || item.page.domain || "未分类")}</span>
    </button>
  `).join("") : emptyState("当前概念没有验证清单或相关问题。");
  bindPageButtons(document.getElementById("questionList"));
  renderHomeReading(focus);
}

function renderLibrary() {
  const pages = filteredPages().sort(sortByDomainAndTitle);
  const target = document.getElementById("libraryList");
  target.innerHTML = pages.length ? pages.map(noteRow).join("") : emptyState("没有匹配的笔记。");
  bindPageButtons(target);
}

async function renderReader() {
  const page = state.pages.get(state.focusId);
  if (!page) return;
  const requestId = ++state.readerRequestId;
  const markdown = await fetchMarkdown(page.path);
  if (requestId !== state.readerRequestId) return;
  document.getElementById("markdownView").innerHTML = markdownToHtml(markdown);
  document.querySelectorAll("[data-wikilink]").forEach((link) => {
    link.addEventListener("click", () => {
      const target = findByTitle(link.dataset.wikilink);
      if (target) {
        selectPage(target.id, "reader");
      }
    });
  });
}

function renderTable() {
  const pages = filteredPages().sort(sortByDomainAndTitle);
  const table = document.getElementById("dataTable");
  table.innerHTML = `
    <thead>
      <tr>
        <th>标题</th>
        <th>系统</th>
        <th>证据/信心</th>
        <th>更新</th>
        <th>路径</th>
      </tr>
    </thead>
    <tbody>
      ${pages.map((page) => `
        <tr>
          <td><button data-id="${escapeAttr(page.id)}">${escapeHtml(page.title)}</button></td>
          <td>${escapeHtml(page.system || page.domain || "未分类")}</td>
          <td>${escapeHtml(page.confidence || page.evidence_level || "")}</td>
          <td>${escapeHtml(page.updated || page.created || "")}</td>
          <td>${escapeHtml(page.path)}</td>
        </tr>
      `).join("")}
    </tbody>
  `;
  bindPageButtons(table);
}

function bindCreateForm() {
  const form = document.getElementById("createForm");
  if (!form) return;
  document.getElementById("createSystemPicker").innerHTML = SYSTEM_NAMES.map((name) => `
    <label class="system-check">
      <input type="checkbox" name="systems" value="${escapeAttr(name)}">
      <span>${escapeHtml(name)}</span>
    </label>
  `).join("");
  form.addEventListener("input", updateCreatePreview);
  form.addEventListener("change", updateCreatePreview);
  document.getElementById("saveDraftBtn").addEventListener("click", saveCreateDraft);
  document.getElementById("clearDraftBtn").addEventListener("click", clearCreateDraft);
  document.getElementById("downloadCardBtn").addEventListener("click", downloadCreateMarkdown);
  loadCreateDraft();
  updateCreatePreview();
}

function renderCreate() {
  updateCreatePreview();
}

function collectCreateForm() {
  const form = document.getElementById("createForm");
  const data = Object.fromEntries(new FormData(form).entries());
  data.systems = [...form.querySelectorAll("input[name='systems']:checked")].map((input) => input.value);
  return data;
}

function createMarkdown(data) {
  const title = data.title?.trim() || "未命名知识卡片";
  const systems = data.systems?.length ? data.systems : ["未分类"];
  const today = new Date().toISOString().slice(0, 10);
  const primarySystem = systems[0];
  return `---\ntitle: "${yamlEscape(title)}"\ntype: concept\nfolder: 概念\ndomain: ${primarySystem}\nsystem: ${primarySystem}\nsystems:\n${systems.map((item) => `  - ${item}`).join("\n")}\nnote_type: concept\ncreated: ${today}\nupdated: ${today}\nstatus: draft\nconfidence: low\nevidence_level: low\nexecution_permission: learning_only\ntopics:\n  - 待整理\ntags:\n  - knowledge/card\nrelated_questions:\n  - 这个概念最值得迁移到哪里？\n---\n\n# ${title}\n\n## 所属系统\n\n${systems.map((item) => `- ${item}`).join("\n")}\n\n## 一句话解释\n\n${fieldOrPlaceholder(data.summary)}\n\n## 核心原理\n\n${fieldOrPlaceholder(data.principle)}\n\n## 关键模型\n\n${listBlock(data.models)}\n\n## 典型案例\n\n${listBlock(data.cases)}\n\n## 相关产业\n\n${listBlock(data.industries)}\n\n## 我的启发\n\n${fieldOrPlaceholder(data.insight)}\n\n## 可迁移场景\n\n${listBlock(data.transfer)}\n\n## 风险和误区\n\n${listBlock(data.risks)}\n\n## 关联知识\n\n${wikiListBlock(data.related)}\n`;
}

function updateCreatePreview() {
  const target = document.getElementById("createPreview");
  if (!target) return;
  target.innerHTML = markdownToHtml(createMarkdown(collectCreateForm()));
}

function saveCreateDraft() {
  localStorage.setItem(CREATE_DRAFT_KEY, JSON.stringify(collectCreateForm()));
}

function loadCreateDraft() {
  const raw = localStorage.getItem(CREATE_DRAFT_KEY);
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    const form = document.getElementById("createForm");
    for (const [key, value] of Object.entries(data)) {
      if (key === "systems") continue;
      const input = form.elements[key];
      if (input) input.value = value || "";
    }
    for (const input of form.querySelectorAll("input[name='systems']")) {
      input.checked = (data.systems || []).includes(input.value);
    }
  } catch {
    localStorage.removeItem(CREATE_DRAFT_KEY);
  }
}

function clearCreateDraft() {
  localStorage.removeItem(CREATE_DRAFT_KEY);
  document.getElementById("createForm").reset();
  updateCreatePreview();
}

function downloadCreateMarkdown() {
  const data = collectCreateForm();
  const markdown = createMarkdown(data);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${safeFileName(data.title || "未命名知识卡片")}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

function renderContext(page) {
  document.getElementById("detailType").textContent = page.system || page.domain || "未分类";
  document.getElementById("detailTitle").textContent = page.title;
  document.getElementById("detailMeta").textContent = [
    page.confidence ? `信心 ${page.confidence}` : page.evidence_level ? `证据 ${page.evidence_level}` : "",
    page.execution_permission ? `权限 ${page.execution_permission}` : "",
    page.updated ? `更新 ${page.updated}` : "",
  ].filter(Boolean).join(" · ");
  document.getElementById("identityTags").innerHTML = [
    page.domain,
    page.system && page.system !== page.domain ? page.system : "",
    ...(page.topics || []),
    ...(page.tags || []).slice(0, 4),
  ].filter(Boolean).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("");
  renderLinkList("outLinks", page.resolved_links || []);
  renderLinkList("backLinks", page.backlinks || []);
  renderRelatedConcepts(page);
  renderReadingRecommendations(page);
  renderHeadings(page);
  renderChecklist(page);
}

function renderRelatedConcepts(page) {
  const target = document.getElementById("relatedConcepts");
  if (!target) return;
  const related = relatedConceptPages(page).slice(0, 16);
  target.innerHTML = related.length ? related.map(relationPill).join("") : `<span class="pill">暂无直接关系</span>`;
  bindPageButtons(target);
}

function renderReadingRecommendations(page) {
  const target = document.getElementById("readingList");
  if (!target) return;
  const books = recommendBooks(page, 8);
  target.innerHTML = books.length ? books.map(bookCard).join("") : `<span class="pill">暂无匹配书籍</span>`;
}

function renderHomeReading(page) {
  const target = document.getElementById("readingListHome");
  if (!target) return;
  const books = recommendBooks(page, state.query ? 10 : 6);
  document.getElementById("readingCount").textContent = books.length ? `${books.length} 本` : "";
  target.innerHTML = books.length ? books.map(bookCard).join("") : emptyState("没有匹配到本地书籍。可把 PDF / EPUB / MOBI / AZW3 放入 D:\\onlinereading 后重新生成索引。");
}

function recommendBooks(page, limit = 8) {
  if (!state.books.length) return [];
  const terms = readingTerms(page);
  const minScore = state.query ? 300 : 1;
  return state.books
    .map((book) => ({ book, score: bookScore(book, terms, page) }))
    .filter((item) => item.score >= minScore)
    .sort((a, b) => b.score - a.score || a.book.title.localeCompare(b.book.title, "zh-CN"))
    .slice(0, limit)
    .map((item) => item.book);
}

function bookScore(book, terms, page) {
  const title = String(book.title || "").toLowerCase();
  const text = String(book.search_text || "").toLowerCase();
  const categories = book.categories || [];
  const systemCategories = SYSTEM_BOOK_CATEGORIES[page?.system || page?.domain] || [];
  let score = 0;
  let directHit = false;
  if (state.query) {
    const query = state.query.toLowerCase();
    if (!title.includes(query) && !text.includes(query)) return 0;
  }

  for (const category of categories) {
    if (systemCategories.includes(category)) score += 220;
  }

  for (const term of terms) {
    const needle = term.toLowerCase();
    if (!needle || needle.length < 2) continue;
    if (title === needle) {
      score += 2600;
      directHit = true;
    }
    if (title.includes(needle)) {
      score += 700;
      directHit = true;
    }
    if (text.includes(needle)) {
      score += 140;
      directHit = true;
    }
  }

  if (state.query) {
    const query = state.query.toLowerCase();
    if (title.includes(query)) {
      score += 1800;
      directHit = true;
    }
    if (text.includes(query)) {
      score += 360;
      directHit = true;
    }
    if (!directHit) return 0;
  }

  if (book.extension === ".pdf" || book.extension === ".epub" || book.extension === ".txt") score += 35;
  if (book.extension === ".mobi" || book.extension === ".azw3") score += 15;
  if (categories.includes("未分类") && score < 400) score -= 100;
  return score;
}

function readingTerms(page) {
  const coreValues = [
    state.query,
    page?.title,
    page?.path,
    page?.system,
    page?.domain,
    ...(page?.topics || []),
    ...(page?.tags || []),
  ].filter(Boolean);
  const values = state.query ? coreValues : [
    ...coreValues,
    page?.summary,
    ...(page?.related_questions || []),
    ...(page?.headings || []).map((heading) => heading.title),
  ].filter(Boolean);

  const terms = new Set();
  for (const value of values) {
    const text = String(value).trim();
    if (!text) continue;
    terms.add(text);
    text
      .replace(/全景地图|专题地图|产业链|知识地图|基础地图|经典思想地图|系统/g, " ")
      .split(/[\s,，、\/|｜:：;；()[\]（）《》「」""'']+/)
      .map((item) => item.trim())
      .filter((item) => item.length >= 2 && item.length <= 18)
      .forEach((item) => terms.add(item));
  }
  return [...terms].slice(0, 60);
}

function bookCard(book) {
  const categories = (book.categories || []).slice(0, 3);
  return `
    <a class="book-card" href="${bookReadUrl(book)}" target="_blank" rel="noreferrer">
      <strong>${escapeHtml(book.title)}</strong>
      <span class="book-meta">${escapeHtml(book.extension?.replace(".", "").toUpperCase() || "BOOK")} · ${escapeHtml(book.size_label || "")} · ${escapeHtml(book.folder || "")}</span>
      <span class="book-path">${escapeHtml(book.relative_path || book.path || "")}</span>
      <span class="book-tags">${categories.map((category) => `<em>${escapeHtml(category)}</em>`).join("")}</span>
    </a>
  `;
}

function bookReadUrl(book) {
  return `${BOOK_READER_ORIGIN}/books/read/${encodeURIComponent(book.id)}`;
}

function renderHeadings(page) {
  const target = document.getElementById("headingList");
  const headings = (page.headings || []).filter((heading) => heading.level > 1).slice(0, 14);
  target.innerHTML = headings.length ? headings.map((heading) => `
    <div>${"&nbsp;".repeat(Math.max(0, heading.level - 2) * 2)}${escapeHtml(heading.title)}</div>
  `).join("") : `<span>无目录</span>`;
}

function renderChecklist(page) {
  const target = document.getElementById("checkList");
  const items = [
    ...(page.related_questions || []).map((text) => ({ done: false, text })),
    ...(page.checklist || []),
  ].slice(0, 12);
  target.innerHTML = items.length ? items.map((item) => `
    <div>${item.done ? "已完成" : "待处理"} · ${escapeHtml(item.text)}</div>
  `).join("") : `<span>无清单</span>`;
}

function renderLinkList(targetId, ids) {
  const target = document.getElementById(targetId);
  if (!ids.length) {
    target.innerHTML = `<span class="pill">无</span>`;
    return;
  }
  target.innerHTML = ids.slice(0, 18).map((id) => {
    const page = state.pages.get(id);
    if (!page) return "";
    return `<button class="pill" data-id="${escapeAttr(page.id)}">${escapeHtml(page.title)}</button>`;
  }).join("");
  bindPageButtons(target);
}

function relatedConceptPages(page) {
  if (!page) return [];
  const result = [];
  const seen = new Set();
  const add = (id, relation) => {
    if (!id || seen.has(id)) return;
    const linked = state.pages.get(id);
    if (!linked) return;
    seen.add(id);
    result.push({ page: linked, relation });
  };
  for (const id of page.resolved_links || []) add(id, "出链");
  for (const id of page.backlinks || []) add(id, "反链");
  return result;
}

function relationPill(item) {
  return `<button class="pill relation-pill" data-id="${escapeAttr(item.page.id)}">${escapeHtml(item.relation)} · ${escapeHtml(item.page.title)}</button>`;
}

function relationRow(item) {
  return `
    <button class="note-row relation-row ${item.page.id === state.focusId ? "active" : ""}" data-id="${escapeAttr(item.page.id)}">
      <strong>${escapeHtml(item.page.title)}</strong>
      <span>${escapeHtml(item.relation)} · ${escapeHtml(item.page.system || item.page.domain || "未分类")} · ${escapeHtml(item.page.folder || "")}</span>
      <span>${escapeHtml(item.page.summary || "")}</span>
    </button>
  `;
}

function setHomeLabels(topicTitle, topicButton, recentTitle, recentButton, questionTitle) {
  document.getElementById("topicSectionTitle").textContent = topicTitle;
  document.getElementById("allTopicsBtn").textContent = topicButton;
  document.getElementById("recentSectionTitle").textContent = recentTitle;
  document.getElementById("allNotesBtn").textContent = recentButton;
  document.getElementById("questionSectionTitle").textContent = questionTitle;
}

function visibleGraph() {
  const pages = filteredPages();
  if (state.query) {
    const nodeIds = new Set(pages.map((page) => page.id));
    const edges = state.data.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
    return { nodes: pages, edges };
  }

  if (state.depth >= 99) {
    const nodeIds = new Set(pages.map((page) => page.id));
    const edges = state.data.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
    return { nodes: pages, edges };
  }

  const allowedIds = new Set(pages.map((page) => page.id));
  const focusId = allowedIds.has(state.focusId) ? state.focusId : pages[0]?.id;
  if (!focusId) return { nodes: [], edges: [] };

  const ids = new Set([focusId]);
  const frontier = [focusId];
  const adjacency = buildAdjacency();
  let depth = 0;
  while (frontier.length && depth < state.depth) {
    const size = frontier.length;
    for (let i = 0; i < size; i++) {
      const current = frontier.shift();
      for (const next of adjacency.get(current) || []) {
        if (!allowedIds.has(next)) continue;
        if (ids.has(next)) continue;
        ids.add(next);
        frontier.push(next);
      }
    }
    depth += 1;
  }

  const nodes = [...ids].map((id) => state.pages.get(id)).filter(Boolean);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = state.data.edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  return { nodes, edges };
}

function scheduleGraphRender() {
  if (state.graphRenderTimer) {
    clearTimeout(state.graphRenderTimer);
  }
  state.graphRenderTimer = setTimeout(() => {
    state.graphRenderTimer = null;
    renderGraph();
  }, 0);
}

function renderGraph() {
  if (state.view !== "graph") return;
  const { nodes, edges } = visibleGraph();
  const graphNodes = prioritizeGraphNodes(nodes);
  const focus = state.pages.get(state.focusId);
  const target = document.getElementById("graphSummary");
  const svg = document.getElementById("graph");
  if (svg) svg.innerHTML = "";
  if (!target) return;

  const nodeIds = new Set(graphNodes.map((node) => node.id));
  const visibleEdges = edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  const directIds = new Set([...(focus?.resolved_links || []), ...(focus?.backlinks || [])]);
  const direct = graphNodes.filter((node) => directIds.has(node.id)).slice(0, 30);
  const topics = graphNodes.filter((node) => node.is_topic_map || node.type === "index").slice(0, 24);
  const others = graphNodes.filter((node) => node.id !== state.focusId && !directIds.has(node.id) && !node.is_topic_map && node.type !== "index").slice(0, 36);

  target.innerHTML = `
    <div class="graph-overview">
      <div class="graph-focus">
        <p class="eyebrow">Focus</p>
        <h3>${escapeHtml(focus?.title || "当前节点")}</h3>
        <p>${escapeHtml(focus?.summary || "")}</p>
      </div>
      <div class="graph-metric"><strong>${graphNodes.length}</strong><span>显示节点</span></div>
      <div class="graph-metric"><strong>${visibleEdges.length}</strong><span>显示关系</span></div>
      <div class="graph-metric"><strong>${state.depth >= 99 ? "全图" : `${state.depth}跳`}</strong><span>范围</span></div>
    </div>
    <div class="relation-columns">
      ${relationColumn("直接关联", direct)}
      ${relationColumn("专题地图", topics)}
      ${relationColumn("同范围节点", others)}
    </div>
  `;
  bindPageButtons(target);
  renderLegend(graphNodes);
}

function prioritizeGraphNodes(nodes) {
  const maxNodes = state.depth >= 99 ? 96 : state.depth >= 2 ? 72 : 42;
  const focus = [];
  const topic = [];
  const linked = [];
  const rest = [];
  for (const node of nodes) {
    if (node.id === state.focusId) focus.push(node);
    else if (node.is_topic_map || node.type === "index") topic.push(node);
    else if ((node.resolved_links || []).includes(state.focusId) || (node.backlinks || []).includes(state.focusId)) linked.push(node);
    else rest.push(node);
  }
  return [...focus, ...topic, ...linked, ...rest].slice(0, maxNodes);
}

function relationColumn(title, pages) {
  return `
    <section class="relation-column">
      <h3>${escapeHtml(title)}</h3>
      <div class="relation-list">
        ${pages.length ? pages.map((page) => `
          <button class="relation-item" data-id="${escapeAttr(page.id)}">
            <strong>${escapeHtml(page.title)}</strong>
            <span>${escapeHtml(page.system || page.domain || "未分类")}</span>
          </button>
        `).join("") : `<div class="empty-state">没有匹配节点</div>`}
      </div>
    </section>
  `;
}

function renderLegend(nodes) {
  const systems = [...new Set(nodes.map((node) => node.system || node.domain || "未分类"))].slice(0, 8);
  document.getElementById("legend").innerHTML = systems.map((system) => `
    <span><i></i>${escapeHtml(system)}</span>
  `).join("");
}

function buildAdjacency() {
  const adjacency = new Map();
  for (const edge of state.data.edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set());
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, new Set());
    adjacency.get(edge.source).add(edge.target);
    adjacency.get(edge.target).add(edge.source);
  }
  return adjacency;
}

function topicCard(page) {
  return `
    <button class="topic-card ${page.id === state.focusId ? "active" : ""}" data-id="${escapeAttr(page.id)}">
      <strong>${escapeHtml(page.title)}</strong>
      <p>${escapeHtml(page.summary || "专题地图")}</p>
      <span>${escapeHtml(page.system || page.domain || "未分类")} · ${escapeHtml(page.updated || page.created || "")}</span>
    </button>
  `;
}

function searchResultCard(page) {
  return `
    <button class="topic-card search-result-card ${page.id === state.focusId ? "active" : ""}" data-id="${escapeAttr(page.id)}">
      <strong>${escapeHtml(page.title)}</strong>
      <p>${escapeHtml(page.summary || "暂无摘要。")}</p>
      <span>${escapeHtml(page.system || page.domain || "未分类")} · ${escapeHtml(page.folder || "知识卡")} · ${page.is_topic_map ? "地图" : "笔记"}</span>
    </button>
  `;
}

function noteRow(page) {
  return `
    <button class="note-row ${page.id === state.focusId ? "active" : ""}" data-id="${escapeAttr(page.id)}">
      <strong>${escapeHtml(page.title)}</strong>
      <span>${escapeHtml(page.system || page.domain || "未分类")} · ${escapeHtml(page.updated || page.created || "")}</span>
      <span>${escapeHtml(page.summary || "")}</span>
    </button>
  `;
}

function bindPageButtons(root) {
  root.querySelectorAll("[data-id]").forEach((button) => {
    button.addEventListener("click", () => selectPage(button.dataset.id));
  });
}

function selectPage(id, view = null) {
  const page = state.pages.get(id);
  if (!page) return;
  state.focusId = id;
  if (page.system || page.domain) {
    state.selectedDomain = page.system || page.domain;
    state.selectedModule = "";
  }
  if (view) setView(view, false);
  render();
  document.querySelector(".context-panel")?.classList.add("open");
}

function selectDomain(domain) {
  state.selectedDomain = domain || "全部";
  state.selectedModule = "";
  const landing = systemLandingPage(state.selectedDomain);
  if (landing) state.focusId = landing.id;
}

function selectModule(domain, moduleName) {
  state.selectedDomain = domain || "全部";
  state.selectedModule = moduleName || "";
  const landing = moduleLandingPage(state.selectedDomain, state.selectedModule);
  if (landing) state.focusId = landing.id;
}

function systemLandingPage(domain) {
  if (domain === "全部") {
    return state.pages.get(state.data.root_id) || state.data.pages[0];
  }

  const candidates = state.data.pages.filter((page) => matchesSystem(page, domain));
  return candidates.find((page) => page.title === `${domain}全景地图`)
    || candidates.find((page) => page.title.includes(domain) && (page.is_topic_map || page.type === "index"))
    || candidates.find((page) => page.is_topic_map || page.type === "index")
    || candidates[0];
}

function moduleLandingPage(domain, moduleName) {
  const candidates = state.data.pages
    .filter((page) => matchesSystem(page, domain))
    .filter((page) => matchesModule(page, domain, moduleName));
  return candidates.find((page) => page.title.includes(moduleName) && (page.is_topic_map || page.type === "index"))
    || candidates.find((page) => page.title.includes(moduleName))
    || candidates.find((page) => page.is_topic_map || page.type === "index")
    || systemLandingPage(domain);
}

function collectQuestions(pages) {
  const result = [];
  for (const page of pages) {
    for (const question of page.related_questions || []) {
      result.push({ page, text: question });
    }
    for (const item of page.checklist || []) {
      if (!item.done) result.push({ page, text: item.text });
    }
  }
  return result;
}

function currentScopeTitle() {
  if (state.query) return `全库搜索：${state.query}`;
  if (state.selectedDomain === "全部") return "个人知识库大全";
  return state.selectedModule ? `${state.selectedDomain} / ${state.selectedModule}` : state.selectedDomain;
}

function currentScopeEyebrow() {
  if (state.query) return "Global Search";
  const system = SYSTEM_TREE.find((item) => item.name === state.selectedDomain);
  if (!system) return "Knowledge Workspace";
  return state.selectedModule ? `${system.id} · ${system.subtitle} / ${state.selectedModule}` : `${system.id} · ${system.subtitle}`;
}

function countSystemPages(systemName) {
  return state.data.pages.filter((page) => matchesSystem(page, systemName)).length;
}

function countModulePages(systemName, moduleName) {
  return state.data.pages.filter((page) => matchesSystem(page, systemName) && matchesModule(page, systemName, moduleName)).length;
}

async function fetchMarkdown(path) {
  const encodedPath = encodeURI(path).replace(/#/g, "%23");
  const candidates = [
    `./content/${encodedPath}`,
    `../${encodedPath}`,
  ];
  try {
    for (const url of candidates) {
      const response = await fetch(url, { cache: "no-store" });
      if (response.ok) return response.text();
    }
    return `# ${path}\n\n无法读取文件：已尝试 ${candidates.join("、")}，均未找到。请确认 web/content 已生成。`;
  } catch (error) {
    return `# ${path}\n\n无法读取文件：${error.message}`;
  }
}

function markdownToHtml(markdown) {
  const body = markdown.replace(/^---[\s\S]*?---\s*/, "");
  const lines = body.split(/\r?\n/);
  const html = [];
  let inList = false;
  let table = [];
  let inCallout = false;

  const flushList = () => {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  };
  const flushTable = () => {
    if (!table.length) return;
    if (table.length >= 2) {
      html.push("<table>");
      table.forEach((row, index) => {
        if (index === 1 && row.every((cell) => /^-+$/.test(cell.replace(/:/g, "")))) return;
        const tag = index === 0 ? "th" : "td";
        html.push(`<tr>${row.map((cell) => `<${tag}>${inline(cell)}</${tag}>`).join("")}</tr>`);
      });
      html.push("</table>");
    }
    table = [];
  };
  const flushCallout = () => {
    if (inCallout) {
      html.push("</div>");
      inCallout = false;
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushList();
      flushTable();
      flushCallout();
      continue;
    }
    if (line.startsWith("|") && line.endsWith("|")) {
      flushList();
      flushCallout();
      table.push(line.slice(1, -1).split("|").map((cell) => cell.trim()));
      continue;
    }
    flushTable();
    if (line.startsWith("> [!")) {
      flushList();
      flushCallout();
      html.push(`<div class="callout"><strong>${inline(line.replace(/^>\s*/, ""))}</strong>`);
      inCallout = true;
      continue;
    }
    if (line.startsWith(">")) {
      html.push(`<p>${inline(line.replace(/^>\s?/, ""))}</p>`);
      continue;
    }
    flushCallout();
    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushList();
      const level = Math.min(4, heading[1].length);
      html.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      flushTable();
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${inline(line.replace(/^[-*]\s+/, ""))}</li>`);
      continue;
    }
    flushList();
    html.push(`<p>${inline(line)}</p>`);
  }
  flushList();
  flushTable();
  flushCallout();
  return html.join("");
}

function inline(text) {
  return escapeHtml(text)
    .replace(/\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]/g, (_, target, label) => {
      const title = label || target;
      return `<a data-wikilink="${escapeAttr(target)}">${escapeHtml(title)}</a>`;
    })
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function findByTitle(title) {
  return [...state.pages.values()].find((page) => page.title === title || page.path.endsWith(`${title}.md`));
}

function searchable(page) {
  return [
    page.title,
    page.path,
    page.domain,
    page.note_type,
    page.system,
    ...(page.systems || []),
    page.summary,
    page.search_text,
    ...(page.tags || []),
    ...(page.topics || []),
    ...(page.related_questions || []),
  ].filter(Boolean).join(" ").toLowerCase();
}

function matchesSystem(page, system) {
  return system === "全部" || page.domain === system || page.system === system || (page.systems || []).includes(system);
}

function matchesModule(page, system, moduleName) {
  if (!moduleName || system === "全部") return true;
  const keywords = moduleKeywords(system, moduleName);
  if (!keywords.length) return true;
  const haystack = searchable(page);
  return keywords.some((keyword) => haystack.includes(keyword.toLowerCase()));
}

function moduleKeywords(system, moduleName) {
  const systemConfig = SYSTEM_TREE.find((item) => item.name === system);
  const moduleConfig = systemConfig?.modules.find(([name]) => name === moduleName);
  return moduleConfig ? [moduleName, ...moduleConfig[1]] : [moduleName];
}

function sortByDomainAndTitle(a, b) {
  return `${a.system || a.domain || ""}${a.title}`.localeCompare(`${b.system || b.domain || ""}${b.title}`, "zh-CN");
}

function domainHint(name) {
  return {
    认知系统: "思考、注意、情绪、学习",
    智能系统: "AI、模型、Agent、自动化",
    产业系统: "技术产业化、供应链、公司",
    财富系统: "资产、现金流、周期、市场",
    生命系统: "健康、医学、生物科技",
    物理系统: "能源、材料、制造、机器人",
    美学系统: "美、品味、风格、体验",
    意义系统: "文化、符号、叙事、信念",
    范式系统: "科学、系统、创新、未来",
    AI: "模型、应用、工具、方法",
    写作: "表达、结构、素材、作品",
    个人成长: "习惯、决策、关系、人生系统",
    未分类: "等待整理的知识",
  }[name] || "自定义领域";
}

function fieldOrPlaceholder(value) {
  return value?.trim() || "待补充。";
}

function listBlock(value) {
  const items = lines(value);
  return items.length ? items.map((item) => `- ${item}`).join("\n") : "- 待补充。";
}

function wikiListBlock(value) {
  const items = lines(value);
  return items.length ? items.map((item) => `- [[${item}]]`).join("\n") : "- 待补充。";
}

function lines(value) {
  return String(value || "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function yamlEscape(value) {
  return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function safeFileName(value) {
  return String(value).trim().replace(/[\\/:*?"<>|]/g, "_").slice(0, 80) || "未命名知识卡片";
}

function emptyState(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function shortTitle(title) {
  return title.length > 16 ? `${title.slice(0, 15)}…` : title;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}

boot().catch((error) => {
  document.body.innerHTML = `<pre style="padding:24px;color:#a33">${escapeHtml(error.stack || error.message)}</pre>`;
});
