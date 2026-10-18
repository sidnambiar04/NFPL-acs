import React, { useState, useEffect } from 'react';
import { 
  Shield, CheckCircle, XCircle, Clock, AlertTriangle, ArrowRight, 
  User, RefreshCw, Eye, GitCompare, History, PlusCircle, Lock, 
  Building2, Plane, Ship, Search, ChevronRight, FileCheck, Info
} from 'lucide-react';
import { api, getCurrentUser, setCurrentUser } from './services/api';

const KEY_PERSONAS = [
  { id: 'usr_asha', name: 'Asha Sharma', role: 'Maker Broad / Checker Few', desc: 'Maker everywhere; Checker for Sun Pharma & Dr. Reddy\'s' },
  { id: 'usr_ravi', name: 'Ravi Kumar', role: 'Restricted Checker', desc: 'Checker for Sun Pharma, Mumbai branch, Imports only' },
  { id: 'usr_vikram', name: 'Vikram Seth (ABSENT)', role: 'Delhi Supervisor', desc: 'Currently on leave; delegated to Priya' },
  { id: 'usr_priya', name: 'Priya Nair', role: 'Maker + Active Delegate', desc: 'Maker at Mumbai + inherits Vikram\'s Delhi Supervisor authority' },
  { id: 'usr_client_sun', name: 'Sameer Mehta', role: 'Client Portal User', desc: 'Sun Pharma employee; read-only to Sun Pharma jobs' },
  { id: 'usr_admin_raj', name: 'Rajesh Patel', role: 'System Administrator', desc: 'Full administrative authority (subject to anti-self-escalation)' },
  { id: 'usr_parser_svc', name: 'Overnight EDI Parser', role: 'Service Account', desc: 'Machine identity for manifest ingestion' }
];

