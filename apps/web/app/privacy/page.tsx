import React from 'react';

export const metadata = {
  title: 'Privacy Policy - MCATai',
  description: 'Privacy Policy for MCATai platform',
};

export default function PrivacyPolicy() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12 text-zinc-300">
      <h1 className="text-3xl font-bold text-white mb-6">Privacy Policy</h1>
      <p className="text-sm text-zinc-500 mb-8">
        Last updated: {new Date().toLocaleDateString()}
      </p>

      <section className="space-y-6 text-sm leading-relaxed">
        <div>
          <h2 className="text-lg font-semibold text-white mb-2">1. Information We Collect</h2>
          <p>
            We collect personal information that you provide to us directly when creating an account, such as your email address and name. We also collect usage data when you interact with our MCAT preparation tools.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">2. How We Use Your Information</h2>
          <p>
            Your information is used to personalize your learning experience, maintain and improve our AI model interactions, process account management requests, and send service updates.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">3. Data Security</h2>
          <p>
            We implement industry-standard security measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">4. Third-Party Services</h2>
          <p>
            We utilize secure third-party services such as Supabase for authentication and database management, and Stripe for payment processing. We do not sell your personal data.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">5. Contact Us</h2>
          <p>
            If you have any questions regarding this Privacy Policy, please reach out via your account dashboard.
          </p>
        </div>
      </section>
    </div>
  );
}
