import React, { useState, useEffect } from 'react';
import { 
  Shield, CheckCircle, XCircle, Clock, AlertTriangle, ArrowRight, 
  User, RefreshCw, Eye, GitCompare, History, PlusCircle, Lock, 
  Building2, Plane, Ship, Search, ChevronRight, FileCheck, Info,
  Sun, Moon, Anchor, Package, ArrowUpRight, ArrowDownLeft, Layers,
  Users, BarChart3, TrendingUp, Activity
} from 'lucide-react';
import { api, getCurrentUser, setCurrentUser } from './services/api';

// ─── Lookup Maps for Human-Readable Names ─────────────────────────────────────
const CLIENT_NAMES = {
  client_01: 'Tata Motors',
  client_02: 'Reliance Retail',
  client_03: 'Sun Pharma',
  client_04: 'Infosys Tech',
  client_05: 'Mahindra Auto',
  client_06: 'L&T Engineering',
  client_07: "Dr. Reddy's",
  client_08: 'BHEL Energy',
  client_09: 'Hindustan Unilever',
  client_10: 'Wipro Electronics',
};

const BRANCH_NAMES = {
  branch_mum: 'Mumbai',
  branch_del: 'Delhi',
  branch_cen: 'Chennai',
  branch_kol: 'Kolkata',
  branch_blr: 'Bengaluru',
};

const ACTION_LABELS = {
  prepare_job:  'Prepare',
  check_job:    'Check & Verify',
  file_job:     'File to Customs',
  cancel_job:   'Cancel',
  reopen_job:   'Reopen',
  create_job:   'Created',
  parser_ingest:'Parser Ingested',
};

const STAGE_LABELS = {
  CONFIRMED:  'Confirmed',
  PREPARED:   'Prepared',
  CHECKED:    'Checked',
  FILED:      'Filed',
  CANCELLED:  'Cancelled',
  REOPENED:   'Reopened',
};

// Helper functions
const clientName  = (id) => CLIENT_NAMES[id] || id;
const branchName  = (id) => BRANCH_NAMES[id] || id;
const actionLabel = (a)  => ACTION_LABELS[a] || a;
const stageLabel  = (s)  => STAGE_LABELS[s]  || s;

const KEY_PERSONAS = [
  { id: 'usr_asha',       name: 'Asha Sharma',       role: 'Maker + Checker (Select Clients)', desc: 'Maker everywhere; Checker for Sun Pharma & Dr. Reddy\'s' },
  { id: 'usr_ravi',       name: 'Ravi Kumar',         role: 'Restricted Checker',              desc: 'Checker for Sun Pharma, Mumbai branch, Imports only' },
  { id: 'usr_vikram',     name: 'Vikram Seth (ABSENT)',role: 'Delhi Supervisor',                desc: 'Currently on leave; delegated authority to Priya' },
  { id: 'usr_priya',      name: 'Priya Nair',         role: 'Maker + Active Delegate',         desc: 'Maker at Mumbai + inherits Vikram\'s Delhi Supervisor authority' },
  { id: 'usr_client_sun', name: 'Sameer Mehta',       role: 'Client Portal (Sun Pharma)',      desc: 'Sun Pharma employee; read-only access to Sun Pharma jobs' },
  { id: 'usr_admin_raj',  name: 'Rajesh Patel',       role: 'System Administrator',            desc: 'Full administrative authority (subject to anti-self-escalation)' },
  { id: 'usr_parser_svc', name: 'Overnight EDI Parser',role: 'Service Account',               desc: 'Machine identity for manifest ingestion' },
];

