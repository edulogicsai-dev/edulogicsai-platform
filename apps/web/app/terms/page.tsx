import React from 'react';

export const metadata = {
  title: 'Terms of Service - MCATai',
  description: 'Terms of Service for MCATai platform',
};

export default function TermsOfService() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12 text-zinc-300">
      <h1 className="text-3xl font-bold text-white mb-6">Terms of Service</h1>
      <p className="text-sm text-zinc-500 mb-8">
        Last updated: {new Date().toLocaleDateString()}
      </p>

      <section className="space-y-6 text-sm leading-relaxed">
        <div>
          <h2 className="text-lg font-semibold text-white mb-2">1. Acceptance of Terms</h2>
          <p>
            By accessing or using MCATai, you agree to be bound by these Terms of Service. If you do not agree, please do not use our services.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">2. Educational Disclaimer</h2>
          <p>
            MCATai provides AI-driven learning assistance for MCAT study preparation. The platform is designed as a study supplement and does not guarantee specific scores or admissions outcomes.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">3. User Accounts</h2>
          <p>
            You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">4. Intellectual Property</h2>
          <p>
            All platform content, graphics, and underlying code are the intellectual property of MCATai and may not be reproduced without prior written permission.
          </p>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-white mb-2">5. Modifications</h2>
          <p>
            We reserve the right to modify these terms at any time. Continued use of the service constitutes acceptance of updated terms.
          </p>
        </div>
      </section>
    </div>
  );
}
