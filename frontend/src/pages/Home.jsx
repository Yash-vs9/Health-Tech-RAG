import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import FeatureCard from "../components/FeatureCard";
import TeamCard from "../components/TeamCard";

export default function Home() {
  return (
    <>
      <Navbar />

      <section className="hero">
        <div className="hero-content">
          <div className="hero-badge">AI-Powered Banking</div>
          <h1>Intelligent Financial<br />Document Analysis</h1>
          <p>
            Upload bank statements, financial reports, and transaction records.
            Get instant AI-powered insights, summaries, and answers to your banking queries.
          </p>
          <div className="hero-buttons">
            <Link to="/signup" className="btn-hero-primary">Start Free Trial</Link>
            <a href="#features" className="btn-hero-secondary">Learn More</a>
          </div>
          <div className="hero-stats">
            <div className="stat">
              <strong>10K+</strong>
              <span>Documents Analyzed</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <strong>99.2%</strong>
              <span>Accuracy Rate</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <strong>256-bit</strong>
              <span>Encryption</span>
            </div>
          </div>
        </div>
      </section>

      <section className="features" id="features">
        <div className="section-container">
          <div className="section-header">
            <span className="section-badge">Features</span>
            <h2>Smart Banking, Smarter Decisions</h2>
            <p>Everything you need to analyze and understand your financial documents</p>
          </div>

          <div className="feature-grid">
            <FeatureCard
              icon="upload"
              title="Secure Document Upload"
              description="Upload bank statements, PDFs, and financial reports with bank-grade encryption."
            />
            <FeatureCard
              icon="chat"
              title="AI Financial Assistant"
              description="Ask questions about your finances and get instant, accurate answers powered by AI."
            />
            <FeatureCard
              icon="search"
              title="Smart Transaction Search"
              description="Find specific transactions, patterns, and anomalies across all your documents."
            />
            <FeatureCard
              icon="shield"
              title="Enterprise Security"
              description="Your financial data is protected with AES-256 encryption and SOC 2 compliance."
            />
          </div>
        </div>
      </section>

      <section className="team" id="team">
        <div className="section-container">
          <div className="section-header">
            <span className="section-badge">Team</span>
            <h2>Built by Experts</h2>
            <p>The minds behind FinAssist AI</p>
          </div>

          <div className="team-grid">
            <TeamCard
              name="Anushka Barman"
              role="Frontend Developer"
            />
            
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-container">
          <div className="footer-brand">
            <div className="logo">
              <div className="logo-icon">FA</div>
              <span>FinAssist AI</span>
            </div>
            <p>AI-powered banking document analysis platform.</p>
          </div>
          <div className="footer-bottom">
            <p>&copy; 2026 FinAssist AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </>
  );
}
