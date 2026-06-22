import React, { useState } from 'react';
import { X, Zap, Lock, ArrowRight, Star, Check, AlertTriangle, Mail, Users, Workflow } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './PremiumPrompt.css';

export const PremiumPrompt = ({ 
  isOpen, 
  onClose, 
  limitType = 'credits', // 'credits', 'emails', 'contacts', 'workflows'
  currentUsage = 0,
  monthlyLimit = 0
}) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [selectedPlan] = useState('plus');
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);

  if (!isOpen || isSuperAdmin) return null;

  const limitMessages = {
    credits: {
      title: "You've Used Your AI Credits",
      description: "You’ve used your AI credits. Buy credits or upgrade to continue.",
      icon: Zap,
      color: 'from-yellow-400 to-orange-500'
    },
    emails: {
      title: "Email Limit Reached",
      description: "You've synced the maximum emails for your plan. Upgrade to manage more emails.",
      icon: Mail,
      color: 'from-blue-400 to-cyan-500'
    },
    contacts: {
      title: "Contact Limit Reached",
      description: "You've reached the maximum number of contacts. Upgrade to manage more relationships.",
      icon: Users,
      color: 'from-green-400 to-emerald-500'
    },
    workflows: {
      title: "Workflow Limit Reached",
      description: "You've reached the maximum number of automated workflows. Upgrade for more automation.",
      icon: Workflow,
      color: 'from-purple-400 to-pink-500'
    }
  };

  const message = limitMessages[limitType] || limitMessages.credits;
  const IconComponent = message.icon;

  // Non-blocking top banner for credits
  if (limitType === 'credits') {
    const percentage = monthlyLimit ? (currentUsage / monthlyLimit) * 100 : 100;
    return (
      <div className="premium-top-banner" role="status">
        <div className="banner-inner">
          <div className="banner-left">
            <IconComponent size={28} />
            <div className="banner-copy">
              <div className="banner-title">{percentage >= 100 ? "You've used all your credits!" : `${Math.round(percentage)}% of your AI credits used`}</div>
              <div className="banner-sub">{currentUsage} / {monthlyLimit} credits used</div>
            </div>
          </div>
          <div className="banner-actions">
            <button className="btn btn-primary" onClick={() => navigate('/billing/upgrade?plan=plus')}>Upgrade</button>
            <button className="btn btn-outline" onClick={() => onClose(limitType, true)} style={{ marginLeft: 8 }}>Dismiss</button>
          </div>
        </div>
      </div>
    );
  }

  // Modal fallback for other limit types
  return (
    <div className="premium-prompt-overlay">
      <div className="premium-prompt-modal">
        <button className="close-btn" onClick={() => onClose(limitType, false)}>
          <X size={24} />
        </button>

        <div className={`prompt-header bg-gradient-to-r ${message.color}`}>
          <IconComponent size={48} />
          <h2>{message.title}</h2>
        </div>

        <div className="prompt-content">
          <p className="prompt-description">{message.description}</p>

          <div className="upgrade-options">
            <div className="option-card">
              <div className="option-header">
                <h3>Plus Plan</h3>
                <span className="price">$12/mo</span>
              </div>
              <ul className="option-features">
                <li>
                  <Check size={16} />
                  <span>1,500 AI Credits/Month</span>
                </li>
                <li>
                  <Check size={16} />
                  <span>Up to 3 Email Accounts</span>
                </li>
                <li>
                  <Check size={16} />
                  <span>Advanced Workflows</span>
                </li>
                <li>
                  <Check size={16} />
                  <span>Email Analytics</span>
                </li>
              </ul>
              <button 
                className="btn btn-primary"
                onClick={() => navigate('/billing/upgrade?plan=plus')}
              >
                Upgrade to Plus
              </button>
            </div>

            <div className="option-card highlighted">
              <div className="popular-badge">Most Popular</div>
              <div className="option-header">
                <h3>Professional Plan</h3>
                <span className="price">$29/mo</span>
              </div>
              <ul className="option-features">
                <li>
                  <Check size={16} />
                  <span>5,000 AI Credits/Month</span>
                </li>
                <li>
                  <Check size={16} />
                  <span>Unlimited Email Accounts</span>
                </li>
                <li>
                  <Check size={16} />
                  <span>Unlimited Workflows</span>
                </li>
                <li>
                  <Check size={16} />
                  <span>Advanced Analytics</span>
                </li>
              </ul>
              <button 
                className="btn btn-primary"
                onClick={() => navigate('/billing/upgrade?plan=professional')}
              >
                Upgrade to Professional
              </button>
            </div>
          </div>

          <button 
            className="link-btn"
            onClick={() => navigate('/billing/upgrade?topup=1000')}
          >
            Buy 1,000 Credits ($4)
          </button>

          <button 
            className="link-btn"
            onClick={() => onClose(limitType, false)}
          >
            Maybe Later
          </button>
        </div>
      </div>
    </div>
  );
};

export const CreditWarningBanner = ({ 
  creditsUsed, 
  creditsLimit,
  onUpgradeClick 
}) => {
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  const percentage = creditsLimit ? (creditsUsed / creditsLimit) * 100 : 0;

  if (isSuperAdmin || percentage < 80) return null;

  return (
    <div className="credit-warning-banner">
      <div className="banner-content">
        <div className="banner-icon">
          <AlertTriangle size={20} />
        </div>
        <div className="banner-text">
          <p className="banner-title">
            {percentage >= 100 ? 
              "You've used all your credits!" : 
              `You're using ${percentage.toFixed(0)}% of your monthly credits`
            }
          </p>
          <p className="banner-subtitle">
            {creditsUsed} / {creditsLimit} credits used
          </p>
        </div>
        <button 
          className="banner-cta"
          onClick={onUpgradeClick}
        >
          Upgrade Now <ArrowRight size={16} />
        </button>
      </div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${Math.min(percentage, 100)}%` }}></div>
      </div>
    </div>
  );
};

export const SubscribeButton = ({ 
  variant = 'floating', // 'floating', 'inline', 'outline'
  onClick,
  showIcon = true,
  label = 'Upgrade to Premium'
}) => {
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  if (isSuperAdmin) return null;
  if (variant === 'floating') {
    return (
      <button 
        className="subscribe-button-floating"
        onClick={onClick}
        title={label}
      >
        <Star size={20} />
        <span>{label}</span>
      </button>
    );
  }

  if (variant === 'inline') {
    return (
      <button 
        className="subscribe-button-inline"
        onClick={onClick}
      >
        {showIcon && <Lock size={16} />}
        <span>{label}</span>
      </button>
    );
  }

  return (
    <button 
      className="subscribe-button-outline"
      onClick={onClick}
    >
      {showIcon && <Zap size={16} />}
      <span>{label}</span>
    </button>
  );
};

export const FeatureLockBanner = ({ 
  featureName,
  requiredPlan = 'plus',
  onUpgradeClick
}) => {
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  if (isSuperAdmin) return null;
  return (
    <div className="feature-lock-banner">
      <div className="lock-icon">
        <Lock size={32} />
      </div>
      <h3>Premium Feature</h3>
      <p>
        <strong>{featureName}</strong> is available in the <strong>{requiredPlan}</strong> plan and above.
      </p>
      <button 
        className="btn btn-primary"
        onClick={onUpgradeClick}
      >
        Upgrade Now <ArrowRight size={16} />
      </button>
    </div>
  );
};
