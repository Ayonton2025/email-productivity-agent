import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import ContactSalesForm from './ContactSalesForm';
import {
  ArrowRight, Check, Zap, Mail, BarChart3, Workflow, Users,
  Github, Linkedin, Twitter, ChevronDown, Play, Shield, Unlock,
  Smartphone, MessageSquare, PlayCircle, TrendingUp
} from 'lucide-react';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [showContactForm, setShowContactForm] = useState(false);
  const [scrollY, setScrollY] = useState(0);
  const canvasRef = useRef(null);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationId;

    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    let time = 0;
    const drawAnimation = () => {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.03)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.strokeStyle = 'rgba(99, 102, 241, 0.2)';
      ctx.lineWidth = 1;

      for (let i = 0; i < 5; i++) {
        const x = (Math.sin(time * 0.001 + i) * 100 + canvas.width / 2) + scrollY * 0.1;
        const y = (Math.cos(time * 0.0008 + i) * 100 + canvas.height / 2);

        ctx.beginPath();
        ctx.arc(x, y, (i === 0 ? 50 : 30) + Math.sin(time * (i === 0 ? 0.002 : 0.003) + i) * (i === 0 ? 20 : 15), 0, Math.PI * 2);
        ctx.stroke();
      }

      time += 1;
      animationId = requestAnimationFrame(drawAnimation);
    };

    drawAnimation();
    return () => cancelAnimationFrame(animationId);
  }, [scrollY]);

  const plans = [
    {
      id: 'personal',
      name: 'Free',
      price: 'Free',
      period: '',
      kes: 'KES 0',
      description: 'For individual professionals starting with structured email.',
      features: [
        '1 Email Account',
        'Intelligent Prioritization',
        '50 AI Credits/Day',
        'Basic Workflow Rules',
        'Email Intelligence Dashboard (Lite)',
        'Community Support'
      ],
      cta: isAuthenticated ? 'Get Started' : 'Start Smarter Email',
      highlighted: false
    },
    {
      id: 'plus',
      name: 'Plus',
      price: '$12',
      period: 'per month',
      kes: 'KES 1,800',
      description: 'For high-volume operators who need execution from email.',
      features: [
        'Up to 3 Email Accounts',
        'Context-Aware AI Composition',
        '1,500 AI Credits/Month',
        'Operational Workflow Triggers',
        'Contact Intelligence Signals',
        'Priority Support',
        'Structured Reply Templates',
        'Response-Time Analytics'
      ],
      cta: 'Start Smarter Email',
      highlighted: true
    },
    {
      id: 'professional',
      name: 'Professional',
      price: '$29',
      period: 'per month',
      kes: 'KES 4,350',
      description: 'For teams orchestrating communication at scale.',
      features: [
        'Unlimited Email Accounts',
        'Advanced Workflow Orchestration',
        '5,000 AI Credits/Month',
        'Cross-Thread Intelligence',
        'Opportunity and Risk Tracking',
        'Advanced Analytics and Reporting',
        'API Access',
        'Dedicated Support'
      ],
      cta: 'Start Smarter Email',
      highlighted: false
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 'Custom',
      period: 'contact sales',
      kes: 'KES equivalent',
      description: 'For organizations making email part of core operations.',
      features: [
        'Unlimited Everything',
        'Team + Role Governance',
        'Custom Integrations',
        'Executive Intelligence Reporting',
        'SLA and Security Controls',
        'Dedicated Account Management',
        'Implementation Support',
        'Custom Enablement'
      ],
      cta: 'Request Early Access',
      highlighted: false
    }
  ];

  const handleSignIn = () => navigate('/login');
  const handleGetStarted = () => navigate('/register?mode=standard');
  const handleGetBylixEmail = () => navigate('/register?mode=hosted');

  const handleStartFreeTrial = (planId = 'plus') => {
    if (isAuthenticated) {
      navigate(`/billing/upgrade?plan=${planId}`);
    } else {
      navigate('/register');
    }
  };

  const handleContactSales = () => setShowContactForm(true);
  const handleDashboard = () => navigate('/');

  return (
    <div className="landing-page">
      <canvas ref={canvasRef} className="bg-canvas"></canvas>

      <header className="landing-header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">✉️</div>
            <div className="logo-text">Bylix Email</div>
          </div>
          <nav className="nav-links">
            <button onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}>Features</button>
            <button onClick={() => document.getElementById('pricing').scrollIntoView({ behavior: 'smooth' })}>Pricing</button>
            <button onClick={() => document.getElementById('demo').scrollIntoView({ behavior: 'smooth' })}>Demo</button>
          </nav>
          <div className="header-actions">
            {isAuthenticated ? (
              <button className="btn btn-primary" onClick={handleDashboard}>Dashboard</button>
            ) : (
              <>
                <button className="btn btn-outline" onClick={handleSignIn}>Sign In</button>
                <button className="btn btn-primary" onClick={handleGetStarted}>Start Smarter Email</button>
              </>
            )}
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="hero-content">
          <div className="hero-badge">
            <Zap size={16} />
            <span>Email Intelligence Platform (EIP)</span>
          </div>
          <h1 className="hero-title">The Intelligence Layer for Email.</h1>
          <p className="hero-subtitle">
            Bylix Email transforms your inbox into an intelligent, structured, and automated operational system.
            This is not another inbox UI. This is communication that executes.
          </p>
          <div className="hero-cta">
            <button className="btn btn-primary btn-lg" onClick={() => handleStartFreeTrial('plus')}>
              Start Smarter Email <ArrowRight size={20} />
            </button>
            <button className="btn btn-outline btn-lg" onClick={handleGetBylixEmail}>
              <Mail size={20} /> Get Free Bylix Email
            </button>
            <button className="btn btn-outline btn-lg" onClick={() => document.getElementById('demo').scrollIntoView({ behavior: 'smooth' })}>
              <Play size={20} /> Watch Demo
            </button>
          </div>
          <div className="hero-stats">
            <div className="stat">
              <div className="stat-value">10K+</div>
              <div className="stat-label">Active Users</div>
            </div>
            <div className="stat">
              <div className="stat-value">500M+</div>
              <div className="stat-label">Emails Processed</div>
            </div>
            <div className="stat">
              <div className="stat-value">99.9%</div>
              <div className="stat-label">Uptime SLA</div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="features-section">
        <div className="section-header">
          <h2>Where Communication Becomes Execution</h2>
          <p>Email was built for messaging. Bylix Email rebuilds it for operational clarity and action.</p>
        </div>

        <div className="features-grid">
          <div className="feature-card" style={{ transform: `translateY(${scrollY * 0.05}px)` }}>
            <div className="feature-icon"><Zap size={32} /></div>
            <h3>Intelligent Prioritization</h3>
            <p>Detect urgency, identify high-value contacts, flag deadlines, and sort by impact instead of chronology.</p>
          </div>

          <div className="feature-card" style={{ transform: `translateY(${scrollY * 0.08}px)` }}>
            <div className="feature-icon"><MessageSquare size={32} /></div>
            <h3>Context-Aware AI Composition</h3>
            <p>Draft replies that mirror your tone, reference history, and adapt communication style dynamically.</p>
          </div>

          <div className="feature-card" style={{ transform: `translateY(${scrollY * 0.06}px)` }}>
            <div className="feature-icon"><Workflow size={32} /></div>
            <h3>Workflow Orchestration</h3>
            <p>Route invoices to finance, contracts to legal, leads to CRM, and tasks to teams automatically.</p>
          </div>

          <div className="feature-card" style={{ transform: `translateY(${scrollY * 0.07}px)` }}>
            <div className="feature-icon"><BarChart3 size={32} /></div>
            <h3>Operational Intelligence Dashboard</h3>
            <p>Track response latency, communication bottlenecks, thread risk, and opportunity signals in one view.</p>
          </div>

          <div className="feature-card" style={{ transform: `translateY(${scrollY * 0.05}px)` }}>
            <div className="feature-icon"><Users size={32} /></div>
            <h3>Adaptive Learning Engine</h3>
            <p>Bylix learns behavior patterns over time so routing, ranking, and drafting become increasingly precise.</p>
          </div>

          <div className="feature-card" style={{ transform: `translateY(${scrollY * 0.09}px)` }}>
            <div className="feature-icon"><Shield size={32} /></div>
            <h3>Enterprise-Grade Governance</h3>
            <p>Use policy controls, audit trails, and team-level visibility to keep communication secure and accountable.</p>
          </div>
        </div>
      </section>

      <section className="how-it-works">
        <div className="section-header">
          <h2>Built for Modern Email Operations</h2>
          <p>From overloaded inbox to structured execution in a few steps.</p>
        </div>

        <div className="steps-container">
          <div className="step">
            <div className="step-number">0</div>
            <div className="step-content">
              <h3>Choose Onboarding Path</h3>
              <p>Use your existing email account or create a new Bylix Email address instantly.</p>
              <div className="step-image">🛫</div>
            </div>
          </div>

          <div className="step-arrow"><ChevronDown size={24} /></div>

          <div className="step">
            <div className="step-number">1</div>
            <div className="step-content">
              <h3>Connect Communication Channels</h3>
              <p>Bring Gmail, Outlook, and team inboxes into one intelligence layer.</p>
              <div className="step-image">📧</div>
            </div>
          </div>

          <div className="step-arrow"><ChevronDown size={24} /></div>

          <div className="step">
            <div className="step-number">2</div>
            <div className="step-content">
              <h3>Define Operational Rules</h3>
              <p>Set routing and trigger logic for invoices, contracts, follow-ups, and approvals.</p>
              <div className="step-image">⚙️</div>
            </div>
          </div>

          <div className="step-arrow"><ChevronDown size={24} /></div>

          <div className="step">
            <div className="step-number">3</div>
            <div className="step-content">
              <h3>Activate Intelligence</h3>
              <p>Bylix prioritizes, drafts, and orchestrates communication-driven workflows automatically.</p>
              <div className="step-image">🤖</div>
            </div>
          </div>

          <div className="step-arrow"><ChevronDown size={24} /></div>

          <div className="step">
            <div className="step-number">4</div>
            <div className="step-content">
              <h3>Measure and Improve</h3>
              <p>Use analytics to reduce task leakage, speed decisions, and improve execution quality.</p>
              <div className="step-image">📊</div>
            </div>
          </div>
        </div>
      </section>

      <section id="pricing" className="pricing-section">
        <div className="section-header">
          <h2>Pricing for Operators and Teams</h2>
          <p>Start free, scale with intelligence, and move to enterprise orchestration when ready.</p>
        </div>

        <div className="pricing-grid">
          {plans.map((plan) => (
            <div key={plan.id} className={`pricing-card ${plan.highlighted ? 'highlighted' : ''}`}>
              {plan.highlighted && <div className="badge">Most Popular</div>}
              <div className="plan-header">
                <h3>{plan.name}</h3>
                <div className="plan-price">
                  {plan.price}
                  <span className="plan-period">{plan.period}</span>
                </div>
                <div className="plan-period">{plan.kes}</div>
                <p className="plan-description">{plan.description}</p>
              </div>

              <div className="plan-features">
                {plan.features.map((feature, idx) => (
                  <div key={idx} className="feature-item">
                    <Check size={20} className="feature-check" />
                    <span>{feature}</span>
                  </div>
                ))}
              </div>

              <button
                className={`btn ${plan.highlighted ? 'btn-primary' : 'btn-outline'} btn-full`}
                onClick={() => {
                  if (plan.id === 'enterprise') {
                    handleContactSales();
                  } else {
                    handleStartFreeTrial(plan.id);
                  }
                }}
              >
                {plan.cta}
              </button>

              {plan.price !== 'Custom' && <div className="plan-footer">Cancel anytime. Upgrade as your operations scale.</div>}
            </div>
          ))}
        </div>
      </section>

      <section id="demo" className="demo-section">
        <div className="section-header">
          <h2>See Bylix Email in Action</h2>
          <p>Watch how Bylix turns scattered communication into structured execution workflows.</p>
        </div>

        <div className="demo-video-container">
          <div className="demo-video-placeholder">
            <PlayCircle size={80} />
            <p>Video Demo - Click to play</p>
          </div>

          <div className="demo-highlights">
            <div className="highlight">
              <TrendingUp size={24} />
              <h4>Operational Intelligence</h4>
              <p>Track communication cost, value, and execution impact in real time.</p>
            </div>
            <div className="highlight">
              <MessageSquare size={24} />
              <h4>Adaptive Responses</h4>
              <p>Generate replies that align with context, tone, and relationship history.</p>
            </div>
            <div className="highlight">
              <Smartphone size={24} />
              <h4>Cross-Device Control</h4>
              <p>Run structured communication workflows across desktop and mobile.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="trust-section">
        <h2>Built for Teams That Run on Email</h2>
        <div className="companies-grid">
          <div className="company">🏢 Founders & Executives</div>
          <div className="company">🤝 Sales Teams</div>
          <div className="company">📈 Agencies & Consultants</div>
          <div className="company">⚙️ Operations Teams</div>
        </div>
      </section>

      <section className="cta-final">
        <h2>Bylix Email - Where Communication Becomes Execution.</h2>
        <p>Own your inbox with structure, clarity, and operational intelligence.</p>
        <button className="btn btn-primary btn-lg" onClick={() => handleStartFreeTrial('plus')}>
          Start Smarter Email
        </button>
      </section>

      <ContactSalesForm isOpen={showContactForm} onClose={() => setShowContactForm(false)} />

      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-section">
            <div className="logo">
              <div className="logo-icon">✉️</div>
              <div className="logo-text">Bylix Email</div>
            </div>
            <p>The AI-powered Email Intelligence Platform for modern teams.</p>
            <div className="social-links">
              <a href="#"><Twitter size={20} /></a>
              <a href="#"><Linkedin size={20} /></a>
              <a href="#"><Github size={20} /></a>
            </div>
          </div>

          <div className="footer-section">
            <h4>Product</h4>
            <a href="#" onClick={(e) => { e.preventDefault(); document.getElementById('features').scrollIntoView({ behavior: 'smooth' }); }}>Features</a>
            <a href="#" onClick={(e) => { e.preventDefault(); document.getElementById('pricing').scrollIntoView({ behavior: 'smooth' }); }}>Pricing</a>
            <span style={{ opacity: 0.6 }}>Security</span>
            <span style={{ opacity: 0.6 }}>Roadmap</span>
          </div>

          <div className="footer-section">
            <h4>Company</h4>
            <span style={{ opacity: 0.6 }}>About</span>
            <span style={{ opacity: 0.6 }}>Blog</span>
            <span style={{ opacity: 0.6 }}>Careers</span>
            <span style={{ opacity: 0.6 }}>Contact</span>
          </div>

          <div className="footer-section">
            <h4>Legal</h4>
            <span style={{ opacity: 0.6 }}>Privacy</span>
            <span style={{ opacity: 0.6 }}>Terms</span>
            <span style={{ opacity: 0.6 }}>Cookie Policy</span>
          </div>
        </div>

        <div className="footer-bottom">
          <p>&copy; 2026 Bylix Email. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
