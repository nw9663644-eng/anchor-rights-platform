import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Bot,
  BriefcaseBusiness,
  Check,
  ChevronRight,
  ClipboardCheck,
  Database,
  Download,
  FileSearch,
  FolderOpen,
  Home,
  Landmark,
  LockKeyhole,
  Menu,
  LogOut,
  Plus,
  Printer,
  Scale,
  Search,
  Settings,
  ShieldCheck,
  ShieldAlert,
  Trash2,
  Upload,
  UserRound,
  UserCheck,
  X,
} from "lucide-react";
import "./styles.css";

const API = "";
type Page =
  "home" | "assessment" | "report" | "matters" | "library" | "ai" | "security" | "admin";
type Dimension = "personal" | "economic" | "organizational" | "risk";
type Question = {
  id: string;
  dimension: Dimension;
  title: string;
  options: { id: string; label: string; score: number }[];
};
type Result = {
  totalScore: number;
  relationLabel: string;
  relationType: string;
  summary: string;
  dimensionScores: Record<string, number>;
  dimensionMax: Record<string, number>;
  dimensionInsights: Record<string, string>;
  rights: string[];
  legalBasis: string[];
  actions: string[];
  gaps: { id: string; title: string; detail: string }[];
  evidenceChecklist: string[];
  disclaimer: string;
  modelVersion?: string;
};
type Matter = {
  id: string;
  title: string;
  partyRole: string;
  mcnName: string;
  disputeTypes: string[];
  status: string;
  currentStep: number;
  updatedAt: string;
  evidence: {
    id: string;
    category: string;
    name: string;
    status: string;
    note: string;
    storedName?: string;
    mimeType?: string;
    sizeBytes?: number;
    sha256?: string;
    encrypted?: boolean;
  }[];
};
type CaseItem = {
  id: string;
  title: string;
  relation: string;
  year: number;
  focus: string[];
  summary: string;
  similarity: number;
};
type Knowledge = {
  id: string;
  category: string;
  title: string;
  summary: string;
  points: string[];
  basis: string[];
  tags: string[];
};
type User = { id: string; email: string; name: string; role: "admin" | "user" };
type AuditLog = { id: string; userName: string; userEmail: string; action: string; entityType: string; detail: string; createdAt: string };
type Review = { id: string; evaluationId: string; status: string; requestNote: string; reviewerComment: string; reviewerName?: string; userName?: string; userEmail?: string; updatedAt: string; result?: Result };
type SecurityStatus = { https: boolean; httpOnlySession: boolean; secureCookie: boolean; loginLockout: { enabled: boolean; attempts: number; minutes: number }; evidenceEncryption: boolean; evidenceIntegrity: string; aiAutoRedaction: boolean; aiLocalStorage: boolean; auditLogging: boolean; manualReview: boolean };

const dimensions: {
  id: Dimension;
  label: string;
  note: string;
  max: number;
}[] = [
  {
    id: "personal",
    label: "人身从属性",
    note: "排班、指令、奖惩与行为控制",
    max: 40,
  },
  {
    id: "economic",
    label: "经济从属性",
    note: "收入依赖、资源与经营风险",
    max: 35,
  },
  {
    id: "organizational",
    label: "组织从属性",
    note: "业务融入、身份与组织体系",
    max: 25,
  },
  {
    id: "risk",
    label: "权益风险筛查",
    note: "不计总分，用于识别保障缺口",
    max: 0,
  },
];
const steps = ["关系评估", "证据归集", "方案建议", "协商或维权"];
const laws = [
  [
    "劳动关系认定",
    "关于确立劳动关系有关事项的通知",
    "从主体资格、劳动管理、报酬支付和业务组成等事实综合审查。",
    "https://www.gov.cn/zhengce/2020-12/27/content_5574113.htm",
  ],
  [
    "劳动合同",
    "中华人民共和国劳动合同法",
    "用于审查书面合同、工资支付、解除补偿及未签合同责任。",
    "https://www.mohrss.gov.cn/xxgk2020/fdzdgknr/zcfg/fl/202011/t20201102_394622.html",
  ],
  [
    "工时与工资",
    "中华人民共和国劳动法",
    "用于判断工时、休息、加班工资和不得克扣工资等问题。",
    "https://www.mohrss.gov.cn/xxgk2020/fdzdgknr/zcfg/fl/202011/t20201102_394625.html",
  ],
  [
    "社会保障",
    "中华人民共和国社会保险法",
    "用于核查参保登记、缴费义务和社会保险权益。",
    "https://www.mohrss.gov.cn/xxgk2020/fdzdgknr/zcfg/fl/202011/t20201102_394629.html",
  ],
  [
    "新业态保护",
    "关于维护新就业形态劳动者劳动保障权益的指导意见",
    "对不完全符合劳动关系情形提供报酬、休息、安全等倾斜保护。",
    "https://www.gov.cn/zhengce/zhengceku/2021-07/23/content_5626761.htm",
  ],
  [
    "合同公平",
    "中华人民共和国民法典",
    "用于处理合作协议、违约金调整、格式条款和损害赔偿。",
    "https://www.gov.cn/xinwen/2020-06/01/content_5516649.htm",
  ],
  [
    "程序救济",
    "中华人民共和国劳动争议调解仲裁法",
    "用于劳动争议调解、仲裁时效、举证和诉讼衔接。",
    "https://www.mohrss.gov.cn/xxgk2020/fdzdgknr/zcfg/fl/202011/t20201102_394623.html",
  ],
  [
    "数据与账号",
    "中华人民共和国个人信息保护法",
    "用于审查主播实名信息、后台数据和收益信息的处理边界。",
    "https://www.gov.cn/xinwen/2021-08/20/content_5632486.htm",
  ],
];