export default function App() {
  // Theme
  const [theme, setTheme] = useState(() => localStorage.getItem('nfpl_theme') || 'dark');
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('nfpl_theme', theme);
  }, [theme]);
  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const [activeUser, setActiveUser] = useState(getCurrentUser());
  const [activeTab, setActiveTab] = useState('queue');
  const [workQueue, setWorkQueue] = useState([]);
  const [queueCount, setQueueCount] = useState(0);
  const [jobsList, setJobsList] = useState([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const [stageFilter, setStageFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedJob, setSelectedJob] = useState(null);
  const [jobTimeline, setJobTimeline] = useState([]);
  const [availableActions, setAvailableActions] = useState({});

  // Simulator
  const [simMode, setSimMode] = useState('compare');
  const [simUserA, setSimUserA] = useState('usr_ravi');
  const [simUserB, setSimUserB] = useState('usr_asha');
  const [simJobId, setSimJobId] = useState('job_101');
  const [simAction, setSimAction] = useState('check_job');
  const [simResult, setSimResult] = useState(null);

  // Time Machine
  const [tmJobId, setTmJobId] = useState('job_101');
  const [tmAction, setTmAction] = useState('check_job');
  const [tmDate, setTmDate] = useState('2026-10-03T12:00:00Z');
  const [tmResult, setTmResult] = useState(null);

  // Admin
  const [assignments, setAssignments] = useState([]);
  const [delegations, setDelegations] = useState([]);
  const [newAsgnUserId, setNewAsgnUserId] = useState('usr_ravi');
  const [newAsgnRole, setNewAsgnRole] = useState('SUPERVISOR');
  const [newAsgnClient, setNewAsgnClient] = useState('*');
  const [newAsgnBranch, setNewAsgnBranch] = useState('*');

  useEffect(() => { loadQueue(); loadJobs(); }, [activeUser]);

  const handleUserChange = (newUid) => {
    setCurrentUser(newUid);
    setActiveUser(newUid);
    setFeedback({
      type: 'info',
      title: 'Switched Active Persona',
      message: `Now acting as: ${KEY_PERSONAS.find(p => p.id === newUid)?.name || newUid}`
    });
  };

  const loadQueue = async () => {
    try {
      setLoading(true);
      const res = await api.getWorkQueue();
      setWorkQueue(res.jobs || []);
      setQueueCount(res.total_waiting || 0);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const loadJobs = async () => {
    try {
      const res = await api.getJobs({ stage: stageFilter, search: searchQuery });
      setJobsList(res.items || []);
      setTotalJobs(res.total || 0);
    } catch (err) { console.error(err); }
  };

  const openJobModal = async (job) => {
    setSelectedJob(job);
    try {
      const [histRes, actRes] = await Promise.all([
        api.getJobHistory(job.id),
        api.getAvailableActions(job.id)
      ]);
      setJobTimeline(histRes.timeline || []);
      setAvailableActions(actRes.evaluations || {});
    } catch (err) { console.error(err); }
  };

  const executeAction = async (jobId, action, defaultReason = '') => {
    let reason = defaultReason;
    if (['cancel_job', 'reopen_job'].includes(action)) {
      reason = window.prompt(`Enter mandatory justification for "${actionLabel(action)}":`, 'Administrative request');
      if (!reason) return;
    }
    try {
      setLoading(true);
      if (action === 'prepare_job') await api.prepareJob(jobId, reason);
      else if (action === 'check_job')  await api.checkJob(jobId, reason);
      else if (action === 'file_job')   await api.fileJob(jobId, reason);
      else if (action === 'cancel_job') await api.cancelJob(jobId, reason);
      else if (action === 'reopen_job') await api.reopenJob(jobId, reason);

      setFeedback({ type: 'success', title: 'Action Executed', message: `"${actionLabel(action)}" succeeded on Job ${jobId}.` });
      loadQueue(); loadJobs();
      if (selectedJob?.id === jobId) {
        const updated = await api.getJob(jobId);
        openJobModal(updated);
      }
    } catch (err) {
      setFeedback({
        type: 'error',
        title: `Access Denied: ${err.detail?.reason_code || 'FORBIDDEN'}`,
        message: err.message || 'Unauthorized action.',
        details: err.detail
      });
    } finally { setLoading(false); }
  };

  const runSimulator = async () => {
    try {
      setLoading(true);
      if (simMode === 'compare') {
        const res = await api.compareAccess(simUserA, simUserB, simJobId, simAction);
        setSimResult(res);
      } else {
        const res = await api.authorizeAction(simUserA, simAction, simJobId);
        setSimResult({ single: res });
      }
    } catch (err) { setFeedback({ type: 'error', title: 'Simulation Error', message: err.message }); }
    finally { setLoading(false); }
  };

  const runTimeMachine = async () => {
    try {
      setLoading(true);
      const res = await api.whoCouldAct(tmJobId, tmAction, tmDate);
      setTmResult(res);
    } catch (err) { setFeedback({ type: 'error', title: 'Query Error', message: err.message }); }
    finally { setLoading(false); }
  };

  const handleCreateAssignment = async (e) => {
    e.preventDefault();
    try {
      await api.createAssignment({
        user_id: newAsgnUserId,
        role_id: newAsgnRole,
        client_id: newAsgnClient,
        branch_id: newAsgnBranch,
        direction: '*',
        mode: '*'
      });
      setFeedback({ type: 'success', title: 'Assignment Granted', message: `Role ${newAsgnRole} assigned to ${newAsgnUserId}` });
      loadAdminData();
    } catch (err) {
      setFeedback({ type: 'error', title: `Grant Failed: ${err.detail?.reason_code || 'DENIED'}`, message: err.message });
    }
  };

  const loadAdminData = async () => {
    try {
      const [asgns, dlgs] = await Promise.all([api.getAssignments(), api.getDelegations()]);
      setAssignments(asgns || []);
      setDelegations(dlgs || []);
    } catch (err) { console.error(err); }
  };

  useEffect(() => { if (activeTab === 'admin') loadAdminData(); }, [activeTab]);

  const activePersonaObj = KEY_PERSONAS.find(p => p.id === activeUser) || { name: activeUser, role: 'Custom', desc: '' };

  // Stats for header
  const confirmedCount  = jobsList.filter(j => j.stage === 'CONFIRMED').length;
  const preparedCount   = jobsList.filter(j => j.stage === 'PREPARED').length;
  const checkedCount    = jobsList.filter(j => j.stage === 'CHECKED').length;

  return (
    <div className="app-root" data-theme={theme}>
      {/* ── TOP HEADER ───────────────────────────────────────────────────── */}
      <header className="main-header">
        <div className="header-left">
          <div className="brand-icon">
            <Shield size={26} color="#ffffff" />
          </div>
          <div>
            <div className="brand-title-row">
              <h1 className="brand-title">NFPL Access Control</h1>
              <span className="policy-badge">Policy v2026.1</span>
            </div>
            <p className="brand-sub">Nagarkot Forwarders Pvt. Ltd. · Customs Brokerage Authorization Engine</p>
          </div>
        </div>

        <div className="header-right">
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="theme-toggle"
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {/* Persona Switcher */}
          <div className="persona-switcher">
            <div className="persona-label">Simulated Identity</div>
            <div className="persona-name">{activePersonaObj.name}</div>
          </div>
          <select
            value={activeUser}
            onChange={(e) => handleUserChange(e.target.value)}
            className="persona-select"
          >
            {KEY_PERSONAS.map(p => (
              <option key={p.id} value={p.id}>{p.name} — {p.role}</option>
            ))}
          </select>
        </div>
      </header>

      {/* ── PERSONA CONTEXT BANNER ──────────────────────────────────────── */}
      <div className="context-banner">
        <div className="context-banner-left">
          <Info size={16} className="context-icon" />
          <span>
            <strong>Active Context:</strong> {activePersonaObj.desc}
          </span>
        </div>
        <span className="identity-pill">ID: {activeUser}</span>
      </div>

      {/* ── QUICK STATS ROW ─────────────────────────────────────────────── */}
      <div className="stats-row">
        {[
          { label: 'My Queue',       value: queueCount,     color: 'var(--accent)',  icon: <Clock size={20}/> },
          { label: 'Total Shipments',value: totalJobs,       color: '#22d3ee',       icon: <Package size={20}/> },
          { label: 'Awaiting Prep',  value: confirmedCount,  color: '#f59e0b',       icon: <Activity size={20}/> },
          { label: 'Awaiting Check', value: preparedCount,   color: '#a78bfa',       icon: <TrendingUp size={20}/> },
          { label: 'Awaiting File',  value: checkedCount,    color: '#34d399',       icon: <BarChart3 size={20}/> },
        ].map(stat => (
          <div key={stat.label} className="stat-card">
            <div className="stat-icon" style={{ color: stat.color }}>{stat.icon}</div>
            <div>
              <div className="stat-value" style={{ color: stat.color }}>{stat.value}</div>
              <div className="stat-label">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── FEEDBACK BANNER ─────────────────────────────────────────────── */}
      {feedback && (
        <div className={`feedback-banner feedback-${feedback.type} animate-fade-in`}>
          <div className="feedback-icon">
            {feedback.type === 'error' ? <XCircle size={18} /> :
             feedback.type === 'success' ? <CheckCircle size={18} /> :
             <Info size={18} />}
          </div>
          <div className="feedback-body">
            <div className="feedback-title">{feedback.title}</div>
            <div className="feedback-msg">{feedback.message}</div>
            {feedback.details?.reason && (
              <div className="feedback-detail">Reason: {feedback.details.reason}</div>
            )}
          </div>
          <button onClick={() => setFeedback(null)} className="feedback-close">✕</button>
        </div>
      )}

      {/* ── NAVIGATION TABS ─────────────────────────────────────────────── */}
      <nav className="tab-nav">
        {[
          { id: 'queue',     label: 'Work Queue',       count: queueCount, icon: Clock },
          { id: 'jobs',      label: 'All Shipments',    count: totalJobs,  icon: Building2 },
          { id: 'simulator', label: 'Access Simulator',                    icon: GitCompare },
          { id: 'history',   label: 'Historical Investigation',            icon: History },
          { id: 'admin',     label: 'Admin & Roles',                       icon: Shield },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-btn ${isActive ? 'tab-btn-active' : ''}`}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className={`tab-count ${isActive ? 'tab-count-active' : ''}`}>{tab.count}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* ════════════════════════════════════════════════════════════════════
          TAB 1: WORK QUEUE
         ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'queue' && (
        <section className="animate-fade-in">
          <div className="section-header">
            <div>
              <h2 className="section-title">Jobs Needing Your Action</h2>
              <p className="section-sub">
                Zero-drift guarantee: Every job below matches your current scoped roles with all separation-of-duties rules enforced.
              </p>
            </div>
            <button onClick={loadQueue} className="btn btn-secondary">
              <RefreshCw size={15} /> Refresh
            </button>
          </div>

          {workQueue.length === 0 ? (
            <div className="empty-state glass-panel">
              <CheckCircle size={44} className="empty-icon" />
              <h3 className="empty-title">All Clear! No jobs waiting for you.</h3>
              <p className="empty-sub">
                No pending tasks match your current scoped permissions as <strong>{activePersonaObj.name}</strong>. Try switching personas!
              </p>
            </div>
          ) : (
            <div className="job-grid">
              {workQueue.map(item => (
                <div key={item.id} className="job-card glass-panel">
                  <div className="job-card-header">
                    <span className={`stage-badge stage-${item.stage.toLowerCase()}`}>
                      {stageLabel(item.stage)}
                    </span>
                    <span className="job-date">{new Date(item.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                  </div>

                  <h3 className="job-number">{item.job_number}</h3>

                  <div className="job-meta-grid">
                    <div className="job-meta-item">
                      <span className="meta-label">Client</span>
                      <span className="meta-value">{clientName(item.client_id)}</span>
                      <span className="meta-id">({item.client_id})</span>
                    </div>
                    <div className="job-meta-item">
                      <span className="meta-label">Branch</span>
                      <span className="meta-value">{branchName(item.branch_id)}</span>
                      <span className="meta-id">({item.branch_id})</span>
                    </div>
                    <div className="job-meta-item">
                      <span className="meta-label">Direction</span>
                      <span className="meta-value">{item.direction === 'IMPORT' ? '⬇ Import' : '⬆ Export'}</span>
                    </div>
                    <div className="job-meta-item">
                      <span className="meta-label">Mode</span>
                      <span className="meta-value">{item.mode?.replace('_', ' ')}</span>
                    </div>
                  </div>

                  <div className="eligible-action-box">
                    <div className="eligible-label">
                      <FileCheck size={14} /> Eligible Action
                    </div>
                    <div className="eligible-name">{actionLabel(item.required_action)}</div>
                    <div className="eligible-desc">{item.action_explanation}</div>
                  </div>

                  <div className="job-card-actions">
                    <button
                      onClick={() => executeAction(item.id, item.required_action)}
                      className="btn btn-primary flex-1"
                      disabled={loading}
                    >
                      <FileCheck size={15} /> {actionLabel(item.required_action)}
                    </button>
                    <button onClick={() => openJobModal(item)} className="btn btn-secondary">
                      <Eye size={15} /> Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          TAB 2: ALL SHIPMENTS EXPLORER
         ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'jobs' && (
        <section className="animate-fade-in">
          <div className="filter-bar glass-panel">
            <div className="search-box">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                placeholder="Search job number, description, entry..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadJobs()}
                className="search-input"
              />
            </div>
            <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)} className="filter-select">
              <option value="">All Stages</option>
              {Object.entries(STAGE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <button onClick={loadJobs} className="btn btn-primary">Apply Filter</button>
          </div>

          <div className="glass-panel table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job Number</th>
                  <th>Stage</th>
                  <th>Client</th>
                  <th>Branch</th>
                  <th>Direction / Mode</th>
                  <th>Preparer / Checker</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {jobsList.map(job => (
                  <tr key={job.id} className="table-row">
                    <td className="td-job-number">{job.job_number}</td>
                    <td>
                      <span className={`stage-badge stage-${job.stage.toLowerCase()}`}>
                        {stageLabel(job.stage)}
                      </span>
                    </td>
                    <td>
                      <div className="td-name">{clientName(job.client_id)}</div>
                      <div className="td-id">{job.client_id}</div>
                    </td>
                    <td>
                      <div className="td-name">{branchName(job.branch_id)}</div>
                      <div className="td-id">{job.branch_id}</div>
                    </td>
                    <td>
                      <div className="direction-pill">
                        {job.direction === 'IMPORT' ? <ArrowDownLeft size={13} /> : <ArrowUpRight size={13} />}
                        {job.direction}
                      </div>
                      <div className="td-id">{job.mode?.replace('_', ' ')}</div>
                    </td>
                    <td className="td-actors">
                      <div>Prep: <strong>{job.preparer_id || '—'}</strong></div>
                      <div>Chk: <strong>{job.checker_id || '—'}</strong></div>
                    </td>
                    <td>
                      <button onClick={() => openJobModal(job)} className="btn btn-secondary btn-sm">
                        Inspect <ChevronRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
                {jobsList.length === 0 && (
                  <tr><td colSpan="7" className="td-empty">No jobs match current filters.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          TAB 3: ACCESS SIMULATOR
         ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'simulator' && (
        <section className="animate-fade-in">
          <div className="glass-panel section-card">
            <h2 className="section-title">Access Simulator & Decision Differential</h2>
            <p className="section-sub" style={{ marginBottom: '20px' }}>
              Answers <strong>"Why can she do this and he can't?"</strong> — compare two identities against the same job and action to see the exact policy divergence.
            </p>

            <div className="sim-controls">
              <div className="form-group">
                <label className="form-label">USER A</label>
                <select value={simUserA} onChange={(e) => setSimUserA(e.target.value)}>
                  {KEY_PERSONAS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">USER B</label>
                <select value={simUserB} onChange={(e) => setSimUserB(e.target.value)}>
                  {KEY_PERSONAS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">TARGET JOB</label>
                <select value={simJobId} onChange={(e) => setSimJobId(e.target.value)}>
                  <option value="job_101">JOB-BOM-2026-0101 — Sun Pharma · Mumbai Import (Prep by Asha)</option>
                  <option value="job_102">JOB-BOM-2026-0102 — Tata Motors · Mumbai Export (Confirmed)</option>
                  <option value="job_104">JOB-DEL-2026-0104 — Infosys · Delhi · FILED</option>
                  <option value="job_105">JOB-DEL-2026-0105 — Reliance · Delhi · Prep by Pooja</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">ACTION</label>
                <select value={simAction} onChange={(e) => setSimAction(e.target.value)}>
                  {Object.entries(ACTION_LABELS).filter(([k]) => ['check_job','prepare_job','file_job','cancel_job','reopen_job'].includes(k)).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
            </div>

            <button onClick={runSimulator} className="btn btn-primary" style={{ padding: '10px 28px' }} disabled={loading}>
              <GitCompare size={17} /> Compare Access Decisions
            </button>
          </div>

          {simResult && (
            <div className="glass-panel-elevated animate-fade-in section-card">
              {simResult.comparison_summary && (
                <div className="divergence-box">
                  <div className="divergence-label">🔍 Root Cause Summary</div>
                  <div className="divergence-text">{simResult.comparison_summary}</div>
                </div>
              )}

              <div className="compare-grid">
                {/* User A */}
                <div className={`compare-card glass-panel ${simResult.user_a?.decision?.allowed ? 'compare-allowed' : 'compare-denied'}`}>
                  <div className="compare-card-header">
                    <div>
                      <h3 className="compare-name">{simResult.user_a?.name}</h3>
                      <span className="compare-id">{simResult.user_a?.id}</span>
                    </div>
                    {simResult.user_a?.decision?.allowed
                      ? <span className="verdict-badge verdict-allowed"><CheckCircle size={13} /> ALLOWED</span>
                      : <span className="verdict-badge verdict-denied"><XCircle size={13} /> DENIED</span>}
                  </div>
                  <div className="reason-code">
                    Reason Code: <code>{simResult.user_a?.decision?.reason_code}</code>
                  </div>
                  <div className="reason-text">{simResult.user_a?.decision?.reason}</div>
                  {simResult.user_a?.decision?.matched_grants?.length > 0 && (
                    <div className="grant-box">
                      <strong>Matched Grant:</strong>
                      <pre>{JSON.stringify(simResult.user_a.decision.matched_grants[0], null, 2)}</pre>
                    </div>
                  )}
                </div>

                {/* User B */}
                <div className={`compare-card glass-panel ${simResult.user_b?.decision?.allowed ? 'compare-allowed' : 'compare-denied'}`}>
                  <div className="compare-card-header">
                    <div>
                      <h3 className="compare-name">{simResult.user_b?.name}</h3>
                      <span className="compare-id">{simResult.user_b?.id}</span>
                    </div>
                    {simResult.user_b?.decision?.allowed
                      ? <span className="verdict-badge verdict-allowed"><CheckCircle size={13} /> ALLOWED</span>
                      : <span className="verdict-badge verdict-denied"><XCircle size={13} /> DENIED</span>}
                  </div>
                  <div className="reason-code">
                    Reason Code: <code>{simResult.user_b?.decision?.reason_code}</code>
                  </div>
                  <div className="reason-text">{simResult.user_b?.decision?.reason}</div>
                  {simResult.user_b?.decision?.missing_requirements?.length > 0 && (
                    <div className="missing-box">
                      <strong>Missing Requirements:</strong>
                      <div className="missing-text">{simResult.user_b.decision.missing_requirements.join(', ')}</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          TAB 4: HISTORICAL TIME MACHINE
         ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'history' && (
        <section className="animate-fade-in">
          <div className="glass-panel section-card">
            <h2 className="section-title">Point-in-Time Historical Investigation</h2>
            <p className="section-sub" style={{ marginBottom: '20px' }}>
              Answers <strong>"Who could have acted on this job on the 3rd?"</strong> — reconstructs historical permission state using validity windows.
            </p>

            <div className="sim-controls">
              <div className="form-group">
                <label className="form-label">JOB ID</label>
                <input type="text" value={tmJobId} onChange={(e) => setTmJobId(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">ACTION</label>
                <select value={tmAction} onChange={(e) => setTmAction(e.target.value)}>
                  {Object.entries(ACTION_LABELS).filter(([k]) => ['check_job','prepare_job','file_job','cancel_job'].includes(k)).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">HISTORICAL TIMESTAMP (ISO)</label>
                <input type="text" value={tmDate} onChange={(e) => setTmDate(e.target.value)} placeholder="2026-10-03T12:00:00Z" />
              </div>
            </div>

            <button onClick={runTimeMachine} className="btn btn-primary" style={{ padding: '10px 28px' }} disabled={loading}>
              <History size={17} /> Reconstruct Historical Eligibility
            </button>
          </div>

          {tmResult && (
            <div className="glass-panel-elevated animate-fade-in section-card">
              <div className="tm-header">
                <h3 className="tm-title">
                  Eligible Actors at {new Date(tmResult.target_timestamp).toLocaleString('en-IN')}
                  <span className="tm-count"> ({tmResult.eligible_user_count} found)</span>
                </h3>
                <span className="stage-badge stage-filed">Action: {actionLabel(tmResult.action)}</span>
              </div>

              <div className="tm-users">
                {tmResult.eligible_users?.map(u => (
                  <div key={u.user_id} className="tm-user-row glass-panel">
                    <div>
                      <div className="tm-user-name">{u.name} <span className="tm-user-id">({u.user_id})</span></div>
                      <div className="tm-user-email">{u.email} · {u.user_type}</div>
                    </div>
                    <div className="tm-reason">{u.reason}</div>
                  </div>
                ))}
              </div>

              {tmResult.historical_job_events?.length > 0 && (
                <>
                  <h4 className="tm-events-title">Actual Job Events Logged</h4>
                  <div className="glass-panel tm-events-box">
                    {tmResult.historical_job_events.map(ev => (
                      <div key={ev.id} className="tm-event-row">
                        <span>
                          <strong>{actionLabel(ev.action)}</strong> by <code>{ev.actor_id}</code>:{' '}
                          {ev.from_stage ? stageLabel(ev.from_stage) : 'Start'} → {stageLabel(ev.to_stage)}
                        </span>
                        <span className="tm-event-time">{new Date(ev.timestamp).toLocaleString('en-IN')}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          TAB 5: ADMIN & DELEGATIONS
         ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'admin' && (
        <section className="animate-fade-in">
          <div className="admin-top-grid">
            {/* Create Assignment */}
            <div className="glass-panel section-card">
              <h3 className="card-title">
                <Shield size={19} className="card-title-icon" /> Grant Scoped Role Assignment
              </h3>
              <p className="section-sub" style={{ marginBottom: '16px' }}>
                Test Anti-Self-Escalation: Try assigning to <code>usr_admin_raj</code> while logged in as Admin.
              </p>

              <form onSubmit={handleCreateAssignment} className="form-stack">
                <div className="form-group">
                  <label className="form-label">USER</label>
                  <select value={newAsgnUserId} onChange={(e) => setNewAsgnUserId(e.target.value)}>
                    {KEY_PERSONAS.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">ROLE</label>
                  <select value={newAsgnRole} onChange={(e) => setNewAsgnRole(e.target.value)}>
                    {['MAKER','CHECKER','FILER','SUPERVISOR','ADMIN'].map(r => <option key={r}>{r}</option>)}
                  </select>
                </div>
                <div className="two-col">
                  <div className="form-group">
                    <label className="form-label">CLIENT SCOPE</label>
                    <input type="text" value={newAsgnClient} onChange={(e) => setNewAsgnClient(e.target.value)} placeholder="* or client_03" />
                  </div>
                  <div className="form-group">
                    <label className="form-label">BRANCH SCOPE</label>
                    <input type="text" value={newAsgnBranch} onChange={(e) => setNewAsgnBranch(e.target.value)} placeholder="* or branch_mum" />
                  </div>
                </div>
                <button type="submit" className="btn btn-primary">
                  <PlusCircle size={15} /> Grant Assignment
                </button>
              </form>
            </div>

            {/* Active Delegations */}
            <div className="glass-panel section-card">
              <h3 className="card-title">
                <Clock size={19} className="card-title-icon card-title-icon-cyan" /> Active Out-of-Office Delegations
              </h3>
              <p className="section-sub" style={{ marginBottom: '16px' }}>
                Seamless absence coverage without password sharing.
              </p>

              <div className="delegation-list">
                {delegations.length === 0 && <div className="empty-sub">No active delegations.</div>}
                {delegations.map(dlg => (
                  <div key={dlg.id} className="delegation-card">
                    <div className="delegation-flow">
                      <span className="delegation-from">{dlg.delegator_id}</span>
                      <ArrowRight size={14} className="delegation-arrow" />
                      <span className="delegation-to">{dlg.delegate_id}</span>
                    </div>
                    <div className="delegation-reason">{dlg.reason}</div>
                    <div className="delegation-validity">
                      Valid until: {new Date(dlg.valid_until).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Role Assignments Table */}
          <div className="glass-panel section-card">
            <h3 className="card-title" style={{ marginBottom: '16px' }}>
              <Users size={19} className="card-title-icon" /> Current Role Grants
            </h3>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Assignment ID</th>
                    <th>User</th>
                    <th>Role</th>
                    <th>Client Scope</th>
                    <th>Branch Scope</th>
                    <th>Direction</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {assignments.slice(0, 20).map(asgn => (
                    <tr key={asgn.id} className="table-row">
                      <td className="td-mono">{asgn.id}</td>
                      <td className="td-bold">{asgn.user_id}</td>
                      <td><span className="stage-badge stage-filed">{asgn.role_id}</span></td>
                      <td>
                        {asgn.client_id === '*' ? <span className="scope-all">All Clients</span> : (
                          <><div className="td-name">{clientName(asgn.client_id)}</div><div className="td-id">{asgn.client_id}</div></>
                        )}
                      </td>
                      <td>
                        {asgn.branch_id === '*' ? <span className="scope-all">All Branches</span> : (
                          <><div className="td-name">{branchName(asgn.branch_id)}</div><div className="td-id">{asgn.branch_id}</div></>
                        )}
                      </td>
                      <td>{asgn.direction === '*' ? <span className="scope-all">Both</span> : asgn.direction}</td>
                      <td>{asgn.mode === '*' ? <span className="scope-all">All</span> : asgn.mode}</td>
                      <td><span className="stage-badge stage-checked">{asgn.status}</span></td>
                      <td>
                        {asgn.status === 'ACTIVE' && (
                          <button
                            onClick={async () => { await api.revokeAssignment(asgn.id); loadAdminData(); }}
                            className="btn btn-danger btn-sm"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* ════════════════════════════════════════════════════════════════════
          JOB DETAIL MODAL
         ════════════════════════════════════════════════════════════════════ */}
      {selectedJob && (
        <div className="modal-overlay" onClick={() => setSelectedJob(null)}>
          <div className="modal-box glass-panel-elevated animate-fade-in" onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="modal-header">
              <div>
                <div className="modal-title-row">
                  <h2 className="modal-title">{selectedJob.job_number}</h2>
                  <span className={`stage-badge stage-${selectedJob.stage.toLowerCase()}`}>
                    {stageLabel(selectedJob.stage)}
                  </span>
                </div>
                <div className="modal-subtitle">
                  {selectedJob.description || 'Customs Clearance Consignment'}
                  {selectedJob.customs_entry_number && <> · Entry: <code>{selectedJob.customs_entry_number}</code></>}
                </div>
              </div>
              <button onClick={() => setSelectedJob(null)} className="modal-close">✕</button>
            </div>

            {/* Scope Metadata */}
            <div className="scope-grid">
              <div className="scope-card glass-panel">
                <div className="scope-label">Client</div>
                <div className="scope-value">{clientName(selectedJob.client_id)}</div>
                <div className="scope-id">{selectedJob.client_id}</div>
              </div>
              <div className="scope-card glass-panel">
                <div className="scope-label">Branch</div>
                <div className="scope-value">{branchName(selectedJob.branch_id)}</div>
                <div className="scope-id">{selectedJob.branch_id}</div>
              </div>
              <div className="scope-card glass-panel">
                <div className="scope-label">Direction</div>
                <div className="scope-value">
                  {selectedJob.direction === 'IMPORT' ? '⬇ Import' : '⬆ Export'}
                </div>
              </div>
              <div className="scope-card glass-panel">
                <div className="scope-label">Mode</div>
                <div className="scope-value">{selectedJob.mode?.replace('_', ' ')}</div>
              </div>
            </div>

            {/* Action Eligibility */}
            <div className="modal-section">
              <h3 className="modal-section-title">
                Action Eligibility for <em>{activePersonaObj.name}</em>
              </h3>
              <div className="action-list">
                {Object.entries(availableActions).map(([action, evalInfo]) => (
                  <div
                    key={action}
                    className={`action-row ${evalInfo.allowed ? 'action-allowed' : 'action-denied'}`}
                  >
                    <div>
                      <div className="action-name">{actionLabel(action)}</div>
                      <div className="action-reason">{evalInfo.reason}</div>
                    </div>
                    {evalInfo.allowed ? (
                      <button
                        onClick={() => executeAction(selectedJob.id, action)}
                        className="btn btn-success btn-sm"
                      >
                        Execute
                      </button>
                    ) : (
                      <span className="stage-badge stage-cancelled">
                        {evalInfo.reason_code}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Chronological Audit Timeline */}
            <div className="modal-section">
              <h3 className="modal-section-title">
                Audit Timeline <span className="timeline-count">({jobTimeline.length} events)</span>
              </h3>
              <div className="timeline">
                {jobTimeline.map((ev, idx) => (
                  <div key={ev.id || idx} className="timeline-item">
                    <div className="timeline-dot" />
                    <div className="timeline-content">
                      <div className="timeline-row">
                        <span className="timeline-action">{actionLabel(ev.action)}</span>
                        <span className="timeline-time">{new Date(ev.timestamp).toLocaleString('en-IN')}</span>
                      </div>
                      <div className="timeline-actor">
                        By <strong>{ev.actor?.name}</strong>
                        <span className="timeline-actor-id"> ({ev.actor?.id})</span>
                        {ev.from_stage && <> · {stageLabel(ev.from_stage)} → <strong>{stageLabel(ev.to_stage)}</strong></>}
                      </div>
                      {ev.reason && <div className="timeline-note">"{ev.reason}"</div>}
                    </div>
                  </div>
                ))}
                {jobTimeline.length === 0 && <div className="empty-sub">No events recorded yet.</div>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