export default function App() {
  const [activeUser, setActiveUser] = useState(getCurrentUser());
  const [activeTab, setActiveTab] = useState('queue'); // 'queue', 'jobs', 'simulator', 'history', 'admin'
  const [workQueue, setWorkQueue] = useState([]);
  const [queueCount, setQueueCount] = useState(0);
  const [jobsList, setJobsList] = useState([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', title, message, details }

  // Filters for jobs list
  const [stageFilter, setStageFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Job for Detail Modal
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobTimeline, setJobTimeline] = useState([]);
  const [availableActions, setAvailableActions] = useState({});

  // Simulator State (Question 10)
  const [simMode, setSimMode] = useState('compare'); // 'single' or 'compare'
  const [simUserA, setSimUserA] = useState('usr_ravi');
  const [simUserB, setSimUserB] = useState('usr_asha');
  const [simJobId, setSimJobId] = useState('job_101');
  const [simAction, setSimAction] = useState('check_job');
  const [simResult, setSimResult] = useState(null);

  // Time Machine State (Question 11)
  const [tmJobId, setTmJobId] = useState('job_101');
  const [tmAction, setTmAction] = useState('check_job');
  const [tmDate, setTmDate] = useState('2026-10-03T12:00:00Z');
  const [tmResult, setTmResult] = useState(null);

  // Admin State
  const [assignments, setAssignments] = useState([]);
  const [delegations, setDelegations] = useState([]);
  const [newAsgnUserId, setNewAsgnUserId] = useState('usr_ravi');
  const [newAsgnRole, setNewAsgnRole] = useState('SUPERVISOR');
  const [newAsgnClient, setNewAsgnClient] = useState('*');
  const [newAsgnBranch, setNewAsgnBranch] = useState('*');

  // Load initial data
  useEffect(() => {
    loadQueue();
    loadJobs();
  }, [activeUser]);

  const handleUserChange = (newUid) => {
    setCurrentUser(newUid);
    setActiveUser(newUid);
    setFeedback({
      type: 'info',
      title: 'Switched Active Persona',
      message: `Active identity switched to: ${KEY_PERSONAS.find(p => p.id === newUid)?.name || newUid}`
    });
  };

  const loadQueue = async () => {
    try {
      setLoading(true);
      const res = await api.getWorkQueue();
      setWorkQueue(res.jobs || []);
      setQueueCount(res.total_waiting || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadJobs = async () => {
    try {
      const res = await api.getJobs({ stage: stageFilter, search: searchQuery });
      setJobsList(res.items || []);
      setTotalJobs(res.total || 0);
    } catch (err) {
      console.error(err);
    }
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
    } catch (err) {
      console.error(err);
    }
  };

  const executeAction = async (jobId, action, defaultReason = '') => {
    let reason = defaultReason;
    if (['cancel_job', 'reopen_job'].includes(action)) {
      reason = window.prompt(`Enter mandatory justification reason for ${action}:`, 'Administrative request');
      if (!reason) return;
    }

    try {
      setLoading(true);
      if (action === 'prepare_job') await api.prepareJob(jobId, reason);
      else if (action === 'check_job') await api.checkJob(jobId, reason);
      else if (action === 'file_job') await api.fileJob(jobId, reason);
      else if (action === 'cancel_job') await api.cancelJob(jobId, reason);
      else if (action === 'reopen_job') await api.reopenJob(jobId, reason);

      setFeedback({
        type: 'success',
        title: 'Action Executed Successfully',
        message: `Action '${action}' succeeded on Job ${jobId}. State updated.`
      });

      // Refresh data
      loadQueue();
      loadJobs();
      if (selectedJob && selectedJob.id === jobId) {
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
    } finally {
      setLoading(false);
    }
  };

  // Run Simulator / Compare
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
    } catch (err) {
      setFeedback({ type: 'error', title: 'Simulation Error', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  // Run Time Machine
  const runTimeMachine = async () => {
    try {
      setLoading(true);
      const res = await api.whoCouldAct(tmJobId, tmAction, tmDate);
      setTmResult(res);
    } catch (err) {
      setFeedback({ type: 'error', title: 'Query Error', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  // Admin: Create Assignment
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
      setFeedback({
        type: 'success',
        title: 'Assignment Granted',
        message: `Role ${newAsgnRole} successfully assigned to ${newAsgnUserId}`
      });
      loadAdminData();
    } catch (err) {
      setFeedback({
        type: 'error',
        title: `Grant Failed: ${err.detail?.reason_code || 'DENIED'}`,
        message: err.message
      });
    }
  };

  const loadAdminData = async () => {
    try {
      const [asgns, dlgs] = await Promise.all([
        api.getAssignments(),
        api.getDelegations()
      ]);
      setAssignments(asgns || []);
      setDelegations(dlgs || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (activeTab === 'admin') loadAdminData();
  }, [activeTab]);

  const activePersonaObj = KEY_PERSONAS.find(p => p.id === activeUser) || { name: activeUser, role: 'Custom' };

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '24px 20px' }}>
      {/* Top Header */}
      <header className="glass-panel" style={{ padding: '18px 24px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: 'linear-gradient(135deg, #6366f1, #06b6d4)', padding: '10px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Shield size={28} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.35rem', fontWeight: 800, letterSpacing: '-0.02em' }}>NFPL Access Control Service</h1>
              <span className="badge badge-filed" style={{ fontSize: '0.7rem' }}>Policy v2026.1</span>
            </div>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>Nagarkot Forwarders Pvt. Ltd. · Customs Brokerage Authorization Engine</p>
          </div>
        </div>

        {/* Persona Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Simulated Persona</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#38bdf8' }}>{activePersonaObj.name}</div>
          </div>
          <select 
            value={activeUser} 
            onChange={(e) => handleUserChange(e.target.value)}
            style={{ fontWeight: 600, padding: '10px 14px', borderRadius: '10px', border: '1px solid #6366f1' }}
          >
            {KEY_PERSONAS.map(p => (
              <option key={p.id} value={p.id}>{p.name} — ({p.role})</option>
            ))}
          </select>
        </div>
      </header>

      {/* Persona Description Banner */}
      <div className="glass-panel" style={{ padding: '12px 20px', marginBottom: '24px', borderLeft: '4px solid #38bdf8', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.875rem' }}>
          <Info size={18} color="#38bdf8" />
          <span><strong>Active Scope Context:</strong> {activePersonaObj.desc}</span>
        </div>
        <span className="badge badge-confirmed" style={{ fontSize: '0.72rem' }}>Identity: {activeUser}</span>
      </div>

      {/* Global Feedback Banner */}
      {feedback && (
        <div className="animate-fade-in" style={{
          padding: '16px 20px',
          borderRadius: '12px',
          marginBottom: '24px',
          background: feedback.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : feedback.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
          border: `1px solid ${feedback.type === 'error' ? '#ef4444' : feedback.type === 'success' ? '#10b981' : '#38bdf8'}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start'
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              {feedback.type === 'error' ? <XCircle size={18} color="#ef4444" /> : <CheckCircle size={18} color="#10b981" />}
              {feedback.title}
            </div>
            <div style={{ fontSize: '0.875rem', marginTop: '4px', color: 'var(--text-secondary)' }}>{feedback.message}</div>
            {feedback.details?.reason && (
              <div style={{ marginTop: '8px', padding: '8px 12px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#f87171' }}>
                Reason: {feedback.details.reason}
              </div>
            )}
          </div>
          <button onClick={() => setFeedback(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.1rem' }}>✕</button>
        </div>
      )}

      {/* Navigation Tabs */}
      <nav style={{ display: 'flex', gap: '10px', marginBottom: '24px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px', flexWrap: 'wrap' }}>
        {[
          { id: 'queue', label: 'Work Queue ("Jobs Waiting For Me")', count: queueCount, icon: Clock },
          { id: 'jobs', label: 'All Shipments Explorer', count: totalJobs, icon: Building2 },
          { id: 'simulator', label: 'Access Simulator & "Why She Can / He Can\'t"', icon: GitCompare },
          { id: 'history', label: 'Historical Investigation ("Who Could Act on 3rd?")', icon: History },
          { id: 'admin', label: 'Admin, Scoped Grants & Delegations', icon: Shield }
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="btn"
              style={{
                background: isActive ? 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(6,182,212,0.15))' : 'transparent',
                borderColor: isActive ? 'var(--accent-primary)' : 'transparent',
                color: isActive ? '#ffffff' : 'var(--text-secondary)'
              }}
            >
              <Icon size={18} color={isActive ? '#38bdf8' : 'currentColor'} />
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span style={{
                  background: isActive ? '#6366f1' : 'rgba(255,255,255,0.08)',
                  color: '#ffffff',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  fontSize: '0.72rem',
                  fontWeight: 700
                }}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* TAB 1: WORK QUEUE */}
      {activeTab === 'queue' && (
        <section className="animate-fade-in">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Jobs Needing Your Action</h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Guaranteed zero-drift: Every job below matches your current active roles and passes all separation-of-duties rules.
              </p>
            </div>
            <button onClick={loadQueue} className="btn btn-secondary"><RefreshCw size={16} /> Refresh Queue</button>
          </div>

          {workQueue.length === 0 ? (
            <div className="glass-panel" style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <CheckCircle size={48} color="#10b981" style={{ margin: '0 auto 16px' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>All Clear! No jobs waiting for you right now.</h3>
              <p style={{ fontSize: '0.875rem', marginTop: '6px' }}>
                You have no pending tasks matching your current scoped permissions ({activeUser}). Try switching personas above!
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '18px' }}>
              {workQueue.map(item => (
                <div key={item.id} className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <span className={`badge badge-${item.stage.toLowerCase()}`}>{item.stage}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>

                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px' }}>{item.job_number}</h3>
                    <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '14px' }}>
                      <div>Client: <strong style={{ color: 'var(--text-primary)' }}>{item.client_id}</strong></div>
                      <div>Branch: <strong style={{ color: 'var(--text-primary)' }}>{item.branch_id}</strong></div>
                      <div>Direction: <strong style={{ color: 'var(--text-primary)' }}>{item.direction}</strong></div>
                      <div>Mode: <strong style={{ color: 'var(--text-primary)' }}>{item.mode}</strong></div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '10px 12px', borderRadius: '8px', fontSize: '0.8rem', borderLeft: '3px solid #10b981', marginBottom: '16px' }}>
                      <div style={{ fontWeight: 600, color: '#34d399' }}>Eligible Action: {item.required_action}</div>
                      <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>{item.action_explanation}</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      onClick={() => executeAction(item.id, item.required_action)}
                      className="btn btn-primary"
                      style={{ flex: 1 }}
                    >
                      <FileCheck size={16} /> Execute {item.required_action.replace('_job', '')}
                    </button>
                    <button 
                      onClick={() => openJobModal(item)}
                      className="btn btn-secondary"
                    >
                      <Eye size={16} /> Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* TAB 2: ALL SHIPMENTS EXPLORER */}
      {activeTab === 'jobs' && (
        <section className="animate-fade-in">
          <div className="glass-panel" style={{ padding: '18px 20px', marginBottom: '20px', display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '240px' }}>
              <Search size={18} color="var(--text-muted)" />
              <input 
                type="text" 
                placeholder="Search job number or description..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>
            <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)}>
              <option value="">All Stages</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="PREPARED">PREPARED</option>
              <option value="CHECKED">CHECKED</option>
              <option value="FILED">FILED</option>
              <option value="CANCELLED">CANCELLED</option>
              <option value="REOPENED">REOPENED</option>
            </select>
            <button onClick={loadJobs} className="btn btn-primary">Filter</button>
          </div>

          <div className="glass-panel" style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '14px 18px' }}>Job Number</th>
                  <th style={{ padding: '14px 18px' }}>Stage</th>
                  <th style={{ padding: '14px 18px' }}>Client</th>
                  <th style={{ padding: '14px 18px' }}>Branch</th>
                  <th style={{ padding: '14px 18px' }}>Direction / Mode</th>
                  <th style={{ padding: '14px 18px' }}>Preparer / Checker</th>
                  <th style={{ padding: '14px 18px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {jobsList.map(job => (
                  <tr key={job.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '14px 18px', fontWeight: 700 }}>{job.job_number}</td>
                    <td style={{ padding: '14px 18px' }}>
                      <span className={`badge badge-${job.stage.toLowerCase()}`}>{job.stage}</span>
                    </td>
                    <td style={{ padding: '14px 18px' }}>{job.client_id}</td>
                    <td style={{ padding: '14px 18px' }}>{job.branch_id}</td>
                    <td style={{ padding: '14px 18px' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{job.direction} · {job.mode}</span>
                    </td>
                    <td style={{ padding: '14px 18px', fontSize: '0.8rem' }}>
                      <div>Prep: <strong>{job.preparer_id || '—'}</strong></div>
                      <div>Chk: <strong>{job.checker_id || '—'}</strong></div>
                    </td>
                    <td style={{ padding: '14px 18px' }}>
                      <button onClick={() => openJobModal(job)} className="btn btn-secondary" style={{ padding: '6px 12px' }}>
                        Inspect <ChevronRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* TAB 3: ACCESS SIMULATOR (QUESTION 10) */}
      {activeTab === 'simulator' && (
        <section className="animate-fade-in">
          <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '6px' }}>Access Simulator & Decision Differential</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Directly answers <strong>Question 10 ("Why can she do this and he can't?")</strong> by comparing two identities against the same job and action.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>USER A</label>
                <select value={simUserA} onChange={(e) => setSimUserA(e.target.value)} style={{ width: '100%' }}>
                  {KEY_PERSONAS.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>USER B</label>
                <select value={simUserB} onChange={(e) => setSimUserB(e.target.value)} style={{ width: '100%' }}>
                  {KEY_PERSONAS.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>TARGET JOB</label>
                <select value={simJobId} onChange={(e) => setSimJobId(e.target.value)} style={{ width: '100%' }}>
                  <option value="job_101">job_101 (Sun Pharma · Mumbai Import · Prep by Asha)</option>
                  <option value="job_102">job_102 (Tata Motors · Mumbai Export · Confirmed)</option>
                  <option value="job_104">job_104 (Infosys · Delhi · FILED)</option>
                  <option value="job_105">job_105 (Reliance · Delhi · Prep by Pooja)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>LIFECYCLE ACTION</label>
                <select value={simAction} onChange={(e) => setSimAction(e.target.value)} style={{ width: '100%' }}>
                  <option value="check_job">check_job</option>
                  <option value="prepare_job">prepare_job</option>
                  <option value="file_job">file_job</option>
                  <option value="cancel_job">cancel_job</option>
                  <option value="reopen_job">reopen_job</option>
                </select>
              </div>
            </div>

            <button onClick={runSimulator} className="btn btn-primary" style={{ padding: '10px 24px' }}>
              <GitCompare size={18} /> Compare Access Decisions
            </button>
          </div>

          {/* Simulation Output Card */}
          {simResult && (
            <div className="glass-panel-elevated animate-fade-in" style={{ padding: '24px' }}>
              {simResult.comparison_summary && (
                <div style={{ background: 'rgba(99, 102, 241, 0.15)', borderLeft: '4px solid #6366f1', padding: '14px 18px', borderRadius: '8px', marginBottom: '24px' }}>
                  <div style={{ fontWeight: 700, color: '#818cf8', marginBottom: '4px' }}>DIVERGENCE ROOT CAUSE SUMMARY</div>
                  <div style={{ fontSize: '0.95rem' }}>{simResult.comparison_summary}</div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                {/* User A Card */}
                <div className="glass-panel" style={{ padding: '18px', borderColor: simResult.user_a.decision.allowed ? '#10b981' : '#ef4444' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{simResult.user_a.name}</h3>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID: {simResult.user_a.id}</span>
                    </div>
                    {simResult.user_a.decision.allowed ? (
                      <span className="badge badge-checked"><CheckCircle size={14} /> ALLOWED</span>
                    ) : (
                      <span className="badge badge-cancelled"><XCircle size={14} /> DENIED</span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.85rem', marginBottom: '10px' }}>
                    <strong>Reason Code:</strong> <span style={{ fontFamily: 'var(--font-mono)', color: '#fbbf24' }}>{simResult.user_a.decision.reason_code}</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                    {simResult.user_a.decision.reason}
                  </div>
                  {simResult.user_a.decision.matched_grants?.length > 0 && (
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.75rem' }}>
                      <strong style={{ color: '#34d399' }}>Matched Role Grant:</strong>
                      <pre style={{ marginTop: '4px' }}>{JSON.stringify(simResult.user_a.decision.matched_grants[0], null, 2)}</pre>
                    </div>
                  )}
                </div>

                {/* User B Card */}
                <div className="glass-panel" style={{ padding: '18px', borderColor: simResult.user_b.decision.allowed ? '#10b981' : '#ef4444' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{simResult.user_b.name}</h3>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID: {simResult.user_b.id}</span>
                    </div>
                    {simResult.user_b.decision.allowed ? (
                      <span className="badge badge-checked"><CheckCircle size={14} /> ALLOWED</span>
                    ) : (
                      <span className="badge badge-cancelled"><XCircle size={14} /> DENIED</span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.85rem', marginBottom: '10px' }}>
                    <strong>Reason Code:</strong> <span style={{ fontFamily: 'var(--font-mono)', color: '#fbbf24' }}>{simResult.user_b.decision.reason_code}</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                    {simResult.user_b.decision.reason}
                  </div>
                  {simResult.user_b.decision.missing_requirements?.length > 0 && (
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.75rem' }}>
                      <strong style={{ color: '#f87171' }}>Missing Invariants:</strong>
                      <div style={{ marginTop: '4px', fontFamily: 'var(--font-mono)' }}>{simResult.user_b.decision.missing_requirements.join(', ')}</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* TAB 4: HISTORICAL TIME MACHINE (QUESTION 11) */}
      {activeTab === 'history' && (
        <section className="animate-fade-in">
          <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '6px' }}>Point-in-Time Historical Investigation</h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Directly answers <strong>Question 11 ("Who could have changed this job on the 3rd?")</strong> by querying historical validity windows.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>JOB ID</label>
                <input type="text" value={tmJobId} onChange={(e) => setTmJobId(e.target.value)} style={{ width: '100%' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>ACTION IN QUESTION</label>
                <select value={tmAction} onChange={(e) => setTmAction(e.target.value)} style={{ width: '100%' }}>
                  <option value="check_job">check_job</option>
                  <option value="prepare_job">prepare_job</option>
                  <option value="file_job">file_job</option>
                  <option value="cancel_job">cancel_job</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>HISTORICAL TIMESTAMP (ISO)</label>
                <input type="text" value={tmDate} onChange={(e) => setTmDate(e.target.value)} style={{ width: '100%' }} />
              </div>
            </div>

            <button onClick={runTimeMachine} className="btn btn-primary" style={{ padding: '10px 24px' }}>
              <History size={18} /> Reconstruct Historical Eligibility
            </button>
          </div>

          {tmResult && (
            <div className="glass-panel-elevated animate-fade-in" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  Eligible Actors at {new Date(tmResult.target_timestamp).toLocaleString()} ({tmResult.eligible_user_count} Found)
                </h3>
                <span className="badge badge-filed">Action: {tmResult.action}</span>
              </div>

              <div style={{ display: 'grid', gap: '12px', marginBottom: '24px' }}>
                {tmResult.eligible_users.map(u => (
                  <div key={u.user_id} className="glass-panel" style={{ padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 700 }}>{u.name} ({u.user_id})</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{u.email} · {u.user_type}</div>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#34d399', maxWidth: '400px', textAlign: 'right' }}>
                      {u.reason}
                    </div>
                  </div>
                ))}
              </div>

              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '10px', color: 'var(--text-muted)' }}>Actual Job Events Logged</h4>
              <div className="glass-panel" style={{ padding: '14px' }}>
                {tmResult.historical_job_events.map(ev => (
                  <div key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.825rem' }}>
                    <span><strong>{ev.action}</strong> by <code>{ev.actor_id}</code>: {ev.from_stage || 'START'} → {ev.to_stage}</span>
                    <span style={{ color: 'var(--text-muted)' }}>{new Date(ev.timestamp).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* TAB 5: ADMIN & DELEGATIONS */}
      {activeTab === 'admin' && (
        <section className="animate-fade-in">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
            {/* Create Scoped Assignment */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={20} color="#6366f1" /> Grant Scoped Role Assignment
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Test Anti-Self-Escalation: Try assigning to <code>usr_admin_raj</code> while logged in as Admin to see policy block!
              </p>

              <form onSubmit={handleCreateAssignment} style={{ display: 'grid', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>USER</label>
                  <select value={newAsgnUserId} onChange={(e) => setNewAsgnUserId(e.target.value)} style={{ width: '100%' }}>
                    {KEY_PERSONAS.map(p => <option key={p.id} value={p.id}>{p.name} ({p.id})</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>ROLE</label>
                  <select value={newAsgnRole} onChange={(e) => setNewAsgnRole(e.target.value)} style={{ width: '100%' }}>
                    <option value="MAKER">MAKER</option>
                    <option value="CHECKER">CHECKER</option>
                    <option value="FILER">FILER</option>
                    <option value="SUPERVISOR">SUPERVISOR</option>
                    <option value="ADMIN">ADMIN</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>CLIENT SCOPE</label>
                    <input type="text" value={newAsgnClient} onChange={(e) => setNewAsgnClient(e.target.value)} placeholder="* or client_03" style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>BRANCH SCOPE</label>
                    <input type="text" value={newAsgnBranch} onChange={(e) => setNewAsgnBranch(e.target.value)} placeholder="* or branch_bom" style={{ width: '100%' }} />
                  </div>
                </div>
                <button type="submit" className="btn btn-primary" style={{ marginTop: '6px' }}>
                  <PlusCircle size={16} /> Grant Assignment
                </button>
              </form>
            </div>

            {/* Active Delegations */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={20} color="#38bdf8" /> Active Out-of-Office Delegations
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Seamless absence coverage without password sharing.
              </p>

              <div style={{ display: 'grid', gap: '10px' }}>
                {delegations.map(dlg => (
                  <div key={dlg.id} style={{ background: 'rgba(0,0,0,0.25)', padding: '12px 16px', borderRadius: '8px', borderLeft: '3px solid #38bdf8' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                      {dlg.delegator_id} → {dlg.delegate_id}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Reason: {dlg.reason}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Valid Until: {new Date(dlg.valid_until).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Active Assignments List */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '14px' }}>Current Role Grants</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: '0.825rem', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                    <th style={{ padding: '10px' }}>ID</th>
                    <th style={{ padding: '10px' }}>User</th>
                    <th style={{ padding: '10px' }}>Role</th>
                    <th style={{ padding: '10px' }}>Client</th>
                    <th style={{ padding: '10px' }}>Branch</th>
                    <th style={{ padding: '10px' }}>Direction</th>
                    <th style={{ padding: '10px' }}>Mode</th>
                    <th style={{ padding: '10px' }}>Status</th>
                    <th style={{ padding: '10px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {assignments.slice(0, 15).map(asgn => (
                    <tr key={asgn.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <td style={{ padding: '10px', fontFamily: 'var(--font-mono)' }}>{asgn.id}</td>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{asgn.user_id}</td>
                      <td style={{ padding: '10px' }}><span className="badge badge-filed">{asgn.role_id}</span></td>
                      <td style={{ padding: '10px' }}>{asgn.client_id}</td>
                      <td style={{ padding: '10px' }}>{asgn.branch_id}</td>
                      <td style={{ padding: '10px' }}>{asgn.direction}</td>
                      <td style={{ padding: '10px' }}>{asgn.mode}</td>
                      <td style={{ padding: '10px' }}><span className="badge badge-checked">{asgn.status}</span></td>
                      <td style={{ padding: '10px' }}>
                        {asgn.status === 'ACTIVE' && (
                          <button 
                            onClick={async () => {
                              await api.revokeAssignment(asgn.id);
                              loadAdminData();
                            }}
                            className="btn btn-danger" 
                            style={{ padding: '4px 8px', fontSize: '0.72rem' }}
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

      {/* JOB DETAILS & AUDIT TIMELINE MODAL */}
      {selectedJob && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="glass-panel-elevated animate-fade-in" style={{ width: '100%', maxWidth: '820px', maxHeight: '90vh', overflowY: 'auto', padding: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{selectedJob.job_number}</h2>
                  <span className={`badge badge-${selectedJob.stage.toLowerCase()}`}>{selectedJob.stage}</span>
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {selectedJob.description || 'Customs Clearance Consignment'} · Customs Entry: {selectedJob.customs_entry_number || 'N/A'}
                </div>
              </div>
              <button onClick={() => setSelectedJob(null)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.4rem' }}>✕</button>
            </div>

            {/* Scope Metadata Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
              <div className="glass-panel" style={{ padding: '12px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Client</div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{selectedJob.client_id}</div>
              </div>
              <div className="glass-panel" style={{ padding: '12px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Branch</div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{selectedJob.branch_id}</div>
              </div>
              <div className="glass-panel" style={{ padding: '12px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Direction</div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{selectedJob.direction}</div>
              </div>
              <div className="glass-panel" style={{ padding: '12px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Mode</div>
                <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{selectedJob.mode}</div>
              </div>
            </div>

            {/* Contextual Action Matrix for Active Persona */}
            <div style={{ marginBottom: '28px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-primary)' }}>
                Action Eligibility for Active Persona ({activeUser})
              </h3>
              <div style={{ display: 'grid', gap: '8px' }}>
                {Object.entries(availableActions).map(([action, evalInfo]) => (
                  <div key={action} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 14px', borderRadius: '8px',
                    background: evalInfo.allowed ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.08)',
                    border: `1px solid ${evalInfo.allowed ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.2)'}`
                  }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{action}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{evalInfo.reason}</div>
                    </div>
                    {evalInfo.allowed ? (
                      <button 
                        onClick={() => executeAction(selectedJob.id, action)}
                        className="btn btn-success" 
                        style={{ padding: '6px 14px', fontSize: '0.78rem' }}
                      >
                        Execute
                      </button>
                    ) : (
                      <span className="badge badge-cancelled" style={{ fontSize: '0.7rem' }}>Blocked: {evalInfo.reason_code}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Chronological Audit Timeline */}
            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-muted)' }}>
                Chronological Job Event History ({jobTimeline.length} entries)
              </h3>
              <div style={{ borderLeft: '2px solid var(--border-subtle)', marginLeft: '12px', paddingLeft: '20px', display: 'grid', gap: '16px' }}>
                {jobTimeline.map((ev, idx) => (
                  <div key={ev.id || idx} style={{ position: 'relative' }}>
                    <div style={{
                      position: 'absolute', left: '-27px', top: '2px', width: '12px', height: '12px',
                      borderRadius: '50%', background: '#6366f1', border: '2px solid #090d16'
                    }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.875rem' }}>{ev.action}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(ev.timestamp).toLocaleString()}</span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Actor: <strong>{ev.actor.name}</strong> ({ev.actor.id}) · Stage: {ev.from_stage || 'START'} → <strong>{ev.to_stage}</strong>
                    </div>
                    {ev.reason && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '2px' }}>
                        "{ev.reason}"
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