async function request(path: string, init?: RequestInit) {
  const isForm = init?.body instanceof FormData;
  const r = await fetch(API + path, {
    credentials: "include",
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!r.ok)
    throw new Error((await r.json().catch(() => ({}))).detail || "请求失败");
  return r.json();
}
function App() {
  const [user, setUser] = useState<User | null>(null),
    [authLoading, setAuthLoading] = useState(true);
  const [page, setPage] = useState<Page>("home"),
    [mobile, setMobile] = useState(false),
    [accountOpen, setAccountOpen] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]),
    [answers, setAnswersState] = useState<Record<string, string>>(() =>
      JSON.parse(localStorage.getItem("anchor_answers") || "{}"),
    ),
    [result, setResult] = useState<Result | null>(() =>
      JSON.parse(localStorage.getItem("anchor_result") || "null"),
    ),
    [evaluationId, setEvaluationId] = useState<string | null>(() =>
      localStorage.getItem("anchor_evaluation_id"),
    );
  const [matters, setMatters] = useState<Matter[]>([]),
    [cases, setCases] = useState<CaseItem[]>([]),
    [knowledge, setKnowledge] = useState<Knowledge[]>([]),
    [reviews, setReviews] = useState<Review[]>([]),
    [security, setSecurity] = useState<SecurityStatus | null>(null),
    [stats, setStats] = useState<any>({});
  const setAnswers = (value: Record<string, string>) => {
    setAnswersState(value);
    localStorage.setItem("anchor_answers", JSON.stringify(value));
  };
  const refresh = () =>
    Promise.all([
      request("/api/questions").then((x) => setQuestions(x.questions)),
      request("/api/matters").then((x) => setMatters(x.items)),
      request("/api/cases").then((x) => setCases(x.items)),
      request("/api/legal-knowledge").then((x) => setKnowledge(x.items)),
      request("/api/reviews").then((x) => setReviews(x.items)),
      request("/api/security/status").then(setSecurity),
      request("/api/dashboard/stats").then(setStats),
    ]).catch(() => {});
  useEffect(() => {
    request("/api/auth/me")
      .then((x) => {
        const previous = localStorage.getItem("anchor_user_id");
        if (previous && previous !== x.user.id) {
          setAnswersState({});
          setResult(null);
          setEvaluationId(null);
          localStorage.removeItem("anchor_answers");
          localStorage.removeItem("anchor_result");
          localStorage.removeItem("anchor_evaluation_id");
        }
        localStorage.setItem("anchor_user_id", x.user.id);
        setUser(x.user);
        setPage(x.user.role === "admin" ? "admin" : "home");
        window.scrollTo(0, 0);
        setAuthLoading(false);
        refresh();
      })
      .catch(() => {
        localStorage.removeItem("anchor_user_id");
        setAuthLoading(false);
      });
  }, []);
  const nav = user?.role === "admin"
    ? ([{ id: "admin", label: "管理工作台", icon: Settings }] as const)
    : ([
        { id: "home", label: "我的工作台", icon: Home },
        { id: "assessment", label: "智能评估", icon: ClipboardCheck },
        { id: "matters", label: "权益事项", icon: BriefcaseBusiness },
        { id: "library", label: "案例与法规", icon: BookOpen },
        { id: "ai", label: "AI 助手", icon: Bot },
        { id: "security", label: "安全中心", icon: ShieldCheck },
      ] as const);
  const go = (id: Page) => {
    setPage(id);
    setMobile(false);
    window.scrollTo(0, 0);
  };
  if (authLoading)
    return (
      <div className="auth-loading">
        <Scale />
        <span>正在进入平台...</span>
      </div>
    );
  if (!user)
    return (
      <Auth
        onSuccess={(data) => {
          const previous = localStorage.getItem("anchor_user_id");
          if (previous !== data.user.id) {
            setAnswersState({});
            setResult(null);
            setEvaluationId(null);
            localStorage.removeItem("anchor_answers");
            localStorage.removeItem("anchor_result");
            localStorage.removeItem("anchor_evaluation_id");
          }
          localStorage.setItem("anchor_user_id", data.user.id);
          setUser(data.user);
          setPage(data.user.role === "admin" ? "admin" : "home");
          window.scrollTo(0, 0);
          setTimeout(refresh, 0);
        }}
      />
    );
  const logout = async () => {
    try {
      await request("/api/auth/logout", { method: "POST" });
    } catch {}
    localStorage.removeItem("anchor_user_id");
    localStorage.removeItem("anchor_answers");
    localStorage.removeItem("anchor_result");
    localStorage.removeItem("anchor_evaluation_id");
    setAnswersState({});
    setResult(null);
    setEvaluationId(null);
    setMatters([]);
    setReviews([]);
    setSecurity(null);
    setStats({});
    setUser(null);
  };
  return (
    <div className={`app-shell ${user.role === "admin" ? "admin-shell" : "user-shell"}`}>
      <header>
        <button className="brand" onClick={() => go(user.role === "admin" ? "admin" : "home")}>
          <span>
            <Scale />
          </span>
          <b>{user.role === "admin" ? "主播权益评估平台 · 管理中心" : "主播权益评估平台"}</b>
        </button>
        <nav className={mobile ? "open" : ""}>
          {nav.map((n) => (
            <button
              className={page === n.id ? "active" : ""}
              onClick={() => go(n.id)}
              key={n.id}
            >
              <n.icon />
              {n.label}
            </button>
          ))}
        </nav>
        <button className="mobile-menu" onClick={() => setMobile(!mobile)}>
          {mobile ? <X /> : <Menu />}
        </button>
        <div className="user-menu">
          <button
            className="account-button"
            onClick={() => setAccountOpen(true)}
            title="账号设置"
          >
            <UserRound />
            <span>{user.name}</span>
          </button>
          <button title="退出登录" onClick={logout}>
            <LogOut />
          </button>
        </div>
      </header>
      {accountOpen && (
        <AccountModal
          user={user}
          close={() => setAccountOpen(false)}
          logout={logout}
        />
      )}
      <main>
        {page === "home" && (
          <HomePage
            go={go}
            matters={matters}
            stats={stats}
            openReport={(item: any) => {
              setResult(item.result);
              setEvaluationId(item.id);
              localStorage.setItem(
                "anchor_result",
                JSON.stringify(item.result),
              );
              localStorage.setItem("anchor_evaluation_id", item.id);
              go("report");
            }}
          />
        )}{" "}
        {page === "assessment" && (
          <Assessment
            questions={questions}
            answers={answers}
            setAnswers={setAnswers}
            onResult={(r, id) => {
              setResult(r);
              setEvaluationId(id);
              localStorage.setItem("anchor_result", JSON.stringify(r));
              localStorage.setItem("anchor_evaluation_id", id);
              go("report");
              refresh();
            }}
          />
        )}{" "}
        {page === "report" && (
          <Report
            result={result}
            evaluationId={evaluationId}
            go={go}
            refresh={refresh}
            reviews={reviews}
          />
        )}{" "}
        {page === "matters" && <Matters items={matters} refresh={refresh} />}{" "}
        {page === "library" && <Library cases={cases} knowledge={knowledge} />}{" "}
        {page === "ai" && <Ai />}{" "}
        {page === "security" && <SecurityCenter status={security} go={go} />}{" "}
        {page === "admin" && user.role === "admin" && (
          <Admin
            stats={stats}
            cases={cases}
            knowledge={knowledge}
            reviews={reviews}
            refresh={refresh}
          />
        )}
      </main>
      <footer><span>本平台用于初步评估与研究辅助，不构成法律意见。</span><span>请按最少必要原则上传材料，并及时删除不再需要的数据。</span></footer>
    </div>
  );
}

