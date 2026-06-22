import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Star, Zap, TrendingUp } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './UpgradeButton.css';

/**
 * UpgradeButton Component
 * Reusable button for triggering upgrade/premium actions
 * Can be placed in headers, dashboards, modals, etc.
 */
export const UpgradeButton = ({ 
  variant = 'default', // 'default' | 'floating' | 'compact' | 'dashboard'
  onClick,
  showIcon = true,
  label = 'Upgrade to Premium',
  className = '',
  disabled = false
}) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  if (isSuperAdmin) return null;

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      navigate('/billing/upgrade');
    }
  };

  const baseClass = `upgrade-btn upgrade-btn-${variant}`;

  return (
    <button 
      className={`${baseClass} ${className}`}
      onClick={handleClick}
      disabled={disabled}
      title={label}
    >
      {showIcon && variant === 'default' && <Star size={16} />}
      {showIcon && variant === 'floating' && <Zap size={18} />}
      {showIcon && variant === 'dashboard' && <TrendingUp size={16} />}
      <span>{label}</span>
    </button>
  );
};

/**
 * UpgradePromptCard
 * Card component for displaying upgrade prompts in grids
 */
export const UpgradePromptCard = ({ 
  title,
  description,
  features = [],
  onUpgradeClick,
  icon: Icon = Star
}) => {
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  if (isSuperAdmin) return null;
  return (
    <div className="upgrade-prompt-card">
      <div className="card-header">
        <Icon className="card-icon" />
        <h3>{title}</h3>
      </div>
      
      <p className="card-description">{description}</p>
      
      {features.length > 0 && (
        <ul className="card-features">
          {features.map((feature, idx) => (
            <li key={idx}>
              <span className="check-mark">✓</span>
              {feature}
            </li>
          ))}
        </ul>
      )}
      
      <button 
        className="btn-upgrade"
        onClick={onUpgradeClick}
      >
        Get Started <Zap size={14} />
      </button>
    </div>
  );
};

/**
 * UpgradeAlert
 * Alert-style component for showing upgrade recommendations
 */
export const UpgradeAlert = ({ 
  message,
  detail,
  onDismiss,
  onUpgrade
}) => {
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  if (isSuperAdmin) return null;
  return (
    <div className="upgrade-alert">
      <div className="alert-content">
        <p className="alert-message">{message}</p>
        {detail && <p className="alert-detail">{detail}</p>}
      </div>
      <div className="alert-buttons">
        {onDismiss && (
          <button className="btn-dismiss" onClick={onDismiss}>
            Dismiss
          </button>
        )}
        <button className="btn-alert-upgrade" onClick={onUpgrade}>
          Upgrade Now
        </button>
      </div>
    </div>
  );
};

/**
 * PremiumBadge
 * Small badge to indicate premium features
 */
export const PremiumBadge = ({ 
  size = 'default', // 'small' | 'default' | 'large'
  label = 'Premium',
  onClick
}) => {
  return (
    <div 
      className={`premium-badge premium-badge-${size}`}
      onClick={onClick}
    >
      <Star size={size === 'small' ? 12 : 14} />
      {label}
    </div>
  );
};

/**
 * FeatureComparisionHint
 * Shows when a user tries to use a premium-only feature
 */
export const FeatureComparisonHint = ({ 
  featureName,
  currentPlan = 'personal',
  requiredPlan = 'plus',
  onViewPlans,
  onUpgrade
}) => {
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  if (isSuperAdmin) return null;
  const planUpgradeMap = {
    'personal': 'plus',
    'plus': 'professional',
    'professional': 'enterprise'
  };

  const upgradeRequired = planUpgradeMap[currentPlan] || requiredPlan;

  return (
    <div className="feature-comparison-hint">
      <div className="hint-icon">
        <Zap size={20} />
      </div>
      <div className="hint-text">
        <p className="hint-title">
          <strong>{featureName}</strong> requires {upgradeRequired.charAt(0).toUpperCase() + upgradeRequired.slice(1)} plan
        </p>
        <p className="hint-subtitle">
          You're on the {currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)} plan
        </p>
      </div>
      <div className="hint-buttons">
        {onViewPlans && (
          <button className="btn-hint-secondary" onClick={onViewPlans}>
            Compare Plans
          </button>
        )}
        <button className="btn-hint-primary" onClick={onUpgrade}>
          Upgrade
        </button>
      </div>
    </div>
  );
};
