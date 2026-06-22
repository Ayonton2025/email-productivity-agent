import React, { useState } from 'react';
import { X, Send, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { submitContactForm, getContactEmail } from '../../services/contactService';
import './ContactSalesForm.css';

const ContactSalesForm = ({ isOpen, onClose }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    message: '',
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const contactEmail = getContactEmail();

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setError('');
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      setError('Name is required');
      return false;
    }
    if (!formData.email.trim()) {
      setError('Email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }
    if (!formData.message.trim()) {
      setError('Message is required');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      await submitContactForm({
        ...formData,
        type: 'sales_inquiry',
      });
      
      setSuccess(true);
      setFormData({ name: '', email: '', company: '', message: '' });
      
      // Auto-close after 3 seconds
      setTimeout(() => {
        onClose();
        setSuccess(false);
      }, 3000);
    } catch (err) {
      setError('Failed to send message. Please try emailing us directly at ' + contactEmail);
      console.error('Contact form error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="contact-form-overlay">
      <div className="contact-form-modal">
        <div className="contact-form-header">
          <h2>Contact Our Sales Team</h2>
          <button
            onClick={onClose}
            className="close-btn"
            aria-label="Close"
          >
            <X size={24} />
          </button>
        </div>

        {success ? (
          <div className="contact-success">
            <CheckCircle size={48} className="success-icon" />
            <h3>Message Sent!</h3>
            <p>Thank you for reaching out. Our sales team will get back to you within 24 hours at {formData.email}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="contact-form">
            {error && (
              <div className="form-error">
                <AlertCircle size={20} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="name">Full Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="John Doe"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email Address *</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="john@example.com"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="company">Company Name</label>
              <input
                type="text"
                id="company"
                name="company"
                value={formData.company}
                onChange={handleInputChange}
                placeholder="Your Company"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="message">Message *</label>
              <textarea
                id="message"
                name="message"
                value={formData.message}
                onChange={handleInputChange}
                placeholder="Tell us about your needs and what you're looking for..."
                rows="5"
                disabled={loading}
              />
            </div>

            <div className="form-info">
              <p>We'll respond to your inquiry at {contactEmail}</p>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-full"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader size={20} className="spinner" />
                  Sending...
                </>
              ) : (
                <>
                  <Send size={20} />
                  Send Message
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ContactSalesForm;