function Auth({
  onSuccess,
}: {
  onSuccess: (data: { user: User }) => void;
}) {
  const [portal, setPortal] = useState<"user" | "admin">("user");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState(""),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const data = await request(`/api/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({ name, email, password, portal: "user" === portal ? "user" : "admin" }),
      });
      onSuccess(data);
    } catch (e: any) {
      setError(typeof e.message === "string" ? e.message : "登录失败");
    } finally {
      setBusy(false);
    }
  };
  const choosePortal = (next: "user" | "admin") => {
    setPortal(next);
    setMode("login");
    setEmail("");
    setPassword("");
    setError("");
  };
  return (
    <div className="auth-page">
      <section className="auth-intro">
        <div className="brand-mark">
          <Scale />
        </div>
        <span className="eyebrow">网络主播与 MCN 用工关系</span>
        <h1>权益评估与证据工作台</h1>
        <p>
          评估记录、权益事项和证据材料按账号独立保存。请勿上传与争议无关的敏感信息。
        </p>
        <div className="auth-points">
          <span>
            <Check />
            36 项事实核查
          </span>
          <span>
            <Check />
            个性化权益方案
          </span>
          <span>
            <Check />
            证据材料加密存档
          </span>
        </div>
      </section>
      <section className={`auth-card auth-card-${portal}`}>
        <div className="auth-portal-switch" role="tablist" aria-label="选择登录身份">
          <button
            className={portal === "user" ? "active" : ""}
            onClick={() => choosePortal("user")}
          >
            <UserRound />
            <span><b>普通用户</b><small>个人评估与权益档案</small></span>
          </button>
          <button
            className={portal === "admin" ? "active" : ""}
            onClick={() => choosePortal("admin")}
          >
            <Settings />
            <span><b>管理员</b><small>内容、复核与运行管理</small></span>
          </button>
        </div>
        <span className="auth-card-kicker">{portal === "admin" ? "平台管理端" : "用户服务端"}</span>
        <h2>{portal === "admin" ? "管理员身份登录" : mode === "login" ? "进入我的权益工作台" : "创建个人权益档案"}</h2>
        <p className="auth-card-desc">
          {portal === "admin"
            ? "登录后进入独立管理空间，普通用户无法访问管理功能。"
            : "每个账号仅显示自己的评估报告、事项进度和证据材料。"}
        </p>
        {portal === "user" && (
          <div className="auth-mode-switch">
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>账号登录</button>
            <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>注册账号</button>
          </div>
        )}
        {portal === "user" && mode === "register" && (
          <label>
            姓名
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="怎么称呼你"
            />
          </label>
        )}
        <label>
          {portal === "admin" ? "管理员账号" : "邮箱"}
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={portal === "admin" ? "请输入管理员账号" : "name@example.com"}
            autoComplete="username"
          />
        </label>
        <label>
          密码
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={mode === "register" ? "至少 10 位，包含字母和数字" : "请输入密码"}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button
          className="primary auth-submit"
          disabled={
            busy ||
            !email ||
            password.length < (mode === "register" ? 10 : 8) ||
            (mode === "register" && name.length < 2)
          }
          onClick={submit}
        >
          {busy ? "正在核验..." : portal === "admin" ? "进入管理工作台" : mode === "login" ? "进入我的工作台" : "注册并进入"}
          <ArrowRight />
        </button>
        <small>
          连续 5 次登录失败会锁定账号 15 分钟；登录身份由服务端校验，会话凭证不可被浏览器脚本读取。
        </small>
      </section>
    </div>
  );
}

function AccountModal({
  user,
  close,
  logout,
}: {
  user: User;
  close: () => void;
  logout: () => void;
}) {
  const [current, setCurrent] = useState(""),
    [next, setNext] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    setError("");
    try {
      await request("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      alert("密码已修改，请重新登录。");
      logout();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && close()}
    >
      <section className="account-modal">
        <div className="section-title">
          <div>
            <span className="kicker">账号安全</span>
            <h2>{user.name}</h2>
            <p>
              {user.email} · {user.role === "admin" ? "管理员" : "普通用户"}
            </p>
          </div>
          <button className="modal-close" onClick={close}>
            <X />
          </button>
        </div>
        <label>
          当前密码
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </label>
        <div className="account-security-note">
          <LockKeyhole />
          <span>当前会话使用 HttpOnly Cookie；修改密码后会撤销全部已登录会话。</span>
        </div>
        <label>
          新密码
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            placeholder="至少 10 位"
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button
          className="primary"
          disabled={busy || !current || next.length < 10}
          onClick={save}
        >
          {busy ? "正在修改..." : "修改密码并重新登录"}
        </button>
      </section>
    </div>
  );
}

function PageHead({
  eyebrow,
  title,
  desc,
  action,
}: {
  eyebrow: string;
  title: string;
  desc: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-head">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{desc}</p>
      </div>
      {action}
    </div>
  );
}
function HomePage({
  go,
  matters,
  stats,
  openReport,
}: {
  go: (p: Page) => void;
  matters: Matter[];
  stats: any;
  openReport: (item: any) => void;
}) {
  return (
    <div className="page home-page">
      <PageHead
        eyebrow="个人权益工作台"
        title="从关系评估到权益行动"
        desc="集中查看你的评估结论、事项进度与证据准备状态，每一项记录均按当前账号独立保存。"
        action={
          <button className="primary" onClick={() => go("assessment")}>
            <ClipboardCheck />
            新建评估
          </button>
        }
      />
      <section className="metric-grid home-metrics" aria-label="我的工作概览">
        <Metric n={stats.totalEvaluations || 0} label="我的评估" />
        <Metric n={stats.matterCount || 0} label="进行中事项" />
        <Metric n={stats.caseCount || 0} label="可检索案例" />
        <Metric n="36" label="事实核查项" />
      </section>
      <section className="dashboard-grid">
        <div className="home-primary-column">
          <div className="panel focus-panel">
          <div className="section-title">
            <div>
              <span className="kicker">核心流程</span>
              <h2>关系认定轨道</h2>
            </div>
            <span className="model">规则模型 2026.07</span>
          </div>
          <div className="track">
            {steps.map((s, i) => (
              <div key={s}>
                <span>{i + 1}</span>
                <b>{s}</b>
                <small>
                  {
                    [
                      "36 项事实核查",
                      "材料分类存档",
                      "权益包与行动清单",
                      "进度持续更新",
                    ][i]
                  }
                </small>
              </div>
            ))}
          </div>
          <div className="callout">
            <ShieldCheck />
            <div>
              <b>模型边界清晰</b>
              <p>
                26 道计分题判断关系类型，10
                道筛查题只触发权益风险，不会抬高关系总分。
              </p>
            </div>
          </div>
          </div>
          <section className="panel quick">
            <div>
              <span className="kicker">快速入口</span>
              <h2>常用工作</h2>
            </div>
            <button onClick={() => go("assessment")}><ClipboardCheck /><b>新建评估</b><small>逐项核查实际履行</small></button>
            <button onClick={() => go("matters")}><FolderOpen /><b>整理证据</b><small>按事项持续存档</small></button>
            <button onClick={() => go("library")}><FileSearch /><b>查询依据</b><small>案例、法规与知识</small></button>
            <button onClick={() => go("ai")}><Bot /><b>咨询 AI</b><small>形成问题分析思路</small></button>
          </section>
        </div>
        <aside className="panel personal-archive">
          <div className="section-title">
            <div>
              <span className="kicker">我的档案</span>
              <h2>评估与处理进度</h2>
            </div>
            <span className="private-badge"><LockKeyhole />仅本人可见</span>
          </div>
          <div className="archive-group">
            <div className="archive-heading">
              <b>评估报告</b>
              <span>{stats.totalEvaluations || 0} 份</span>
            </div>
            {stats.latest?.length ? stats.latest.slice(0, 3).map((item: any) => (
              <button className="report-row" key={item.id} onClick={() => openReport(item)}>
                <span className="score-chip">{item.result.totalScore}</span>
                <div>
                  <b>{item.result.relationLabel}</b>
                  <small>{new Date(item.createdAt).toLocaleDateString()} · 查看完整报告</small>
                </div>
                <ChevronRight />
              </button>
            )) : <p className="archive-empty">完成首次评估后，报告会保存在这里。</p>}
          </div>
          <div className="archive-group">
            <div className="archive-heading">
              <b>权益事项</b>
              <button className="text-btn" onClick={() => go("matters")}>全部事项 <ChevronRight /></button>
            </div>
            {matters.length ? matters.slice(0, 2).map((m) => (
              <button className="matter-row" onClick={() => go("matters")} key={m.id}>
                <span className="status-dot" />
                <div><b>{m.title}</b><small>{m.status} · 已到第 {m.currentStep} 步</small></div>
                <ChevronRight />
              </button>
            )) : <p className="archive-empty">评估后可建立事项并持续归集证据。</p>}
          </div>
        </aside>
      </section>
    </div>
  );
}
function Metric({ n, label }: { n: any; label: string }) {
  return (
    <div className="metric">
      <strong>{n}</strong>
      <span>{label}</span>
    </div>
  );
}
function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <FolderOpen />
      <b>{title}</b>
      <p>{text}</p>
    </div>
  );
}

function Assessment({
  questions,
  answers,
  setAnswers,
  onResult,
}: {
  questions: Question[];
  answers: Record<string, string>;
  setAnswers: (a: Record<string, string>) => void;
  onResult: (r: Result, id: string) => void;
}) {
  const [index, setIndex] = useState(0),
    [busy, setBusy] = useState(false);
  const dim = dimensions[index];
  const list = questions.filter((q) => q.dimension === dim.id);
  const answered = list.filter((q) => answers[q.id]).length;
  const all = questions.length;
  const total = Object.keys(answers).length;
  const submit = async () => {
    setBusy(true);
    try {
      const x = await request("/api/evaluate", {
        method: "POST",
        body: JSON.stringify({ answers }),
      });
      onResult(x.result, x.id);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="page">
      <PageHead
        eyebrow="智能评估"
        title="基于实际履行事实作答"
        desc="不要只看合同名称。选择最接近真实情况的选项，答案会自动保存于当前浏览会话。"
      />
      <div className="assessment-layout">
        <aside className="stage-nav">
          {dimensions.map((d, i) => (
            <button
              className={i === index ? "active" : ""}
              onClick={() => setIndex(i)}
              key={d.id}
            >
              <span>{i + 1}</span>
              <div>
                <b>{d.label}</b>
                <small>
                  {
                    questions.filter(
                      (q) => q.dimension === d.id && answers[q.id],
                    ).length
                  }
                  /{questions.filter((q) => q.dimension === d.id).length} 已完成
                </small>
              </div>
              {i < index && <Check />}
            </button>
          ))}
        </aside>
        <section className="panel questionnaire">
          <div className="questionnaire-head">
            <div>
              <span className="kicker">第 {index + 1} 阶段</span>
              <h2>{dim.label}</h2>
              <p>{dim.note}</p>
            </div>
            <div className="progress-number">
              <strong>{answered}</strong>
              <span>/ {list.length}</span>
            </div>
          </div>
          <div className="progress">
            <i
              style={{
                width: `${list.length ? (answered / list.length) * 100 : 0}%`,
              }}
            />
          </div>
          {list.map((q, qi) => (
            <fieldset key={q.id}>
              <legend>
                <span>{qi + 1}</span>
                {q.title}
              </legend>
              <div className="options">
                {q.options.map((o) => (
                  <label
                    className={answers[q.id] === o.id ? "selected" : ""}
                    key={o.id}
                  >
                    <input
                      type="radio"
                      checked={answers[q.id] === o.id}
                      onChange={() => setAnswers({ ...answers, [q.id]: o.id })}
                    />
                    <span className="choice">{o.id.toUpperCase()}</span>
                    <span>{o.label}</span>
                    {answers[q.id] === o.id && <Check />}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <div className="form-actions">
            <button
              className="secondary"
              disabled={index === 0}
              onClick={() => setIndex(index - 1)}
            >
              <ArrowLeft />
              上一步
            </button>
            {index < 3 ? (
              <button className="primary" onClick={() => setIndex(index + 1)}>
                下一阶段
                <ArrowRight />
              </button>
            ) : (
              <button
                className="primary"
                disabled={total < all || busy}
                onClick={submit}
              >
                {busy
                  ? "正在生成..."
                  : total < all
                    ? `还需完成 ${all - total} 题`
                    : "生成评估报告"}
                <ArrowRight />
              </button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function Report({
  result,
  evaluationId,
  go,
  refresh,
  reviews,
}: {
  result: Result | null;
  evaluationId: string | null;
  go: (p: Page) => void;
  refresh: () => void;
  reviews: Review[];
}) {
  const [reviewNote, setReviewNote] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  if (!result)
    return (
      <div className="page">
        <Empty title="暂无评估报告" text="请先完成一份智能评估。" />
        <button className="primary center" onClick={() => go("assessment")}>
          开始评估
        </button>
      </div>
    );
  const createMatter = async () => {
    await request("/api/matters", {
      method: "POST",
      body: JSON.stringify({
        title: `${result.relationLabel}权益评估`,
        party_role: "主播",
        dispute_types: result.gaps.map((g) => g.title),
        evaluation_id: evaluationId,
      }),
    });
    await refresh();
    go("matters");
  };
  const currentReview = reviews.find((item) => item.evaluationId === evaluationId);
  const submitReview = async () => {
    if (!evaluationId) return;
    setReviewBusy(true);
    try {
      await request(`/api/evaluations/${evaluationId}/reviews`, {
        method: "POST",
        body: JSON.stringify({ note: reviewNote }),
      });
      setReviewNote("");
      await refresh();
    } finally {
      setReviewBusy(false);
    }
  };
  return (
    <div className="page report">
      <PageHead
        eyebrow="个性化报告"
        title="关系判断与权益行动方案"
        desc="结论来自三从属性计分；风险筛查只用于发现缺口。"
        action={<div className="report-actions"><button className="secondary" onClick={() => window.print()}><Printer />打印或导出 PDF</button><button className="primary" onClick={createMatter}><BriefcaseBusiness />建立权益事项</button></div>}
      />
      <section className="result-hero">
        <div>
          <span>关系认定总分</span>
          <strong>{result.totalScore}</strong>
          <small>/ 100</small>
        </div>
        <div>
          <span className="result-label">{result.relationLabel}</span>
          <p>{result.summary}</p>
        </div>
      </section>
      <section className={`panel human-review ${currentReview ? "has-review" : ""}`}>
        <div className="human-review-head">
          <span className="review-icon"><UserCheck /></span>
          <div>
            <span className="kicker">人工校验</span>
            <h2>{currentReview ? `复核状态：${currentReview.status}` : "申请人工复核"}</h2>
            <p>由平台管理员或研究人员核对问卷事实、计分过程和依据引用。人工复核仍不等同于律师出具法律意见。</p>
          </div>
          {currentReview && <span className="review-status">{currentReview.status}</span>}
        </div>
        {currentReview ? (
          <div className="review-result">
            <div><span>复核人员</span><b>{currentReview.reviewerName || "待分配"}</b></div>
            <div><span>更新时间</span><b>{new Date(currentReview.updatedAt).toLocaleString()}</b></div>
            <p>{currentReview.reviewerComment || "复核人员尚未填写意见。"}</p>
          </div>
        ) : (
          <div className="review-request">
            <textarea value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} placeholder="可选：说明最希望人工核对的事实、合同条款或计分项" />
            <button className="primary" disabled={reviewBusy || !evaluationId} onClick={submitReview}>
              <UserCheck />{reviewBusy ? "正在提交..." : "提交复核申请"}
            </button>
          </div>
        )}
      </section>
      <section className="report-grid">
        <div className="panel">
          <div className="section-title">
            <div>
              <span className="kicker">计分解释</span>
              <h2>三从属性构成</h2>
            </div>
          </div>
          {["personal", "economic", "organizational"].map((d, i) => (
            <div className="dimension-bar" key={d}>
              <div>
                <b>{["人身从属性", "经济从属性", "组织从属性"][i]}</b>
                <span>{result.dimensionInsights?.[d]}</span>
                <strong>
                  {result.dimensionScores[d]} / {result.dimensionMax[d]}
                </strong>
              </div>
              <div>
                <i
                  style={{
                    width: `${(result.dimensionScores[d] / result.dimensionMax[d]) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="panel">
          <div className="section-title">
            <div>
              <span className="kicker">风险筛查</span>
              <h2>
                {result.gaps.length
                  ? `识别到 ${result.gaps.length} 项缺口`
                  : "暂未发现明显缺口"}
              </h2>
            </div>
          </div>
          {result.gaps.map((g) => (
            <div className="risk-row" key={g.id}>
              <AlertCircle />
              <div>
                <b>{g.title}</b>
                <p>{g.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="report-grid">
        <ListPanel title="可主张或关注的权益" items={result.rights} />
        <ListPanel title="优先准备的证据" items={result.evidenceChecklist} />
        <ListPanel title="建议行动路径" items={result.actions} />
        <LegalBasisPanel items={result.legalBasis} />
      </section>
      <p className="disclaimer">{result.disclaimer}</p>
    </div>
  );
}
function ListPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="panel list-panel">
      <h2>{title}</h2>
      {items.map((x, i) => (
        <div key={x}>
          <span>{i + 1}</span>
          <p>{x}</p>
        </div>
      ))}
    </div>
  );
}
function LegalBasisPanel({ items }: { items: string[] }) {
  const findUrl = (text: string) =>
    laws.find(
      (l) =>
        text.includes(l[1]) || l[1].includes(text.replace(/《|》|第.*$/g, "")),
    )?.[3];
  return (
    <div className="panel list-panel">
      <h2>主要法律依据</h2>
      {items.map((x, i) => {
        const url = findUrl(x);
        return (
          <div key={x}>
            <span>{i + 1}</span>
            <p>
              {x}
              {url && (
                <>
                  <br />
                  <a
                    className="legal-link"
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    查看官方全文 <ArrowRight />
                  </a>
                </>
              )}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function Matters({ items, refresh }: { items: Matter[]; refresh: () => void }) {
  const [show, setShow] = useState(false),
    [title, setTitle] = useState(""),
    [mcn, setMcn] = useState("");
  const create = async () => {
    await request("/api/matters", {
      method: "POST",
      body: JSON.stringify({
        title,
        mcn_name: mcn,
        party_role: "主播",
        dispute_types: ["关系认定"],
      }),
    });
    setTitle("");
    setMcn("");
    setShow(false);
    refresh();
  };
  const advance = async (m: Matter) => {
    await request(`/api/matters/${m.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        status: m.currentStep >= 4 ? "已完成" : "处理中",
        current_step: Math.min(4, m.currentStep + 1),
      }),
    });
    refresh();
  };
  const addEvidence = async (m: Matter, file: File) => {
    const form = new FormData();
    form.append("file", file);
    form.append("category", "工作管理材料");
    await request(`/api/matters/${m.id}/evidence`, {
      method: "POST",
      body: form,
    });
    refresh();
  };
  const downloadEvidence = async (e: Matter["evidence"][number]) => {
    const r = await fetch(`/api/evidence/${e.id}/download`, {
      credentials: "include",
    });
    if (!r.ok) return;
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = e.name;
    a.click();
    URL.revokeObjectURL(url);
  };
  const removeEvidence = async (id: string) => {
    if (!confirm("确认删除这份证据文件？删除后无法恢复。")) return;
    await request(`/api/evidence/${id}`, { method: "DELETE" });
    refresh();
  };
  const removeMatter = async (id: string) => {
    if (!confirm("确认删除整个事项及其全部证据？此操作无法恢复。")) return;
    await request(`/api/matters/${id}`, { method: "DELETE" });
    refresh();
  };
  return (
    <div className="page">
      <PageHead
        eyebrow="权益事项"
        title="持续管理每一次维权准备"
        desc="评估只是起点。事项中心用于保存当事人、争议类型、证据材料和处理进度。"
        action={
          <button className="primary" onClick={() => setShow(true)}>
            <Plus />
            新建事项
          </button>
        }
      />
      {show && (
        <div className="inline-form panel">
          <h2>建立权益事项</h2>
          <label>
            事项名称
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例如：与某 MCN 的劳动关系认定"
            />
          </label>
          <label>
            相关机构
            <input
              value={mcn}
              onChange={(e) => setMcn(e.target.value)}
              placeholder="MCN 或平台名称"
            />
          </label>
          <div>
            <button className="secondary" onClick={() => setShow(false)}>
              取消
            </button>
            <button className="primary" disabled={!title} onClick={create}>
              保存事项
            </button>
          </div>
        </div>
      )}
      <div className="matter-list">
        {items.map((m) => (
          <article className="panel matter-card" key={m.id}>
            <div className="matter-top">
              <div>
                <span className="status">{m.status}</span>
                <h2>{m.title}</h2>
                <p>
                  {m.mcnName || "未填写机构"} · {m.partyRole}
                </p>
              </div>
              <div className="matter-actions">
                <label className="secondary upload-button">
                  <Upload />
                  上传证据
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp,.txt,.xlsx,.xls,.csv"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) addEvidence(m, file);
                      e.currentTarget.value = "";
                    }}
                  />
                </label>
                <button
                  className="icon-danger"
                  title="删除事项"
                  onClick={() => removeMatter(m.id)}
                >
                  <Trash2 />
                </button>
              </div>
            </div>
            <div className="mini-track">
              {steps.map((s, i) => (
                <div className={i < m.currentStep ? "done" : ""} key={s}>
                  <span>{i < m.currentStep ? <Check /> : i + 1}</span>
                  <b>{s}</b>
                </div>
              ))}
            </div>
            <div className="evidence-summary">
              <div>
                <b>{m.evidence.length}</b>
                <span>份证据已存档</span>
              </div>
              {m.evidence.slice(0, 3).map((e) => (
                <span className="evidence-file" key={e.id}>
                  <button
                    className="file-chip"
                    onClick={() => downloadEvidence(e)}
                    title={e.encrypted ? `已加密 · SHA-256 ${e.sha256?.slice(0, 12) || "已记录"}` : "下载证据文件"}
                  >
                    {e.encrypted ? <LockKeyhole /> : <FileSearch />}
                    {e.name}
                    <Download />
                  </button>
                  <button
                    className="delete-file"
                    onClick={() => removeEvidence(e.id)}
                    title="删除证据"
                  >
                    <Trash2 />
                  </button>
                </span>
              ))}
              <button className="text-btn" onClick={() => advance(m)}>
                {m.currentStep >= 4 ? "已完成" : "推进下一步"}
                <ChevronRight />
              </button>
            </div>
          </article>
        ))}
        {!items.length && (
          <Empty
            title="还没有事项"
            text="建立一个事项后，其他使用者录入的材料会保存在后端数据库中。"
          />
        )}
      </div>
    </div>
  );
}

function Library({
  cases,
  knowledge,
}: {
  cases: CaseItem[];
  knowledge: Knowledge[];
}) {
  const [tab, setTab] = useState<"case" | "law" | "knowledge">("case"),
    [q, setQ] = useState("");
  const filtered = useMemo(
    () =>
      cases.filter((x) => (x.title + x.summary + x.focus.join("")).includes(q)),
    [q, cases],
  );
  return (
    <div className="page">
      <PageHead
        eyebrow="研究资料库"
        title="在同一个入口核查案例、法规与实务知识"
        desc="每条依据都说明适用场景；法规可直接跳转官方全文。"
      />
      <div className="library-tabs">
        <button
          className={tab === "case" ? "active" : ""}
          onClick={() => setTab("case")}
        >
          争议案例 <span>{cases.length}</span>
        </button>
        <button
          className={tab === "law" ? "active" : ""}
          onClick={() => setTab("law")}
        >
          法规依据 <span>{laws.length}</span>
        </button>
        <button
          className={tab === "knowledge" ? "active" : ""}
          onClick={() => setTab("knowledge")}
        >
          实务知识 <span>{knowledge.length}</span>
        </button>
      </div>
      <div className="searchbar">
        <Search />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="输入关系类型、争议焦点或法律问题"
        />
      </div>
      {tab === "case" && (
        <div className="library-list">
          {filtered.map((c) => (
            <article className="library-item" key={c.id}>
              <div>
                <span className="category">{c.relation}</span>
                <h2>{c.title}</h2>
                <p>{c.summary}</p>
                <div className="tags">
                  {c.focus.map((x) => (
                    <span key={x}>{x}</span>
                  ))}
                </div>
              </div>
              <aside>
                <strong>{c.year}</strong>
                <span>案例年份</span>
              </aside>
            </article>
          ))}
        </div>
      )}
      {tab === "law" && (
        <div className="library-list">
          {laws
            .filter((x) => x.join("").includes(q))
            .map((l) => (
              <article className="library-item law" key={l[1]}>
                <div>
                  <span className="category">{l[0]}</span>
                  <h2>{l[1]}</h2>
                  <p>{l[2]}</p>
                </div>
                <a href={l[3]} target="_blank" rel="noreferrer">
                  查看官方全文
                  <ArrowRight />
                </a>
              </article>
            ))}
        </div>
      )}
      {tab === "knowledge" && (
        <div className="library-list">
          {knowledge
            .filter((x) => (x.title + x.summary).includes(q))
            .map((k) => (
              <article className="library-item" key={k.id}>
                <div>
                  <span className="category">{k.category}</span>
                  <h2>{k.title}</h2>
                  <p>{k.summary}</p>
                  <ul>
                    {k.points.slice(0, 3).map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
        </div>
      )}
    </div>
  );
}

function Ai() {
  const [input, setInput] = useState(""),
    [messages, setMessages] = useState<
      { role: "user" | "assistant"; content: string }[]
    >([]),
    [privacyMessage, setPrivacyMessage] = useState("AI 对话正文不会写入本地数据库。"),
    [busy, setBusy] = useState(false);
  const send = async (text = input) => {
    if (!text.trim()) return;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const x = await request("/api/ai/chat", {
        method: "POST",
        body: JSON.stringify({ messages: next }),
      });
      setMessages([...next, { role: "assistant", content: x.answer }]);
      setPrivacyMessage(x.privacy?.redactedCount ? `已自动脱敏 ${x.privacy.redactedCount} 处敏感信息；对话正文未保存。` : "未检测到常见敏感号码；对话正文未保存。")
    } catch (e: any) {
      setMessages([
        ...next,
        { role: "assistant", content: "暂时无法连接 AI 服务：" + e.message },
      ]);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="page ai-page">
      <PageHead
        eyebrow="AI 法律助手"
        title="围绕事实提出更清楚的问题"
        desc="AI 用于梳理思路和材料，不替代律师意见或司法认定。"
      />
      <div className="privacy-notice">
        <ShieldCheck />
        <span>
          问题通过 HTTPS 发送至第三方 AI，发送前自动遮蔽身份证号、手机号、银行卡号和邮箱。家庭住址、姓名等仍请主动隐去。
        </span>
      </div>
      <div className="privacy-state"><LockKeyhole />{privacyMessage}</div>
      <div className="ai-layout">
        <aside className="panel">
          <h2>常见问题</h2>
          {[
            "合作协议写明非劳动关系，还能认定吗？",
            "高额违约金可以请求调低吗？",
            "应该优先保存哪些电子证据？",
            "机构未缴社保应如何处理？",
          ].map((x) => (
            <button onClick={() => send(x)} key={x}>
              {x}
              <ChevronRight />
            </button>
          ))}
        </aside>
        <section className="chat panel">
          <div className="messages">
            {!messages.length && (
              <div className="ai-empty">
                <Bot />
                <h2>先说说发生了什么</h2>
                <p>
                  建议包含合作期限、排班方式、收入结算、机构管理和当前争议。
                </p>
              </div>
            )}
            {messages.map((m, i) => (
              <div className={m.role} key={i}>
                <b>{m.role === "user" ? "你" : "AI 助手"}</b>
                <p>{m.content.replace(/[#*`]/g, "")}</p>
              </div>
            ))}
            {busy && (
              <div className="assistant">
                <b>AI 助手</b>
                <p>正在分析...</p>
              </div>
            )}
          </div>
          <div className="composer">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="描述事实或输入法律问题"
            />
            <button
              className="primary"
              onClick={() => send()}
              disabled={busy || !input.trim()}
            >
              <ArrowRight />
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}

function SecurityCenter({ status, go }: { status: SecurityStatus | null; go: (page: Page) => void }) {
  const controls = [
    { icon: LockKeyhole, title: "账号与会话保护", ok: !!status?.httpOnlySession, text: `连续 ${status?.loginLockout?.attempts || 5} 次登录失败，账号锁定 ${status?.loginLockout?.minutes || 15} 分钟；会话凭证禁止浏览器脚本读取。` },
    { icon: ShieldCheck, title: "证据加密与完整性", ok: !!status?.evidenceEncryption, text: `新上传证据采用应用层加密，并记录 ${status?.evidenceIntegrity || "SHA-256"} 指纹用于发现文件篡改。` },
    { icon: Bot, title: "AI 隐私保护", ok: !!status?.aiAutoRedaction, text: "常见身份证号、手机号、银行卡号和邮箱在发送前自动脱敏；平台不保存 AI 对话正文。" },
    { icon: UserCheck, title: "人工复核闭环", ok: !!status?.manualReview, text: "评估报告可申请人工复核，处理状态、复核人、意见和时间均留痕。" },
    { icon: Database, title: "操作审计", ok: !!status?.auditLogging, text: "登录、评估、证据、内容维护、AI 使用与复核处理均记录关键操作，不记录密码和对话正文。" },
  ];
  return <div className="page security-page">
    <PageHead eyebrow="安全与合规" title="让每一次数据处理都可说明、可追溯" desc="安全不是页面上的一个开关，而是账号、传输、存储、AI 和人工流程共同组成的防护体系。" />
    {!status?.https && <div className="security-warning"><ShieldAlert /><div><b>当前连接尚未启用 HTTPS</b><p>应用层保护已经生效，但正式对外使用前仍需配置域名和 HTTPS，才能防止传输链路被窃听或篡改。</p></div></div>}
    <section className="security-grid">{controls.map((item) => <article className="panel security-control" key={item.title}><span className={item.ok ? "ok" : "warn"}><item.icon /></span><div><small>{item.ok ? "已启用" : "需配置"}</small><h2>{item.title}</h2><p>{item.text}</p></div></article>)}</section>
    <section className="panel security-boundary"><div><span className="kicker">数据处理边界</span><h2>平台只处理完成服务所必需的数据</h2></div><div className="boundary-list"><p><b>评估数据</b><span>按账号隔离保存，用于恢复历史报告和人工复核。</span></p><p><b>证据文件</b><span>加密保存，只有文件所属用户和管理员可访问。</span></p><p><b>AI 问答</b><span>第三方处理前自动脱敏，本站不保存聊天正文。</span></p><p><b>人工复核</b><span>复核意见可追溯，但不冒充律师正式法律意见。</span></p></div><div className="security-actions"><button className="secondary" onClick={() => go("ai")}><Bot />查看 AI 隐私模式</button><button className="primary" onClick={() => go("assessment")}><ClipboardCheck />开始受保护评估</button></div></section>
  </div>;
}

function Admin({
  stats,
  cases,
  knowledge,
  reviews,
  refresh,
}: {
  stats: any;
  cases: CaseItem[];
  knowledge: Knowledge[];
  reviews: Review[];
  refresh: () => void;
}) {
  const [tab, setTab] = useState("overview"),
    [showAdd, setShowAdd] = useState(false),
    [adminQuery, setAdminQuery] = useState(""),
    [newTitle, setNewTitle] = useState(""),
    [newSummary, setNewSummary] = useState(""),
    [reviewComments, setReviewComments] = useState<Record<string, string>>({}),
    [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const adminTabs = [
    { id: "overview", label: "运行概览", desc: "数据与系统状态", icon: Database },
    { id: "cases", label: "案例管理", desc: "录入、检索与删除", icon: BriefcaseBusiness },
    { id: "knowledge", label: "知识库管理", desc: "依据与实务内容", icon: BookOpen },
    { id: "reviews", label: "人工复核", desc: "处理用户复核申请", icon: UserCheck },
    { id: "audit", label: "操作审计", desc: "查看关键操作记录", icon: ShieldCheck },
    { id: "model", label: "评估模型", desc: "权重与版本说明", icon: ClipboardCheck },
  ] as const;
  const normalizedQuery = adminQuery.trim().toLowerCase();
  const visibleCases = cases.filter((item) =>
    !normalizedQuery || `${item.title} ${item.relation} ${item.year}`.toLowerCase().includes(normalizedQuery)
  );
  const visibleKnowledge = knowledge.filter((item) =>
    !normalizedQuery || `${item.title} ${item.category} ${item.summary}`.toLowerCase().includes(normalizedQuery)
  );
  useEffect(() => { if (tab === "audit") request("/api/admin/audit-logs").then(x => setAuditLogs(x.items)).catch(() => {}); }, [tab]);
  const remove = async (id: string) => {
    if (confirm("确认删除这条案例？")) {
      await request(`/api/admin/cases/${id}`, { method: "DELETE" });
      refresh();
    }
  };
  const removeKnowledge = async (id: string) => {
    if (confirm("确认删除这条知识内容？")) { await request(`/api/admin/legal-knowledge/${id}`, { method: "DELETE" }); refresh(); }
  };
  const addContent = async () => {
    if (tab === "cases") {
      await request("/api/admin/cases", {
        method: "POST",
        body: JSON.stringify({
          title: newTitle,
          summary: newSummary,
          relation: "新业态模糊混合用工关系",
          year: new Date().getFullYear(),
          focus: ["待分类"],
          similarity: 60,
        }),
      });
    } else {
      await request("/api/admin/legal-knowledge", {
        method: "POST",
        body: JSON.stringify({
          title: newTitle,
          summary: newSummary,
          category: "实务补充",
          points: [newSummary],
          basis: ["管理员录入，待复核"],
          tags: ["自定义"],
        }),
      });
    }
    setNewTitle("");
    setNewSummary("");
    setShowAdd(false);
    refresh();
  };
  const importCases = async (file: File) => {
    try {
      const parsed = JSON.parse(await file.text());
      const items = Array.isArray(parsed) ? parsed : parsed.cases;
      if (!Array.isArray(items)) throw new Error("文件中缺少 cases 数组");
      await request("/api/admin/cases/bulk", {
        method: "POST",
        body: JSON.stringify({ cases: items }),
      });
      refresh();
    } catch (e: any) {
      alert("导入失败：" + e.message);
    }
  };
  const handleReview = async (id: string, status: string) => {
    await request(`/api/admin/reviews/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status, comment: reviewComments[id] || "" }),
    });
    refresh();
  };
  return (
    <div className="page admin-page">
      <PageHead
        eyebrow="平台管理中心"
        title="内容、复核与运行管理"
        desc="集中维护公共案例与知识内容，处理人工复核，并监测平台关键数据和操作记录。"
        action={<span className="admin-session-state"><ShieldCheck />管理员会话已验证</span>}
      />
      <div className="admin-layout">
        <aside className="admin-nav">
          <span className="admin-nav-label">管理模块</span>
          {adminTabs.map((item) => {
            const Icon = item.icon;
            return (
            <button
              className={tab === item.id ? "active" : ""}
              onClick={() => { setTab(item.id); setAdminQuery(""); setShowAdd(false); }}
              key={item.id}
            >
              <Icon />
              <span><b>{item.label}</b><small>{item.desc}</small></span>
              <ChevronRight />
            </button>
          )})}
        </aside>
        <section className="panel admin-content">
          {tab === "overview" && (
            <>
              <div className="admin-content-head">
                <div><span className="kicker">实时数据</span><h2>平台运行概览</h2><p>快速了解业务数据与待处理工作。</p></div>
                <span className="admin-updated">当前数据已同步</span>
              </div>
              <div className="admin-stat-strip">
                <div><strong>{stats.totalEvaluations || 0}</strong><span>评估记录</span><small>用户独立存档</small></div>
                <div><strong>{stats.matterCount || 0}</strong><span>权益事项</span><small>持续跟踪进度</small></div>
                <div><strong>{cases.length}</strong><span>公共案例</span><small>面向前台检索</small></div>
                <div><strong>{knowledge.length}</strong><span>知识条目</span><small>法规与实务依据</small></div>
              </div>
              <div className="admin-overview-grid">
                <section className="admin-work-queue">
                  <div className="section-title"><div><span className="kicker">待办入口</span><h2>常用管理工作</h2></div></div>
                  <button onClick={() => setTab("reviews")}><UserCheck /><span><b>处理人工复核</b><small>{reviews.filter(r => r.status !== "已完成").length} 项待处理</small></span><ChevronRight /></button>
                  <button onClick={() => setTab("cases")}><BriefcaseBusiness /><span><b>维护案例库</b><small>{cases.length} 条案例可检索</small></span><ChevronRight /></button>
                  <button onClick={() => setTab("knowledge")}><BookOpen /><span><b>维护知识库</b><small>{knowledge.length} 条知识内容</small></span><ChevronRight /></button>
                </section>
                <section className="admin-system-state">
                  <div><Database /><span><b>服务端数据库</b><small>案例、知识、评估和事项已持久化</small></span><em>正常</em></div>
                  <div><ShieldCheck /><span><b>权限与审计</b><small>角色隔离及关键操作记录已启用</small></span><em>正常</em></div>
                  <p>公共内容的新增或删除会影响所有普通用户，请在确认来源与准确性后再提交。</p>
                </section>
              </div>
            </>
          )}
          {tab === "cases" && (
            <>
              <div className="admin-content-head">
                <div><span className="kicker">公共案例库</span><h2>案例管理</h2><p>维护前台检索和评估报告引用的案例内容。</p></div>
                <span className="admin-count">{cases.length} 条</span>
              </div>
              <div className="admin-toolbar">
                <label className="admin-search"><Search /><input value={adminQuery} onChange={(e) => setAdminQuery(e.target.value)} placeholder="搜索案例名称、关系类型或年份" /></label>
                <div className="admin-actions">
                  <label className="secondary upload-button">
                    <Upload />
                    导入 JSON
                    <input
                      type="file"
                      accept=".json"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) importCases(f);
                        e.currentTarget.value = "";
                      }}
                    />
                  </label>
                  <button
                    className="primary"
                    onClick={() => setShowAdd(!showAdd)}
                  >
                    <Plus />
                    新增案例
                  </button>
                </div>
              </div>
              {showAdd && (
                <AdminAdd
                  title={newTitle}
                  summary={newSummary}
                  setTitle={setNewTitle}
                  setSummary={setNewSummary}
                  save={addContent}
                />
              )}
              <div className="admin-list-head"><span>案例信息</span><span>操作</span></div>
              {visibleCases.map((c) => (
                <div className="admin-row" key={c.id}>
                  <div className="admin-row-main">
                    <b>{c.title}</b>
                    <span><em>{c.relation}</em><small>{c.year || "年份待补充"}</small></span>
                  </div>
                  <button className="icon-danger" title="删除案例" onClick={() => remove(c.id)}>
                    <Trash2 />
                  </button>
                </div>
              ))}
              {!visibleCases.length && <Empty title="没有匹配案例" text="请更换关键词，或新增一条案例。" />}
            </>
          )}
          {tab === "knowledge" && (
            <>
              <div className="admin-content-head">
                <div><span className="kicker">法律依据库</span><h2>知识库管理</h2><p>维护法规、政策、裁判规则与实务指引。</p></div>
                <span className="admin-count">{knowledge.length} 条</span>
              </div>
              <div className="admin-toolbar">
                <label className="admin-search"><Search /><input value={adminQuery} onChange={(e) => setAdminQuery(e.target.value)} placeholder="搜索标题、分类或内容" /></label>
                <button
                  className="primary"
                  onClick={() => setShowAdd(!showAdd)}
                >
                  <Plus />
                  新增知识
                </button>
              </div>
              {showAdd && (
                <AdminAdd
                  title={newTitle}
                  summary={newSummary}
                  setTitle={setNewTitle}
                  setSummary={setNewSummary}
                  save={addContent}
                />
              )}
              <div className="admin-list-head"><span>知识内容</span><span>操作</span></div>
              {visibleKnowledge.slice(0, 50).map((k) => (
                <div className="admin-row" key={k.id}>
                  <div className="admin-row-main">
                    <b>{k.title}</b>
                    <span><em>{k.category}</em><small>{k.summary.slice(0, 58)}{k.summary.length > 58 ? "…" : ""}</small></span>
                  </div>
                  <button className="icon-danger" title="删除知识" onClick={() => removeKnowledge(k.id)}><Trash2 /></button>
                </div>
              ))}
              {!visibleKnowledge.length && <Empty title="没有匹配知识" text="请更换关键词，或新增一条知识内容。" />}
            </>
          )}
          {tab === "reviews" && <>
            <div className="admin-content-head"><div><span className="kicker">人工质量控制</span><h2>人工复核工单</h2><p>核查问卷事实、计分过程和依据引用，并留下可追溯意见。</p></div><span className="review-count">{reviews.filter(r => r.status !== "已完成").length} 项待处理</span></div>
            {reviews.map((review) => <article className="review-admin-row" key={review.id}>
              <div className="review-admin-summary">
                <span className="category">{review.status}</span>
                <h3>{review.result?.relationLabel || "评估报告"} · {review.result?.totalScore ?? "-"} 分</h3>
                <p>{review.userName || "平台用户"} {review.userEmail ? `· ${review.userEmail}` : ""}</p>
                {review.requestNote && <blockquote>{review.requestNote}</blockquote>}
              </div>
              <textarea value={reviewComments[review.id] ?? review.reviewerComment ?? ""} onChange={(e) => setReviewComments({...reviewComments, [review.id]: e.target.value})} placeholder="填写事实核对、计分校验、依据引用及需补材料说明" />
              <div className="review-admin-actions">
                <button className="secondary" onClick={() => handleReview(review.id, "复核中")}>开始复核</button>
                <button className="secondary" onClick={() => handleReview(review.id, "需补充材料")}>需补材料</button>
                <button className="primary" disabled={!(reviewComments[review.id] ?? review.reviewerComment ?? "").trim()} onClick={() => handleReview(review.id, "已完成")}>完成复核</button>
              </div>
            </article>)}
            {!reviews.length && <Empty title="暂无复核申请" text="用户可在评估报告中提交人工复核工单。" />}
          </>}
          {tab === "audit" && <><div className="admin-content-head"><div><span className="kicker">安全追溯</span><h2>关键操作审计</h2><p>记录评估、事项、证据和公共内容的新增、修改与删除。</p></div><span className="admin-count">最近 {auditLogs.length} 条</span></div><div className="audit-list-head"><span>时间</span><span>操作与用户</span><span>说明</span></div>{auditLogs.map(log => <div className="audit-row" key={log.id}><span>{new Date(log.createdAt).toLocaleString()}</span><div><b>{log.action}</b><small>{log.userName} {log.userEmail && `· ${log.userEmail}`}</small></div><p>{log.detail || log.entityType}</p></div>)}{!auditLogs.length && <Empty title="暂无审计记录" text="后续关键操作会显示在这里。" />}</>}
          {tab === "model" && (
            <>
              <div className="admin-content-head"><div><span className="kicker">规则模型 2026.07</span><h2>关系认定权重结构</h2><p>三项从属性合计 100 分；权益筛查只触发风险提示，不改变关系得分。</p></div><span className="admin-count">36 题</span></div>
              <div className="model-composition">
                {[
                  { name: "人身从属性", questions: "10 道计分题", score: 40, note: "排班、考勤、指令与惩戒" },
                  { name: "经济从属性", questions: "9 道计分题", score: 35, note: "收入依赖、底薪与结算控制" },
                  { name: "组织从属性", questions: "7 道计分题", score: 25, note: "业务纳入、账号与团队管理" },
                ].map((item, index) => <div className="model-dimension" key={item.name}>
                  <span className="model-index">0{index + 1}</span>
                  <div className="model-dimension-main"><div><b>{item.name}</b><small>{item.note}</small></div><div className="model-scale"><span style={{width: `${item.score}%`}} /></div></div>
                  <div className="model-value"><strong>{item.score}</strong><span>分 · {item.questions}</span></div>
                </div>)}
                <div className="model-dimension model-risk-row">
                  <span className="model-index"><ShieldAlert /></span>
                  <div className="model-dimension-main"><div><b>权益风险筛查</b><small>社保、报酬、休息、合同与经营风险</small></div><div className="model-scale"><span /></div></div>
                  <div className="model-value"><strong>10</strong><span>题 · 不计分</span></div>
                </div>
              </div>
              <div className="notice">
                <ShieldCheck />
                <div>
                  <b>修改模型需版本化</b>
                  <p>
                    为保证历史报告可追溯，题目和权重不在浏览器内随意修改。后续应通过发布新模型版本并保留旧版本完成变更。
                  </p>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function AdminAdd({
  title,
  summary,
  setTitle,
  setSummary,
  save,
}: {
  title: string;
  summary: string;
  setTitle: (v: string) => void;
  setSummary: (v: string) => void;
  save: () => void;
}) {
  return (
    <div className="admin-add">
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="标题"
      />
      <textarea
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        placeholder="摘要、裁判要点或知识说明"
      />
      <button
        className="primary"
        disabled={title.length < 2 || summary.length < 5}
        onClick={save}
      >
        保存到公共资料库
      </button>
    </div>
  );
}

const runtime = globalThis as typeof globalThis & {
  __anchorRightsRoot?: ReturnType<typeof createRoot>;
};
const appRoot = runtime.__anchorRightsRoot ?? createRoot(document.getElementById("root")!);
runtime.__anchorRightsRoot = appRoot;
appRoot.render(<App />);
