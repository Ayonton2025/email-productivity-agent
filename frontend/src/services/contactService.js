/**
 * Contact Service - Handles contact form submissions
 * Sends emails to configured support email address
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL || 'sales@bylix.email';

export const submitContactForm = async (data) => {
  try {
    const response = await fetch(`${API_BASE}/contact/send-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: data.name,
        email: data.email,
        company: data.company || '',
        message: data.message,
        type: data.type || 'sales_inquiry',
        recipients: [CONTACT_EMAIL],
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to send contact form');
    }

    return await response.json();
  } catch (error) {
    console.error('Contact form submission error:', error);
    // Fallback: Try to send via backend contact endpoint
    try {
      const fallbackResponse = await fetch(`${API_BASE}/contact`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: data.name,
          email: data.email,
          company: data.company || '',
          message: data.message,
          contact_type: data.type || 'sales_inquiry',
        }),
      });

      if (fallbackResponse.ok) {
        return await fallbackResponse.json();
      }
    } catch (fallbackError) {
      console.error('Fallback contact submission error:', fallbackError);
    }

    throw error;
  }
};

export const getContactEmail = () => CONTACT_EMAIL;
